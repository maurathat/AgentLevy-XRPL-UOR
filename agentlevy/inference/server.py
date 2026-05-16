"""FastAPI inference server with x402 + content-addressed memoization.

Endpoints
---------

* ``POST /complete`` — request inference. Two states:

  - Without ``X-Payment`` header: returns HTTP 402 + JSON describing the
    request UOR address, the price (cache miss → full, hit → discount),
    the destination wallet, and the required memo. The agent uses this to
    construct an RLUSD ``Payment`` on XRPL.

  - With ``X-Payment: <txid>`` header: verifies the payment on-ledger
    matches the request, then either serves a cached :class:`DerivationCert`
    (hit) or runs Anthropic, builds + signs + anchors a new cert (miss).

* ``GET /cert/{uor_address}`` — retrieve a stored cert by request UOR address.
  Public read; no payment required. The cert itself is the audit artifact.

* ``GET /health`` — liveness probe.

State
-----

In-process :class:`CertStore`. Server is stateless across restarts; in
production back this with Redis / S3 / DynamoDB / etc. For May 16 demo,
in-process is intentional.

Async tail
----------

The server returns the response to the agent as soon as the primary payment
is verified and the cert is signed. Two slow paths fire-and-forget in the
background:

* **HCS anchor** — submits the cert's address to the Hedera topic. Mock by
  default (``MOCK_HEDERA=true``); live with override.
* **Royalty dispatch** — sends a second RLUSD Payment to the model NFT
  owner. Failures are logged, never raised at the response boundary.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from anthropic import Anthropic
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet

from agentlevy.inference.canonical import (
    build_request_dict,
    compute_request_address,
)
from agentlevy.inference.cert_store import (
    CertStore,
    FULL_PRICE_RLUSD,
    HIT_PRICE_RLUSD,
    price_for,
)
from agentlevy.inference.dashboard import (
    EVENT_CACHE_HIT,
    EVENT_CERT_MINTED,
    EVENT_HCS_ANCHORED,
    EVENT_PAYMENT_VALIDATED,
    EVENT_REQUEST_QUOTED,
    EVENT_ROYALTY_DISPATCHED,
    EVENT_UOR_MCPS_RECEIPT,
    EventLog,
    register_dashboard_routes,
)
from agentlevy.inference.mcp_client import EncodeAddressResult, UORMCPClient
from agentlevy.inference.nft import ModelNFTConfig, lookup_royalty_recipient
from agentlevy.inference.payment import (
    RLUSDConfig,
    _xrp_fallback_enabled,
    verify_rlusd_payment,
)
from agentlevy.inference.receipt import (
    SettlementMetadata,
    attach_settlement_metadata,
    build_inference_cert,
    compute_completion_address,
)
from agentlevy.inference.royalty import (
    compute_split,
    dispatch_royalty,
)
from agentlevy.primitives.signing import Keypair, public_key_hex


logger = logging.getLogger("agentlevy.inference.server")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class ServerConfig:
    """Inference server configuration loaded from environment.

    All fields are required unless noted. See ``.env.example`` for the
    canonical list with descriptions.
    """
    xrpl_rpc_url: str
    server_xrpl_seed: str
    server_ed25519_seed_hex: str   # 64 hex chars (32 bytes)
    anthropic_api_key: str
    rlusd_issuer: str
    nft_config: ModelNFTConfig
    default_model: str = "claude-haiku-4-5"
    royalty_enabled: bool = True
    use_live_uor_mcp: bool = False   # gate for the optional Foundation MCP receipt
    hcs_anchor_enabled: bool = True  # set MOCK_HEDERA in env to skip live anchor
    cert_store_mirror_path: str = "/tmp/agentlevy_certs.json"

    @classmethod
    def from_env(cls) -> "ServerConfig":
        def _need(name: str) -> str:
            v = os.environ.get(name, "").strip()
            if not v:
                raise RuntimeError(f"{name} not set in environment")
            return v

        from . import wallets
        return cls(
            xrpl_rpc_url=wallets.rpc_url(),
            server_xrpl_seed=wallets.get_seed("server"),
            server_ed25519_seed_hex=_need("INFERENCE_SERVER_ED25519_SEED_HEX"),
            anthropic_api_key=_need("ANTHROPIC_API_KEY"),
            rlusd_issuer=wallets.rlusd_issuer(),
            nft_config=ModelNFTConfig.from_env(),
            default_model=os.environ.get("INFERENCE_DEFAULT_MODEL", "claude-haiku-4-5"),
            royalty_enabled=os.environ.get("INFERENCE_ROYALTY_ENABLED", "true").lower() != "false",
            use_live_uor_mcp=os.environ.get("INFERENCE_USE_LIVE_UOR_MCP", "false").lower() == "true",
            hcs_anchor_enabled=os.environ.get("INFERENCE_HCS_ANCHOR_ENABLED", "true").lower() != "false",
            cert_store_mirror_path=os.environ.get(
                "AGENTLEVY_CERT_STORE_PATH", "/tmp/agentlevy_certs.json"
            ),
        )


# ---------------------------------------------------------------------------
# Wire models
# ---------------------------------------------------------------------------

class CompleteRequest(BaseModel):
    """Body for ``POST /complete``."""
    prompt: str = Field(..., min_length=1, max_length=8000)
    model: Optional[str] = None
    temperature: int | float = 0
    max_tokens: int = Field(default=400, ge=1, le=4096)


class PriceQuote(BaseModel):
    """The 402 response body.

    Field ``price_rlusd`` is named for legacy compatibility with early callers
    but actually carries the numeric price in whichever currency the server is
    configured to settle in. Read ``currency`` to know the unit. ``currency``
    is ``"XRP"`` when ``INFERENCE_USE_XRP_FALLBACK=true`` and ``"RLUSD"``
    otherwise.
    """
    error: str = "Payment Required"
    request_uor_address: str
    price_rlusd: str
    currency: str = "RLUSD"
    currency_hex: Optional[str] = None
    issuer: Optional[str] = None
    destination: str
    memo_type: str = "uor-addr-1"
    memo_required_address: str
    is_cache_hit: bool
    uor_mcps_receipt: Optional[dict] = None


class CompletionResponse(BaseModel):
    """The 200 response body after payment + (cache-miss) inference."""
    completion: str
    request_uor_address: str
    cert: dict
    settlement: dict
    is_cache_hit: bool


# ---------------------------------------------------------------------------
# Server logic
# ---------------------------------------------------------------------------

class InferenceServer:
    """The stateful inference service. One instance per process."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.cert_store = CertStore()
        self.xrpl_client = JsonRpcClient(config.xrpl_rpc_url)
        from . import wallets as _wallets
        self.server_wallet = _wallets.get_wallet("server")
        ed_seed = bytes.fromhex(config.server_ed25519_seed_hex)
        self.server_keypair = Keypair.from_seed(ed_seed)
        self.server_pubkey_hex = public_key_hex(self.server_keypair)
        self.anthropic = Anthropic(api_key=config.anthropic_api_key)
        self.rlusd_config = RLUSDConfig(issuer=config.rlusd_issuer)
        self.event_log = EventLog()

    # --- helpers ---

    def model_for(self, requested: Optional[str]) -> str:
        return requested or self.config.default_model

    def _maybe_fetch_uor_mcps_receipt(self, request: dict) -> Optional[dict]:
        """If enabled, round-trip the request through the Foundation MCP to
        obtain a signed receipt that the address we computed matches the
        canonical computation. Returns the raw MCPS receipt dict or None.

        Skipped silently on any error — this is enrichment, not load-bearing.
        """
        if not self.config.use_live_uor_mcp:
            return None
        try:
            with UORMCPClient() as cli:
                result: EncodeAddressResult = cli.encode_address(request)
            if result.mcps_receipt is None:
                return None
            return result.mcps_receipt.raw
        except Exception as exc:
            logger.warning("UOR MCP enrichment failed (continuing): %s", exc)
            return None

    # --- handlers ---

    def handle_complete(
        self,
        body: CompleteRequest,
        x_payment_txid: Optional[str],
    ) -> tuple[int, dict]:
        """Process a ``POST /complete``. Returns ``(status_code, body)``.

        Used by the FastAPI route handler.
        """
        # 1. Canonicalize the request → derive UOR address
        model = self.model_for(body.model)
        request_dict = build_request_dict(
            model=model,
            prompt=body.prompt,
            temperature=body.temperature,
        )
        request_addr = compute_request_address(request_dict)

        # 2. Cache check (peek = no side effect; we may not actually serve a hit)
        cached = self.cert_store.peek(request_addr)
        is_hit = cached is not None

        # 3. No payment yet → 402 with price quote
        if not x_payment_txid:
            mcps_receipt = self._maybe_fetch_uor_mcps_receipt(dict(request_dict))
            # When XRP fallback is on, settlement is native XRP — quote reports
            # currency="XRP" and omits issuer/currency_hex so the agent doesn't
            # try to build an IssuedCurrencyAmount.
            xrp_mode = _xrp_fallback_enabled()
            quote = PriceQuote(
                request_uor_address=request_addr,
                price_rlusd=str(price_for(is_hit=is_hit)),
                currency="XRP" if xrp_mode else "RLUSD",
                currency_hex=None if xrp_mode else self.rlusd_config.currency_hex,
                issuer=None if xrp_mode else self.rlusd_config.issuer,
                destination=self.server_wallet.classic_address,
                memo_required_address=request_addr,
                is_cache_hit=is_hit,
                uor_mcps_receipt=mcps_receipt,
            )
            self.event_log.push(
                EVENT_REQUEST_QUOTED,
                request_uor=request_addr,
                price=str(price_for(is_hit=is_hit)),
                is_cache_hit=is_hit,
                # Prompt is included so the dashboard banner can display the
                # actual question being asked. Truncated to keep payload small.
                prompt=body.prompt[:280],
                model=model,
            )
            if mcps_receipt is not None:
                self.event_log.push(
                    EVENT_UOR_MCPS_RECEIPT,
                    request_uor=request_addr,
                    trust_level=mcps_receipt.get("trust_level", "?"),
                    public_key=mcps_receipt.get("public_key", "")[:32],
                )
            return 402, quote.model_dump()

        # 4. Verify the payment
        verification = verify_rlusd_payment(
            self.xrpl_client,
            txid=x_payment_txid,
            expected_from=None,  # any payer
            expected_to=self.server_wallet.classic_address,
            expected_amount=price_for(is_hit=is_hit),
            expected_uor_memo_address=request_addr,
            config=self.rlusd_config,
        )
        if not verification.valid:
            return 402, {
                "error": "Payment verification failed",
                "reason": verification.reason,
                "txid": x_payment_txid,
                "request_uor_address": request_addr,
            }

        # Primary payment validated
        self.event_log.push(
            EVENT_PAYMENT_VALIDATED,
            request_uor=request_addr,
            actor=verification.from_address,
            txid=x_payment_txid,
            amount=verification.amount_value or str(price_for(is_hit=is_hit)),
            destination=verification.to_address,
        )

        # 5. Cache HIT — serve the stored cert
        if is_hit:
            entry = self.cert_store.get(request_addr)  # increments hit_count
            assert entry is not None
            self.event_log.push(
                EVENT_CACHE_HIT,
                request_uor=request_addr,
                actor=verification.from_address,
                cert_uor=entry.cert.content_address(),
                hit_count=entry.hit_count,
            )
            self._dump_mirror()
            self._dispatch_royalty_best_effort(
                request_addr=request_addr,
                total_paid=price_for(is_hit=True),
            )
            return 200, self._render_completion(
                completion_text=entry.completion_text,
                cert=entry.cert,
                request_addr=request_addr,
                xrpl_payment_txid=x_payment_txid,
                is_cache_hit=True,
            )

        # 6. Cache MISS — run inference, build + sign + (best-effort) anchor cert
        completion_text = self._run_inference(model=model, body=body)
        cert = build_inference_cert(
            request=request_dict,
            completion_text=completion_text,
            server_pubkey_hex=self.server_pubkey_hex,
            request_address=request_addr,
            completion_address=compute_completion_address(completion_text),
        )
        cert.sign(self.server_keypair)
        self.event_log.push(
            EVENT_CERT_MINTED,
            request_uor=request_addr,
            cert_uor=cert.content_address(),
            output_addr=cert.output_address,
            model=cert.operation_description.get("model"),
        )
        if self.config.hcs_anchor_enabled:
            try:
                cert.anchor()
                if cert.hcs_receipt:
                    self.event_log.push(
                        EVENT_HCS_ANCHORED,
                        request_uor=request_addr,
                        topic_id=cert.hcs_receipt.topic_id,
                        sequence_number=cert.hcs_receipt.sequence_number,
                        consensus_timestamp=(
                            str(cert.hcs_receipt.consensus_timestamp)
                            if cert.hcs_receipt.consensus_timestamp else None
                        ),
                    )
            except Exception as exc:
                logger.warning("HCS anchor failed (continuing): %s", exc)

        # Store; tolerate the race where another agent stored concurrently
        try:
            self.cert_store.put(request_addr, cert, completion_text)
        except ValueError:
            existing = self.cert_store.peek(request_addr)
            if existing is not None:
                cert = existing.cert
                completion_text = existing.completion_text
        self._dump_mirror()

        # Attach UOR MCPS receipt if enabled (best-effort)
        mcps_receipt_raw = self._maybe_fetch_uor_mcps_receipt(dict(request_dict))
        meta = SettlementMetadata(
            xrpl_payment_txid=x_payment_txid,
            uor_mcps_receipt=mcps_receipt_raw,
        )
        attach_settlement_metadata(cert, meta)

        self._dispatch_royalty_best_effort(
            request_addr=request_addr,
            total_paid=price_for(is_hit=False),
        )

        return 200, self._render_completion(
            completion_text=completion_text,
            cert=cert,
            request_addr=request_addr,
            xrpl_payment_txid=x_payment_txid,
            is_cache_hit=False,
        )

    # --- mirror dump for MCP server ---

    def _dump_mirror(self) -> None:
        """Write the cert store to a JSON file so the MCP server subprocess
        can read it. Atomic via write-then-rename. Best-effort; errors logged."""
        try:
            entries: dict[str, dict] = {}
            for addr, entry in self.cert_store.all_entries():
                entries[addr] = {
                    "cert": entry.cert.model_dump(mode="json"),
                    "completion_text": entry.completion_text,
                    "stored_at": entry.stored_at.isoformat(),
                    "hit_count": entry.hit_count,
                }
            data = {"entries": entries}
            tmp_path = self.config.cert_store_mirror_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
            os.replace(tmp_path, self.config.cert_store_mirror_path)
        except Exception as exc:
            logger.warning("cert store mirror dump failed: %s", exc)

    # --- inference ---

    def _run_inference(self, model: str, body: CompleteRequest) -> str:
        """Call Anthropic, return the completion text."""
        msg = self.anthropic.messages.create(
            model=model,
            max_tokens=body.max_tokens,
            temperature=float(body.temperature),
            messages=[{"role": "user", "content": body.prompt}],
        )
        parts = [b.text for b in msg.content if getattr(b, "type", "") == "text"]
        return "".join(parts) or ""

    # --- royalty ---

    def _dispatch_royalty_best_effort(
        self,
        *,
        request_addr: str,
        total_paid: Decimal,
    ) -> None:
        """Run royalty dispatch in a background task. Logs failures, never raises."""
        if not self.config.royalty_enabled:
            return
        split = compute_split(total_paid)
        try:
            recipient = lookup_royalty_recipient(
                config=self.config.nft_config,
                verify_live=False,
            )
        except Exception as exc:
            logger.warning("royalty lookup failed: %s", exc)
            return

        # Fire-and-forget — we hand back the response while this runs.
        t = threading.Thread(
            target=self._do_royalty,
            args=(recipient, split.royalty_share, request_addr),
            daemon=True,
            name=f"royalty-{request_addr[7:15]}",
        )
        t.start()

    def _do_royalty(self, recipient: str, amount: Decimal, request_addr: str) -> None:
        try:
            result = dispatch_royalty(
                self.xrpl_client,
                server_wallet=self.server_wallet,
                recipient_address=recipient,
                royalty_amount=amount,
                uor_memo_address=request_addr,
                config=self.rlusd_config,
            )
            if result.succeeded:
                logger.info("royalty %s RLUSD → %s tx=%s", amount, recipient, result.txid)
                self.event_log.push(
                    EVENT_ROYALTY_DISPATCHED,
                    request_uor=request_addr,
                    actor=recipient,
                    amount=format(amount, "f"),
                    txid=result.txid,
                )
            else:
                logger.warning(
                    "royalty dispatch did not succeed: skipped=%s payment=%s",
                    result.skipped_reason, result.payment_result,
                )
        except Exception as exc:
            logger.warning("royalty dispatch raised: %s", exc)

    # --- response shaping ---

    def _render_completion(
        self,
        *,
        completion_text: str,
        cert,  # DerivationCert
        request_addr: str,
        xrpl_payment_txid: str,
        is_cache_hit: bool,
    ) -> dict:
        cert_dict = cert.model_dump(mode="json")
        # The DerivationCert.hcs_receipt field already serializes via model_dump.
        return CompletionResponse(
            completion=completion_text,
            request_uor_address=request_addr,
            cert=cert_dict,
            settlement={
                "xrpl_payment_txid": xrpl_payment_txid,
                "xrpl_royalty_txid": None,  # async — see /cert/<addr> for final
                "uor_mcps_receipt_present": (
                    getattr(cert, "_settlement_metadata", None) is not None
                    and getattr(cert, "_settlement_metadata").uor_mcps_receipt is not None
                ),
                "model_nft_id": self.config.nft_config.nftoken_id,
            },
            is_cache_hit=is_cache_hit,
        ).model_dump()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

