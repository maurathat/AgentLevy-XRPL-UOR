# Canonical Form — Single Source of Truth

> **Status: Phase 0.2 verified, reconciled with the updated task list.** Findings below were confirmed by running PRISM directly. See `scripts/test_prism.py` for the executable verification.

This document is the only authoritative reference for how content is canonicalized in this project. Every triad computation, every cache key, every signature input depends on these rules. If they drift between modules, you get silent triad mismatches that take hours to debug under deadline.

---

## ★ Quantum width: Q(31), with hybrid display layer (confirmed May 3 2026)

The protocol layer uses **`Q(31)` (32-byte / 256-bit width)**, matching the canonical UOR address width verified against a real `cert:ModuleCertificate` example ([`mcp/example-module-certificate.json`](mcp/example-module-certificate.json), `store:uorAddress.u:length: 32`).

This means:
- AgentLevy triads are byte-width-compatible with UOR Passport Envelopes
- When wrapped in the `uor-v1.jsonld` `@context`, our certs can be verified directly with UOR MCP's `uor.verify_passport` tool — no width-conversion adapter needed
- The fingerprint function passes the SHA-256 digest through with no truncation, preserving full ~128-bit cryptographic collision resistance

**Single source for triad computation:** [`agentlevy/prism_layer/triad.py`](agentlevy/prism_layer/triad.py). Exports `compute_triad(canonical_bytes) -> Triad` and `engine_info()`. Do not instantiate `Q(31)` elsewhere.

**Hybrid display layer:** [`agentlevy/primitives/display.py`](agentlevy/primitives/display.py) provides three projections of a 32-byte datum so the audit trail stays readable on stage:
- `glyph(datum)` → 32-character Braille string (`U+2800 + byte` per char). Matches UOR's `store:uorAddress.u:glyph` exactly.
- `compact(datum, n=4)` → first n bytes hex + ellipsis (`a1b2c3d4...`). Default `n=4`.
- `hex_full(datum)` → all 64 hex chars. Use for cross-system comparison and regulator audit.

**Discipline:** display helpers are lossy projections. **Never use them as inputs to signing, hashing, or content addressing.** The protocol layer always operates on raw `Triad` objects.

---

## TL;DR

1. **PRISM does not canonicalize content.** It operates on integers in a finite modular ring. Canonicalizing JSON (or any other content type) into bytes is **entirely AgentLevy's responsibility**.
2. **The integration pattern is:** `content → canonical bytes (us) → SHA-256 (us) → take low N bytes (us) → ring-element int → engine.triad(int)` (PRISM).
3. **The engine is `Q(31)` (256-bit, 32-byte width)** — matches the canonical UOR address width verified against published `cert:ModuleCertificate` examples. Triads are byte-compatible with UOR Passport Envelopes; collision resistance is the full SHA-256 strength. Audit-trail readability is recovered via the hybrid display layer in `agentlevy/primitives/display.py`.
4. **PRISM is vendored** at `vendor/prism.py` (byte-identical to upstream commit `6cafdac`), imported as `from vendor.prism import Q, ...`. Not installed via pip, not symlinked.
5. **One module — `agentlevy/primitives/canonical.py` — is the only place canonical bytes are produced.** No exceptions. PRISM consumers, signing, and the LLM cache layer all consume its output.

---

## What PRISM actually is

Verified by reading `vendor/prism.py`, `~/prism/docs/API.md`, and running `python vendor/prism.py`:

- **Single-file Python module** (`prism.py`, 1,531 lines). No `setup.py` or `pyproject.toml`. There is **no `pip install -e .`** — we vendor the file at `vendor/prism.py` (MIT license preserved at `vendor/LICENSE-prism`).
- **Requires Python ≥ 3.10** (uses `int.bit_count()`).
- **Public API entry points** (verified, do not assume):
  - `from vendor.prism import Q0, Q1, Q2, Q3, Q, Triad, Derivation` — engines and dataclasses
  - `engine = Q(n)` — engine at `8 × (n + 1)` bits. **AgentLevy uses `Q(31)`** (256-bit, 32 bytes wide, 2^256 states — matches UOR canonical width).
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
from agentlevy.prism_layer.triad import compute_triad
# compute_triad is the only triad-producing entry point.
# It uses Q(31) internally — see agentlevy/prism_layer/triad.py.

