# Canonical Form — Single Source of Truth

> **Status: PLACEHOLDER.** Fill in during Phase 0.2 after verifying PRISM's expected canonical form directly from the source. Do not start building primitives or the LLM cache layer until this document is filled in.

This document is the only authoritative reference for how content is canonicalized in this project. Every triad computation, every cache key, every signature input depends on these rules. If the rules drift between modules, you get silent triad mismatches that take hours to debug under deadline.

---

## The rule

**One module — `agentlevy/primitives/canonical.py` — is the only place canonical bytes are produced.** No exceptions.

All of the following consume the output of `canonical.to_canonical_bytes(obj)`:
- PRISM triad computation (`agentlevy/prism/triad.py`)
- Ed25519 signing and verification (`agentlevy/primitives/signing.py`)
- LLM response cache keys (`agentlevy/llm/cache.py`)

---

## What canonical form does PRISM expect?

**TO VERIFY (Phase 0.2):**

- [ ] Does PRISM accept raw bytes, or structured objects?
- [ ] Does it specify a JSON canonicalization standard? (RFC 8785 / JCS, custom, other)
- [ ] What is the behavior when the same logical content is given with different whitespace or key ordering?
- [ ] Is there a difference between input encoding (UTF-8, base64) and the canonicalization step itself?
- [ ] What is the public function signature: `canonicalize(...)` vs `compute_triad(...)` vs both?

Answer each here with a code reference (file + line) from the PRISM repo:

```
PRISM canonical form: <FILL IN>
PRISM canonical function: <FILL IN — file:line>
PRISM triad function:    <FILL IN — file:line>
```

---

## Project-level rules (do not violate)

1. **LLM responses are parsed into Pydantic schemas before canonicalization.** Never canonicalize raw LLM output strings — whitespace and ordering will drift across calls.
2. **Pydantic models expose `to_canonical_bytes()`** that delegates to `canonical.to_canonical_bytes(self.model_dump())`. Models do not implement their own canonicalization.
3. **Cache keys are `sha256(canonical_bytes)`.** Live and cached runs must produce identical triads — there is a test for this in `tests/test_cache_invariant.py`.
4. **No stringly-typed canonicalization.** No `json.dumps(..., sort_keys=True)` sprinkled around the codebase. If you find yourself reaching for it outside `canonical.py`, stop and fix the design.

---

## Why this discipline matters

Without it, the demo's audit trail breaks invisibly:
- A signature produced over canonical form A won't verify against canonical form B
- A cached LLM response keyed on canonical form A becomes a cache miss when the caller produces canonical form B
- A triad computed over canonical form A in the buyer agent won't match a triad computed over canonical form B in the compliance agent, and the derivation chain looks corrupt to a verifier — even though the underlying content is identical

The bug surfaces as "the demo worked yesterday and now signatures don't verify." It is the single most likely class of bug to lose the hackathon to. Centralizing canonical-bytes production in one module is the fix.
