#!/usr/bin/env python3
"""Migrate RoyaltAI Mainnet wallet seeds into macOS Keychain.

Accepts EITHER format:
  - Family Seed: ~29 Base58 chars starting with 's' or 'sEd'
  - Xaman Secret Numbers: 48 digits in 8 rows of 6 (separators/whitespace OK)

Prompts for each seed via hidden input, derives the address, compares
against the expected Mainnet address (typo guard), and stores the Family
Seed form in Keychain on match.

Seeds are never logged, never written to disk in the .env, never echoed.

Usage:
    pip3 install keyring xrpl-py xrpl-secret-numbers
    python3 scripts/migrate_seeds_to_keychain.py

Verify after running:
    python3 -c "import keyring; print('OK' if keyring.get_password('agentlevy.inference','agent_a_seed') else 'MISSING')"
"""
import sys
from getpass import getpass

try:
    import keyring
except ImportError:
    sys.exit("ERROR: pip3 install keyring")

try:
    from xrpl.wallet import Wallet
    from xrpl.constants import CryptoAlgorithm
except ImportError:
    sys.exit("ERROR: pip3 install xrpl-py")


SERVICE = "agentlevy.inference"


def secret_numbers_to_wallet(digits: str, expected_addr: str) -> Wallet:
    """Convert 48-digit Xaman Secret Numbers → Wallet.

    Each row = 5 data digits + 1 checksum digit.
    Checksum: (value × (position × 2 + 1)) mod 9.
    8 row values → 16 bytes entropy → Family Seed.

    Tries both secp256k1 (Xaman default) and ed25519. Picks whichever derives
    to the expected address.
    """
    if len(digits) != 48 or not digits.isdigit():
        raise ValueError(f"need exactly 48 digits, got {len(digits)}")

    entropy = bytearray(16)
    for i in range(8):
        row = digits[i * 6:(i + 1) * 6]
        value = int(row[:5])
        check = int(row[5])
        expected_check = (value * (i * 2 + 1)) % 9
        if expected_check != check:
            raise ValueError(
                f"row {i + 1} checksum failed (got {check}, expected {expected_check}) "
                f"— typo in row {i + 1}?"
            )
        if value > 65535:
            raise ValueError(f"row {i + 1} value {value} exceeds 65535 — invalid")
        entropy[i * 2] = (value >> 8) & 0xff
        entropy[i * 2 + 1] = value & 0xff

    entropy_hex = entropy.hex()

    last_err = None
    for algo in (CryptoAlgorithm.SECP256K1, CryptoAlgorithm.ED25519):
        try:
            w = Wallet.from_entropy(entropy_hex, algorithm=algo)
            if w.classic_address == expected_addr:
                return w
            last_err = f"{algo.value} → {w.classic_address}"
        except Exception as e:
            last_err = f"{algo.value} → {e}"

    raise ValueError(
        f"secret numbers parsed (checksums OK) but neither algorithm derived "
        f"to {expected_addr}. Last attempt: {last_err}"
    )

WALLETS = [
    ("agent_a",     "r94gJ43Jb5rFdKZkg67jVdgnJNYZhdGG8M", "RoyaltAI-1"),
    ("agent_b",     "rN8S1J5LnsAnBwNJyFAU5BGpWivjMWi1Bi", "RoyaltAI-2"),
    ("server",      "rGJktGYrb8ynmPk5NiJm9dmcqsEXAZVTDp", "RoyaltAI-Server"),
    ("model_owner", "r9PjHvj8kKwA61fTMx5ANpH6BrGmQdrQgf", "RoyaltAI-Model-Owner"),
]


def parse_input(raw: str, expected_addr: str) -> Wallet:
    """Accept Family Seed OR Xaman Secret Numbers. Returns a Wallet or raises."""
    s = raw.strip()
    if not s:
        raise ValueError("empty input")

    digits = ''.join(c for c in s if c.isdigit())
    if len(digits) == 48:
        return secret_numbers_to_wallet(digits, expected_addr)

    if s[0].lower() == 's' and len(s) <= 35 and all(c.isalnum() for c in s):
        return Wallet.from_seed(s)

    raise ValueError(
        f"unrecognized format — got {len(digits)} digits in {len(s)} chars. "
        f"Expected 48-digit Secret Numbers or ~29-char Family Seed"
    )


def migrate_one(role: str, expected_addr: str, display: str) -> bool:
    print(f"\n{display}  ({role})")
    print(f"  expected address: {expected_addr}")

    existing = keyring.get_password(SERVICE, f"{role}_seed")
    if existing:
        try:
            w = Wallet.from_seed(existing)
            if w.classic_address == expected_addr:
                print(f"  ✓ already in Keychain (verified) — skipping")
                return True
            else:
                print(f"  ⚠ Keychain entry derives to {w.classic_address}, not expected — will overwrite")
        except Exception:
            print(f"  ⚠ Keychain entry is malformed — will overwrite")

    while True:
        raw = getpass("  paste Family Seed or Secret Numbers (hidden, blank to skip): ")
        if not raw.strip():
            print(f"  skipped — {role} not stored")
            return False
        try:
            w = parse_input(raw, expected_addr)
        except Exception as e:
            print(f"  ✗ {e}")
            continue
        if w.classic_address != expected_addr:
            print(f"  ✗ derives to {w.classic_address}, expected {expected_addr}")
            print(f"     wrong seed for this role — try again or blank to skip")
            continue
        # Store the canonical Family Seed form (works whether input was seed or secret numbers)
        seed_to_store = getattr(w, 'seed', None)
        if not seed_to_store:
            print(f"  ⚠ couldn't extract Family Seed from Wallet — let Claude know")
            return False
        keyring.set_password(SERVICE, f"{role}_seed", seed_to_store)
        print(f"  ✓ stored {role} in Keychain (address verified)")
        return True


def main():
    print("=" * 64)
    print("RoyaltAI Mainnet seed → macOS Keychain migration")
    print("=" * 64)
    print("Service name: agentlevy.inference")
    print("Accepts: Family Seed (starts with 's') OR Xaman Secret Numbers (48 digits)")
    print("Input hidden. Seeds never logged or written to disk.")
    print("Tip: also paste each seed into Proton Pass as a Secure Note backup")
    print("     before continuing.")

    stored = 0
    for role, addr, display in WALLETS:
        if migrate_one(role, addr, display):
            stored += 1

    print()
    print("=" * 64)
    print(f"  {stored}/{len(WALLETS)} seeds in Keychain")
    print("=" * 64)
    if stored == len(WALLETS):
        print("✓ all four migrated. Safe to remove XRPL_INFERENCE_*_SEED lines from .env.")
    else:
        print("Some seeds missing — re-run this script to fill them in.")


if __name__ == "__main__":
    main()
