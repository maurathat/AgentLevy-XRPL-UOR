"""Tests for agentlevy.hedera_layer.anchor.

Covers the mock-mode path comprehensively (no network required) plus a
single live-testnet smoke test that's skipped by default. Set
``RUN_LIVE_HEDERA_TESTS=true`` in the environment to enable the live test.

The mock receipts are deterministic — same content_address + topic_id
always produce the same receipt — so we can assert exact equality
without flakiness.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make repo root importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentlevy.hedera_layer.anchor import (  # noqa: E402
    HCSReceipt,
    submit_anchor,
    verify_anchor,
)


SAMPLE_ADDR = "sha256:" + ("a" * 64)
SAMPLE_ADDR_2 = "sha256:" + ("b" * 64)
SAMPLE_TOPIC = "0.0.8856047"


# ---------------------------------------------------------------------------
# Mock-mode submit
# ---------------------------------------------------------------------------

def test_mock_submit_returns_marked_receipt():
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    assert isinstance(receipt, HCSReceipt)
    assert receipt.is_mock is True
    assert receipt.network == "mock"
    assert receipt.topic_id == SAMPLE_TOPIC


def test_mock_submit_is_deterministic():
    """Same content_address + topic -> same receipt across runs."""
    a = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    b = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    assert a.sequence_number == b.sequence_number
    assert a.transaction_id == b.transaction_id
    assert a.consensus_timestamp == b.consensus_timestamp


def test_mock_submit_different_addresses_different_receipts():
    a = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    b = submit_anchor(SAMPLE_ADDR_2, topic_id=SAMPLE_TOPIC, force_mock=True)
    assert a.sequence_number != b.sequence_number
    assert a.transaction_id != b.transaction_id


def test_mock_transaction_id_format():
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    assert receipt.transaction_id.startswith("MOCK_")


def test_mock_consensus_timestamp_iso8601():
    """Mock receipts populate consensus_timestamp at submit time."""
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    assert receipt.consensus_timestamp is not None
    # Should parse as ISO 8601
    from datetime import datetime
    # Strip nanoseconds (Python's fromisoformat handles up to microseconds)
    ts = receipt.consensus_timestamp[:26] + "+00:00"
    datetime.fromisoformat(ts)


def test_mock_mode_via_env_var(monkeypatch):
    """Without force_mock arg, MOCK_HEDERA env var controls mode."""
    monkeypatch.setenv("MOCK_HEDERA", "true")
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC)
    assert receipt.is_mock is True


def test_force_mock_overrides_env(monkeypatch):
    monkeypatch.setenv("MOCK_HEDERA", "false")
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    assert receipt.is_mock is True


def test_mock_mode_default_when_env_unset(monkeypatch):
    """Safety default: when MOCK_HEDERA is unset, behave as mock."""
    monkeypatch.delenv("MOCK_HEDERA", raising=False)
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC)
    assert receipt.is_mock is True


# ---------------------------------------------------------------------------
# Topic-resolution
# ---------------------------------------------------------------------------

def test_topic_id_arg_overrides_env(monkeypatch):
    monkeypatch.setenv("HEDERA_HCS_TOPIC_ID", "0.0.999999")
    receipt = submit_anchor(SAMPLE_ADDR, topic_id="0.0.111111", force_mock=True)
    assert receipt.topic_id == "0.0.111111"


def test_topic_id_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("HEDERA_HCS_TOPIC_ID", "0.0.222222")
    receipt = submit_anchor(SAMPLE_ADDR, force_mock=True)
    assert receipt.topic_id == "0.0.222222"


def test_missing_topic_raises(monkeypatch):
    monkeypatch.delenv("HEDERA_HCS_TOPIC_ID", raising=False)
    with pytest.raises(RuntimeError, match="HEDERA_HCS_TOPIC_ID"):
        submit_anchor(SAMPLE_ADDR, force_mock=True)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def test_mock_receipt_verifies_trivially():
    """Mock receipts verify True without any network call."""
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    assert verify_anchor(SAMPLE_ADDR, receipt) is True


def test_mock_receipt_verifies_regardless_of_address():
    """Mock receipts trivially verify because they're fixtures, not facts."""
    receipt = submit_anchor(SAMPLE_ADDR, topic_id=SAMPLE_TOPIC, force_mock=True)
    # Even with a wrong address, mock returns True — they're not real anchors.
    assert verify_anchor(SAMPLE_ADDR_2, receipt) is True


# ---------------------------------------------------------------------------
# Pydantic validation on the receipt model
# ---------------------------------------------------------------------------

def test_receipt_rejects_extra_fields():
    with pytest.raises(ValueError):
        HCSReceipt(
            topic_id=SAMPLE_TOPIC,
            sequence_number=1,
            transaction_id="MOCK_test",
            network="mock",
            extra_field="oops",
        )


def test_receipt_rejects_negative_sequence():
    with pytest.raises(ValueError):
        HCSReceipt(
            topic_id=SAMPLE_TOPIC,
            sequence_number=-1,
            transaction_id="MOCK_test",
            network="mock",
        )


def test_receipt_serializes_to_json():
    receipt = HCSReceipt(
        topic_id=SAMPLE_TOPIC,
        sequence_number=42,
        transaction_id="MOCK_abc",
        network="mock",
        is_mock=True,
        consensus_timestamp="2026-05-04T00:00:00.000000000+00:00",
    )
    d = receipt.model_dump(mode="json")
    assert d["topic_id"] == SAMPLE_TOPIC
    assert d["sequence_number"] == 42
    assert d["is_mock"] is True


# ---------------------------------------------------------------------------
# Live testnet (skipped by default)
# ---------------------------------------------------------------------------

LIVE_TEST_ENABLED = os.environ.get("RUN_LIVE_HEDERA_TESTS", "").lower() == "true"


@pytest.mark.skipif(
    not LIVE_TEST_ENABLED,
    reason="Live HCS test disabled. Set RUN_LIVE_HEDERA_TESTS=true to run.",
)
def test_live_submit_and_verify_roundtrip():
    """Live smoke test: submit a unique address, then verify it via the
    Mirror Node REST API.

    Requires .env populated with operator credentials + topic ID.
    Costs ~$0.0001 testnet HBAR per run. Mirror Node propagation takes
    ~5-10 seconds, so the verify polls.
    """
    import time
    import uuid

    # Ensure live mode for this test.
    addr = f"sha256:{uuid.uuid4().hex}{uuid.uuid4().hex}"  # 64 hex chars
    receipt = submit_anchor(addr, force_mock=False)

    assert receipt.is_mock is False
    assert receipt.sequence_number > 0

    # Poll Mirror Node until propagated (max 30s)
    for _ in range(15):
        time.sleep(2)
        if verify_anchor(addr, receipt):
            assert receipt.consensus_timestamp is not None
            return
    pytest.fail("Mirror Node did not return the message within 30s")
