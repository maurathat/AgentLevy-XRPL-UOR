# Canonical Form — Single Source of Truth

> **Status: Phase 0.2 verified, reconciled with the updated task list.** Findings below were confirmed by running PRISM directly. See `scripts/test_prism.py` for the executable verification.

This document is the only authoritative reference for how content is canonicalized in this project. Every triad computation, every cache key, every signature input depends on these rules. If they drift between modules, you get silent triad mismatches that take hours to debug under deadline.

---

## TL;DR

1. **PRISM does not canonicalize content.** It operates on integers in a finite modular ring. Canonicalizing JSON (or any other content type) into bytes is **entirely AgentLevy's responsibility**.
2. **The integration pattern is:** `content → canonical bytes (us) → SHA-256 (us) → take low N bytes (us) → ring-element int → engine.triad(int)` (PRISM).
3. **The engine is `Q(3)` (32-bit, 4.29 billion states)** — small enough to display human-readably in the demo audit trail, large enough that birthday-bound collisions for ~10 demo items are negligible.
4. **PRISM is vendored** at `vendor/prism.py` (byte-identical to upstream commit `6cafdac`), imported as `from vendor.prism import Q, ...`. Not installed via pip, not symlinked.
5. **One module — `agentlevy/primitives/canonical.py` — is the only place canonical bytes are produced.** No exceptions. PRISM consumers, signing, and the LLM cache layer all consume its output.

---

## What PRISM actually is

Verified by reading `vendor/prism.py`, `~/prism/docs/API.md`, and running `python vendor/prism.py`:

- **Single-file Python module** (`prism.py`, 1,531 lines). No `setup.py` or `pyproject.toml`. There is **no `pip install -e .`** — we vendor the file at `vendor/prism.py` (MIT license preserved at `vendor/LICENSE-prism`).
- **Requires Python ≥ 3.10** (uses `int.bit_count()`).
- **Public API entry points** (verified, do not assume):
  - `from vendor.prism import Q0, Q1, Q2, Q3, Q, Triad, Derivation` — engines and dataclasses
  - `engine = Q(n)` — engine at `8 × (n + 1)` bits. **AgentLevy uses `Q(3)`** (32-bit, 4 bytes wide, 4,294,967,296 states).
  - `engine.verify()` — runs algebraic coherence check; raises `CoherenceError` on failure.
  - `engine.triad(value)` → `Triad` (frozen dataclass with tuple fields, directly hashable). Has `.datum`, `.stratum`, `.spectrum`, `.total_stratum`, `.width`.
    - `value` may be an `int` (auto-reduced mod cycle) or a `tuple[int, ...]` of bytes (validated to engine width).
  - `engine.derive(term)` → `Derivation` with `.derivation_id` (URN: `urn:uor:derivation:sha256:<16hex>`), `.canonical_term`, `.result_datum`, `.metrics`.
  - `engine.canonicalize_term(term)` — **does NOT canonicalize content**; it normalizes algebraic operation trees (XOR/AND/OR chains). Unrelated to JSON canonicalization.
  - `engine.correlate(a, b)` → distance metrics between two values (Hamming-based fidelity).
- **What PRISM does not provide:** a content canonicalizer, a JSON serializer, a content-hashing function, an Ed25519 signing function. None of these are in PRISM's scope. AgentLevy owns all of them.

---

## What `examples/mapping.py` actually demonstrates

Reading the example *before* designing the fingerprint: the pattern shown there is **direct mapping**, not hashing.

| Content | Engine | Pattern |
|---|---|---|
| ASCII char | `Q0` (8-bit) | `engine.triad(ord(char))` — the byte IS the ring element |
| RGB pixel | `Q(2)` (24-bit) | `engine.triad((r, g, b))` — the bytes ARE the ring element |
| Status code | `Q(3)` (32-bit) | `engine.triad(0x01)` — the small int IS the ring element |

The example works because each input already fits inside the engine's quantum width. **AgentLevy's content does not** — task specs and certs are far larger than 4 bytes. So `mapping.py` validates the *projection-into-coordinates* idea but does not give us the bridge for arbitrary-sized content. **The SHA-256 fingerprint is our extension of the pattern, not a literal mirror of `mapping.py`.**

---

## The integration pattern (verified end-to-end)

```python
from agentlevy.primitives.fingerprint import content_to_ring_element
from vendor.prism import Q

ENGINE = Q(3)  # 32-bit; matches AgentLevy's chosen quantum

def content_triad(canonical_bytes: bytes):
    ring_element = content_to_ring_element(canonical_bytes, quantum=3)
    return ENGINE.triad(ring_element)
```