triad = compute_triad(canonical_bytes)
```

Internally that resolves to:

```python
from agentlevy.primitives.fingerprint import content_to_ring_element
from vendor.prism import Q

ENGINE = Q(31)  # 32 bytes / 256 bits — UOR-canonical width

def content_triad(canonical_bytes: bytes):
    ring_element = content_to_ring_element(canonical_bytes, quantum=31)
    return ENGINE.triad(ring_element)
```

`content_to_ring_element` (in `agentlevy/primitives/fingerprint.py`) does:

1. `digest = sha256(canonical_bytes)` — collision-resistant 32-byte digest
2. `low_bytes = digest[-32:]` — explicit truncation to engine width (`quantum + 1`); at `Q(31)` this is the entire digest (passthrough)
3. `int.from_bytes(low_bytes, "big")` — ring element in `[0, 2^256)`

### Why we still truncate explicitly (even at Q(31))

`engine.triad(int)` will silently reduce any int mod the engine's cycle. Doing the truncation in our code makes the projection visible in the audit trail and reproducible by anyone reading our code, instead of relying on PRISM's `_normalize` to silently take the low N bytes. At `Q(31)` the "truncation" is a passthrough — but the discipline matters for forward compatibility if we ever re-select a smaller `quantum` for a low-bandwidth display channel.

### Collision-resistance budget

At `Q(31)` (256-bit ring), the ring element IS the SHA-256 digest. Collision resistance is the full SHA-256 strength (~128-bit by birthday bound) — effectively unlimited for any practical agent commerce volume. No need to consider switching widths until SHA-256 itself is broken.

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

- **Use [RFC 8785 (JSON Canonicalization Scheme / JCS)](https://datatracker.ietf.org/doc/html/rfc8785) plus Unicode NFC normalization on every string field.** This matches UOR Passport's `jcs-rfc8785+nfc` algorithm byte-for-byte (verified live against `mcp.uor.foundation/encode_address` — see [`docs/UOR_PASSPORT_VERIFIED.md`](docs/UOR_PASSPORT_VERIFIED.md)).
- **NFC normalization is required for non-ASCII content.** Without it, "café" with composed `é` (U+00E9) hashes differently than "café" with decomposed `e` + combining acute (U+0301), even though they render identically. Empirically verified: same input, NFC vs no-NFC produces different SHA-256 addresses for non-ASCII strings. For KYC compliance with international names ("Müller", "São Paulo"), this matters.
- For the hackathon initial implementation, `unicodedata.normalize("NFC", s)` recursively on all string values + `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")` is sufficient. Full RFC 8785 (which also handles number-formatting edge cases like `1.0` → `1`) can graduate to a library like [`jcs`](https://pypi.org/project/jcs/) if any test surfaces a divergence.
- **Decide once** in `canonical.py`. Document the choice at the top of the module. Do not let it drift.

Reference implementation sketch (full text in `docs/UOR_PASSPORT_VERIFIED.md`):

```python
import json
import unicodedata


def to_canonical_bytes(obj) -> bytes:
    obj = _nfc_recursive(obj)  # NFC every string, recursively
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _nfc_recursive(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", k): _nfc_recursive(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_nfc_recursive(x) for x in value]
    return value
```

For raw bytes (file contents, opaque blobs), no canonicalization is needed — they go through `to_canonical_bytes()` as a passthrough.

---

## Project-level rules (do not violate)

1. **LLM responses are parsed into Pydantic schemas before canonicalization.** Never canonicalize raw LLM output strings — whitespace and ordering will drift across calls.
2. **Pydantic models expose `to_canonical_bytes()`** that delegates to `canonical.to_canonical_bytes(self.model_dump())`. Models do not implement their own canonicalization.
3. **Cache keys are `sha256(canonical_bytes)`.** Live and cached runs must produce identical triads — there will be a test for this in `tests/test_cache_invariant.py`.
4. **No stringly-typed canonicalization.** No `json.dumps(..., sort_keys=True)` sprinkled around the codebase. If you find yourself reaching for it outside `canonical.py`, stop and fix the design.
5. **PRISM quantum is `Q(31)` everywhere.** All triad computations go through `compute_triad` in `agentlevy/prism_layer/triad.py`. Do not instantiate other engine widths anywhere in the project. The hybrid display layer (`agentlevy/primitives/display.py`) provides projections for audit-trail rendering — never use display strings as inputs to signing or hashing.
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
