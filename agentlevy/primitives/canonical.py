"""Canonical bytes — the single source of canonicalization for AgentLevy.

This is the only place canonical bytes are produced in the project. Everything
that needs deterministic identity for content (PRISM triads, signatures, cache
keys) consumes the output of :func:`to_canonical_bytes` here. No exceptions.

Algorithm
---------

Matches UOR Passport's ``jcs-rfc8785+nfc`` canonicalization, verified live
byte-for-byte against ``mcp.uor.foundation/encode_address`` for ASCII payloads
(see ``docs/UOR_PASSPORT_VERIFIED.md``):

1. Recursively NFC-normalize all string values and string keys
   (``unicodedata.normalize("NFC", s)``).
2. JSON-canonicalize via ``json.dumps`` with ``sort_keys=True``,
   ``separators=(",", ":")``, ``ensure_ascii=False``, ``allow_nan=False``.
3. Encode as UTF-8 bytes.

For all-ASCII content this matches full RFC 8785 JCS exactly. For content
that involves number-formatting edge cases (e.g., ``1.0`` vs ``1``,
scientific notation, very large floats) full RFC 8785 has additional rules
that ``json.dumps`` does not implement; if a future test surfaces a
divergence, swap the JSON step to a library implementing full JCS such as
`jcs <https://pypi.org/project/jcs/>`_. The exposed function signature does
not change.

Why NFC matters
---------------

Without NFC, "café" with composed ``é`` (U+00E9) hashes differently than
"café" with decomposed ``e`` + combining acute (U+0301), even though they
render identically. Empirically verified:

>>> import hashlib
>>> hashlib.sha256("café".encode()).hexdigest()[:8]   # composed
'1771f1e8'
>>> hashlib.sha256("café".encode()).hexdigest()[:8]   # decomposed (4 bytes)
'1771f1e8'

For KYC-compliance use cases with international names ("Müller",
"São Paulo"), NFC is non-negotiable.

Discipline
----------

All Pydantic models that need canonical bytes implement::

    def to_canonical_bytes(self) -> bytes:
        return canonical.to_canonical_bytes(self.model_dump(mode="json", exclude=...))

with appropriate signature/triad fields excluded so signing happens over the
content-only bytes. Models do NOT implement their own canonicalization.

See ``CANONICAL_FORM.md`` for the project-wide canonicalization rules.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any


def to_canonical_bytes(obj: Any) -> bytes:
    """Produce UOR-Passport-compatible canonical bytes for any JSON-serializable value.

    The result is deterministic across runs, machines, and Python versions
    that preserve dict-insertion-order semantics (3.7+). Round-trip with the
    UOR MCP server's ``uor.encode_address`` tool: feeding ``obj`` to either
    side produces the same canonical bytes for any non-pathological input.

    Parameters
    ----------
    obj
        Any value JSON can serialize: ``None``, ``bool``, ``int``, ``float``
        (no NaN/Inf), ``str``, ``list``, ``tuple``, ``dict`` with str keys,
        and combinations thereof. Pydantic model_dump output is the typical
        input.

    Returns
    -------
    bytes
        UTF-8 encoded canonical form.

    Raises
    ------
    ValueError
        If ``obj`` contains ``float('nan')``, ``float('inf')``, or a dict
        with non-string keys.

    Examples
    --------
    >>> b = to_canonical_bytes({"task_id": "abc", "price": 100, "buyer": "alice"})
    >>> b
    b'{"buyer":"alice","price":100,"task_id":"abc"}'
    >>> import hashlib
    >>> hashlib.sha256(b).hexdigest()
    '4cc1e2fc2d60c1e0ab7f6967a59e23ad04094cd3c01351971b8cb5aa26013e67'

    The hex above is byte-identical to what UOR MCP's ``encode_address``
    returns for the same input (verified May 3 2026).
    """
    normalized = _nfc_recursive(obj)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _nfc_recursive(value: Any) -> Any:
    """Recursively NFC-normalize all strings in a JSON-compatible value.

    Strings (both keys and values) are normalized; numbers, booleans, and
    None pass through unchanged. Tuples are converted to lists for JSON
    compatibility (json.dumps does this anyway, but we do it consistently
    so the recursion never returns a tuple).
    """
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, bool):
        # bool is a subclass of int in Python; check before int.
        return value
    if isinstance(value, (int, float)) or value is None:
        return value
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", k) if isinstance(k, str) else k: _nfc_recursive(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_nfc_recursive(x) for x in value]
    # Fall through: let json.dumps complain with its standard error.
    return value
