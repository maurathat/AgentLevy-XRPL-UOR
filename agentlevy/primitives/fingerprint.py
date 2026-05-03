"""Bridge between canonical bytes and PRISM ring elements.

This is a Phase 0 placeholder. The implementation is sketched here for
reference and will be exercised by ``scripts/test_prism.py``. Real
production-shape code lands in Phase 2.3 alongside ``canonical.py``.

The bridge exists because PRISM's engines operate on integers in a finite
modular ring (``Q(3)`` = 32-bit, 4,294,967,296 states). AgentLevy content
(task specs, derivation certs, LLM outputs) is structured data that vastly
exceeds 32 bits. We need a deterministic, collision-resistant projection from
arbitrary canonical bytes to a ring element.

Pattern
-------

    canonical_bytes (any length, produced by canonical.py)
        |
        v
    sha256() -> 32-byte digest                 # collision-resistant
        |
        v
    take low N bytes (N = quantum + 1)         # explicit truncation
        |
        v
    int.from_bytes(low_N_bytes, "big")          # ring element in [0, 2^(8N))
        |
        v
    engine.triad(ring_element) -> Triad         # PRISM coordinate

Why explicit truncation
-----------------------

``engine.triad(int)`` automatically reduces an int mod the engine's cycle.
Passing the full 256-bit SHA-256 integer to ``Q(3)`` would silently take the
low 32 bits. We do the truncation ourselves so the operation is visible in
the audit trail and so the same ``digest -> ring_element`` mapping is
reproducible by anyone reading the code, not buried inside PRISM's
``_normalize``.

Collision resistance
--------------------

For ``Q(3)`` (32-bit ring), birthday-bound collision probability is ~50%
after ~65,536 distinct content items. For a hackathon demo with O(10) items
this is fine. If the demo grows or production is on the table, switch to
``Q(7)`` (64-bit, ~4 billion items before 50% birthday collision) by
changing ``DEFAULT_QUANTUM`` in ``agentlevy/prism_layer/triad.py``.

See ``CANONICAL_FORM.md`` for the project-wide canonical form discipline.
"""

from __future__ import annotations

import hashlib


def content_to_ring_element(canonical_bytes: bytes, quantum: int) -> int:
    """Project canonical bytes onto a PRISM ring element at the given quantum.

    Parameters
    ----------
    canonical_bytes : bytes
        Output of ``agentlevy.primitives.canonical.to_canonical_bytes()``.
        Never raw user input or unparsed LLM output.
    quantum : int
        PRISM quantum level (engine width = quantum + 1 bytes).

    Returns
    -------
    int
        Ring element in ``[0, 2 ** (8 * (quantum + 1)))``.

    Notes
    -----
    Deterministic. Same canonical bytes always produce the same ring element
    for the same quantum. Different canonical bytes produce different ring
    elements with probability dependent on the quantum (birthday bound).
    """
    if quantum < 0:
        raise ValueError(f"quantum must be non-negative, got {quantum}")
    width = quantum + 1
    digest = hashlib.sha256(canonical_bytes).digest()  # 32 bytes
    low_bytes = digest[-width:]  # take low N bytes (big-endian semantics → trailing bytes are low)
    return int.from_bytes(low_bytes, "big")
