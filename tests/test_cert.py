"""Tests for agentlevy.primitives.cert.

Verifies the DerivationCert model:
  * Construction + validation (content-address pattern, pubkey format,
    timezone-aware timestamp)
  * Canonical bytes are stable across signature addition (signature is
    detached and excluded from canonicalization)
  * Sign/verify roundtrip
  * Wrong-keypair signing rejected
  * Tampering with any field invalidates the signature
  * Subcontract chain: parent cert references child cert by content
    address; both certs verify independently
  * Determinism: same inputs -> same content address
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Make repo root importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentlevy.primitives.cert import DerivationCert  # noqa: E402
from agentlevy.primitives.signing import Keypair, public_key_hex  # noqa: E402


TEST_SEED_SELLER = b"\xCC" * 32
TEST_SEED_OTHER = b"\xDD" * 32

# Sample valid content addresses for fixtures.
SPEC_ADDR = "sha256:" + ("1" * 64)
INPUT_ADDR_A = "sha256:" + ("a" * 64)
INPUT_ADDR_B = "sha256:" + ("b" * 64)
OUTPUT_ADDR = "sha256:" + ("c" * 64)
CHILD_CERT_ADDR = "sha256:" + ("d" * 64)


def _build_cert(seller_kp: Keypair, **overrides) -> DerivationCert:
    """Build a valid DerivationCert for the given seller keypair."""
    defaults = dict(
        task_spec_address=SPEC_ADDR,
        input_addresses=[INPUT_ADDR_A],
        output_address=OUTPUT_ADDR,
        operation_description={
            "operation": "kyc.beneficial_ownership_extract",
            "inputs_described": ["Acme Holdings disclosure"],
            "outputs_described": ["Owner list with percentages"],
        },
        seller_pubkey=public_key_hex(seller_kp),
    )
    defaults.update(overrides)
    return DerivationCert(**defaults)


# ---------------------------------------------------------------------------
# Construction + validation
# ---------------------------------------------------------------------------

def test_minimal_cert_constructs():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    assert cert.task_spec_address == SPEC_ADDR
    assert cert.output_address == OUTPUT_ADDR
    assert cert.signature is None
    assert cert.subcontract_cert_addresses == []


def test_cert_id_is_uuid_by_default():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    import uuid
    uuid.UUID(cert.cert_id)  # raises if not a valid UUID


def test_timestamp_defaults_to_utc_now():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    before = datetime.now(timezone.utc)
    cert = _build_cert(seller)
    after = datetime.now(timezone.utc)
    assert cert.timestamp.tzinfo is not None
    assert before <= cert.timestamp <= after


def test_naive_timestamp_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_cert(seller, timestamp=datetime(2026, 5, 3))  # no tzinfo


def test_malformed_task_spec_address_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_cert(seller, task_spec_address="not-an-address")
    with pytest.raises(ValueError):
        _build_cert(seller, task_spec_address="sha256:short")


def test_malformed_output_address_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_cert(seller, output_address="md5:" + ("a" * 32))


def test_malformed_input_address_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_cert(seller, input_addresses=[INPUT_ADDR_A, "garbage"])


def test_malformed_subcontract_address_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_cert(seller, subcontract_cert_addresses=["sha256:" + ("z" * 64)])


def test_malformed_pubkey_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_cert(seller, seller_pubkey="not-hex")
    with pytest.raises(ValueError):
        _build_cert(seller, seller_pubkey="ab" * 31)  # wrong length


def test_extra_fields_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    with pytest.raises(ValueError):
        _build_cert(seller, surprise_field="oops")


# ---------------------------------------------------------------------------
# Canonical bytes / content address
# ---------------------------------------------------------------------------

def test_canonical_bytes_stable_before_and_after_signing():
    """Critical invariant: signature is detached. Adding it must NOT change
    the canonical bytes — otherwise the signed bytes drift between sign-time
    and verify-time."""
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)

    pre_sign_bytes = cert.to_canonical_bytes()
    cert.sign(seller)
    post_sign_bytes = cert.to_canonical_bytes()

    assert pre_sign_bytes == post_sign_bytes


def test_canonical_bytes_excludes_signature_explicitly():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    cert.sign(seller)
    canonical = cert.to_canonical_bytes()
    assert b"signature" not in canonical


def test_content_address_format():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    addr = cert.content_address()
    assert addr.startswith("sha256:")
    hex_part = addr.removeprefix("sha256:")
    assert len(hex_part) == 64
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_same_data_same_address():
    """Determinism: build the same cert twice -> same content address."""
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    fixed_id = "00000000-0000-0000-0000-000000000002"
    fixed_ts = datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc)
    c1 = _build_cert(seller, cert_id=fixed_id, timestamp=fixed_ts)
    c2 = _build_cert(seller, cert_id=fixed_id, timestamp=fixed_ts)
    assert c1.content_address() == c2.content_address()


# ---------------------------------------------------------------------------
# Sign / verify roundtrip
# ---------------------------------------------------------------------------

def test_sign_and_verify_roundtrip():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    assert cert.verify_signature() is False  # not yet signed
    cert.sign(seller)
    assert cert.signature is not None
    assert len(cert.signature) == 128
    assert cert.verify_signature() is True


def test_signing_with_wrong_keypair_rejected():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    other = Keypair.from_seed(TEST_SEED_OTHER)
    cert = _build_cert(seller)
    with pytest.raises(ValueError, match="seller_pubkey"):
        cert.sign(other)


# ---------------------------------------------------------------------------
# Tamper detection
# ---------------------------------------------------------------------------

def test_tampering_with_output_invalidates_signature():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    cert.sign(seller)
    assert cert.verify_signature()

    cert.output_address = "sha256:" + ("e" * 64)
    assert cert.verify_signature() is False


def test_tampering_with_inputs_invalidates_signature():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    cert.sign(seller)

    cert.input_addresses.append(INPUT_ADDR_B)
    assert cert.verify_signature() is False


def test_tampering_with_operation_description_invalidates_signature():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    cert.sign(seller)

    cert.operation_description["operation"] = "kyc.something_else"
    assert cert.verify_signature() is False


def test_tampering_with_subcontract_addresses_invalidates_signature():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    cert.sign(seller)

    cert.subcontract_cert_addresses.append(CHILD_CERT_ADDR)
    assert cert.verify_signature() is False


def test_tampered_signature_does_not_verify():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    cert.sign(seller)
    cert.signature = "00" * 64
    assert cert.verify_signature() is False


# ---------------------------------------------------------------------------
# Subcontracting chain (the protocol's headline feature)
# ---------------------------------------------------------------------------

def test_subcontract_chain_verifies_independently():
    """Parent cert references child cert by content address; each cert
    verifies on its own keypair. This is the audit-trail invariant."""
    sanctions_kp = Keypair.from_seed(TEST_SEED_OTHER)
    compliance_kp = Keypair.from_seed(TEST_SEED_SELLER)

    # Child: sanctions agent's cert.
    child = DerivationCert(
        task_spec_address=SPEC_ADDR,
        input_addresses=[INPUT_ADDR_A],
        output_address="sha256:" + ("f" * 64),
        operation_description={"operation": "kyc.sanctions_screen"},
        seller_pubkey=public_key_hex(sanctions_kp),
    )
    child.sign(sanctions_kp)
    assert child.verify_signature()

    # Parent: compliance agent's cert, citing child by content address.
    parent = DerivationCert(
        task_spec_address=SPEC_ADDR,
        input_addresses=[INPUT_ADDR_A],
        output_address=OUTPUT_ADDR,
        operation_description={"operation": "kyc.beneficial_ownership_extract"},
        subcontract_cert_addresses=[child.content_address()],
        seller_pubkey=public_key_hex(compliance_kp),
    )
    parent.sign(compliance_kp)

    assert parent.verify_signature()
    # Child is still independently valid (not affected by parent's signing).
    assert child.verify_signature()
    # The chain is intact: parent's subcontract list contains child's address.
    assert child.content_address() in parent.subcontract_cert_addresses


def test_modifying_child_breaks_chain_link_but_not_parent_signature():
    """If a child cert is tampered after the parent commits its address,
    the parent's signature still verifies (it signed the child's address
    at sign-time), but the child's content_address now differs — so the
    verifier discovers the chain is broken at the address-resolution step,
    not the signature step."""
    sanctions_kp = Keypair.from_seed(TEST_SEED_OTHER)
    compliance_kp = Keypair.from_seed(TEST_SEED_SELLER)

    child = DerivationCert(
        task_spec_address=SPEC_ADDR,
        input_addresses=[INPUT_ADDR_A],
        output_address="sha256:" + ("f" * 64),
        operation_description={"operation": "kyc.sanctions_screen"},
        seller_pubkey=public_key_hex(sanctions_kp),
    )
    child.sign(sanctions_kp)
    original_child_addr = child.content_address()

    parent = DerivationCert(
        task_spec_address=SPEC_ADDR,
        input_addresses=[INPUT_ADDR_A],
        output_address=OUTPUT_ADDR,
        operation_description={"operation": "kyc.beneficial_ownership_extract"},
        subcontract_cert_addresses=[original_child_addr],
        seller_pubkey=public_key_hex(compliance_kp),
    )
    parent.sign(compliance_kp)

    # Tamper with the child after the fact.
    child.output_address = "sha256:" + ("0" * 64)

    # Parent's signature is unaffected — it signed the original child address.
    assert parent.verify_signature() is True
    # Child's own signature now fails (it was over the original output_address).
    assert child.verify_signature() is False
    # And the child's content address has shifted, so the parent's
    # subcontract reference no longer resolves to this object.
    assert child.content_address() != original_child_addr
    assert child.content_address() not in parent.subcontract_cert_addresses


# ---------------------------------------------------------------------------
# Round-trip via dict (Pydantic serialization)
# ---------------------------------------------------------------------------

def test_model_dump_includes_signature():
    seller = Keypair.from_seed(TEST_SEED_SELLER)
    cert = _build_cert(seller)
    cert.sign(seller)
    d = cert.model_dump(mode="json")
    assert "signature" in d
    assert d["signature"] is not None