def create_app(server: Optional[InferenceServer] = None) -> FastAPI:
    """Build the FastAPI app bound to an :class:`InferenceServer`.

    When no server is provided, we instantiate one from env. Load ``.env``
    first so the app starts cleanly under uvicorn / nohup / any launcher that
    doesn't already populate ``os.environ`` for us.
    """
    if server is None:
        try:
            from dotenv import load_dotenv as _load_dotenv
            from pathlib import Path as _Path
            # Find .env: prefer the symlinked one in the cwd-style location,
            # fall back to the canonical main-checkout .env.
            for candidate in (
                _Path.cwd() / ".env",
                _Path(__file__).resolve().parent.parent.parent / ".env",
                _Path("/Users/mauraclark/AgentLevy-XRPL-UOR/.env"),
            ):
                if candidate.exists():
                    # override=True so the .env file is authoritative even if
                    # the shell has blank/legacy values set (we hit this with
                    # an empty ANTHROPIC_API_KEY exported by an rc file).
                    _load_dotenv(candidate, override=True)
                    break
        except Exception:
            pass  # If dotenv isn't available, just trust os.environ.
        server = InferenceServer(ServerConfig.from_env())

    app = FastAPI(title="AgentLevy Inference", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {
            "ok": True,
            "server_wallet": server.server_wallet.classic_address,
            "server_pubkey": server.server_pubkey_hex,
            "model_nft_id": server.config.nft_config.nftoken_id,
            "cache_size": server.cert_store.size(),
            "total_hits": server.cert_store.total_hits(),
        }

    # NB: sync route handler (not async). FastAPI dispatches sync routes to a
    # thread pool, which keeps xrpl-py's sync JsonRpcClient — which internally
    # calls asyncio.run() for HTTP — from colliding with FastAPI's own event
    # loop. Async + xrpl-py-sync = "asyncio.run() cannot be called from a
    # running event loop" at verify time.
    @app.post("/complete")
    def complete(
        body: CompleteRequest,
        request: Request,
        x_payment: Optional[str] = Header(default=None, alias="X-Payment"),
    ):
        t0 = time.time()
        try:
            status, payload = server.handle_complete(body, x_payment)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("handle_complete failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        elapsed_ms = int((time.time() - t0) * 1000)
        headers = {
            "X-Request-UOR-Addr": payload.get("request_uor_address") or "",
            "X-Cache-Status": "HIT" if payload.get("is_cache_hit") else "MISS",
            "X-Elapsed-Ms": str(elapsed_ms),
        }
        return JSONResponse(status_code=status, content=payload, headers=headers)

    @app.get("/cert/{uor_address}")
    def get_cert(uor_address: str) -> dict:
        entry = server.cert_store.peek(uor_address)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"no cert at {uor_address}")
        return {
            "request_uor_address": uor_address,
            "cert": entry.cert.model_dump(mode="json"),
            "stored_at": entry.stored_at.isoformat(),
            "hit_count": entry.hit_count,
        }

    register_dashboard_routes(app, server)
    return app
