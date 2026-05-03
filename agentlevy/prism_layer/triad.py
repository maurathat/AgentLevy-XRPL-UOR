"""AgentLevy's PRISM wrapper at ``Q(31)`` (256-bit, UOR-canonical width).

The single source of truth for triad computation. Every cert, every spec,
every output goes through ``compute_triad(canonical_bytes)``.

Quantum choice
--------------

``Q(31)`` (32 bytes / 256 bits) was chosen because it matches the canonical
UOR address width verified against a real ``cert:ModuleCertificate`` example
(``mcp/example-module-certificate.json``: ``store:uorAddress.u:length: 32``).

This means AgentLevy-produced triads are byte-width-compatible with UOR
Passport Envelopes, and (when wrapped in the JSON-LD ``@context``) directly
verifiable with the live UOR MCP's ``uor.verify_passport`` tool.

It also matches SHA-256's digest width (32 bytes), so the
``content_to_ring_element`` fingerprint can pass the digest through without
truncation — collision resistance is the full SHA-256 strength.

Discipline
----------

Use ``compute_triad`` only via this module. Do not instantiate ``Q(31)``
elsewhere; we want a single shared engine for cache locality, error-message
consistency, and audit-trail provenance.

For audit-trail rendering of the resulting triad, import the display
helpers from ``agentlevy.primitives.display``. Never produce signatures or
content addresses from display strings — they are lossy projections.
"""

from __future__ import annotations

from agentlevy.primitives.fingerprint import content_to_ring_element
from vendor.prism import Q, Triad

#: AgentLevy quantum level. ``Q(31)`` => 32-byte width => UOR-canonical.
#: Documented in ``CANONICAL_FORM.md``. Do not change without re-running
#: ``scripts/test_prism.py`` and updating the spec.
QUANTUM = 31

_engine = Q(QUANTUM)
_engine.verify()  # one-time at import; raises ``CoherenceError`` on failure


def compute_triad(canonical_bytes: bytes) -> Triad:
    """Project canonical bytes onto a UOR-canonical-width triad.

    Parameters
    ----------
    canonical_bytes : bytes
        Output of ``agentlevy.primitives.canonical.to_canonical_bytes()``.
        Never raw user input or unparsed LLM output.

    Returns
    -------
    Triad
        A frozen ``Triad`` with ``.datum`` (32-byte tuple), ``.stratum``,
        ``.spectrum``, ``.total_stratum``, ``.width``.
    """
    ring_element = content_to_ring_element(canonical_bytes, QUANTUM)
    return _engine.triad(ring_element)


def engine_info() -> dict:
    """Engine metadata (for diagnostics / audit-trail headers)."""
    return {
        "quantum": _engine.quantum,
        "width_bytes": _engine.width,
        "bits": _engine.bits,
        "cycle_bits": _engine.bits,  # cycle = 2 ** bits; bits is the human-friendly value
    }
