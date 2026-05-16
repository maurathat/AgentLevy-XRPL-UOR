"""Dashboard state assembly + FastAPI routes.

Keeps dashboard concerns separate from the core inference protocol code in
:mod:`agentlevy.inference.server`.

Three pieces:

* :class:`EventLog` — append-only chronological event log. Each protocol step
  (request received, payment validated, cert minted, royalty dispatched,
  HCS anchored, cache hit) pushes a typed event with a monotonically
  increasing sequence number. The dashboard polls
  ``/api/events?since=<seq>`` and animates only the deltas.

* :class:`BalanceCache` — caches RLUSD + XRP balance reads from XRPL with
  a TTL so we don't hammer the public RPC every 500 ms. Balances refresh
  every ``BALANCE_TTL_SECONDS`` (default 5).

* ``register_dashboard_routes`` — wires ``/api/state``, ``/api/events``,
  ``/dashboard``, and static-asset routes onto the FastAPI app.

The state shape is documented inline in :func:`build_state`; the dashboard
HTML/JS lives at :mod:`agentlevy.inference.templates` and :mod:`...static`.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from xrpl.models.requests import AccountInfo, AccountLines

from agentlevy.inference.cert_store import (
    FULL_PRICE_RLUSD,
    HIT_PRICE_RLUSD,
)
from agentlevy.inference.payment import RLUSD_CURRENCY_HEX

if TYPE_CHECKING:
    from agentlevy.inference.server import InferenceServer


# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------

#: Kinds of events the protocol emits. Open set; new kinds can be added
#: without breaking dashboard contracts (the dashboard renders unknown kinds
#: as generic log entries).
EVENT_REQUEST_QUOTED = "request_quoted"            # 402 returned to an agent
EVENT_PAYMENT_VALIDATED = "payment_validated"      # XRPL primary payment confirmed
EVENT_CERT_MINTED = "cert_minted"                  # Server signed a new DerivationCert
EVENT_CACHE_HIT = "cache_hit"                      # Stored cert served to a second agent
EVENT_HCS_ANCHORED = "hcs_anchored"                # Hedera HCS topic message submitted
EVENT_ROYALTY_DISPATCHED = "royalty_dispatched"    # Server → model NFT owner payment
EVENT_UOR_MCPS_RECEIPT = "uor_mcps_receipt"        # Foundation MCPS receipt obtained


@dataclass
class Event:
    """A single dashboard-visible protocol event."""
    seq: int
    ts: str
    kind: str
    request_uor: Optional[str] = None
    actor: Optional[str] = None
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class EventLog:
    """Thread-safe append-only chronological event log."""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._lock = threading.RLock()
        self._next_seq = 1

    def push(
        self,
        kind: str,
        *,
        request_uor: Optional[str] = None,
        actor: Optional[str] = None,
        **payload: Any,
    ) -> Event:
        with self._lock:
            ev = Event(
                seq=self._next_seq,
                ts=datetime.now(timezone.utc).isoformat(),
                kind=kind,
                request_uor=request_uor,
                actor=actor,
                payload=payload,
            )
            self._events.append(ev)
            self._next_seq += 1
            return ev

    def since(self, seq: int) -> list[Event]:
        """Return all events with ``seq > since``. ``seq=0`` returns everything."""
        with self._lock:
            return [e for e in self._events if e.seq > seq]

    def all(self) -> list[Event]:
        with self._lock:
            return list(self._events)

    def latest_seq(self) -> int:
        with self._lock:
            return self._next_seq - 1


# ---------------------------------------------------------------------------
# Balance cache
# ---------------------------------------------------------------------------

BALANCE_TTL_SECONDS = 5.0


@dataclass
class WalletBalance:
    """RLUSD + XRP balances for one wallet, plus a timestamp."""
    address: str
    rlusd: Optional[str]   # None means trust line not established / lookup failed
    xrp: Optional[str]
    fetched_at: float      # monotonic seconds


class BalanceCache:
    """Caches XRPL balance reads with a TTL to avoid hammering RPC."""

    def __init__(self, server: "InferenceServer") -> None:
        self._server = server
        self._lock = threading.RLock()
        self._cache: dict[str, WalletBalance] = {}

    def get(self, address: str, *, force_refresh: bool = False) -> WalletBalance:
        with self._lock:
            entry = self._cache.get(address)
            if entry and not force_refresh:
                if (time.monotonic() - entry.fetched_at) < BALANCE_TTL_SECONDS:
                    return entry
        # Refresh outside the lock so we don't block other readers
        balance = self._fetch(address)
        with self._lock:
            self._cache[address] = balance
        return balance

    def _fetch(self, address: str) -> WalletBalance:
        client = self._server.xrpl_client
        rlusd_issuer = self._server.rlusd_config.issuer
        rlusd_str: Optional[str] = None
        xrp_str: Optional[str] = None
        try:
            info = client.request(
                AccountInfo(account=address, ledger_index="validated", strict=True)
            )
            if info.is_successful():
                drops = int(info.result["account_data"]["Balance"])
                # 1 XRP = 1,000,000 drops
                xrp_str = format(Decimal(drops) / Decimal(1_000_000), "f")
        except Exception:
            pass
        try:
            lines = client.request(AccountLines(account=address, ledger_index="validated"))
            if lines.is_successful():
                for ln in lines.result.get("lines", []):
                    if (
                        ln.get("currency") == RLUSD_CURRENCY_HEX
                        and ln.get("account") == rlusd_issuer
                    ):
                        rlusd_str = ln.get("balance")
                        break
        except Exception:
            pass
        return WalletBalance(
            address=address,
            rlusd=rlusd_str,
            xrp=xrp_str,
            fetched_at=time.monotonic(),
        )


# ---------------------------------------------------------------------------
# State assembly
# ---------------------------------------------------------------------------

def _actors_info(server: "InferenceServer") -> dict[str, dict]:
    """Build the actors panel: addresses + labels for the dashboard.

    Agent A and Agent B seeds live in env; if absent (e.g. server started
    standalone, not via demo runner), their slots are filled in lazily as
    payments arrive on the event log.
    """
    import os

    actors: dict[str, dict] = {
        "server": {
            "address": server.server_wallet.classic_address,
            "label": "Inference Server",
            "pubkey_hex": server.server_pubkey_hex[:16] + "…",
        },
        "model_owner": {
            "address": server.config.nft_config.owner_address,
            "label": server.config.nft_config.model_name
                     or "Model NFT Owner",
            "nft_id": server.config.nft_config.nftoken_id,
            "metadata_uri": server.config.nft_config.metadata_uri,
        },
    }

    from . import wallets
    for role in ("agent_a", "agent_b"):
        try:
            addr = wallets.get_address(role)
        except Exception:
            continue
        actors[role] = {
            "address": addr,
            "label": f"Agent {role[-1].upper()}",
        }
    return actors


def _attach_balances(actors: dict, balance_cache: BalanceCache) -> None:
    """Mutate the actors dict to include current cached balances."""
    for role, info in actors.items():
        addr = info.get("address")
        if not addr:
            continue
        bal = balance_cache.get(addr)
        info["balance_rlusd"] = bal.rlusd
        info["balance_xrp"] = bal.xrp


def _certs_info(server: "InferenceServer") -> list[dict]:
    """Snapshot of the cert store, suitable for the dashboard."""
    out = []
    for addr, entry in server.cert_store.all_entries():
        op = entry.cert.operation_description or {}
        meta = getattr(entry.cert, "_settlement_metadata", None)
        hcs = entry.cert.hcs_receipt
        out.append({
            "request_uor": addr,
            "cert_uor": entry.cert.content_address(),
            "output_address": entry.cert.output_address,
            "model": op.get("model"),
            "completion_preview": op.get("completion_preview", "")[:240],
            "hour_bucket": op.get("hour_bucket"),
            "seller_pubkey_short": (entry.cert.seller_pubkey or "")[:16] + "…",
            "hit_count": entry.hit_count,
            "stored_at": entry.stored_at.isoformat(),
            "settlement": {
                "primary_txid": getattr(meta, "xrpl_payment_txid", None),
                "royalty_txid": getattr(meta, "xrpl_royalty_txid", None),
                "uor_mcps_present": bool(getattr(meta, "uor_mcps_receipt", None)),
            },
            "hcs": ({
                "topic_id": hcs.topic_id,
                "sequence_number": hcs.sequence_number,
                "consensus_timestamp": (
                    str(hcs.consensus_timestamp) if hcs.consensus_timestamp else None
                ),
            } if hcs is not None else None),
        })
    return out


def _metrics(server: "InferenceServer", events: list[Event]) -> dict:
    """Aggregate metrics for the bottom panel."""
    misses = sum(1 for e in events if e.kind == EVENT_CERT_MINTED)
    hits = sum(1 for e in events if e.kind == EVENT_CACHE_HIT)
    royalty_total = Decimal(0)
    rlusd_volume = Decimal(0)
    for e in events:
        if e.kind == EVENT_PAYMENT_VALIDATED:
            try:
                rlusd_volume += Decimal(str(e.payload.get("amount", "0")))
            except Exception:
                pass
        elif e.kind == EVENT_ROYALTY_DISPATCHED:
            try:
                amt = Decimal(str(e.payload.get("amount", "0")))
                royalty_total += amt
                rlusd_volume += amt  # royalty payments are also RLUSD flow on-chain
            except Exception:
                pass
    total_inferences = misses + hits
    cache_hit_rate = (hits / total_inferences) if total_inferences else 0.0
    return {
        "total_inferences": total_inferences,
        "cache_misses": misses,
        "cache_hits": hits,
        "cache_hit_rate": round(cache_hit_rate, 3),
        "total_rlusd_volume": format(rlusd_volume, "f"),
        "total_royalty_paid": format(royalty_total, "f"),
        "anthropic_calls_made": misses,
        "anthropic_calls_saved_by_cache": hits,
        "full_price_rlusd": str(FULL_PRICE_RLUSD),
        "hit_price_rlusd": str(HIT_PRICE_RLUSD),
    }


def _standards_info() -> dict:
    """Static info about the standards stack underneath."""
    import os
    return {
        "vteai": {
            "name": "VTEAI",
            "long_name": "Verified Task Escrow + Attestation Interface",
            "status": "ERC draft (CC0, April 2026) — authored by Maura Clark",
        },
        "uor_addr_1": {
            "name": "UOR-ADDR-1",
            "long_name": "Universal Object Reference Address",
            "status": "Officially adopted by UOR Foundation — authored by Maura Clark, co-implemented with Alex Flom",
            "repo": "github.com/UOR-Foundation/uor-addr-1",
        },
        "prism": {
            "name": "Prism framework",
            "long_name": "UOR Foundation algebraic substrate (Rust)",
            "status": "uor-foundation-sdk on crates.io",
            "repo": "github.com/UOR-Foundation/UOR-Framework",
        },
        "uor_mcp_endpoint": os.environ.get("UOR_MCP_URL", "https://mcp.uor.foundation/mcp"),
    }


def _settlement_currency() -> str:
    """Whether this server is settling in XRP or RLUSD. Driven by the env flag."""
    import os
    xrp_mode = os.environ.get("INFERENCE_USE_XRP_FALLBACK", "false").lower() == "true"
    return "XRP" if xrp_mode else "RLUSD"


def build_state(
    server: "InferenceServer",
    balance_cache: BalanceCache,
    *,
    since_seq: int = 0,
) -> dict:
    """Build the full dashboard-state dict.

    Parameters
    ----------
    since_seq
        Only include events with ``seq > since_seq``. The dashboard
        passes its highest-seen seq to minimize bytes over the wire.
    """
    all_events = server.event_log.all()
    new_events = [e for e in all_events if e.seq > since_seq]
    actors = _actors_info(server)
    _attach_balances(actors, balance_cache)
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "currency": _settlement_currency(),
        "actors": actors,
        "certs": _certs_info(server),
        "events": [e.to_dict() for e in new_events],
        "latest_seq": server.event_log.latest_seq(),
        "metrics": _metrics(server, all_events),
        "standards": _standards_info(),
    }


# ---------------------------------------------------------------------------
# Route wiring
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_STATIC_DIR = Path(__file__).resolve().parent / "static"


def register_dashboard_routes(app: FastAPI, server: "InferenceServer") -> None:
    """Mount ``/api/state``, ``/api/events``, ``/dashboard``, ``/static`` on the app."""
    balance_cache = BalanceCache(server)

    @app.get("/api/state")
    def api_state(since: int = 0) -> JSONResponse:
        return JSONResponse(build_state(server, balance_cache, since_seq=since))

    @app.get("/api/events")
    def api_events(since: int = 0) -> JSONResponse:
        new = server.event_log.since(since)
        return JSONResponse({
            "latest_seq": server.event_log.latest_seq(),
            "events": [e.to_dict() for e in new],
        })

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> HTMLResponse:
        html_path = _TEMPLATES_DIR / "dashboard.html"
        if not html_path.exists():
            raise HTTPException(status_code=503, detail=f"dashboard not built: {html_path} missing")
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.get("/pitch", response_class=HTMLResponse)
    def pitch() -> HTMLResponse:
        """Scrollable pitch deck with the live dashboard embedded as section 1."""
        html_path = _TEMPLATES_DIR / "pitch.html"
        if not html_path.exists():
            raise HTTPException(status_code=503, detail=f"pitch deck not built: {html_path} missing")
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    # In-flight guard so a double key-tap doesn't spawn parallel batches.
    _demo_lock = threading.Lock()
    _demo_running = {"flag": False}

    DEMO_PROMPT = (
        "Summarize this TechCrunch article in three bullets: "
        "Acme Robotics raised a $120M Series B led by Andreessen Horowitz "
        "at a $1.2B valuation. The Boston-based humanoid warehouse robotics "
        "startup, founded by former Boston Dynamics engineers Sarah Chen and "
        "Marcus Rivera, claims a sub-0.1% drop rate on delicate inventory and "
        "has signed pilots with three Fortune 500 retailers. Commercial "
        "shipping begins Q3 2026."
    )

    @app.post("/demo/run")
    def demo_run(total: int = 1, request: Request = None) -> JSONResponse:
        """Fire a demo batch from the dashboard (keyboard shortcuts press '1' or '9').

        Runs entirely in a background thread so the HTTP response returns
        immediately. The thread instantiates demo agents using the same
        ``agent_from_env`` helper the CLI script uses, so the event stream
        and dashboard animations are identical to running the script.
        """
        if total < 1 or total > 25:
            raise HTTPException(status_code=400, detail="total must be between 1 and 25")

        with _demo_lock:
            if _demo_running["flag"]:
                return JSONResponse(
                    {"status": "rejected", "reason": "a batch is already running"},
                    status_code=409,
                )
            _demo_running["flag"] = True

        scheme = request.url.scheme if request else "http"
        netloc = request.url.netloc if request else "127.0.0.1:8765"
        server_url = f"{scheme}://{netloc}"

        def _run_batch() -> None:
            try:
                from .agent import agent_from_env
                agent_a = agent_from_env(role="a", server_url=server_url)
                agent_b = agent_from_env(role="b", server_url=server_url)
                agent_a.complete(DEMO_PROMPT)
                for i in range(1, total):
                    time.sleep(1.0)
                    a = agent_b if i % 2 == 1 else agent_a
                    a.complete(DEMO_PROMPT)
            except Exception:  # pragma: no cover — surfaced via server logs only
                import logging as _logging
                _logging.getLogger("agentlevy.inference.dashboard").exception(
                    "demo batch failed"
                )
            finally:
                with _demo_lock:
                    _demo_running["flag"] = False

        threading.Thread(target=_run_batch, daemon=True).start()
        return JSONResponse({"status": "started", "total": total})

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
