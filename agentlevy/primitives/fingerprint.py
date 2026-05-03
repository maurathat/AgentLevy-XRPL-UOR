"""Bridge between canonical bytes and PRISM ring elements.

The bridge exists because PRISM's engines operate on integers in a finite
modular ring. AgentLevy content (task specs, derivation certs, LLM outputs)
is arbitrary-sized structured data. We need a deterministic, collision-
resistant projection from arbitrary canonical bytes to a ring element.

Quantum-31 alignment with UOR
-----------------------------

AgentLevy uses ``Q(31)`` (32-byte width = 256 bits), matching the canonical
UOR address width verified against published cert examples
(``mcp/example-module-certificate.json``: ``store:uorAddress.u:length: 32``).

Because this width matches SHA-256's digest size exactly, the fingerprint
function's "low N bytes" reduces to "the whole digest" at ``quantum=31`` —
no information is lost from the SHA-256, and collision resistance is the
full ~128-bit cryptographic strength of SHA-256.

Pattern
-------

    canonical_bytes (any length, produced by canonical.py)
        |
        v
    sha256() -> 32-byte digest                  # collision-resistant
        |
        v
    take low N bytes (N = quantum + 1)          # explicit truncation
        | (at Q(31) this is the whole digest;
        |  at lower quanta this is the trailing N bytes)
        v
    int.from_bytes(low_N_bytes, "big")          # ring element in [0, 2^(8N))
        |
        v
    engine.triad(ring_element) -> Triad         # PRISM coordinate

Why explicit truncation (still relevant at Q(31), even though no bytes
are dropped)
-----------------------------------------------------------------------

``engine.triad(int)`` automatically reduces an int mod the engine's cycle.
Doing the truncation ourselves makes the projection visible in the audit
trail and reproducible by anyone reading our code, instead of relying on
PRISM's ``_normalize`` to silently take the low N bytes for us. At ``Q(31)``
N happens to equal the digest length so it's a passthrough — the discipline
matters for forward compatibility if a smaller ``quantum`` is ever
re-selected (e.g., for low-bandwidth display channels).

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
