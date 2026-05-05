"""TaskSpec — the dual-signed work-acceptance contract.

Implements the VTEAI ``TaskSpec`` interface (``pitch/VTEAI-DRAFT.md``) as a
Pydantic model. A ``TaskSpec`` is the buyer's commitment to pay for work
that, when delivered with a valid attestation, will release escrow.

Lifecycle
---------

1. Buyer drafts ``TaskSpec`` with their public key and the work parameters
   (task_type, inputs, expected_output_schema, price_drops, deadline).
2. Buyer optionally signs (``signature_buyer``); pre-signed specs are
   "offers" awaiting seller acceptance.
3. Negotiation phase (``agentlevy/protocol/negotiate.py``, future): seller
   may counter-propose modifications. Each negotiation turn is itself a
   signed object referencing the prior spec.
4. Seller accepts and signs (``signature_seller``). The fully-signed spec
   is the work-acceptance contract.
5. Buyer creates escrow on the chosen chain, with a hashlock on the
   expected final-cert content address.
6. Seller performs the work and produces a ``DerivationCert`` (see
   ``derivation_cert.py``) that references this spec.
7. Settlement: cert hash matches escrow hashlock -> funds release.

Discipline
----------

* Signatures are **detached** (separate fields), never embedded in
  canonical bytes. ``to_canonical_bytes()`` excludes the signature
  fields so canonical bytes remain stable across the sign/verify cycle.
* Public keys are stored as 64-char hex strings for JSON-LD friendliness.
* The ``spec_triad`` is a cache of the content address; it's recomputable
  at any time from ``to_canonical_bytes()``. Verifiers should always
  recompute rather than trust the stored triad.
* Field names align with VTEAI vocabulary where possible. Specifically:
  ``task_id``, ``task_type``, ``buyer_pubkey``, ``seller_pubkey``,
  ``price_drops``, ``deadline`` map onto VTEAI's standard fields.

UOR Passport alignment
----------------------

The model serializes to JSON-LD using ``https://uor.foundation/contexts/uor-v1.jsonld``
as the ``@context`` and ``cert:TaskSpec`` (or comparable) as ``@type``.
This makes the spec directly inspectable by any UOR-aware client. Content
address is computed via the project's standard
``compute_triad(to_canonical_bytes(spec_dict))`` pipeline, byte-identical
to what UOR MCP would produce for the same canonical bytes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentlevy.primitives.canonical import to_canonical_bytes
from agentlevy.primitives.signing import (
    Keypair,
    PublicKeyBytes,
    SignatureBytes,
    public_key_hex,
    sign,
    signature_hex,
    verify,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Allowed task_type values for the demo. Phase 2.5 may extend.
KYC_BENEFICIAL_OWNERSHIP = "kyc.beneficial_ownership_verify"
KYC_SANCTIONS_SCREEN = "kyc.sanctions_screen"
ALLOWED_TASK_TYPES = frozenset({KYC_BENEFICIAL_OWNERSHIP, KYC_SANCTIONS_SCREEN})

#: Allowed settlement-currency values. RLUSD is the project default per the
#: Phase 2.8 decision (see project memory: stronger pitch for an enterprise
#: KYC-compliance demo than crypto-native XRP). XRP remains permitted as a
#: fallback for environments where RLUSD trustline isn't established.
CURRENCY_RLUSD = "RLUSD"
CURRENCY_XRP = "XRP"
ALLOWED_CURRENCIES = frozenset({CURRENCY_RLUSD, CURRENCY_XRP})


# ---------------------------------------------------------------------------
# Sub-model: input reference
# ---------------------------------------------------------------------------

class InputRef(BaseModel):
    """A reference to an input the task will operate on.

    Per VTEAI: tasks reference their inputs by content address, not by
    inline content. This decouples spec size from input size.
    """
    model_config = ConfigDict(frozen=False, extra="forbid")

    description: str = Field(..., min_length=1, description="Human-readable label.")
    content_address: str = Field(
        ...,
        pattern=r"^sha256:[0-9a-f]{64}$",
        description="UOR-Passport-compatible content address (sha256: prefix + 64 hex).",
    )


# ---------------------------------------------------------------------------
# Main model
# ---------------------------------------------------------------------------

class TaskSpec(BaseModel):
    """A VTEAI TaskSpec.

    Build with ``TaskSpec(...)`` directly, then sign with
    :meth:`sign_buyer` and :meth:`sign_seller` once both parties agree.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    # --- Identity ---
    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID; assigned at construction.",
    )
    task_type: str = Field(..., description="One of ALLOWED_TASK_TYPES.")

    # --- Inputs / expected output ---
    inputs: list[InputRef] = Field(default_factory=list, description="Input content references.")
    expected_output_schema: dict = Field(
        default_factory=dict,
        description="JSON Schema describing the output shape (Pydantic-friendly).",
    )

    # --- Settlement ---
    price_drops: int = Field(
        ...,
        ge=1,
        description="Amount in the chain's smallest unit (XRP drops for "
                    "XRPL-native; equivalent for RLUSD trustline amounts).",
    )
    chain: str = Field(default="xrpl", description="Settlement chain identifier.")
    currency: str = Field(
        default=CURRENCY_RLUSD,
        description="Settlement currency. Defaults to RLUSD per Phase 2.8 "
                    "decision; XRP also permitted. See ALLOWED_CURRENCIES.",
    )

    # --- Parties ---
    buyer_pubkey: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="64-hex Ed25519 public key.",
    )
    seller_pubkey: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="64-hex Ed25519 public key.",
    )

    # --- Time ---
    deadline: datetime = Field(..., description="UTC; spec expires after this.")

    # --- Signatures (detached; populated post-construction) ---
    signature_buyer: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{128}$",
        description="128-hex Ed25519 signature from buyer.",
    )
    signature_seller: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{128}$",
        description="128-hex Ed25519 signature from seller.",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("task_type")
    @classmethod
    def _valid_task_type(cls, v: str) -> str:
        if v not in ALLOWED_TASK_TYPES:
            allowed = ", ".join(sorted(ALLOWED_TASK_TYPES))
            raise ValueError(f"task_type must be one of [{allowed}], got {v!r}")
        return v

    @field_validator("currency")
    @classmethod
    def _valid_currency(cls, v: str) -> str:
        if v not in ALLOWED_CURRENCIES:
            allowed = ", ".join(sorted(ALLOWED_CURRENCIES))
            raise ValueError(f"currency must be one of [{allowed}], got {v!r}")
        return v

    @field_validator("deadline")
    @classmethod
    def _deadline_has_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("deadline must be timezone-aware (UTC preferred)")
        return v.astimezone(timezone.utc)

    # ------------------------------------------------------------------
    # Canonical bytes
    # ------------------------------------------------------------------

    def to_canonical_bytes(self) -> bytes:
        """Canonical bytes excluding signatures.

        This is what gets signed by buyer and seller. Excluding signatures
        from the canonicalization makes the bytes stable across the
        sign/verify cycle: the same dict produces the same bytes whether
        signatures are filled in or not.
        """
        d = self.model_dump(mode="json", exclude={"signature_buyer", "signature_seller"})
        return to_canonical_bytes(d)

    def content_address(self) -> str:
        """UOR-Passport-style content address (sha256: + 64 hex).

        Computed from canonical bytes excluding signatures. Verifies
        against UOR MCP's ``uor.encode_address`` for the same canonical
        bytes (algorithm: SHA-256 of jcs-rfc8785+nfc canonical form).
        """
        import hashlib
        digest = hashlib.sha256(self.to_canonical_bytes()).hexdigest()
        return f"sha256:{digest}"

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def sign_buyer(self, keypair: Keypair) -> "TaskSpec":
        """Sign as the buyer. Mutates ``self.signature_buyer`` in place.

        Raises if the keypair's public key doesn't match ``buyer_pubkey``
        — prevents accidental signing-as-the-wrong-party.
        """
        if public_key_hex(keypair) != self.buyer_pubkey:
            raise ValueError(
                "Keypair public key does not match buyer_pubkey on this spec"
            )
        sig = sign(self.to_canonical_bytes(), keypair)
        self.signature_buyer = signature_hex(sig)
        return self

    def sign_seller(self, keypair: Keypair) -> "TaskSpec":
        """Sign as the seller. Mutates ``self.signature_seller`` in place."""
        if public_key_hex(keypair) != self.seller_pubkey:
            raise ValueError(
                "Keypair public key does not match seller_pubkey on this spec"
            )
        sig = sign(self.to_canonical_bytes(), keypair)
        self.signature_seller = signature_hex(sig)
        return self

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_buyer_signature(self) -> bool:
        """Return True iff the buyer signature is present and valid."""
        if self.signature_buyer is None:
            return False
        return _verify_hex_sig(
            self.to_canonical_bytes(),
            self.signature_buyer,
            self.buyer_pubkey,
        )

    def verify_seller_signature(self) -> bool:
        """Return True iff the seller signature is present and valid."""
        if self.signature_seller is None:
            return False
        return _verify_hex_sig(
            self.to_canonical_bytes(),
            self.signature_seller,
            self.seller_pubkey,
        )

    def is_fully_signed(self) -> bool:
        """Return True iff both parties have signed and both sigs verify."""
        return self.verify_buyer_signature() and self.verify_seller_signature()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_hex_sig(canonical_bytes: bytes, sig_hex: str, pub_hex: str) -> bool:
    """Verify a hex-encoded signature against hex-encoded public key."""
    try:
        sig = bytes.fromhex(sig_hex)
        pub = bytes.fromhex(pub_hex)
    except ValueError:
        return False
    if len(sig) != 64 or len(pub) != 32:
        return False
    return verify(canonical_bytes, sig, pub)
