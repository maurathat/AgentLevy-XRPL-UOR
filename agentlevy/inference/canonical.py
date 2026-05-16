"""Canonicalization for inference requests.

An inference request is a structured value with four fields the audit trail
cares about:

* ``model``         — model identifier (e.g. ``claude-haiku-4-5``)
* ``prompt``        — the user message text
* ``temperature``   — sampling temperature (0.0 by default for determinism)
* ``hour_bucket``   — UTC hour the request was issued, ISO-format
  (``2026-05-14T18:00:00+00:00``). Quantizing to hours is what makes
  two agents asking the same question within the same hour produce the
  **same UOR address**, which is the dedup key.

The address is computed via the same pipeline as the rest of the repo:
``sha256(to_canonical_bytes(request_dict))``. Verified byte-identical against
the UOR Foundation MCP's ``encode_address`` tool — see
:func:`compute_request_address` docstring for the live cross-check pattern.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from agentlevy.primitives.canonical import to_canonical_bytes


# ---------------------------------------------------------------------------
# Request shape
# ---------------------------------------------------------------------------

class InferenceRequestDict(TypedDict):
    """The canonicalizable shape of an inference request.

    Field order in this TypedDict is for documentation only — canonicalization
    is JCS-RFC8785 which sorts keys lexicographically.

    Note on ``temperature``: typed as ``int | float`` to preserve JCS number
    normalization. RFC 8785 §3.2.4 mandates that whole-number floats serialize
    as integers (``0.0`` → ``"0"``), matching ECMAScript ``Number.prototype.toString``.
    Python's ``json.dumps`` emits ``"0.0"`` for ``float(0.0)``, which would
    diverge from the UOR Foundation MCP server. :func:`build_request_dict`
    handles this by coercing whole-number floats to ints before storage.
    """
    model: str
    prompt: str
    temperature: int | float
    hour_bucket: str


# ---------------------------------------------------------------------------
# Hour bucketing
# ---------------------------------------------------------------------------

def hour_bucket_for(dt: datetime | None = None) -> str:
    """Return the UTC hour bucket as ISO string for the given (or current) time.

    Two requests in the same UTC hour produce identical bucket strings, which
    means they canonicalize to the same UOR address (given identical model +
    prompt + temperature). That's what enables cache hits across agents.

    Returns
    -------
    str
        ISO 8601 with explicit UTC offset, e.g. ``"2026-05-14T18:00:00+00:00"``.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> hour_bucket_for(datetime(2026, 5, 14, 18, 32, 11, tzinfo=timezone.utc))
    '2026-05-14T18:00:00+00:00'
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        raise ValueError("dt must be timezone-aware (UTC preferred)")
    floored = dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return floored.isoformat()


def next_hour_bucket_after(bucket_iso: str) -> str:
    """Return the bucket one hour after the given one. Useful for tests/cache TTL."""
    dt = datetime.fromisoformat(bucket_iso)
    return hour_bucket_for(dt + timedelta(hours=1))


# ---------------------------------------------------------------------------
# Request dict construction + addressing
# ---------------------------------------------------------------------------

def build_request_dict(
    *,
    model: str,
    prompt: str,
    temperature: float = 0.0,
    when: datetime | None = None,
) -> InferenceRequestDict:
    """Build the canonical request dict given a model, prompt, temperature, time.

    The returned dict is the exact thing whose JCS-canonical bytes get hashed
    to produce the request UOR address. Pass identical inputs (same model,
    same prompt, same temperature, same hour) → get an identical dict → get an
    identical address.
    """
    if not model:
        raise ValueError("model must be non-empty")
    if not prompt:
        raise ValueError("prompt must be non-empty")
    bucket = hour_bucket_for(when)
    # JCS-RFC8785 §3.2.4: whole-number floats serialize as integers.
    # The UOR Foundation MCP emits "0" for 0.0; Python's json emits "0.0".
    # Coerce to int when whole-numbered so canonical bytes match.
    t: int | float
    f = float(temperature)
    t = int(f) if f.is_integer() else f
    return InferenceRequestDict(
        model=model,
        prompt=prompt,
        temperature=t,
        hour_bucket=bucket,
    )


def compute_request_address(request: InferenceRequestDict) -> str:
    """Compute the UOR address of an inference request.

    Returns ``sha256:<64hex>`` — byte-identical to what UOR Foundation MCP's
    ``encode_address`` tool returns for the same canonical bytes.

    Live cross-check pattern (when needed for verification at demo time):

    .. code-block:: python

        # Local:
        addr_local = compute_request_address(req)

        # Foundation MCP:
        from agentlevy.inference.mcp_client import UORMCPClient
        with UORMCPClient() as cli:
            result = cli.encode_address(req)
            addr_remote = result["address"]

        assert addr_local == addr_remote  # always
    """
    canonical = to_canonical_bytes(dict(request))
    digest = hashlib.sha256(canonical).hexdigest()
    return f"sha256:{digest}"


def request_canonical_bytes(request: InferenceRequestDict) -> bytes:
    """Return the canonical bytes that hash to the request's UOR address.

    Exposed for debug + cross-check against the MCP server's ``canonical_form``
    response field.
    """
    return to_canonical_bytes(dict(request))
