"""HCS audit-trail anchor — submit cert content addresses to Hedera Consensus
Service for tamper-evident timestamping, complementing XRPL settlement.

Why this exists
---------------

XRPL handles settlement: money moves when the cert hash matches what the
escrow committed to. Hedera handles **ordering**: every signed cert has its
content address submitted to a Hedera Consensus Service topic, producing an
authoritative consensus timestamp + sequence number from a chain independent
of XRPL.

The combination earns the pitch line: *"verifiable from public keys alone,
across two independent ledgers, without trusting either agent."*

Anchoring runs **after** signing — the cert's canonical bytes do not include
the HCS receipt. (Same invariant as signatures: receipts are detached from
the bytes they reference.)

Two modes
---------

* **Live mode** (``MOCK_HEDERA=false``): submits via the Hiero Python SDK
  using the operator account from ``.env``; verifies via the Mirror Node
  REST API (no SDK needed for verify — just an HTTP GET, which makes the
  verifier path trivially auditable from any environment).

* **Mock mode** (``MOCK_HEDERA=true``, the default): returns deterministic
  synthetic receipts derived from the content address. Lets the demo and
  tests run end-to-end without live Hedera credentials. Receipts are
  marked ``is_mock=True``; ``verify_anchor`` accepts mock receipts
  trivially without any network call.

Setup
-----

.env must have:

    HEDERA_NETWORK             testnet | mainnet | previewnet
    HEDERA_OPERATOR_ID         0.0.NNNNNN
    HEDERA_OPERATOR_PRIVATE_KEY  DER-encoded hex from portal.hedera.com
    HEDERA_HCS_TOPIC_ID        0.0.NNNNNN  (created by scripts/setup_hcs_topic.py)
    HEDERA_MIRROR_NODE_URL     https://testnet.mirrornode.hedera.com
    MOCK_HEDERA                true | false

The topic must exist before live submits work. Run
``python scripts/setup_hcs_topic.py`` once to create it.
"""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Receipt model
# ---------------------------------------------------------------------------

