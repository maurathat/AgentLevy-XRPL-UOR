"""Phase 0.4 verification - confirms XRPL wallets work end-to-end.

Run from the repo root with the venv active:

    python scripts/test_xrpl.py

What this does:
  1. Loads .env (XRPL_RPC_URL, XRPL_BUYER_SEED, XRPL_COMPLIANCE_SEED, XRPL_SANCTIONS_SEED).
  2. Builds a Wallet from each seed and prints its classic address.
  3. Connects to the configured XRPL JSON-RPC endpoint.
  4. Looks up each wallet's balance.
  5. If the buyer has > 1 XRP, sends 1 XRP from buyer -> compliance and waits
     for the transaction to validate. Confirms signing and submission work
     on xrpl-py 4.5.0 with the seeds in .env.

If a wallet is unfunded (returns actNotFound), the script prints a one-line
hint with the faucet URL and exits 1 without attempting the transfer.

Designed to run in 10-20 seconds against testnet. Idempotent enough for
re-running: each run sends 1 XRP, so balances drift slightly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the repo root importable so 'from agentlevy...' would work later.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from xrpl.clients import JsonRpcClient  # noqa: E402
from xrpl.models.requests import AccountInfo  # noqa: E402
from xrpl.models.transactions import Payment  # noqa: E402
from xrpl.transaction import autofill_and_sign, submit_and_wait  # noqa: E402
from xrpl.utils import drops_to_xrp, xrp_to_drops  # noqa: E402
from xrpl.wallet import Wallet  # noqa: E402


# Map env var name -> friendly role label
WALLET_VARS = (
    ("XRPL_BUYER_SEED", "buyer"),
    ("XRPL_COMPLIANCE_SEED", "compliance"),
    ("XRPL_SANCTIONS_SEED", "sanctions"),
)

# Faucet URLs by network host (substring match against rpc_url)
FAUCET_HINTS = {
    "altnet.rippletest.net": "https://faucet.altnet.rippletest.net/accounts (or https://xrpl.org/xrp-testnet-faucet.html)",
    "devnet.rippletest.net": "https://faucet.devnet.rippletest.net/accounts",
    "wasm.devnet.rippletest.net": "https://faucet.wasm.devnet.rippletest.net/accounts",
    "lend.devnet.rippletest.net": "https://faucet.lend.devnet.rippletest.net/accounts",
}


def load_env() -> tuple[str, dict[str, str]]:
    """Load .env, return (rpc_url, {role: seed})."""
    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")

    rpc_url = os.environ.get("XRPL_RPC_URL", "").strip()
    if not rpc_url:
        raise SystemExit("XRPL_RPC_URL is empty in .env")

    seeds: dict[str, str] = {}
    missing: list[str] = []
    for var, role in WALLET_VARS:
        val = os.environ.get(var, "").strip()
        if not val:
            missing.append(var)
        else:
            seeds[role] = val
    if missing:
        raise SystemExit(f"Missing seed env vars: {', '.join(missing)}")

    return rpc_url, seeds


def faucet_hint(rpc_url: str) -> str:
    for host, url in FAUCET_HINTS.items():
        if host in rpc_url:
            return url
    return "https://xrpl.org/xrp-testnet-faucet.html"


def get_balance_drops(client: JsonRpcClient, address: str) -> int | None:
    """Return account balance in drops, or None if account not found (unfunded)."""
    req = AccountInfo(account=address, ledger_index="validated", strict=True)
    resp = client.request(req)
    if resp.is_successful():
        return int(resp.result["account_data"]["Balance"])
    err = resp.result.get("error", "")
    if err == "actNotFound":
        return None
    raise SystemExit(f"AccountInfo failed for {address}: {resp.result}")


def main() -> None:
    rpc_url, seeds = load_env()
    print(f"XRPL endpoint: {rpc_url}")
    print()

    # Build wallets
    wallets: dict[str, Wallet] = {}
    print("Wallets")
    print("-" * 56)
    for role, seed in seeds.items():
        try:
            w = Wallet.from_seed(seed)
        except Exception as exc:
            raise SystemExit(f"  [{role}] failed to build Wallet from seed: {exc}")
        wallets[role] = w
        print(f"  {role:11s}  {w.classic_address}")
    print()

    client = JsonRpcClient(rpc_url)

    # Balances
    print("Balances")
    print("-" * 56)
    balances: dict[str, int | None] = {}
    any_unfunded = False
    for role, w in wallets.items():
        drops = get_balance_drops(client, w.classic_address)
        balances[role] = drops
        if drops is None:
            print(f"  {role:11s}  UNFUNDED")
            any_unfunded = True
        else:
            print(f"  {role:11s}  {drops_to_xrp(str(drops)):>15} XRP   ({drops:,} drops)")
    print()

    if any_unfunded:
        hint = faucet_hint(rpc_url)
        print("[FAIL] At least one wallet is unfunded.")
        print(f"       Fund wallets via: {hint}")
        print("       For testnet, the faucet returns 1000 test XRP per request.")
        print("       After funding, re-run this script.")
        raise SystemExit(1)

    # Buyer -> compliance transfer
    buyer_drops = balances["buyer"]
    assert buyer_drops is not None
    buyer_xrp = drops_to_xrp(str(buyer_drops))
    if buyer_xrp <= 2:
        print(f"[FAIL] Buyer balance {buyer_xrp} XRP is too low to send 1 XRP and keep reserve.")
        raise SystemExit(1)

    transfer_amount_drops = xrp_to_drops(1)
    print(f"Sending 1 XRP: buyer -> compliance ({transfer_amount_drops} drops)")
    payment = Payment(
        account=wallets["buyer"].classic_address,
        destination=wallets["compliance"].classic_address,
        amount=transfer_amount_drops,
    )
    signed = autofill_and_sign(payment, client, wallets["buyer"])
    print(f"  signed tx hash: {signed.get_hash()}")

    response = submit_and_wait(signed, client)
    result = response.result
    tx_result = result.get("meta", {}).get("TransactionResult", "?")
    validated = result.get("validated", False)
    print(f"  validated={validated}  TransactionResult={tx_result}")
    if tx_result != "tesSUCCESS" or not validated:
        print("[FAIL] Payment did not validate as tesSUCCESS.")
        raise SystemExit(1)

    # Re-check balances
    print()
    print("Post-transfer balances")
    print("-" * 56)
    for role in ("buyer", "compliance"):
        drops = get_balance_drops(client, wallets[role].classic_address)
        if drops is None:
            print(f"  {role:11s}  UNFUNDED (unexpected)")
        else:
            print(f"  {role:11s}  {drops_to_xrp(str(drops)):>15} XRP   ({drops:,} drops)")
    print()
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
