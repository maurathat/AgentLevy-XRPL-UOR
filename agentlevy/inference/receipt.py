"""Inference receipts — :class:`DerivationCert` builders for LLM completions.

Maps one inference call onto one signed cert. The cert is the verifiable
receipt the agent gets in exchange for the RLUSD payment.

Shape mapping
-------------

============================  ==============================================
:class:`DerivationCert` field  What it holds for inference
============================  ==============================================
``task_spec_address``         Request UOR address (model+prompt+temperature+
                              hour_bucket). The "spec the work fulfills."
``input_addresses``           ``[request_uor_addr]`` — the request itself is
                              the only input.
``output_address``            UOR address of the completion text.
``operation_description``     ``{operation: "llm.inference.complete",
                              model: ..., temperature: ..., hour_bucket: ...,
                              completion_preview: ...}``. Enough to reconstruct
                              what was asked + previewed without revealing
                              the full output bytes if PII concerns require it.
``subcontract_cert_addresses`` ``[]`` for leaf inferences. Nonempty when
                              chained (RAG sub-call, tool use, etc.).
``seller_pubkey``             Server's Ed25519 public key (the entity that
                              ran the inference).
``signature``                 Server-signed ``to_canonical_bytes()``.
``hcs_receipt``               Populated by :meth:`DerivationCert.anchor` after
                              the cert is signed.
============================  ==============================================

The XRPL Payment txid that settled this cert and the UOR Foundation MCPS
receipt are recorded on the cert via attached metadata — see
:func:`attach_settlement_metadata`. Those are post-signing facts, kept
detached from the canonical bytes so re-canonicalization stays stable.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from agentlevy.inference.canonical import (
    InferenceRequestDict,
    compute_request_address,
)
from agentlevy.primitives.canonical import to_canonical_bytes
from agentlevy.primitives.cert import DerivationCert


# ---------------------------------------------------------------------------
# Completion addressing
# ---------------------------------------------------------------------------

def compute_completion_address(completion_text: str) -> str:
    """UOR address of an LLM completion string.

    The completion is wrapped in ``{"completion": ...}`` before canonicalization
    so the address is over a structured artifact, not raw text. Two servers
    that produce identical completion strings produce identical addresses.

    Returns
    -------
    str
        ``sha256:<64hex>``.
    """
    canon = to_canonical_bytes({"completion": completion_text})
    return f"sha256:{hashlib.sha256(canon).hexdigest()}"


# ---------------------------------------------------------------------------
# Cert builder
# ---------------------------------------------------------------------------

OPERATION_TYPE = "llm.inference.complete"

PREVIEW_CHARS = 120


def build_inference_cert(
    *,
    request: InferenceRequestDict,
    completion_text: str,
    server_pubkey_hex: str,
    request_address: Optional[str] = None,
    completion_address: Optional[str] = None,
) -> DerivationCert:
    """Build an unsigned :class:`DerivationCert` for an inference completion.

    Caller must sign the returned cert with the server's keypair before
    persisting or returning it to the agent. The keypair's public key must
    equal ``server_pubkey_hex`` (the :meth:`DerivationCert.sign` method
    enforces this).

    Parameters
    ----------
    request
        The canonicalizable inference request dict
        (from :func:`agentlevy.inference.canonical.build_request_dict`).
    completion_text
        The full LLM completion. Stored only as a UOR address + preview;
        the full text is kept out-of-band.
    server_pubkey_hex
        64-hex Ed25519 public key of the inference server.
    request_address, completion_address
        Optional pre-computed addresses. If omitted, recomputed from the
        inputs. Passing them is a micro-optimization for the server path
        where the request address is already known from the 402 step.
    """
    if request_address is None:
        request_address = compute_request_address(request)
    if completion_address is None:
        completion_address = compute_completion_address(completion_text)

    preview = completion_text[:PREVIEW_CHARS]
    if len(completion_text) > PREVIEW_CHARS:
        preview = preview + "…"

    return DerivationCert(
        task_spec_address=request_address,
        input_addresses=[request_address],
        output_address=completion_address,
        operation_description={
            "operation": OPERATION_TYPE,
            "model": request["model"],
            "temperature": request["temperature"],
            "hour_bucket": request["hour_bucket"],
            "completion_preview": preview,
            "completion_length_chars": len(completion_text),
        },
        seller_pubkey=server_pubkey_hex,
    )


# ---------------------------------------------------------------------------
# Settlement metadata (detached from signed bytes)
# ---------------------------------------------------------------------------

class SettlementMetadata:
    """Post-signing facts about how a cert was settled and witnessed.

    Kept on the cert as an attached attribute (not a Pydantic field) so it
    does not affect :meth:`DerivationCert.to_canonical_bytes` and therefore
    does not invalidate the seller signature. The three sources of truth:

    * ``xrpl_payment_txid``  — XRPL Payment that settled this inference.
    * ``xrpl_royalty_txid``  — XRPL Payment that routed the royalty to the
      model NFT owner. ``None`` if the royalty has not (yet) been dispatched.
    * ``uor_mcps_receipt``   — The full ``_meta.uor.mcps.receipt`` value
      from the UOR Foundation MCP server's response, an ed25519-signed
      attestation that the server computed the address we're using.
    """

    __slots__ = ("xrpl_payment_txid", "xrpl_royalty_txid", "uor_mcps_receipt")

    def __init__(
        self,
        *,
        xrpl_payment_txid: Optional[str] = None,
        xrpl_royalty_txid: Optional[str] = None,
        uor_mcps_receipt: Optional[dict] = None,
    ) -> None:
        self.xrpl_payment_txid = xrpl_payment_txid
        self.xrpl_royalty_txid = xrpl_royalty_txid
        self.uor_mcps_receipt = uor_mcps_receipt

    def to_audit_dict(self) -> dict:
        """Serialize for the audit trail dump at the end of the demo."""
        return {
            "xrpl_payment_txid": self.xrpl_payment_txid,
            "xrpl_royalty_txid": self.xrpl_royalty_txid,
            "uor_mcps_receipt_present": self.uor_mcps_receipt is not None,
        }


def attach_settlement_metadata(
    cert: DerivationCert,
    metadata: SettlementMetadata,
) -> None:
    """Stamp settlement metadata onto a (signed) cert. Detached from canonical bytes."""
    object.__setattr__(cert, "_settlement_metadata", metadata)


def get_settlement_metadata(cert: DerivationCert) -> Optional[SettlementMetadata]:
    return getattr(cert, "_settlement_metadata", None)
