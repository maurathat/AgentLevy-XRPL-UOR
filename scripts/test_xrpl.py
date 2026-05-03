"""Phase 0.4 / 0.8 verification - confirms XRPL wallets work end-to-end.

Run from the repo root with the venv active:

    python scripts/test_xrpl.py                  # default: testnet
    python scripts/test_xrpl.py --network=wasm   # WASM Devnet (Phase 2.8)

What this does:
  1. Loads .env. Default network reads XRPL_RPC_URL + XRPL_*_SEED. The
     --network=wasm option reads XRPL_WASM_RPC_URL + XRPL_WASM_*_SEED.
  2. Builds a Wallet from each seed and prints its classic address.
  3. Connects to the configured XRPL JSON-RPC endpoint.
  4. Looks up each wallet's balance.
  5. If the buyer has enough headroom over the network's base reserve,
     sends 1 XRP buyer -> compliance and waits for validation. Confirms
     signing and submission work on xrpl-py 4.5.0 against the chosen
     network.

If a wallet is unfunded (actNotFound) or pinned to its base reserve, the
script prints a one-line hint with the faucet URL and exits non-zero
without attempting the transfer.

Designed to run in 10-20 seconds. Idempotent enough for re-running: each
run sends 1 XRP, so balances drift slightly.

Why the --network=wasm flag exists
----------------------------------
docs/NETWORK_CHOICE.md records the project's separation: regular Testnet
hosts the agent-negotiation/signing demos (Phases 2.1-2.7); WASM Devnet
hosts the XLS-100 SmartEscrow demo (Phase 2.8). The flag makes the
network switch explicit in the script invocation, never implicit in env
state, so we can never accidentally sign a Phase 2.8 escrow on the wrong
network.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make the repo root importable so 'from agentlevy...' would work later.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from xrpl.clients import JsonRpcClient  # noqa: E402
from xrpl.models.requests import AccountInfo, ServerState  # noqa: E402
from xrpl.models.transactions import Payment  # noqa: E402
from xrpl.transaction import autofill_and_sign, submit_and_wait  # noqa: E402
from xrpl.utils import drops_to_xrp, xrp_to_drops  # noqa: E402
from xrpl.wallet import Wallet  # noqa: E402


# Network -> (rpc-url env var, seed env var prefix)
NETWORKS = {
    "testnet": ("XRPL_RPC_URL", "XRPL"),
    "wasm":    ("XRPL_WASM_RPC_URL", "XRPL_WASM"),
}

ROLES = ("buyer", "compliance", "sanctions")

# Faucet URLs by network host (substring match against rpc_url)
FAUCET_HINTS = {
    "altnet.rippletest.net":      "https://xrpl.org/resources/dev-tools/xrp-faucets (Testnet)",
    "wasm.devnet.rippletest.net": "https://xrpl.org/resources/dev-tools/xrp-faucets (select WASM Devnet)",
    "devnet.rippletest.net":      "https://xrpl.org/resources/dev-tools/xrp-faucets (Devnet)",
    "lend.devnet.rippletest.net": "https://xrpl.org/resources/dev-tools/xrp-faucets (Lending Devnet)",
}


def load_env(network_key: str) -> tuple[str, dict[str, str]]:
    """Load .env, return (rpc_url, {role: seed}) for the chosen network."""
    repo_root = Path(__file__).resolve().parent.parent
    # override=True so the .env file beats any shell-level empty defaults.
    load_dotenv(repo_root / ".env", override=True)

    rpc_var, seed_prefix = NETWORKS[network_key]
    rpc_url = os.environ.get(rpc_var, "").strip()
    if not rpc_url:
        raise SystemExit(f"{rpc_var} is empty in .env")

    seeds: dict[str, str] = {}
    missing: list[str] = []
    for role in ROLES:
        var = f"{seed_prefix}_{role.upper()}_SEED"
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
    return "https://xrpl.org/resources/dev-tools/xrp-faucets"


def reserve_drops(client: JsonRpcClient) -> int:
    """Network's per-account base reserve in drops."""
    resp = client.request(ServerState())
    return int(resp.result["state"]["validated_ledger"]["reserve_base"])


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
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--network",
        choices=list(NETWORKS.keys()),
        default="testnet",
        help="Which network's seeds to use from .env (default: testnet).",
    )
    args = parser.parse_args()

    rpc_url, seeds = load_env(args.network)
    print(f"Network: {args.network}")
    print(f"Endpoint: {rpc_url}")
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

    base_reserve = reserve_drops(client)
    print(f"Base reserve: {drops_to_xrp(str(base_reserve))} XRP "
          f"(account must keep at least this much)")
    print()

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
        raise SystemExit(1)

    # Buyer -> compliance transfer (need headroom over base reserve)
    buyer_drops = balances["buyer"]
    assert buyer_drops is not None
    transfer_drops = int(xrp_to_drops(1))
    fee_buffer_drops = 100_000  # 0.1 XRP buffer for fees and rounding
    needed = base_reserve + transfer_drops + fee_buffer_drops
    if buyer_drops < needed:
        hint = faucet_hint(rpc_url)
        print(
            f"[FAIL] Buyer has {drops_to_xrp(str(buyer_drops))} XRP, needs "
            f">= {drops_to_xrp(str(needed))} XRP "
            f"(reserve {drops_to_xrp(str(base_reserve))} + 1 send + buffer)."
        )
        print(f"       Fund via: {hint}")
        raise SystemExit(1)

    print(f"Sending 1 XRP: buyer -> compliance ({transfer_drops:,} drops)")
    payment = Payment(
        account=wallets["buyer"].classic_address,
        destination=wallets["compliance"].classic_address,
        amount=str(transfer_drops),
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
