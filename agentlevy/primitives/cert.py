"""DerivationCert — the seller's signed attestation that work was performed.

A ``DerivationCert`` is the second half of the AgentLevy protocol contract.
Where ``TaskSpec`` is the dual-signed *acceptance* of work, ``DerivationCert``
is the seller's signed *delivery*: it states "I, holder of ``seller_pubkey``,
performed operation X over inputs ``input_addresses``, producing output
``output_address``, in fulfillment of spec ``task_spec_address``."

Lifecycle
---------

1. ``TaskSpec`` is fully signed (buyer + seller); escrow is funded with a
   hashlock on the expected final-cert content address.
2. Seller performs the work locally (LLM call, sanctions screen, etc.).
3. Seller constructs ``DerivationCert`` referencing the spec, the inputs
   actually consumed, the output produced, and a structured
   ``operation_description``.
4. If the work was sub-contracted (e.g. compliance agent calls sanctions
   agent), the parent cert lists the child cert's content address in
   ``subcontract_cert_addresses`` — producing a content-addressed chain.
5. Seller signs the cert with their keypair (must match ``seller_pubkey``).
6. Buyer (or escrow) verifies: signature is valid, input/output content
   addresses resolve, the cert's own content address matches the escrow
   hashlock — funds release.

Discipline
----------

* Signatures are **detached** (``signature`` is excluded from
  ``to_canonical_bytes``). Same invariant as ``TaskSpec``: re-canonicalizing
  a signed cert produces the same bytes that were originally signed.
* All cross-references are by **content address** (``sha256:<64-hex>``),
  never by UUID. Content addresses are immutable; UUIDs are not. The whole
  point of the protocol is that a verifier holding only public keys + the
  cert chain can rebuild every link without trusting any agent's database.
* ``operation_description`` is a free-form dict, but conventionally has
  ``operation``, ``inputs_described``, and ``outputs_described`` keys.
  Validation of its shape lives at the agent layer, not here, because
  different ``operation`` types have different schemas.
* Subcontract references are flat content addresses, not nested cert
  objects. This keeps each cert independently transportable: a verifier
  can fetch each cert in the chain by its address and verify each
  signature in isolation.

UOR Passport alignment
----------------------

Serializes to JSON-LD using ``https://uor.foundation/contexts/uor-v1.jsonld``
as ``@context`` and ``cert:DerivationCert`` as ``@type``. Content address is
computed via the project's standard ``sha256(to_canonical_bytes(...))``
pipeline, byte-identical to what UOR MCP would produce for the same
canonical bytes.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentlevy.hedera_layer.anchor import (
    HCSReceipt,
    submit_anchor,
    verify_anchor as _verify_hcs_anchor,
)
from agentlevy.primitives.canonical import to_canonical_bytes
from agentlevy.primitives.signing import (
    Keypair,
    public_key_hex,
    sign,
    signature_hex,
    verify,
)


# ---------------------------------------------------------------------------
# Pattern reused by every content-address field
# ---------------------------------------------------------------------------

CONTENT_ADDRESS_PATTERN = r"^sha256:[0-9a-f]{64}$"


# ---------------------------------------------------------------------------
# Main model
# ---------------------------------------------------------------------------

class DerivationCert(BaseModel):
    """A seller's signed attestation of work performed against a TaskSpec.

    Build with ``DerivationCert(...)`` once the work is complete, then call
    :meth:`sign` with the seller's keypair. Verify with
    :meth:`verify_signature`.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    # --- Identity ---
    cert_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID; assigned at construction. Not authoritative — "
                    "downstream code references certs by content_address().",
    )

    # --- Back-reference to the spec this cert fulfills ---
    task_spec_address: str = Field(
        ...,
        pattern=CONTENT_ADDRESS_PATTERN,
        description="Content address of the TaskSpec this cert delivers on.",
    )

    # --- Inputs the seller actually consumed ---
    input_addresses: list[str] = Field(
        default_factory=list,
        description="Content addresses of the inputs the seller consumed. "
                    "Should be a subset of the spec's declared inputs; the "
                    "verifier checks alignment.",
    )

    # --- Output the seller produced ---
    output_address: str = Field(
        ...,
        pattern=CONTENT_ADDRESS_PATTERN,
        description="Content address of the produced output document.",
    )

    # --- Structured operation description ---
    operation_description: dict = Field(
        default_factory=dict,
        description="Free-form dict; conventionally includes 'operation', "
                    "'inputs_described', 'outputs_described'. Schema is "
                    "operation-specific; this primitive does not validate.",
    )

    # --- Subcontracting chain (by content address, never UUID) ---
    subcontract_cert_addresses: list[str] = Field(
        default_factory=list,
        description="Content addresses of any child certs whose work this "
                    "cert subsumes. Empty for leaf certs.",
    )

    # --- Signer ---
    seller_pubkey: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="64-hex Ed25519 public key of the cert signer.",
    )

    # --- Detached signature (populated post-construction) ---
    signature: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{128}$",
        description="128-hex Ed25519 signature over to_canonical_bytes().",
    )

    # --- Time ---
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC; when the work was attested. Naive datetimes "
                    "rejected.",
    )

    # --- Hedera HCS audit anchor (detached; populated post-signing) ---
    hcs_receipt: Optional[HCSReceipt] = Field(
        default=None,
        description="HCS topic receipt produced by submitting this cert's "
                    "content_address to the configured Hedera Consensus "
                    "Service topic. Detached from canonical bytes — "
                    "anchoring happens AFTER signing, same invariant as "
                    "the signature field. None until anchor() is called.",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("input_addresses", "subcontract_cert_addresses")
    @classmethod
    def _all_addresses_well_formed(cls, v: list[str]) -> list[str]:
        import re
        pat = re.compile(CONTENT_ADDRESS_PATTERN)
        for a in v:
            if not pat.match(a):
                raise ValueError(
                    f"address {a!r} does not match {CONTENT_ADDRESS_PATTERN}"
                )
        return v

    @field_validator("timestamp")
    @classmethod
    def _timestamp_has_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC preferred)")
        return v.astimezone(timezone.utc)

    # ------------------------------------------------------------------
    # Canonical bytes
    # ------------------------------------------------------------------

    def to_canonical_bytes(self) -> bytes:
        """Canonical bytes excluding signature AND hcs_receipt.

        Same invariant as TaskSpec: detached fields stay detached so
        canonical bytes are stable across the sign / anchor / verify
        cycles. The HCS receipt is a post-signing fact about the cert
        (when it was anchored on Hedera), not part of what the seller
        signed.
        """
        d = self.model_dump(mode="json", exclude={"signature", "hcs_receipt"})
        return to_canonical_bytes(d)

    def content_address(self) -> str:
        """UOR-Passport-style content address (sha256: + 64 hex)."""
        digest = hashlib.sha256(self.to_canonical_bytes()).hexdigest()
        return f"sha256:{digest}"

    # ------------------------------------------------------------------
    # Signing / verification
    # ------------------------------------------------------------------

    def sign(self, keypair: Keypair) -> "DerivationCert":
        """Sign the cert. Mutates ``self.signature`` in place.

        Raises if the keypair's public key doesn't match ``seller_pubkey``
        — prevents accidentally signing as the wrong identity.
        """
        if public_key_hex(keypair) != self.seller_pubkey:
            raise ValueError(
                "Keypair public key does not match seller_pubkey on this cert"
            )
        sig = sign(self.to_canonical_bytes(), keypair)
        self.signature = signature_hex(sig)
        return self

    def verify_signature(self) -> bool:
        """Return True iff the signature is present and valid."""
        if self.signature is None:
            return False
        try:
            sig = bytes.fromhex(self.signature)
            pub = bytes.fromhex(self.seller_pubkey)
        except ValueError:
            return False
        if len(sig) != 64 or len(pub) != 32:
            return False
        return verify(self.to_canonical_bytes(), sig, pub)

    # ------------------------------------------------------------------
    # Hedera HCS audit anchor
    # ------------------------------------------------------------------

    def anchor(
        self,
        *,
        topic_id: Optional[str] = None,
        force_mock: Optional[bool] = None,
    ) -> "DerivationCert":
        """Submit this cert's content_address to Hedera HCS and store the receipt.

        Anchoring happens AFTER signing — the HCS receipt is a sibling
        fact about when the cert was witnessed by Hedera consensus, not
        part of the signed bytes.

        Mutates ``self.hcs_receipt`` in place. Idempotent in mock mode
        (same content_address always produces the same mock receipt);
        live anchoring submits a new transaction each call (so callers
        should check ``hcs_receipt is None`` before re-anchoring).

        Parameters
        ----------
        topic_id
            Override the configured HCS topic. Defaults to env var
            ``HEDERA_HCS_TOPIC_ID``.
        force_mock
            Force mock or live mode. Defaults to env var ``MOCK_HEDERA``.
        """
        receipt = submit_anchor(
            self.content_address(),
            topic_id=topic_id,
            force_mock=force_mock,
        )
        self.hcs_receipt = receipt
        return self

    def verify_anchor(self, **kwargs) -> bool:
        """Verify the cert's HCS anchor against the Mirror Node.

        Returns ``False`` if no anchor has been recorded; otherwise
        delegates to :func:`agentlevy.hedera_layer.anchor.verify_anchor`
        which re-fetches the topic message via Mirror Node REST and
        confirms it matches this cert's content_address.

        Mock receipts always verify True (they're fixtures, not facts).
        """
        if self.hcs_receipt is None:
            return False
        return _verify_hcs_anchor(self.content_address(), self.hcs_receipt, **kwargs)
