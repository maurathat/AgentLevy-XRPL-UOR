"""In-process cert store with content-addressed memoization.

When a request's UOR address matches an existing entry, the server returns the
prior :class:`DerivationCert` at a discounted price. *The prior cert IS the
citation* — there is no separate cache layer because the cert itself is the
verifiable artifact. This is the demo of the deck's Slide 11 claim:
"memoization with audit — cache hits become cryptographically auditable."

Pricing tiers
-------------

For the May 16 demo we use a flat two-tier model:

* **Cache miss** — full price (``FULL_PRICE_RLUSD``). The server is doing the
  Anthropic inference; this covers the Anthropic spend + margin.
* **Cache hit** — discount price (``HIT_PRICE_RLUSD``). The server is serving
  a pre-signed cert; near-zero marginal cost.

A future split-payment model would route a fraction of every cache hit back
to the original payer ("memory commons royalty"); intentionally out of scope
for May 16 to keep the headline moment clean.

Persistence
-----------

In-process dict. Survives one server-process lifetime. The deck explicitly
acknowledges this: in production, the store would be backed by Redis / S3 /
DynamoDB / etc., but the content-addressed nature means any K/V store works
without coordination. For a hackathon demo, an in-process dict is correct.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from agentlevy.primitives.cert import DerivationCert


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

#: Full price for a cache-miss inference. RLUSD (issued IOU on XRPL).
FULL_PRICE_RLUSD = Decimal("0.010")

#: Discount price for a cache-hit inference. 10× cheaper than full price.
HIT_PRICE_RLUSD = Decimal("0.001")


def price_for(*, is_hit: bool) -> Decimal:
    """Return the RLUSD amount to charge for this request."""
    return HIT_PRICE_RLUSD if is_hit else FULL_PRICE_RLUSD


# ---------------------------------------------------------------------------
# Store entry
# ---------------------------------------------------------------------------

@dataclass
class StoreEntry:
    """A single entry in the cert store.

    ``cert``           — signed :class:`DerivationCert`, the canonical artifact.
    ``completion_text``— the full LLM completion text (kept alongside the cert
                          for serving cache hits without re-running Anthropic).
    ``stored_at``      — when the entry was first written (UTC).
    ``hit_count``      — how many times this entry has been served on cache
                          hits. Useful for the audit summary at the end.
    """

    cert: DerivationCert
    completion_text: str
    stored_at: datetime
    hit_count: int = 0


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class CertStore:
    """Thread-safe in-process cert store keyed by request UOR address.

    Usage::

        store = CertStore()
        # On cache miss, after building + signing the cert:
        store.put(request_addr, cert, completion_text)
        # On cache lookup:
        entry = store.get(request_addr)
        if entry is None:
            # cache miss → do the inference
            ...
        else:
            # cache hit → serve entry.cert directly, increment counter
            ...
    """

    def __init__(self) -> None:
        self._entries: dict[str, StoreEntry] = {}
        self._lock = threading.RLock()

    # --- core ops ---

    def get(self, request_address: str) -> Optional[StoreEntry]:
        """Return the entry for a request UOR address, or ``None`` if absent.

        Side effect: increments ``hit_count`` on a successful lookup. Lookups
        are state-changing because the audit summary wants to know how many
        hits happened per entry.
        """
        with self._lock:
            entry = self._entries.get(request_address)
            if entry is not None:
                entry.hit_count += 1
            return entry

    def put(
        self,
        request_address: str,
        cert: DerivationCert,
        completion_text: str,
    ) -> StoreEntry:
        """Store a cert under its request UOR address.

        Raises if the address is already present (this protocol does not
        re-key entries — that would silently lose the original payer's
        provenance). Callers must check ``get`` first.
        """
        with self._lock:
            if request_address in self._entries:
                raise ValueError(
                    f"refusing to overwrite existing entry for {request_address!r} — "
                    "call get() first and treat presence as a cache hit"
                )
            entry = StoreEntry(
                cert=cert,
                completion_text=completion_text,
                stored_at=datetime.now(timezone.utc),
            )
            self._entries[request_address] = entry
            return entry

    def has(self, request_address: str) -> bool:
        """Return True iff an entry exists for this address (no side effect)."""
        with self._lock:
            return request_address in self._entries

    def peek(self, request_address: str) -> Optional[StoreEntry]:
        """Return entry without incrementing hit_count. For tests + audit."""
        with self._lock:
            return self._entries.get(request_address)

    # --- bulk ---

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def all_entries(self) -> list[tuple[str, StoreEntry]]:
        """Snapshot of all entries. For end-of-demo audit summary."""
        with self._lock:
            return list(self._entries.items())

    def total_hits(self) -> int:
        with self._lock:
            return sum(e.hit_count for e in self._entries.values())

    def clear(self) -> None:
        """Reset the store. Tests only."""
        with self._lock:
            self._entries.clear()
