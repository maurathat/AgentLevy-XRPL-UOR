"""Tests for agentlevy.primitives.task_spec.

Verifies the VTEAI TaskSpec model:
  * Construction + validation (task_type whitelist, timezone-aware deadline,
    public-key hex format, price >= 1)
  * Canonical bytes are stable across signature additions (signatures are
    detached and excluded from canonicalization)
  * Sign/verify roundtrip for buyer and seller
  * Wrong-keypair signing rejected
  * Tampering with any field invalidates signatures
  * Content address is sha256:<64-hex> format
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Make repo root importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentlevy.primitives.signing import Keypair, public_key_hex  # noqa: E402
from agentlevy.primitives.task_spec import (  # noqa: E402
    CURRENCY_RLUSD,
    CURRENCY_XRP,
    KYC_BENEFICIAL_OWNERSHIP,
    KYC_SANCTIONS_SCREEN,
    InputRef,
    TaskSpec,
)


TEST_SEED_BUYER = b"\xAA" * 32
TEST_SEED_SELLER = b"\xBB" * 32


def _build_spec(buyer_kp: Keypair, seller_kp: Keypair, **overrides) -> TaskSpec:
    """Build a valid TaskSpec for a given pair of keypairs."""
    defaults = dict(
        task_type=KYC_BENEFICIAL_OWNERSHIP,
        inputs=[
            InputRef(
                description="Acme Holdings disclosure",
                content_address="sha256:" + ("a" * 64),
            )
        ],
        expected_output_schema={"type": "object"},
        price_drops=1_000_000,
        buyer_pubkey=public_key_hex(buyer_kp),
        seller_pubkey=public_key_hex(seller_kp),
        deadline=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    defaults.update(overrides)
    return TaskSpec(**defaults)


# ---------------------------------------------------------------------------
# Construction + validation
# ---------------------------------------------------------------------------

def test_minimal_spec_constructs():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    assert spec.task_type == KYC_BENEFICIAL_OWNERSHIP
    assert spec.price_drops == 1_000_000
    assert spec.signature_buyer is None
    assert spec.signature_seller is None


def test_task_id_is_uuid_by_default():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    # Should look like a UUID
    import uuid
    uuid.UUID(spec.task_id)  # raises if not a valid UUID


def test_task_type_whitelist():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_spec(buyer, seller, task_type="not_a_real_type")


def test_both_kyc_task_types_accepted():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    s1 = _build_spec(buyer, seller, task_type=KYC_BENEFICIAL_OWNERSHIP)
    s2 = _build_spec(buyer, seller, task_type=KYC_SANCTIONS_SCREEN)
    assert s1.task_type == KYC_BENEFICIAL_OWNERSHIP
    assert s2.task_type == KYC_SANCTIONS_SCREEN


def test_naive_deadline_rejected():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_spec(buyer, seller, deadline=datetime(2026, 12, 31))  # no tzinfo


def test_negative_or_zero_price_rejected():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_spec(buyer, seller, price_drops=0)
    with pytest.raises(ValueError):
        _build_spec(buyer, seller, price_drops=-1)


def test_malformed_pubkey_rejected():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_spec(buyer, seller, buyer_pubkey="not-hex")
    with pytest.raises(ValueError):
        _build_spec(buyer, seller, buyer_pubkey="ab" * 31)  # wrong length


def test_currency_defaults_to_rlusd():
    """Per Phase 2.8 decision: RLUSD is the default settlement currency."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    assert spec.currency == CURRENCY_RLUSD


def test_xrp_currency_accepted():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller, currency=CURRENCY_XRP)
    assert spec.currency == CURRENCY_XRP


def test_invalid_currency_rejected():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError, match="currency"):
        _build_spec(buyer, seller, currency="USD")
    with pytest.raises(ValueError, match="currency"):
        _build_spec(buyer, seller, currency="ETH")


def test_currency_is_in_canonical_bytes():
    """Currency is part of the signed bytes — change in currency should
    change the canonical representation (and thus invalidate signatures)."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    canonical = spec.to_canonical_bytes()
    assert b"currency" in canonical
    assert b"RLUSD" in canonical


def test_tampering_with_currency_invalidates_signatures():
    """If anyone modifies the currency after signing, both signatures fail."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    spec.sign_buyer(buyer)
    spec.sign_seller(seller)
    assert spec.is_fully_signed()

    spec.currency = CURRENCY_XRP
    assert spec.verify_buyer_signature() is False
    assert spec.verify_seller_signature() is False


def test_input_ref_requires_valid_address():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_spec(
            buyer, seller,
            inputs=[InputRef(description="bad", content_address="not-an-address")],
        )


