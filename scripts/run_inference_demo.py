"""Demo orchestrator — the May 16 stage script.

What it does
------------

1. Loads ``.env`` and validates required config (XRPL endpoint, wallet seeds,
   RLUSD issuer, NFT id).
2. Confirms agent A, agent B, and the server wallet are funded.
3. Starts the FastAPI inference server in a background thread (uvicorn).
4. Runs **agent A** → cache miss → server runs Anthropic inference → cert
   signed + anchored + royalty dispatched.
5. Runs **agent B** asking the same question → cache hit → server returns
   the stored cert at 10× discount.
6. Prints the audit trail summary: XRPL Payment txids, Hedera HCS sequence
   (if live), UOR Foundation MCPS receipt fingerprint (if enabled), model
   NFT id.

Usage
-----

::

    python scripts/run_inference_demo.py
    python scripts/run_inference_demo.py --prompt "summarize HN today"
    python scripts/run_inference_demo.py --port 8765 --skip-server-startup
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402
import uvicorn  # noqa: E402

from agentlevy.inference.agent import agent_from_env  # noqa: E402
from agentlevy.inference.server import (  # noqa: E402
    InferenceServer,
    ServerConfig,
    create_app,
)


HRULE = "─" * 78


def _line(label: str, value: str = "") -> None:
    """Render a `[label] value` line for the stage."""
    print(f"  [{label:<10}] {value}")


def _section(title: str) -> None:
    print()
    print(HRULE)
    print(f"  {title}")
    print(HRULE)


def start_server_in_background(host: str, port: int) -> threading.Thread:
    """Start uvicorn in a daemon thread; return the thread handle."""
    config = uvicorn.Config(
        app=create_app(),
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    t = threading.Thread(target=server.run, daemon=True, name="inference-server")
    t.start()

    # Poll /health until it responds
    import httpx
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://{host}:{port}/health", timeout=1.0)
            if r.status_code == 200:
                return t
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"server did not come up at http://{host}:{port}")


def run_agent(role: str, server_url: str, prompt: str, *, model: str | None) -> None:
    """Run one agent end-to-end with stage-formatted output."""
    _section(f"AGENT {role.upper()} — POST /complete")
    _line("prompt", prompt[:60] + ("…" if len(prompt) > 60 else ""))

    state = {"currency": "?"}  # captured from the quote and reused for "paid" line

    def on_event(kind: str, payload: dict) -> None:
        if kind == "quote_received":
            state["currency"] = payload.get("currency", "?")
            _line("server",
                  f"402 — UOR {payload['request_uor_address'][7:15]}…  "
                  f"price {payload['price_rlusd']} {state['currency']}  "
                  f"cache_hit={payload['is_cache_hit']}")
            if payload.get("uor_mcps_receipt"):
                pubkey = payload["uor_mcps_receipt"].get("public_key", "")[:24]
                _line("foundation", f"UOR MCP receipt — pubkey {pubkey}… trust={payload['uor_mcps_receipt'].get('trust_level','?')}")
        elif kind == "payment_submitted":
            _line("xrpl", f"Payment submitted — txid {payload['txid']}")
        elif kind == "payment_validated":
            _line("xrpl", f"Payment VALIDATED — txid {payload['txid']}")
        elif kind == "completion_received":
            cert = payload.get("cert", {})
            settle = payload.get("settlement", {})
            preview = cert.get("operation_description", {}).get("completion_preview", "")
            _line("server", f"200 — cache_hit={payload['is_cache_hit']}")
            _line("cert", f"output={cert.get('output_address','')[7:15]}…  signed by {cert.get('seller_pubkey','')[:16]}…")
            if cert.get("hcs_receipt"):
                hcs = cert["hcs_receipt"]
                _line("hedera",
                      f"HCS topic={hcs.get('topic_id','?')}  seq={hcs.get('sequence_number','?')}  "
                      f"@ {str(hcs.get('consensus_timestamp',''))[:23]}")
            if settle.get("uor_mcps_receipt_present"):
                _line("foundation", "UOR MCPS receipt attached to cert")
            if settle.get("model_nft_id"):
                _line("nft", f"model {settle['model_nft_id'][:16]}… — royalty routed (best-effort)")
            _line("preview", preview)

    agent = agent_from_env(role=role, server_url=server_url)
    try:
        result = agent.complete(prompt, model=model, on_event=on_event)
    finally:
        agent.close()

    _line("paid", f"{result.paid_rlusd} {state['currency']}")
    _line("elapsed", f"{result.elapsed_ms} ms")
    return result


def print_audit_summary(server_url: str) -> None:
    import httpx
    _section("AUDIT SUMMARY")
    try:
        h = httpx.get(f"{server_url}/health", timeout=5.0).json()
        _line("server", h.get("server_wallet", "?"))
        _line("nft", h.get("model_nft_id", "?"))
        _line("cache", f"size={h.get('cache_size','?')}  total_hits={h.get('total_hits','?')}")
    except Exception as exc:
        _line("error", f"health fetch failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--prompt",
        default=(
            "Draft a polite 2-sentence reschedule email for a meeting "
            "running 15 minutes late."
        ),
        help="The prompt both agents will ask. Default is a head-of-distribution "
             "agent query that lands well on stage.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default=None, help="Override default model.")
    parser.add_argument(
        "--skip-server-startup",
        action="store_true",
        help="Assume the server is already running on host:port (don't start it).",
    )
    parser.add_argument(
        "--total-calls",
        type=int,
        default=2,
        help="Total number of agent calls (default 2 = 1 miss + 1 hit). "
             "Use --total-calls 10 for the killer 1-miss + 9-hits demo.",
    )
    parser.add_argument(
        "--inter-call-pause",
        type=float,
        default=1.0,
        help="Seconds to pause between calls so each beat is readable.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env", override=True)

    server_url = f"http://{args.host}:{args.port}"

    xrp_mode = os.environ.get("INFERENCE_USE_XRP_FALLBACK", "false").lower() == "true"
    settlement_label = "native XRP" if xrp_mode else "RLUSD"

    _section("AGENTLEVY INFERENCE — PAY-PER-CALL DEMO")
    _line("server_url", server_url)
    _line("xrpl", os.environ.get("XRPL_RPC_URL", "(unset)"))
    _line("settlement", settlement_label)
    _line("model_nft", os.environ.get("MODEL_NFT_ID", "(unset)") or "(unset)")
    _line("anthropic", "key set" if os.environ.get("ANTHROPIC_API_KEY") else "(unset)")
    if not xrp_mode:
        _line("rlusd_issuer", os.environ.get("RLUSD_TESTNET_ISSUER", "(unset)") or "(unset)")

    if not args.skip_server_startup:
        _section("STARTING INFERENCE SERVER")
        start_server_in_background(args.host, args.port)
        _line("status", "up")

    # Call 1: agent_a — cache MISS (real Anthropic call, cert minted)
    # Calls 2..N: alternating agent_b / agent_a — cache HITs (cert reused,
    # karakurenai pulse, 10× cheaper, royalty still flows to model owner)
    if args.total_calls < 1:
        raise SystemExit("--total-calls must be >= 1")

    run_agent("a", server_url, args.prompt, model=args.model)
    for i in range(1, args.total_calls):
        time.sleep(args.inter_call_pause)
        # Alternate b, a, b, a, … so the audit trail shows multiple distinct payers
        role = "b" if i % 2 == 1 else "a"
        run_agent(role, server_url, args.prompt, model=args.model)

    print_audit_summary(server_url)
    print()
    # Pull the server wallet address from /health rather than expecting an env var
    server_addr = None
    try:
        import httpx
        health = httpx.get(f"{server_url}/health", timeout=2.0).json()
        server_addr = health.get("server_wallet")
    except Exception:
        pass

    network_host = "testnet.xrpl.org" if "altnet" in os.environ.get("XRPL_RPC_URL", "") else "xrpscan.com"
    print(f"Demo complete. Verify on XRPL ({network_host}):")
    if server_addr:
        print(f"  account: https://{network_host}/account/{server_addr}")
    if os.environ.get("MODEL_NFT_ID"):
        print(f"  nft:     https://{network_host}/nft/{os.environ['MODEL_NFT_ID']}")
    print()


if __name__ == "__main__":
    main()
