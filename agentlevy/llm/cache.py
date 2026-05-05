"""Fixture-based LLM response cache.

Two modes, controlled by the ``LLM_CACHE_MODE`` env var (or explicit arg):

  * **live** — call the LLM, write the response to ``fixtures/llm/<hash>.json``
    so subsequent runs in cache mode can replay deterministically.
  * **cache** — read the response from ``fixtures/llm/<hash>.json``; raise
    ``CacheMiss`` if the file doesn't exist. Use this on stage / in CI /
    during demos to avoid hitting the API and to keep timing predictable.

The cache key is a SHA-256 of the JSON-canonicalized request envelope —
model + messages + tool/schema + temperature. This is the same canonical
discipline used everywhere else in the project, so the same logical
request always hashes to the same key across machines.

Why this exists
---------------

Demos that call the LLM live are fragile: API hiccups, rate limits, and
non-determinism at temperature > 0 all sabotage the demo at exactly the
worst moment. Recording responses on a stable run and replaying them
during the actual demo gives us a deterministic, audited path that's
identical to a real LLM call modulo the network.

Phase 2.4 ships the cache. Phase 2.5 agents call it via the LLM client.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from agentlevy.primitives.canonical import to_canonical_bytes


# Default fixtures directory — overridable via constructor for tests.
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "llm"


class CacheMiss(KeyError):
    """Raised when cache mode is ``cache`` but no fixture exists for the request."""


class LLMCache:
    """File-backed cache for LLM responses keyed by request canonical bytes.

    Parameters
    ----------
    mode
        ``"live"`` writes responses to disk after fetching; ``"cache"``
        reads only and raises CacheMiss on missing fixtures. Defaults to
        the ``LLM_CACHE_MODE`` env var, then to ``"live"``.
    cache_dir
        Where fixtures live. Defaults to ``fixtures/llm/``.
    """

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self.mode = (mode or os.environ.get("LLM_CACHE_MODE", "live")).strip().lower()
        if self.mode not in {"live", "cache"}:
            raise ValueError(f"LLM_CACHE_MODE must be 'live' or 'cache', got {self.mode!r}")
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # --- Key derivation ----------------------------------------------

    def key_for(self, request: dict) -> str:
        """Compute the deterministic cache key for a request envelope.

        ``request`` is the full LLM request: model, messages, tool defs
        (or schema), temperature, system prompt. Anything that affects
        the response should be in here — different keys for different
        responses.
        """
        canonical = to_canonical_bytes(request)
        return hashlib.sha256(canonical).hexdigest()

    def path_for(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    # --- Lookup / store ----------------------------------------------

    def get(self, request: dict) -> dict:
        """Return the cached response for ``request``.

        Raises
        ------
        CacheMiss
            If no fixture exists at the computed key path.
        """
        path = self.path_for(self.key_for(request))
        if not path.exists():
            raise CacheMiss(
                f"No cached LLM response at {path.name}. "
                "Run with LLM_CACHE_MODE=live to record one."
            )
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def put(self, request: dict, response: dict) -> None:
        """Persist ``response`` keyed by canonical hash of ``request``.

        Idempotent: writing the same request twice produces the same key
        and overwrites the existing fixture. Live mode calls this after
        each successful LLM call.
        """
        path = self.path_for(self.key_for(request))
        with path.open("w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, sort_keys=True, ensure_ascii=False)

    # --- Convenience -------------------------------------------------

    def has(self, request: dict) -> bool:
        return self.path_for(self.key_for(request)).exists()
