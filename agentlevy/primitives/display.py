"""Display helpers for triads.

The protocol layer always operates on full ``Q(31)`` (32-byte) triads. Audit
trail printers SHOULD use these helpers to render the triad in a form a
human can scan quickly.

**Never use these helpers to produce inputs to signing, hashing, or content
addressing.** That is the protocol layer's job and uses raw ``Triad``
objects from ``agentlevy.prism_layer.triad``. These display strings are
lossy projections.

Why hybrid display
------------------

The protocol-layer width is 32 bytes (UOR-canonical, see
``agentlevy/prism_layer/triad.py``). On stage, printing 32-byte tuples in a
console makes the audit trail visually noisy. The hybrid pattern keeps
the protocol clean while letting the demo stay readable:

* Console output uses ``compact(triad.datum)`` to show ``a1b2c3d4...`` form
* Or ``glyph(triad.datum)`` to show the 32-character Braille form
* Or ``hex_full(triad.datum)`` for diagnostic / cross-system comparison
"""

from __future__ import annotations


def glyph(datum: tuple[int, ...]) -> str:
    """Render a triad's ``datum`` as a Braille glyph string.

    Each byte ``b`` in ``[0, 255]`` maps to ``chr(0x2800 + b)``. This is the
    same encoding UOR uses for ``store:uorAddress.u:glyph`` in published
    cert envelopes (see ``mcp/example-module-certificate.json``).

    A 32-byte datum becomes a 32-character string.
    """
    return "".join(chr(0x2800 + b) for b in datum)


def compact(datum: tuple[int, ...], n: int = 4) -> str:
    """Render the first ``n`` bytes of a triad's ``datum`` as hex + ellipsis.

    Useful when 32-byte full hex (64 chars) is too noisy for a console
    audit-trail line. Default ``n=4`` gives an 8-character hex prefix, like
    ``a1b2c3d4...``. If ``n`` exceeds the datum length, returns full hex.
    """
    if n <= 0 or n >= len(datum):
        return bytes(datum).hex()
    return bytes(datum[:n]).hex() + "..."


def hex_full(datum: tuple[int, ...]) -> str:
    """Full hex of a triad's ``datum``. 64 chars for a 32-byte ``Q(31)`` datum.

    Use this for cross-system comparison (logs, regulator audit, replay).
    """
    return bytes(datum).hex()
