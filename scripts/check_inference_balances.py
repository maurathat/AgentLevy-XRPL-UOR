"""Check XRP + RLUSD balances for all 4 inference-demo wallets.

Quick sanity check after running setup + tryrlusd faucet. Confirms:

* All wallets have XRP balance (10 XRP from Testnet faucet)
* All wallets have RLUSD trust line
* agent_a and agent_b have RLUSD balance >= 0.05 (ready for demo)
* server and model_owner have RLUSD trust line but zero balance (expected)

Usage
-----

    python scripts/check_inference_balances.py
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
from xrpl.clients import JsonRpcClient  # noqa: E402
from xrpl.models.requests import AccountInfo, AccountLines  # noqa: E402
from xrpl.utils import drops_to_xrp  # noqa: E402
from xrpl.wallet import Wallet  # noqa: E402

from agentlevy.inference.payment import RLUSD_CURRENCY_HEX  # noqa: E402


ROLES = {
    "agent_a":     "XRPL_INFERENCE_AGENT_A_SEED",
    "agent_b":     "XRPL_INFERENCE_AGENT_B_SEED",
    "server":      "XRPL_INFERENCE_SERVER_SEED",
    "model_owner": "XRPL_INFERENCE_MODEL_OWNER_SEED",
}


def main() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        env_path = Path("/Users/mauraclark/AgentLevy-XRPL-UOR/.env")
    load_dotenv(env_path, override=True)

    rpc = os.environ.get("XRPL_RPC_URL", "").strip()
    issuer = os.environ.get("RLUSD_TESTNET_ISSUER", "").strip()
    if not rpc or not issuer:
        raise SystemExit("XRPL_RPC_URL or RLUSD_TESTNET_ISSUER missing")

    print(f"Network: {rpc}")
    print(f"RLUSD issuer: {issuer}")
    print()
    print(f"  {'role':<12s}  {'XRP':>12s}  {'RLUSD':>14s}  {'trust line':<12s}  address")
    print(f"  {'-'*12}  {'-'*12}  {'-'*14}  {'-'*12}  {'-'*40}")

    client = JsonRpcClient(rpc)
    ready_for_demo = True
    for role, env in ROLES.items():
        seed = os.environ.get(env, "").strip()
        if not seed:
            print(f"  {role:<12s}  {'?':>12s}  {'?':>14s}  {'?':<12s}  (no seed)")
            continue
        wallet = Wallet.from_seed(seed)
        addr = wallet.classic_address

        info = client.request(AccountInfo(account=addr, strict=True, ledger_index="validated"))
        if info.is_successful():
            drops = int(info.result["account_data"]["Balance"])
            xrp_str = str(drops_to_xrp(str(drops)))
        else:
            xrp_str = "unfunded"

        rlusd_str = "—"
        trust = "absent"
        lines = client.request(AccountLines(account=addr, ledger_index="validated"))
        if lines.is_successful():
            for ln in lines.result.get("lines", []):
                if ln.get("currency") == RLUSD_CURRENCY_HEX and ln.get("account") == issuer:
                    rlusd_str = ln.get("balance", "0")
                    trust = "✓"
                    break

        print(f"  {role:<12s}  {xrp_str:>12s}  {rlusd_str:>14s}  {trust:<12s}  {addr}")

        # Demo-readiness check
        if role in ("agent_a", "agent_b"):
            try:
                if Decimal(rlusd_str) < Decimal("0.05"):
                    ready_for_demo = False
            except Exception:
                ready_for_demo = False
        if trust != "✓" and role in ROLES:
            if role in ("server", "model_owner") and rlusd_str == "0":
                pass  # OK
            elif role in ("agent_a", "agent_b") and rlusd_str == "—":
                ready_for_demo = False

    print()
    if ready_for_demo:
        print("READY FOR DEMO ✓")
        print("agent_a and agent_b both have ≥ 0.05 RLUSD. Server + model_owner trust line in place.")
        print()
        print("Next: scripts/mint_model_nft.py")
    else:
        print("NOT YET READY")
        print("Visit https://tryrlusd.com/ → XRPL Testnet → paste agent_a + agent_b addresses")
        print("Then re-run this check.")


if __name__ == "__main__":
    main()
