"""Centralized wallet and network configuration for the inference subpackage.

Selects between Testnet (development) and Mainnet (production booth demo)
based on a single environment flag. All wallet-seed loading, RPC URL, RLUSD
issuer, and settlement-currency lookups go through this module so the rest
of the codebase stays network-agnostic.

Network selection
-----------------
``XRPL_INFERENCE_NETWORK`` — ``mainnet`` or ``testnet`` (default ``testnet``).

Seed sources
------------
* Mainnet → macOS Keychain (service ``agentlevy.inference``, account
  ``{role}_seed``). Populate with ``scripts/migrate_seeds_to_keychain.py``.
* Testnet → environment variable ``XRPL_INFERENCE_{ROLE}_SEED``.

Why this split: Testnet seeds are throwaway and stay in ``.env`` for
convenience. Mainnet seeds are real money — never written to disk in
plaintext after the one-time Keychain migration.
"""
from __future__ import annotations

import os
from typing import Literal

from xrpl.constants import CryptoAlgorithm
from xrpl.wallet import Wallet


KEYRING_SERVICE = "agentlevy.inference"

RLUSD_ISSUER_MAINNET = "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De"
RLUSD_ISSUER_TESTNET = "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De"

DEFAULT_MAINNET_RPC = "https://xrplcluster.com"

ROLES = ("agent_a", "agent_b", "server", "model_owner")


def network() -> Literal["mainnet", "testnet"]:
    val = os.environ.get("XRPL_INFERENCE_NETWORK", "testnet").strip().lower()
    return "mainnet" if val == "mainnet" else "testnet"


def is_mainnet() -> bool:
    return network() == "mainnet"


def rpc_url() -> str:
    if is_mainnet():
        return os.environ.get("XRPL_MAINNET_RPC_URL", DEFAULT_MAINNET_RPC).strip() or DEFAULT_MAINNET_RPC
    url = os.environ.get("XRPL_RPC_URL", "").strip()
    if not url:
        raise RuntimeError("XRPL_RPC_URL not set (Testnet mode)")
    return url


def rlusd_issuer() -> str:
    override = os.environ.get("RLUSD_ISSUER", "").strip()
    if override:
        return override
    if is_mainnet():
        return RLUSD_ISSUER_MAINNET
    return os.environ.get("RLUSD_TESTNET_ISSUER", RLUSD_ISSUER_TESTNET).strip() or RLUSD_ISSUER_TESTNET


def settlement_currency() -> Literal["RLUSD", "XRP"]:
    explicit = os.environ.get("INFERENCE_SETTLEMENT_CURRENCY", "").strip().upper()
    if explicit in ("RLUSD", "XRP"):
        return explicit  # type: ignore[return-value]
    xrp_legacy = os.environ.get("INFERENCE_USE_XRP_FALLBACK", "false").lower() == "true"
    return "XRP" if xrp_legacy else "RLUSD"


def get_seed(role: str) -> str:
    """Return the Family Seed string for a wallet role.

    Mainnet → Keychain. Testnet → ``XRPL_INFERENCE_{ROLE}_SEED`` env var.
    Raises ``RuntimeError`` with an actionable message if the seed is missing.
    """
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")

    if is_mainnet():
        try:
            import keyring  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "Mainnet seed loading requires the keyring package: "
                "pip install keyring"
            ) from e
        seed = keyring.get_password(KEYRING_SERVICE, f"{role}_seed")
        if not seed:
            raise RuntimeError(
                f"No Mainnet seed in Keychain for role {role!r} "
                f"(service {KEYRING_SERVICE!r}). Run "
                f"`python3 scripts/migrate_seeds_to_keychain.py` to populate."
            )
        return seed

    env_name = f"XRPL_INFERENCE_{role.upper()}_SEED"
    seed = os.environ.get(env_name, "").strip()
    if not seed:
        raise RuntimeError(f"{env_name} not set (Testnet mode)")
    return seed


def get_wallet(role: str) -> Wallet:
    """Construct a Wallet from the role's stored seed.

    Detects the signing algorithm from the seed prefix: ``sEd…`` is ed25519,
    anything else (e.g. ``snF…``, ``ssm…``) is secp256k1. xrpl-py's
    ``Wallet.from_seed`` defaults to ed25519 if you don't tell it otherwise,
    which silently produces wrong addresses for secp256k1 seeds — common when
    seeds come from Xaman, which uses secp256k1 by default.
    """
    seed = get_seed(role)
    algo = CryptoAlgorithm.ED25519 if seed.startswith("sEd") else CryptoAlgorithm.SECP256K1
    return Wallet.from_seed(seed, algorithm=algo)


def get_address(role: str) -> str:
    """Public classic address for a role. Derived from the seed."""
    return get_wallet(role).classic_address