class HCSReceipt(BaseModel):
    """Receipt of an HCS topic message submission.

    Detached from the cert's canonical bytes — anchoring happens *after*
    signing, so the receipt is a sibling fact about the cert, not part of
    what was signed.

    A verifier holding only ``(content_address, receipt)`` can independently
    confirm the anchor exists by fetching the topic+sequence from the
    Mirror Node REST API and checking the message body matches.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    topic_id: str = Field(..., description="HCS topic ID, format '0.0.NNNNNN'.")
    sequence_number: int = Field(..., ge=0, description="Per-topic sequence number assigned by consensus.")
    transaction_id: str = Field(..., description="Submission transaction ID, format '0.0.NNN@SEC.NANOS' or 'MOCK_<hex>'.")
    network: str = Field(..., description="Network the anchor lives on: testnet/mainnet/previewnet/mock.")
    is_mock: bool = Field(default=False, description="True iff the receipt was produced by mock mode (no network call).")
    consensus_timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC consensus timestamp. Populated either at "
                    "submit time (mock) or by verify_anchor (live, fetched "
                    "from Mirror Node).",
    )


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _is_mock_enabled(force_mock: Optional[bool]) -> bool:
    """Determine whether to use mock mode for this call.

    Precedence: explicit ``force_mock`` argument wins; otherwise read
    ``MOCK_HEDERA`` from the environment, defaulting to True (so the
    demo never accidentally hits the live network without intent).
    """
    if force_mock is not None:
        return force_mock
    return os.environ.get("MOCK_HEDERA", "true").strip().lower() == "true"


def _resolve_topic(topic_id: Optional[str]) -> str:
    """Pick the topic ID: explicit arg or env. Raises if neither set."""
    topic = topic_id or os.environ.get("HEDERA_HCS_TOPIC_ID", "").strip()
    if not topic:
        raise RuntimeError(
            "HEDERA_HCS_TOPIC_ID not set in .env and no topic_id passed. "
            "Run scripts/setup_hcs_topic.py to create one."
        )
    return topic


def _mirror_node_url() -> str:
    return os.environ.get(
        "HEDERA_MIRROR_NODE_URL",
        "https://testnet.mirrornode.hedera.com",
    ).rstrip("/")


# ---------------------------------------------------------------------------
# Mock receipt generator
# ---------------------------------------------------------------------------

#: Deterministic mock anchor reference time. Used so mock receipts produce a
#: stable, predictable consensus_timestamp across runs (useful for fixtures).
_MOCK_REFERENCE_TIMESTAMP = datetime(2026, 5, 4, 0, 0, 0, tzinfo=timezone.utc)


def _mock_receipt(content_address: str, topic_id: str) -> HCSReceipt:
    """Produce a deterministic synthetic HCSReceipt for a content_address.

    Same ``content_address`` + ``topic_id`` always produce the same receipt.
    Sequence numbers are derived from a SHA-256 of the inputs, so they're
    stable across runs but distinct across different cert addresses.
    """
    digest = hashlib.sha256(f"{topic_id}|{content_address}".encode()).digest()
    seq = int.from_bytes(digest[:4], "big") % 1_000_000
    nanos = int.from_bytes(digest[4:8], "big") % 1_000_000_000
    return HCSReceipt(
        topic_id=topic_id,
        sequence_number=seq,
        transaction_id=f"MOCK_{digest[:8].hex()}",
        network="mock",
        is_mock=True,
        consensus_timestamp=_MOCK_REFERENCE_TIMESTAMP.isoformat().replace(
            "+00:00", f".{nanos:09d}+00:00"
        ),
    )


# ---------------------------------------------------------------------------
# Live submission (Hiero SDK)
# ---------------------------------------------------------------------------

def _submit_live(content_address: str, topic_id: str) -> HCSReceipt:
    """Submit a content address to the configured HCS topic via Hiero SDK."""
    # Imported lazily so mock-mode users don't pay the SDK import cost.
    from hiero_sdk_python import AccountId, Client, Network, PrivateKey
    from hiero_sdk_python.consensus.topic_id import TopicId
    from hiero_sdk_python.consensus.topic_message_submit_transaction import (
        TopicMessageSubmitTransaction,
    )

    network = os.environ.get("HEDERA_NETWORK", "testnet").strip()
    operator_id_str = os.environ.get("HEDERA_OPERATOR_ID", "").strip()
    operator_key_str = os.environ.get("HEDERA_OPERATOR_PRIVATE_KEY", "").strip()
    if not operator_id_str or not operator_key_str:
        raise RuntimeError(
            "Live HCS submit requires HEDERA_OPERATOR_ID and "
            "HEDERA_OPERATOR_PRIVATE_KEY in .env. (Or set MOCK_HEDERA=true.)"
        )

    operator_id = AccountId.from_string(operator_id_str)
    operator_key = PrivateKey.from_string(operator_key_str)

    client = Client(Network(network=network))
    client.set_operator(operator_id, operator_key)

    tx = (
        TopicMessageSubmitTransaction()
        .set_topic_id(TopicId.from_string(topic_id))
        .set_message(content_address)
    )
    receipt = tx.execute(client)

    # The receipt has topic_sequence_number; transaction_id format is
    # the SDK's internal repr — we stringify for storage. Mirror Node will
    # populate the consensus_timestamp on first verify_anchor call.
    return HCSReceipt(
        topic_id=topic_id,
        sequence_number=int(receipt.topic_sequence_number),
        transaction_id=str(receipt.transaction_id),
        network=network,
        is_mock=False,
        consensus_timestamp=None,
    )


# ---------------------------------------------------------------------------
# Public API: submit
# ---------------------------------------------------------------------------

def submit_anchor(
    content_address: str,
    *,
    topic_id: Optional[str] = None,
    force_mock: Optional[bool] = None,
) -> HCSReceipt:
    """Submit a cert ``content_address`` to HCS and return the receipt.

    Parameters
    ----------
    content_address
        The cert's content address (e.g., ``sha256:abc...``). Submitted
        verbatim as UTF-8 bytes to the topic.
    topic_id
        Override the topic ID. If ``None``, reads from
        ``HEDERA_HCS_TOPIC_ID`` env var.
    force_mock
        Override the mock/live decision. ``None`` → use ``MOCK_HEDERA``
        env var (default ``true``). ``True`` → always mock. ``False`` →
        always live (raises if credentials missing).
    """
    topic = _resolve_topic(topic_id)
    if _is_mock_enabled(force_mock):
        return _mock_receipt(content_address, topic)
    return _submit_live(content_address, topic)


# ---------------------------------------------------------------------------
# Public API: verify
# ---------------------------------------------------------------------------

def verify_anchor(
    content_address: str,
    receipt: HCSReceipt,
    *,
    mirror_url: Optional[str] = None,
    timeout_s: float = 10.0,
) -> bool:
    """Verify a receipt by fetching the message from the Mirror Node REST API.

    Returns ``True`` iff the topic+sequence on the Mirror Node has a message
    body matching ``content_address``. Mock receipts return ``True``
    immediately without a network call.

    Side effect: on live receipts that don't yet have a
    ``consensus_timestamp``, this populates the field on the passed-in
    receipt object from the Mirror Node response.

    Parameters
    ----------
    content_address
        The expected cert content address.
    receipt
        The HCSReceipt produced by ``submit_anchor``.
    mirror_url
        Override the Mirror Node base URL. Default reads from
        ``HEDERA_MIRROR_NODE_URL``.
    timeout_s
        HTTP request timeout in seconds.
    """
    if receipt.is_mock:
        return True  # mock anchors verify trivially

    base = (mirror_url or _mirror_node_url()).rstrip("/")
    url = f"{base}/api/v1/topics/{receipt.topic_id}/messages/{receipt.sequence_number}"

    try:
        r = httpx.get(url, timeout=timeout_s)
    except httpx.RequestError:
        return False
    if r.status_code != 200:
        return False

    data = r.json()
    encoded = data.get("message", "")
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False

    if decoded != content_address:
        return False

    # Backfill consensus_timestamp on the receipt (informational).
    if receipt.consensus_timestamp is None:
        ts = data.get("consensus_timestamp")
        if ts:
            receipt.consensus_timestamp = ts

    return True