`content_to_ring_element` (in `agentlevy/primitives/fingerprint.py`) does:

1. `digest = sha256(canonical_bytes)` — collision-resistant 32-byte digest
2. `low_bytes = digest[-4:]` — explicit truncation to engine width (`quantum + 1`)
3. `int.from_bytes(low_bytes, "big")` — ring element in `[0, 2^32)`

### Why we truncate explicitly

`engine.triad(int)` will silently reduce any int mod the engine's cycle. Passing the full 256-bit SHA-256 integer to `Q(3)` would auto-truncate to the low 32 bits inside PRISM's `_normalize`. We do the truncation ourselves so:

- The audit trail shows the 256-bit digest **and** the 32-bit ring element side by side
- Anyone reading our code can reproduce the projection without reading PRISM's internals
- If we change quantum later, the truncation logic moves with us, not buried in a third-party

### Collision-resistance budget

`Q(3)` has 2^32 ≈ 4.29 billion states. Birthday-bound 50% collision probability arrives at ~65,536 distinct content items. For an on-stage demo with ~10 items, this is overkill. If the demo grows, switch to `Q(7)` (64-bit, ~4 billion items before 50% birthday collision) — single-line change in `agentlevy/prism_layer/triad.py`.

`scripts/test_prism.py` exercises this pattern against three content types (string, JSON, file) and confirms:

- Same input → same triad ✓
- Different inputs → different triads ✓
- JSON with same logical content but different key order → same triad **iff** canonicalized identically ✓

The third bullet is why everything below the `canonical_bytes` line matters.

---

## The rule (project-level)

**One module — `agentlevy/primitives/canonical.py` — is the only place canonical bytes are produced.** No exceptions.

All of the following consume the output of `canonical.to_canonical_bytes(obj)`:
- PRISM triad computation (`agentlevy/prism_layer/triad.py`)
- Ed25519 signing and verification (`agentlevy/primitives/signing.py`)
- LLM response cache keys (`agentlevy/llm/cache.py`)

The PRISM wrapper signature is:

```python
# agentlevy/prism_layer/triad.py
from agentlevy.primitives.fingerprint import content_to_ring_element
from vendor.prism import Q, Triad

_QUANTUM = 3
_ENGINE = Q(_QUANTUM)
_ENGINE.verify()  # one-time at import

def compute_triad(canonical_bytes: bytes) -> Triad:
    return _ENGINE.triad(content_to_ring_element(canonical_bytes, _QUANTUM))
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
5. **PRISM quantum is `Q(3)` everywhere.** All triad computations go through the same engine instance in `agentlevy/prism_layer/triad.py`. Do not mix engine widths within a derivation chain. If you change quantum, change it there and rerun every test.
6. **PRISM is consumed via `from vendor.prism import ...`** — never `from prism import ...` (which would resolve to a `~/prism/` clone and break for anyone else).

---

## Why this discipline matters

Without it, the demo's audit trail breaks invisibly:
- A signature produced over canonical form A won't verify against canonical form B.
- A cached LLM response keyed on canonical form A becomes a cache miss when the caller produces canonical form B.
- A triad computed over canonical form A in the buyer agent won't match a triad computed over canonical form B in the compliance agent, and the derivation chain looks corrupt to a verifier — even though the underlying content is identical.

The bug surfaces as "the demo worked yesterday and now signatures don't verify." It is the single most likely class of bug to lose the hackathon to. Centralizing canonical-bytes production in one module is the fix.

---

## References

- **PRISM upstream:** https://github.com/UOR-Foundation/prism (MIT)
- **PRISM commit pinned:** `6cafdac1a00017bf740fc494a91d71170617c5ab` (Feb 16, 2026)
  - Vendored at `vendor/prism.py` (byte-identical, SHA-256 `52cf630552b3ce1ddaf8699eb9591864bc7796260e67bb0d692733f38609660c`)
  - License preserved at `vendor/LICENSE-prism`
  - Update path: re-copy from a verified upstream commit, update `vendor/__init__.py` metadata and the references above, rerun `scripts/test_prism.py`.
  - **Do not fork.** PRISM is consumed read-only.
- PRISM API reference: `~/prism/docs/API.md`
- PRISM concepts: `~/prism/docs/CONCEPTS.md`
- PRISM algebra: `~/prism/docs/ALGEBRA.md`
- PRISM mapping example: `~/prism/examples/mapping.py`
- RFC 8785 (JCS): https://datatracker.ietf.org/doc/html/rfc8785
- Verification script: `scripts/test_prism.py`
