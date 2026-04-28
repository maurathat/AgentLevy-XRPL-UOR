# Canonical Form — Single Source of Truth

> **Status: Phase 0.2 verified.** Findings below were confirmed by running PRISM directly. See `scripts/test_prism.py` for the executable verification.

This document is the only authoritative reference for how content is canonicalized in this project. Every triad computation, every cache key, every signature input depends on these rules. If they drift between modules, you get silent triad mismatches that take hours to debug under deadline.

---

## TL;DR

1. **PRISM does not canonicalize content.** It operates on integers or byte tuples in a closed algebraic space. Canonicalizing JSON (or any other content type) into bytes is **entirely AgentLevy's responsibility**.
2. **The integration pattern is:** `content → canonical bytes (us) → SHA-256 (us) → byte tuple → engine.triad(...)` (PRISM).
3. **The engine width is `Q(31)`** — 32 bytes / 256 bits — which matches a SHA-256 digest exactly. No padding or truncation needed.
4. **One module — `agentlevy/primitives/canonical.py` — is the only place canonical bytes are produced.** No exceptions. PRISM consumers, signing, and the LLM cache layer all consume its output.

---

## What PRISM actually is

Verified by reading `/Users/mauraclark/prism/prism.py`, `docs/API.md`, and running `python prism.py`:

- **Single-file Python module** (`prism.py`, ~64 KB). No `setup.py` or `pyproject.toml`. There is **no `pip install -e .`** — installation is by adding the directory to `PYTHONPATH` (we use a `.pth` file in the venv: `.venv/lib/python3.13/site-packages/prism_repo.pth`).
- **Requires Python ≥ 3.10** (uses `int.bit_count()`).
- **Public API entry points** (verified, do not assume):
  - `from prism import Q0, Q1, Q2, Q3, Q` — engines at fixed bit widths
  - `engine = Q(n)` — engine at `8 × (n + 1)` bits. Q31 = 256-bit (matches SHA-256).
  - `engine.verify()` — runs algebraic coherence check; raises `CoherenceError` on failure.
  - `engine.triad(value)` → `Triad` with `.datum`, `.stratum`, `.spectrum`, `.total_stratum`, `.width`.
    - `value` may be an `int` or a `tuple[int, ...]` of bytes.
  - `engine.derive(term)` → `Derivation` with `.derivation_id` (content-addressed certificate ID), `.canonical_term`, `.result_datum`, `.metrics`.
  - `engine.canonicalize_term(term)` — **does NOT canonicalize content**; it normalizes algebraic operation trees (XOR/AND/OR chains). Unrelated to JSON canonicalization.
  - `engine.correlate(a, b)` → distance metrics between two values.
- **What PRISM does not provide:** a content canonicalizer, a JSON serializer, a hashing function, a signing function. None of these are in PRISM's scope.

---

## The integration pattern (verified end-to-end)

```python
import hashlib
from prism import Q

ENGINE = Q(31)  # 32 bytes = 256 bits, matches SHA-256

def content_triad(canonical_bytes: bytes):
    digest = hashlib.sha256(canonical_bytes).digest()  # 32 bytes
    return ENGINE.triad(tuple(digest))                 # PRISM consumes the byte tuple
```

This is what `scripts/test_prism.py` exercises against three content types (string, JSON, file) and confirms:
- Same input → same triad ✓
- Different inputs → different triads ✓
- JSON with same logical content but different key order → same triad **iff** canonicalized identically ✓

The third bullet is why everything below the `canonical_bytes` line matters.

---

## The rule (project-level)

**One module — `agentlevy/primitives/canonical.py` — is the only place canonical bytes are produced.** No exceptions.

All of the following consume the output of `canonical.to_canonical_bytes(obj)`:
- PRISM triad computation (`agentlevy/prism/triad.py`)
- Ed25519 signing and verification (`agentlevy/primitives/signing.py`)
- LLM response cache keys (`agentlevy/llm/cache.py`)

The PRISM wrapper signature is:

```python
# agentlevy/prism/triad.py
def compute_triad(canonical_bytes: bytes) -> Triad:
    digest = hashlib.sha256(canonical_bytes).digest()
    return _engine.triad(tuple(digest))
```

It always takes `bytes`, never raw objects. This enforces the discipline.

---

## Choice of canonical form for JSON

Recommendation, to be implemented in `canonical.py`:

- **Use [RFC 8785 (JSON Canonicalization Scheme / JCS)](https://datatracker.ietf.org/doc/html/rfc8785)** for any structured content (Pydantic models → `.model_dump()` → JCS bytes).
- Why JCS: it's a published IETF standard, deterministic across implementations, and widely used in cryptographic-signing contexts (W3C VC, JWS, COSE adjacent ecosystems). Easier to defend in a design conversation than a custom canonicalizer.
- For the hackathon, `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")` is JCS-adjacent and almost identical for the schemas we'll use (no NaN, no Infinity, no integer/float ambiguity), but full JCS handles edge cases like number normalization that simple `sort_keys` does not.
- **Decide once** in `canonical.py`. Document the choice at the top of the module. Do not let it drift.

For raw bytes (file contents, opaque blobs), no canonicalization is needed — they go through `to_canonical_bytes()` as a passthrough.

---

## Project-level rules (do not violate)

1. **LLM responses are parsed into Pydantic schemas before canonicalization.** Never canonicalize raw LLM output strings — whitespace and ordering will drift across calls.
2. **Pydantic models expose `to_canonical_bytes()`** that delegates to `canonical.to_canonical_bytes(self.model_dump())`. Models do not implement their own canonicalization.
3. **Cache keys are `sha256(canonical_bytes)`.** Live and cached runs must produce identical triads — there will be a test for this in `tests/test_cache_invariant.py`.
4. **No stringly-typed canonicalization.** No `json.dumps(..., sort_keys=True)` sprinkled around the codebase. If you find yourself reaching for it outside `canonical.py`, stop and fix the design.
5. **PRISM engine is `Q(31)` everywhere.** All triad computations go through the same engine instance. Do not mix engine widths within a derivation chain.

---

## Why this discipline matters

Without it, the demo's audit trail breaks invisibly:
- A signature produced over canonical form A won't verify against canonical form B.
- A cached LLM response keyed on canonical form A becomes a cache miss when the caller produces canonical form B.
- A triad computed over canonical form A in the buyer agent won't match a triad computed over canonical form B in the compliance agent, and the derivation chain looks corrupt to a verifier — even though the underlying content is identical.

The bug surfaces as "the demo worked yesterday and now signatures don't verify." It is the single most likely class of bug to lose the hackathon to. Centralizing canonical-bytes production in one module is the fix.

---

## References

- PRISM source: `/Users/mauraclark/prism/prism.py`
- PRISM API: `/Users/mauraclark/prism/docs/API.md`
- PRISM concepts: `/Users/mauraclark/prism/docs/CONCEPTS.md`
- PRISM algebra: `/Users/mauraclark/prism/docs/ALGEBRA.md`
- RFC 8785 (JCS): https://datatracker.ietf.org/doc/html/rfc8785
- Verification script: `scripts/test_prism.py`
