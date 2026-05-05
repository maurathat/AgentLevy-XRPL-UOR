"""Pydantic schemas for LLM-produced KYC artifacts.

These define the structured outputs the LLM is asked to produce. The
LLM client will validate responses against these models, so a malformed
LLM output raises a clear error at the parse boundary instead of
propagating bad data into the cert chain.

Used by:
  * agentlevy/llm/client.py — passes the schema to Anthropic's tool-use
    API as a JSON Schema and validates the response.
  * agentlevy/agents/compliance.py (Phase 2.5) — calls the client with
    BeneficialOwnershipExtraction as the expected output schema.
  * agentlevy/agents/sanctions.py (Phase 2.5) — calls the client with
    SanctionsScreenResult as the expected output schema.

Naming aligns with the VTEAI vocabulary where applicable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Beneficial ownership extraction
# (kyc.beneficial_ownership_verify)
# ---------------------------------------------------------------------------

class BeneficialOwner(BaseModel):
    """One named individual or entity holding ownership in the subject."""

    model_config = ConfigDict(frozen=False, extra="forbid")

    name: str = Field(..., min_length=1, description="Full legal name of the owner.")
    ownership_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of beneficial ownership, 0.0 to 100.0.",
    )
    role: Optional[str] = Field(
        default=None,
        description="Role descriptor (e.g., 'Director', 'Trustee', 'UBO'). "
                    "Optional; some disclosures omit it.",
    )


class BeneficialOwnershipExtraction(BaseModel):
    """Structured output of the beneficial-ownership extraction task.

    The LLM reads a corporate-disclosure document and emits this object.
    The compliance agent then signs a DerivationCert whose
    output_address is the content address of this object's canonical bytes.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    subject_entity: str = Field(
        ...,
        min_length=1,
        description="Legal name of the entity whose ownership is being extracted.",
    )
    owners: list[BeneficialOwner] = Field(
        ...,
        description="All beneficial owners disclosed in the source document.",
    )
    extraction_notes: Optional[str] = Field(
        default=None,
        description="Free-form notes the LLM emits about the extraction "
                    "(e.g., 'document specifies UBOs only', 'percentages do "
                    "not sum to 100 in source'). Audited but not "
                    "machine-acted-upon.",
    )


# ---------------------------------------------------------------------------
# Sanctions screening
# (kyc.sanctions_screen)
# ---------------------------------------------------------------------------

SanctionsHitSeverity = Literal["clear", "weak_match", "strong_match", "exact_match"]


class SanctionsHit(BaseModel):
    """One name screened against the sanctions list, with the result."""

    model_config = ConfigDict(frozen=False, extra="forbid")

    name_screened: str = Field(..., min_length=1)
    severity: SanctionsHitSeverity = Field(
        ...,
        description="Match severity: clear (no hit), weak/strong/exact match.",
    )
    matched_sanctions_entry: Optional[str] = Field(
        default=None,
        description="The sanctions-list entry that produced the match. None if clear.",
    )
    notes: Optional[str] = Field(default=None)


class SanctionsScreenResult(BaseModel):
    """Structured output of the sanctions-screening task.

    Sanctions agent signs a DerivationCert with this object's content
    address as output_address. Compliance agent then references the cert
    via subcontract_cert_addresses on its own cert.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    sanctions_list_version: str = Field(
        ...,
        description="Identifier of the sanctions list snapshot used "
                    "(e.g., 'OFAC-SDN-2026-04-15'). Auditable.",
    )
    screened_at: datetime = Field(
        ...,
        description="UTC timestamp of when the screen was performed.",
    )
    hits: list[SanctionsHit] = Field(
        ...,
        description="One entry per name screened, including clear results "
                    "(no false negatives via omission).",
    )

    def has_any_hit(self) -> bool:
        """Convenience: True iff any name produced anything other than 'clear'."""
        return any(h.severity != "clear" for h in self.hits)


# ---------------------------------------------------------------------------
# Negotiation messages (Phase 2.6 — bounded-turn protocol)
# ---------------------------------------------------------------------------

NegotiationAction = Literal["request", "accept", "counter", "cancel"]


class NegotiationTurn(BaseModel):
    """One turn in the bounded buyer<->compliance negotiation.

    Each turn is itself a signable artifact (Phase 2.6 will wire signing
    into the protocol layer). Defining the schema now means the agent
    layer can produce these without inventing ad-hoc structures.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    turn_index: int = Field(..., ge=1, le=4, description="1-indexed turn number; max 4.")
    actor: Literal["buyer", "compliance"] = Field(
        ...,
        description="Which agent emitted this turn.",
    )
    action: NegotiationAction = Field(...)
    message: str = Field(
        ...,
        description="Human-readable explanation. Audited; can be empty.",
    )
    proposed_changes: Optional[dict] = Field(
        default=None,
        description="On 'counter', a sparse dict of TaskSpec field "
                    "modifications (e.g., {'price_drops': 2_000_000, "
                    "'deadline': '2026-05-08T00:00:00Z'}).",
    )
