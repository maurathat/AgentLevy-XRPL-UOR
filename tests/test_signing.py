"""Tests for agentlevy.primitives.signing.

Verifies Ed25519 signing primitives:
  * Keypair generation (random + from-seed)
  * Sign / verify round-trip
  * Tamper detection: any modification invalidates the signature
  * Wrong-key rejection
  * Determinism: same seed -> same keypair, same canonical bytes -> same signature
  * Hex interop helpers
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make repo root importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from agentlevy.primitives.canonical import to_canonical_bytes  # noqa: E402
from agentlevy.primitives.signing import (  # noqa: E402
    Keypair,
    public_key_from_hex,
    public_key_hex,
    sign,
    signature_from_hex,
    signature_hex,
    verify,
    verify_or_raise,
)
from cryptography.exceptions import InvalidSignature  # noqa: E402


# A fixed seed for reproducible test fixtures. Never use this in production.
TEST_SEED_ALICE = b"\x01" * 32
TEST_SEED_BOB = b"\x02" * 32


# ---------------------------------------------------------------------------
# Keypair generation
# ---------------------------------------------------------------------------

def test_generate_produces_valid_lengths():
    kp = Keypair.generate()
    assert len(kp.private) == 32
    assert len(kp.public) == 32


def test_two_generated_keypairs_differ():
    a = Keypair.generate()
    b = Keypair.generate()
    assert a.private != b.private
    assert a.public != b.public


def test_from_seed_is_deterministic():
    a = Keypair.from_seed(TEST_SEED_ALICE)
    b = Keypair.from_seed(TEST_SEED_ALICE)
    assert a.private == b.private
    assert a.public == b.public


def test_from_seed_rejects_wrong_length():
    with pytest.raises(ValueError):
        Keypair.from_seed(b"\x01" * 31)
    with pytest.raises(ValueError):
        Keypair.from_seed(b"\x01" * 33)


# ---------------------------------------------------------------------------
# Sign / verify round-trip
# ---------------------------------------------------------------------------

def test_sign_verify_roundtrip():
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"task_id": "abc", "price": 100})
    sig = sign(canonical, kp)
    assert len(sig) == 64
    assert verify(canonical, sig, kp) is True


def test_verify_accepts_raw_public_key_bytes():
    """``verify`` should accept either a Keypair or raw public key bytes."""
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"a": 1})
    sig = sign(canonical, kp)
    assert verify(canonical, sig, kp.public) is True


def test_signing_canonical_bytes_is_deterministic():
    """Ed25519 is deterministic — same key, same message -> same signature.

    This matters for cache invariants: if the same canonical bytes are
    signed twice, both signatures should be byte-identical, so cache
    keys based on (canonical_bytes, signature) remain stable.
    """
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"hello": "world"})
    sig_a = sign(canonical, kp)
    sig_b = sign(canonical, kp)
    assert sig_a == sig_b


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------

def test_tamper_in_canonical_bytes_fails_verification():
    """Any single bit changed in the signed bytes invalidates the signature."""
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"task_id": "abc"})
    sig = sign(canonical, kp)

    tampered = bytearray(canonical)
    tampered[0] ^= 0x01  # flip one bit at the start
    assert verify(bytes(tampered), sig, kp) is False


def test_tamper_in_signature_fails_verification():
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"task_id": "abc"})
    sig = sign(canonical, kp)

    tampered_sig = bytearray(sig)
    tampered_sig[0] ^= 0x01
    assert verify(canonical, bytes(tampered_sig), kp) is False


def test_wrong_public_key_fails_verification():
    """A signature from Alice does not verify under Bob's public key."""
    alice = Keypair.from_seed(TEST_SEED_ALICE)
    bob = Keypair.from_seed(TEST_SEED_BOB)
    canonical = to_canonical_bytes({"task_id": "abc"})
    sig_alice = sign(canonical, alice)
    assert verify(canonical, sig_alice, bob) is False


def test_completely_wrong_signature_fails_gracefully():
    """An obviously-wrong signature returns False, doesn't raise."""
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"task_id": "abc"})
    bogus = b"\x00" * 64
    assert verify(canonical, bogus, kp) is False


def test_garbage_signature_length_fails_gracefully():
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"task_id": "abc"})
    garbage = b"\x00" * 16  # wrong length
    assert verify(canonical, garbage, kp) is False


# ---------------------------------------------------------------------------
# verify_or_raise
# ---------------------------------------------------------------------------

def test_verify_or_raise_passes_silently_on_valid():
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"task_id": "abc"})
    sig = sign(canonical, kp)
    verify_or_raise(canonical, sig, kp)  # no exception


def test_verify_or_raise_raises_on_invalid():
    alice = Keypair.from_seed(TEST_SEED_ALICE)
    bob = Keypair.from_seed(TEST_SEED_BOB)
    canonical = to_canonical_bytes({"task_id": "abc"})
    sig_alice = sign(canonical, alice)
    with pytest.raises(InvalidSignature):
        verify_or_raise(canonical, sig_alice, bob)


# ---------------------------------------------------------------------------
# Hex interop
# ---------------------------------------------------------------------------

def test_public_key_hex_round_trip():
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    h = public_key_hex(kp)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
    assert public_key_from_hex(h) == kp.public


def test_signature_hex_round_trip():
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    canonical = to_canonical_bytes({"x": 1})
    sig = sign(canonical, kp)
    h = signature_hex(sig)
    assert len(h) == 128
    assert signature_from_hex(h) == sig


def test_public_key_hex_accepts_raw_bytes():
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    assert public_key_hex(kp.public) == kp.public.hex()


def test_public_key_from_hex_rejects_wrong_length():
    with pytest.raises(ValueError):
        public_key_from_hex("00" * 16)


def test_signature_from_hex_rejects_wrong_length():
    with pytest.raises(ValueError):
        signature_from_hex("00" * 16)


# ---------------------------------------------------------------------------
# Integration: canonical + sign + verify with a non-trivial Pydantic-shaped object
# ---------------------------------------------------------------------------

def test_full_chain_with_complex_object():
    """End-to-end: build object, canonicalize, sign, verify, reject tampered.

    This is the pattern Phase 2.3+ Pydantic models will use:
      to_canonical_bytes(model.model_dump(mode='json', exclude={'signature'}))
      -> sign(...) -> attach signature -> verify(...) reproduces the bytes
      and validates the sig.
    """
    kp = Keypair.from_seed(TEST_SEED_ALICE)
    spec = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "task_type": "kyc.beneficial_ownership_verify",
        "buyer_pubkey": public_key_hex(kp),
        "deadline": "2026-05-07T23:59:59Z",
        "price_drops": 1_000_000,
    }
    canonical = to_canonical_bytes(spec)
    sig = sign(canonical, kp)

    # Original verifies
    assert verify(canonical, sig, kp.public) is True

    # Reproducing the canonical from the same dict verifies
    reproduced = to_canonical_bytes(spec)
    assert verify(reproduced, sig, kp.public) is True

    # Modifying any field breaks verification
    spec_modified = dict(spec)
    spec_modified["price_drops"] = 999_999
    canonical_modified = to_canonical_bytes(spec_modified)
    assert verify(canonical_modified, sig, kp.public) is False
