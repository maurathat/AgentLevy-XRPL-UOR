"""AgentLevy MCP server — expose inference audit trail to any MCP-capable agent.

Tools exposed (intentionally read-only for the May 16 demo)
------------------------------------------------------------

* ``inference_status()`` — server health, model NFT id, cache size, total hits.
* ``inference_quote(prompt, model, temperature)`` — compute the request UOR
  address and price tier (cache hit vs miss) **without** running the inference
  or charging anything. Lets agents discover whether the answer is cached.
* ``verify_cert(request_uor_address)`` — fetch a stored cert by request UOR
  address; recompute the address from the stored body; verify the server
  signature; return the verification report. **No payment required** — the
  cert chain is public audit data, exactly as the deck Slide 10 claims.
* ``lookup_royalty_recipient()`` — return the model NFT id and the XRPL
  address that receives per-inference royalties.

Why read-only
-------------

The hot path (running inference + accepting payment) lives on the HTTP API
because x402 over HTTP is the canonical wire format for agent-to-service
payments. The MCP surface is the *audit + discovery* layer: it lets agents
discover what work has been done, by which model, with what provenance,
without spending money to find out.

This matches the strongest claim from the deck Slide 11:
*"cross-agent memory sharing — an agent referencing another agent's prior
work cites by content address, not by API. The reference resolves whether
the original agent still exists or not."* The MCP server is how the agent
*does the referencing*.

Adding the MCP server to Claude Desktop / Cursor
------------------------------------------------

The MCP server runs as a subprocess started by the MCP host (Claude Desktop)
via stdio transport. Configure it by adding to ``~/.config/claude/mcp.json``::

    {
      "mcpServers": {
        "agentlevy": {
          "command": "python",
          "args": ["-m", "agentlevy.inference.mcp_server"]
        }
      }
    }

Once added, the four tools above appear in the host's tool palette and the
agent can call them natively.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from agentlevy.inference.canonical import (
    build_request_dict,
    compute_request_address,
)
from agentlevy.inference.cert_store import (
    HIT_PRICE_RLUSD,
    FULL_PRICE_RLUSD,
)
from agentlevy.inference.nft import ModelNFTConfig
from agentlevy.primitives.cert import DerivationCert
from agentlevy.primitives.signing import verify
from agentlevy.primitives.canonical import to_canonical_bytes


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class MCPServerState:
    """Shared state between the MCP tools.

    For the demo, the MCP server reads cert data from a JSON file that the
    HTTP server periodically dumps (no IPC complexity). In production, the
    MCP server and HTTP server share a backing K/V store (Redis / DynamoDB).
    """

    def __init__(
        self,
        cert_store_path: Optional[str] = None,
        nft_config: Optional[ModelNFTConfig] = None,
    ) -> None:
        self.cert_store_path = cert_store_path or os.environ.get(
            "AGENTLEVY_CERT_STORE_PATH", "/tmp/agentlevy_certs.json"
        )
        try:
            self.nft_config = nft_config or ModelNFTConfig.from_env()
        except RuntimeError:
            self.nft_config = None  # not configured yet; tools degrade gracefully

    def load_cert(self, request_uor_address: str) -> Optional[dict]:
        """Look up a stored cert in the local mirror file."""
        import json
        try:
            with open(self.cert_store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None
        entries = data.get("entries", {})
        return entries.get(request_uor_address)


_state = MCPServerState()


# ---------------------------------------------------------------------------
# Tools (importable plain functions; the MCP wiring is at the bottom)
# ---------------------------------------------------------------------------

def inference_status() -> dict:
    """Return server health + model NFT id + cache stats from the mirror file."""
    import json
    try:
        with open(_state.cert_store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        cache_size = 0
        total_hits = 0
    else:
        cache_size = len(data.get("entries", {}))
        total_hits = sum(e.get("hit_count", 0) for e in data.get("entries", {}).values())
    return {
        "service": "agentlevy-inference",
        "model_nft_id": _state.nft_config.nftoken_id if _state.nft_config else None,
        "model_nft_owner": _state.nft_config.owner_address if _state.nft_config else None,
        "model_name": _state.nft_config.model_name if _state.nft_config else None,
        "cache_size": cache_size,
        "total_hits": total_hits,
        "full_price_rlusd": str(FULL_PRICE_RLUSD),
        "hit_price_rlusd": str(HIT_PRICE_RLUSD),
    }


def inference_quote(
    prompt: str,
    model: str = "claude-haiku-4-5",
    temperature: int | float = 0,
) -> dict:
    """Compute the UOR address and price tier for a hypothetical inference.

    Does **not** run the inference; does **not** charge anything; does **not**
    require a wallet. Lets agents probe whether their question is cached
    before deciding to pay.
    """
    request = build_request_dict(model=model, prompt=prompt, temperature=temperature)
    addr = compute_request_address(request)
    cached = _state.load_cert(addr) is not None
    return {
        "request_uor_address": addr,
        "is_cache_hit": cached,
        "price_rlusd": str(HIT_PRICE_RLUSD if cached else FULL_PRICE_RLUSD),
        "currency": "RLUSD",
        "model": model,
        "hour_bucket": request["hour_bucket"],
        "note": (
            "This is a price quote, not a payment. To proceed, POST /complete "
            "on the HTTP API to receive a 402 + payment instructions."
        ),
    }


def verify_cert(request_uor_address: str) -> dict:
    """Fetch a cert by request UOR address and verify its signature.

    Returns a structured report with the cert payload, the recomputed address
    (which must match the lookup key), and the boolean signature validity.
    """
    raw = _state.load_cert(request_uor_address)
    if raw is None:
        return {
            "found": False,
            "request_uor_address": request_uor_address,
            "reason": "no cert at this address",
        }

    try:
        cert = DerivationCert.model_validate(raw["cert"])
    except Exception as exc:
        return {
            "found": True,
            "valid": False,
            "request_uor_address": request_uor_address,
            "reason": f"cert payload could not be parsed: {exc}",
            "cert_raw": raw,
        }

    sig_ok = cert.verify_signature()
    addr_matches = cert.task_spec_address == request_uor_address
    return {
        "found": True,
        "valid": sig_ok and addr_matches,
        "signature_valid": sig_ok,
        "task_spec_address_matches": addr_matches,
        "request_uor_address": request_uor_address,
        "cert": cert.model_dump(mode="json"),
        "hit_count": raw.get("hit_count", 0),
        "stored_at": raw.get("stored_at"),
        "completion_preview": cert.operation_description.get("completion_preview", ""),
    }


def lookup_royalty_recipient() -> dict:
    """Return the model NFT id, owner, and metadata URI.

    The owner address is the wallet that receives per-inference royalties.
    Anyone can verify the NFT exists and is held by this wallet via the
    XRPL Testnet explorer: ``https://testnet.xrpl.org/nft/<nft_id>``.
    """
    if _state.nft_config is None:
        return {
            "configured": False,
            "reason": "MODEL_NFT_* env not set; run scripts/mint_model_nft.py",
        }
    cfg = _state.nft_config
    return {
        "configured": True,
        "model_nft_id": cfg.nftoken_id,
        "owner_address": cfg.owner_address,
        "metadata_uri": cfg.metadata_uri,
        "model_name": cfg.model_name,
        "explorer_url": f"https://testnet.xrpl.org/nft/{cfg.nftoken_id}",
    }


# ---------------------------------------------------------------------------
# MCP wiring (FastMCP)
# ---------------------------------------------------------------------------

def build_mcp_app():
    """Build the FastMCP application. Imported here so the module imports
    cleanly even when ``mcp`` isn't installed."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("agentlevy-inference")

    @mcp.tool()
    def status() -> dict:
        """AgentLevy inference: status, model NFT, cache stats, prices."""
        return inference_status()

    @mcp.tool()
    def quote(prompt: str, model: str = "claude-haiku-4-5", temperature: int | float = 0) -> dict:
        """Quote the UOR address and price for a hypothetical inference request — no charge."""
        return inference_quote(prompt, model, temperature)

    @mcp.tool()
    def cert(request_uor_address: str) -> dict:
        """Verify an inference cert by its request UOR address."""
        return verify_cert(request_uor_address)

    @mcp.tool()
    def royalty_recipient() -> dict:
        """Look up the model NFT's owner — the royalty recipient for inferences."""
        return lookup_royalty_recipient()

    return mcp


def main() -> None:
    """Entry point for ``python -m agentlevy.inference.mcp_server``."""
    app = build_mcp_app()
    app.run()


if __name__ == "__main__":
    main()
