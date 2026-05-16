"""One-shot setup for the inference demo on XRPL Testnet.

What this does
--------------

1. Generates 4 XRPL Testnet wallets via the Testnet faucet (auto-funded with ~10 XRP each):
   - ``agent_a``, ``agent_b``, ``server``, ``model_owner``
2. Generates a 32-byte Ed25519 seed for the inference server's cert-signing key.
3. Writes everything to ``.env`` under the standard variable names.
4. Sets a sensible default for ``RLUSD_TESTNET_ISSUER`` if not already set.

Idempotency
-----------

Each wallet generation is gated by an env-var existence check. If
``XRPL_INFERENCE_AGENT_A_SEED`` is already set in ``.env``, this script will
SKIP creating agent_a. Run with ``--force`` to override and re-generate (this
WILL change your wallet addresses, so don't do it after minting the NFT).

Usage
-----

    python scripts/setup_inference_demo.py
    python scripts/setup_inference_demo.py --force            # regenerate even if set
    python scripts/setup_inference_demo.py --only agent_a     # generate just one role
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from pathlib import Path

# Make repo root importable
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv, set_key  # noqa: E402
from xrpl.clients import JsonRpcClient  # noqa: E402
from xrpl.wallet import Wallet, generate_faucet_wallet  # noqa: E402


# Default Testnet RLUSD issuer (cross-checked May 2026)
# Source: https://docs.ripple.com/stablecoin/developer-resources/rlusd-on-the-xrpl/
DEFAULT_RLUSD_TESTNET_ISSUER = "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De"

ROLES = {
    "agent_a":     "XRPL_INFERENCE_AGENT_A_SEED",
    "agent_b":     "XRPL_INFERENCE_AGENT_B_SEED",
    "server":      "XRPL_INFERENCE_SERVER_SEED",
    "model_owner": "XRPL_INFERENCE_MODEL_OWNER_SEED",
}


def ensure_rlusd_issuer(env_path: Path) -> str:
    """Make sure RLUSD_TESTNET_ISSUER is set in .env. Returns the address."""
    current = os.environ.get("RLUSD_TESTNET_ISSUER", "").strip()
    if current:
        print(f"  RLUSD_TESTNET_ISSUER already set: {current}")
        return current
    print(f"  RLUSD_TESTNET_ISSUER unset — writing default: {DEFAULT_RLUSD_TESTNET_ISSUER}")
    set_key(str(env_path), "RLUSD_TESTNET_ISSUER", DEFAULT_RLUSD_TESTNET_ISSUER)
    return DEFAULT_RLUSD_TESTNET_ISSUER


def ensure_ed25519_seed(env_path: Path) -> None:
    name = "INFERENCE_SERVER_ED25519_SEED_HEX"
    current = os.environ.get(name, "").strip()
    if current:
        print(f"  {name} already set ({len(current)} chars)")
        return
    seed = secrets.token_hex(32)
    set_key(str(env_path), name, seed)
    print(f"  {name} generated and written (64 hex chars)")


def ensure_inference_defaults(env_path: Path) -> None:
    """Set sane defaults for the inference-server env flags."""
    defaults = {
        "INFERENCE_DEFAULT_MODEL": "claude-haiku-4-5",
        "INFERENCE_ROYALTY_ENABLED": "true",
        "INFERENCE_USE_LIVE_UOR_MCP": "false",
        "INFERENCE_HCS_ANCHOR_ENABLED": "true",
        "AGENTLEVY_CERT_STORE_PATH": "/tmp/agentlevy_certs.json",
    }
    for k, v in defaults.items():
        if not os.environ.get(k, "").strip():
            set_key(str(env_path), k, v)
            print(f"  {k} = {v}  (default)")


def generate_wallet_with_retry(
    client: JsonRpcClient,
    role: str,
    *,
    max_attempts: int = 3,
) -> Wallet:
    """Generate a Testnet wallet via the faucet, retrying on transient errors."""
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"    attempt {attempt}/{max_attempts}: requesting faucet...")
            wallet = generate_faucet_wallet(client, debug=False)
            return wallet
        except Exception as exc:  # noqa: BLE001 — xrpl-py raises broad types
            last_err = exc
            print(f"    attempt {attempt} failed: {exc}")
            if attempt < max_attempts:
                time.sleep(3)
    raise RuntimeError(f"faucet failed for {role} after {max_attempts} attempts: {last_err}")


def maybe_generate_wallet(
    client: JsonRpcClient,
    env_path: Path,
    role: str,
    env_name: str,
    *,
    force: bool,
) -> tuple[str | None, str | None]:
    """Generate one wallet unless its seed is already in .env (and not --force)."""
    current = os.environ.get(env_name, "").strip()
    if current and not force:
        try:
            w = Wallet.from_seed(current)
            print(f"  {role:12s}  ✓ already set  {w.classic_address}")
            return current, w.classic_address
        except Exception as exc:
            print(f"  {role:12s}  ⚠ seed is set but invalid: {exc}. Regenerating.")
    print(f"  {role:12s}  generating fresh wallet via Testnet faucet...")
    wallet = generate_wallet_with_retry(client, role)
    set_key(str(env_path), env_name, wallet.seed)
    print(f"  {role:12s}  ✓ generated  {wallet.classic_address}")
    return wallet.seed, wallet.classic_address


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--force", action="store_true",
                        help="Regenerate wallets even if seeds are already set in .env")
    parser.add_argument("--only", choices=list(ROLES.keys()),
                        help="Generate only one role")
    args = parser.parse_args()

    env_path = REPO_ROOT.parent.parent.parent / ".env"  # …/AgentLevy-XRPL-UOR/.env
    # Resolve: scripts/ is one level under repo root for both worktrees + main checkout.
    repo_root_candidates = [Path(__file__).resolve().parent.parent]
    for cand in repo_root_candidates:
        if (cand / ".env").exists():
            env_path = cand / ".env"
            break
    # If still not found, walk up to the parent .env (main repo from a worktree)
    if not env_path.exists():
        # Try going up to find the .env at the main checkout
        main_env = Path("/Users/mauraclark/AgentLevy-XRPL-UOR/.env")
        if main_env.exists():
            env_path = main_env

    if not env_path.exists():
        raise SystemExit(f".env not found at {env_path}")
    print(f"Loading and writing to: {env_path}")
    load_dotenv(env_path, override=True)
    print()

    rpc_url = os.environ.get("XRPL_RPC_URL", "").strip()
    if not rpc_url:
        raise SystemExit("XRPL_RPC_URL not set in .env")
    if "altnet.rippletest.net" not in rpc_url and "testnet" not in rpc_url.lower():
        print(f"⚠ Warning: XRPL_RPC_URL={rpc_url!r} doesn't look like a Testnet endpoint.")
        print("  The faucet only works on Testnet. Proceeding anyway.")

    print(f"Network: {rpc_url}")
    print()

    print("=== RLUSD issuer ===")
    ensure_rlusd_issuer(env_path)
    print()

    print("=== Inference server defaults ===")
    ensure_inference_defaults(env_path)
    print()

    print("=== Server Ed25519 cert-signing seed ===")
    ensure_ed25519_seed(env_path)
    print()

    print("=== Wallets ===")
    client = JsonRpcClient(rpc_url)
    roles = [args.only] if args.only else list(ROLES.keys())
    addresses: dict[str, str] = {}
    for role in roles:
        env_name = ROLES[role]
        _, addr = maybe_generate_wallet(client, env_path, role, env_name, force=args.force)
        if addr:
            addresses[role] = addr

    print()
    print("=" * 70)
    print("SETUP COMPLETE")
    print("=" * 70)
    for role, addr in addresses.items():
        print(f"  {role:12s}  {addr}")
        print(f"               https://test.bithomp.com/account/{addr}")
    print()
    print("Next steps:")
    print("  1. Run scripts/setup_rlusd_trust_lines.py (establishes RLUSD trust on all 4)")
    print("  2. Visit https://tryrlusd.com/ and request RLUSD for agent_a + agent_b")
    print(f"     agent_a: {addresses.get('agent_a','(unset)')}")
    print(f"     agent_b: {addresses.get('agent_b','(unset)')}")
    print("  3. Run scripts/mint_model_nft.py to mint the model NFT")
    print("  4. Run scripts/run_inference_demo.py")


if __name__ == "__main__":
    main()