# ---------------------------------------------------------------------------
# Canonical bytes / content address stability
# ---------------------------------------------------------------------------

def test_canonical_bytes_stable_before_and_after_signing():
    """Critical invariant: signatures are detached. Adding signatures must
    NOT change the canonical bytes — otherwise the signed bytes could
    drift between sign-time and verify-time."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)

    pre_sign_bytes = spec.to_canonical_bytes()
    spec.sign_buyer(buyer)
    post_buyer_sign_bytes = spec.to_canonical_bytes()
    spec.sign_seller(seller)
    post_seller_sign_bytes = spec.to_canonical_bytes()

    assert pre_sign_bytes == post_buyer_sign_bytes
    assert pre_sign_bytes == post_seller_sign_bytes


def test_content_address_format():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    addr = spec.content_address()
    assert addr.startswith("sha256:")
    hex_part = addr.removeprefix("sha256:")
    assert len(hex_part) == 64
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_same_spec_data_same_address():
    """Determinism: build the same spec twice -> same content address."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    deadline = datetime.now(timezone.utc) + timedelta(hours=1)
    s1 = _build_spec(buyer, seller, task_id="00000000-0000-0000-0000-000000000001",
                     deadline=deadline)
    s2 = _build_spec(buyer, seller, task_id="00000000-0000-0000-0000-000000000001",
                     deadline=deadline)
    assert s1.content_address() == s2.content_address()


# ---------------------------------------------------------------------------
# Sign / verify roundtrip
# ---------------------------------------------------------------------------

def test_buyer_can_sign_and_verify():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    assert spec.verify_buyer_signature() is False  # not yet signed
    spec.sign_buyer(buyer)
    assert spec.signature_buyer is not None
    assert len(spec.signature_buyer) == 128
    assert spec.verify_buyer_signature() is True


def test_seller_can_sign_and_verify():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    spec.sign_seller(seller)
    assert spec.verify_seller_signature() is True


def test_is_fully_signed_requires_both():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    assert spec.is_fully_signed() is False
    spec.sign_buyer(buyer)
    assert spec.is_fully_signed() is False
    spec.sign_seller(seller)
    assert spec.is_fully_signed() is True


# ---------------------------------------------------------------------------
# Wrong-keypair rejection (anti-confusion safeguards)
# ---------------------------------------------------------------------------

def test_buyer_signing_with_seller_keypair_rejected():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    with pytest.raises(ValueError, match="buyer_pubkey"):
        spec.sign_buyer(seller)  # accidentally passing seller keypair


def test_seller_signing_with_buyer_keypair_rejected():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    with pytest.raises(ValueError, match="seller_pubkey"):
        spec.sign_seller(buyer)


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------

def test_tampering_with_price_invalidates_signatures():
    """If anyone modifies the spec after signing, both signatures fail."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    spec.sign_buyer(buyer)
    spec.sign_seller(seller)
    assert spec.is_fully_signed()

    # Now tamper
    spec.price_drops = 999_999
    assert spec.verify_buyer_signature() is False
    assert spec.verify_seller_signature() is False


def test_tampering_with_inputs_invalidates_signatures():
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    spec.sign_buyer(buyer)

    spec.inputs.append(
        InputRef(description="extra input", content_address="sha256:" + ("b" * 64))
    )
    assert spec.verify_buyer_signature() is False


def test_tampering_with_one_signature_does_not_affect_other():
    """Detached signatures: corrupting buyer's sig should not affect seller's."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    spec.sign_buyer(buyer)
    spec.sign_seller(seller)

    # Tamper with the buyer signature only
    spec.signature_buyer = "00" * 64
    assert spec.verify_buyer_signature() is False
    assert spec.verify_seller_signature() is True


# ---------------------------------------------------------------------------
# Round-trip via dict (Pydantic serialization)
# ---------------------------------------------------------------------------

def test_model_dump_excludes_nothing_includes_signatures():
    """Plain model_dump (without exclude=) keeps signatures so they
    travel with the cert when serialized for transport."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    spec.sign_buyer(buyer)
    d = spec.model_dump(mode="json")
    assert "signature_buyer" in d
    assert d["signature_buyer"] is not None


def test_canonical_bytes_excludes_signatures_explicitly():
    """to_canonical_bytes should NOT include signatures (they're detached
    and the bytes that get signed are the spec's content fields only)."""
    buyer = Keypair.from_seed(TEST_SEED_BUYER)
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    spec = _build_spec(buyer, seller)
    spec.sign_buyer(buyer)
    canonical = spec.to_canonical_bytes()
    assert b"signature_buyer" not in canonical
    assert b"signature_seller" not in canonical
