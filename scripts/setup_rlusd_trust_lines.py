"""Establish RLUSD trust lines on all 4 inference-demo wallets.

A trust line is a one-shot TrustSet transaction that authorizes the wallet to
hold an IOU (here, RLUSD) issued by a specific issuer address. Without trust
lines, RLUSD payments are rejected by the protocol — they have nowhere to land.

What this does
--------------

For each of agent_a, agent_b, server, model_owner:

* Loads the wallet from the seed in ``.env``
* Checks if a trust line already exists for RLUSD on that wallet
* If not, submits a TrustSet with a high limit (1M RLUSD — demo-only)
* If yes, prints the existing limit and skips

Idempotent. Re-running the script is safe — already-established lines are
detected and skipped.

Usage
-----

    python scripts/setup_rlusd_trust_lines.py
    python scripts/setup_rlusd_trust_lines.py --only agent_a
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
from xrpl.clients import JsonRpcClient  # noqa: E402
from xrpl.models.requests import AccountLines  # noqa: E402
from xrpl.wallet import Wallet  # noqa: E402

from agentlevy.inference.payment import (  # noqa: E402
    DEFAULT_TRUST_LIMIT,
    RLUSDConfig,
    RLUSD_CURRENCY_HEX,
    establish_trust_line,
)


ROLES = {
    "agent_a":     "XRPL_INFERENCE_AGENT_A_SEED",
    "agent_b":     "XRPL_INFERENCE_AGENT_B_SEED",
    "server":      "XRPL_INFERENCE_SERVER_SEED",
    "model_owner": "XRPL_INFERENCE_MODEL_OWNER_SEED",
}


def has_rlusd_trust_line(
    client: JsonRpcClient,
    wallet_address: str,
    issuer: str,
) -> tuple[bool, str | None]:
    """Return (has_line, current_limit) for the wallet's RLUSD trust to issuer."""
    marker = None
    while True:
        resp = client.request(AccountLines(account=wallet_address, marker=marker))
        if not resp.is_successful():
            return False, f"account_lines failed: {resp.result.get('error', 'unknown')}"
        for line in resp.result.get("lines", []):
            if line.get("currency") == RLUSD_CURRENCY_HEX and line.get("account") == issuer:
                return True, line.get("limit")
        marker = resp.result.get("marker")
        if not marker:
            return False, None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--only", choices=list(ROLES.keys()),
                        help="Only set trust line for one role")
    parser.add_argument("--limit", type=Decimal, default=DEFAULT_TRUST_LIMIT,
                        help="Trust line limit (default 1,000,000 RLUSD)")
    args = parser.parse_args()

    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        # Worktrees: look at the main checkout's .env
        env_path = Path("/Users/mauraclark/AgentLevy-XRPL-UOR/.env")
    if not env_path.exists():
        raise SystemExit(f".env not found at {env_path}")
    load_dotenv(env_path, override=True)

    rpc_url = os.environ.get("XRPL_RPC_URL", "").strip()
    if not rpc_url:
        raise SystemExit("XRPL_RPC_URL not set in .env")

    rlusd = RLUSDConfig.from_env()
    print(f"Network: {rpc_url}")
    print(f"RLUSD issuer: {rlusd.issuer}")
    print(f"Trust limit: {args.limit} RLUSD")
    print()

    client = JsonRpcClient(rpc_url)
    roles = [args.only] if args.only else list(ROLES.keys())

    for role in roles:
        seed = os.environ.get(ROLES[role], "").strip()
        if not seed:
            print(f"  {role:12s}  ✗ {ROLES[role]} not set in .env. "
                  "Run scripts/setup_inference_demo.py first.")
            continue
        try:
            wallet = Wallet.from_seed(seed)
        except Exception as exc:
            print(f"  {role:12s}  ✗ invalid seed: {exc}")
            continue

        # Check whether trust line already exists
        has_line, info = has_rlusd_trust_line(client, wallet.classic_address, rlusd.issuer)
        if has_line:
            print(f"  {role:12s}  ✓ already trusts RLUSD  limit={info}  {wallet.classic_address}")
            continue

        print(f"  {role:12s}  submitting TrustSet... {wallet.classic_address}")
        try:
            result = establish_trust_line(client, wallet, rlusd, limit=args.limit)
            tx_result = result.get("meta", {}).get("TransactionResult", "?")
            validated = result.get("validated", False)
            txid = result.get("hash", "(unknown)")
            if validated and tx_result == "tesSUCCESS":
                print(f"  {role:12s}  ✓ trust line established  tx={txid}")
                print(f"               https://test.bithomp.com/transactions/{txid}")
            else:
                print(f"  {role:12s}  ⚠ TrustSet completed but result={tx_result} "
                      f"validated={validated}")
        except Exception as exc:
            print(f"  {role:12s}  ✗ TrustSet failed: {exc}")

    print()
    print("=" * 70)
    print("TRUST LINES READY")
    print("=" * 70)
    print()
    print("Next: visit https://tryrlusd.com/ — request RLUSD for agent_a and agent_b.")
    print("(Server and model_owner do not need RLUSD up front; they receive it from")
    print(" agents and royalty splits.)")


if __name__ == "__main__":
    main()
