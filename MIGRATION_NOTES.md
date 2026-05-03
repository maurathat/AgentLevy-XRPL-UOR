# Migration Notes — Old AgentLevy → AgentLevy-XRPL-UOR

> **Decision: fresh-repo-with-narrative-port.** Code: rewritten from scratch (we already have). Pitch material, architecture diagrams, VTEAI ERC draft, conceptual task-spec model: ported selectively from `~/AgentLevy/`.

This document records what's in the prior codebases, what's worth porting, what isn't, and why the technical core is genuinely different from the old project.

---

## Repos surveyed

| Repo | Status | Use it? |
|---|---|---|
| `~/AgentLevy/` | Active head (commit `4a4eac9`, "Edit the demo video, add subtitles", Apr 4 2026) | **Yes — sole reference** |
| `~/AgentLevy-origin-main/` | Stale snapshot (commit `ce7b661`, 5 commits behind), `-origin-main` suffix suggests historical pin | **No — ignore.** The only unique content was `frontend-v0/`, deliberately removed in `c52df57` |

Hereafter "old AgentLevy" = `~/AgentLevy/`.

---

## What old AgentLevy actually is

Different beast from what I'd assumed when planning this rebuild. Concrete reality:

| Aspect | Old AgentLevy | New AgentLevy-XRPL-UOR |
|---|---|---|
| Built for | Cannes hackathon (~April 2026) | Consensus EasyA hackathon (May 5–7, 2026) |
| Language | TypeScript/JavaScript + Solidity 0.8.28 | Python 3.13 |
| Chain | Flare Coston2 (EVM) + light XRPL (Smart Accounts) | XRPL Testnet + WASM Devnet |
| Agents | **Deterministic state machines.** No LLM calls anywhere. | **LLM agents (Anthropic + tool use).** |
| Settlement | `Treasury.sol` (single contract, escrow + attestation + auto-settle) | XRPL `EscrowCreate` + WASM `FinishFunction` (XLS-100) |
| Verification | Deterministic checks (json_schema, test_suite, checksum_match, ftso_price_bound) | Content-addressed PRISM derivation certificates over canonical bytes |
| Attestation | Flare TEE registration + FDC attestation | Ed25519 signatures + PRISM triads |
| Domain | Generic agent task marketplace (sentiment analysis, data extraction, code review, translation, data validation) | KYC compliance specifically (beneficial-ownership extraction, sanctions screening) |
| Code size | ~36 KB Solidity + 64 KB JS sdk + 332 KB demo agents (excluding 540 MB of `node_modules` and `0G-agents/`) | Empty scaffolding so far |

**The two projects share a problem statement** — verifiable agent-to-agent settlement, with hash-committed task specs and post-completion attestations — **but virtually no implementation overlap.** The old code's `Treasury.sol`, `MasterAccountController`, FDC attestation, TEE registration, and 0G runtime are all Flare/EVM-coupled and don't translate. There are no LLM prompts, Pydantic schemas, or synthetic KYC fixtures to port — they don't exist there.

---

## What to port

### Tier 1 — port these now (during Phase 1 / Vegas plane time)

These are chain-agnostic narrative or conceptual artifacts. Each saves real Phase 2 / Phase 3 time.

| File in `~/AgentLevy/` | What it is | Where it lands |
|---|---|---|
| `README.md` (8.2 KB) | Project overview, problem framing, architecture summary | Reference for `README.md` in new repo. Keep the framing; rewrite the technical sections to match XRPL/PRISM. |
| `docs/AGENTLEVY_LONGFORM.md` (4.2 KB) | Long-form positioning & narrative | Mine the language. Pitch refrains and analogies are reusable. |
| `docs/erc-draft-vteai.md` | "Verified Task Escrow and Attestation Interface" — a chain-agnostic spec for the protocol | This is the most valuable single artifact in the old repo. Even on XRPL, the VTEAI vocabulary (TaskSpec, ProofPayload, VerificationSpec, AttestationHash) is the right abstraction. Read carefully; align new Pydantic models with VTEAI vocabulary so the demo can claim "implements VTEAI on XRPL." |
| `demo/HACKATHON_DECK.md` and `HACKATHON_DECK_V2.md` | Structured 3-min pitches | Skeleton for the Consensus pitch. Replace Flare-specific slides with XRPL/PRISM equivalents. |
| `demo/VIDEO_SCRIPT_3MIN.md`, `VIDEO_SCRIPT_3MIN_V2.md`, `demo/LIVE_DEMO_SCRIPT.md`, `demo/RUN_OF_SHOW.md` | Demo flow scripts | Adapt structure; rewrite content. The act-1/act-2/act-3 framing is sound. |
| `docs/x402-comparison.svg`, `docs/verifier-process.svg`, `demo/agentlevy-workflow-slide.svg` | Architecture diagrams (vector) | Reuse layout; relabel nodes to XRPL/PRISM. SVGs are editable in Figma/Inkscape. |

**Action:** during the Vegas plane time on April 30 (per Phase 1.2 of the plan), copy these into a top-level `pitch/` dir in this repo. Don't edit yet — read on the plane, edit after Vegas Q&A informs what to emphasize.

### Tier 2 — port the *concept*, not the code

These are conceptual patterns from the old code that are worth knowing but require complete reimplementation.

| Old pattern | What's reusable | Where in new architecture |
|---|---|---|
| **5 service types in `sdk/taskSpecRegistry.js`** (sentiment-analysis, data-extraction, code-review, translation, data-validation) with input schema + output schema + quality criteria | The shape: each service has structured inputs, structured outputs, deterministic verification rules. | Phase 2.1 task spec schema. Replace the 5 services with 2 (`kyc.beneficial_ownership_verify`, `kyc.sanctions_screen`). Keep the input/output/criteria triple. |
| **`Treasury.sol` event schema** (`LevySettled` with taskId, agentA, agentB, taskFee, levyAmount, attestationHash, timestamp) | Settlement event vocabulary. | Phase 2.7 audit trail printout. The old fields map cleanly onto new derivation cert references. |
| **Hash-committed spec model** (`Treasury.registerSpec(specHash, serviceId)` + later submission of cert that matches) | The pattern of "commit-then-reveal" for spec → result. | Phase 2.8 escrow design. The XRPL `EscrowCreate` Data field stores the expected final cert hash (32 bytes); the WASM `FinishFunction` verifies the submitted cert preimage matches. Same pattern, different mechanism. |
| **x402 facilitator HTTP shape** (`GET /services`, `GET /spec/{serviceId}`, `POST /pay`, `POST /submit`, `GET /status/:taskId`) | An HTTP layer that's fully chain-agnostic. | Optional. We probably don't need an HTTP shell — the Phase 2.6 negotiation runs in-process. But if we add a thin web frontend in Phase 3.1, mirror these routes. |
| **`VerificationSpec` union type** (json_schema, test_suite, checksum_match, ftso_price_bound) | Structured verification dispatch. | We don't have direct re-use because our verification is signature + triad chain validity, not deterministic schema checks. But the *idea* of typing the verification approach is sound. |

**Action:** in Phase 2.1 design docs, reference the VTEAI vocabulary explicitly. This makes the pitch story stronger ("we extend the VTEAI pattern from EVM to XRPL with content-addressed certificates") instead of weaker ("we built something new from scratch").

### Tier 3 — do NOT port (architecturally incompatible)

| Item | Why skip |
|---|---|
| `contracts/Treasury.sol` | Solidity, Flare EVM, `msg.sender`, ERC-20 token escrow. Every primitive needs a different XRPL counterpart; nothing line-by-line transfers. |
| `MasterAccountController` integration (Flare Smart Accounts) | EVM account abstraction. XRPL has no equivalent; XRPL agents are wallets directly. |
| Flare Data Connector (FDC) attestation pipeline | Flare-specific oracle Merkle proofs. XRPL has its own attestation model. Don't re-import the assumption. |
| TEE registration model (`Treasury.sol` TEE addresses) | Flare-specific on-chain TEE registry. We replace this with PRISM derivation certs + Ed25519 signatures, which are conceptually stronger (no trusted hardware). |
| 0G-agents runtime (473 MB of `node_modules`) | Entirely 0G compute. Out of scope. The plan explicitly excludes 0G. |
| Frontend (`frontend/`, 67 MB React + Vite) | Hackathon-specific UI for the old protocol. Phase 3.1 might justify a small new frontend, but it'd be from-scratch FastAPI/Streamlit. |
| C2FLR / USDT0 token assumptions throughout | Flare-native asset bindings. XRPL uses XRP and (potentially) RLUSD — different token model. |

---

## Cross-architectural callouts

Three places where the new project must be careful *because* it carries forward old AgentLevy's branding/positioning:

1. **The pitch must not over-claim continuity.** Saying "we're rebuilding AgentLevy on XRPL" is fair; saying "AgentLevy already does this on Flare and we're just porting" is misleading. The new project's core (LLM agents producing content-addressed PRISM derivation certificates verifiable from public keys alone) is genuinely new. Lean into that. The Cannes-vintage Flare demo was a different project — same brand, different technical idea.

2. **VTEAI is the bridge.** The old repo's `docs/erc-draft-vteai.md` is the only artifact that explicitly anticipates a chain-neutral protocol. New project should explicitly cite VTEAI and frame XRPL+PRISM as the canonical implementation of that interface (with the WASM `FinishFunction` as the on-chain verifier). This gives the new project a credible standards-adjacent story instead of just "another agent demo."

3. **Watch for accidental Flare references.** Anywhere we copy text from the old README or pitch decks, double-check that "Flare", "Coston2", "C2FLR", "USDT0", "FDC", "TEE", "0G", "MasterAccountController", "ftso_price_bound" are scrubbed. These are easy to miss when copy-pasting.

---

## Recommended port action plan

Concrete steps, ordered by when they fit in the project timeline:

### Now (before Vegas, April 28–29)
- [ ] Copy the Tier-1 narrative files into `pitch/` in this repo (don't edit yet):
  - `~/AgentLevy/README.md` → `pitch/old-readme.md` (reference only)
  - `~/AgentLevy/docs/AGENTLEVY_LONGFORM.md` → `pitch/old-longform.md`
  - `~/AgentLevy/docs/erc-draft-vteai.md` → `pitch/VTEAI-DRAFT.md` (this one *is* the spec we cite)
  - `~/AgentLevy/demo/HACKATHON_DECK_V2.md` → `pitch/old-deck.md`
  - `~/AgentLevy/demo/RUN_OF_SHOW.md` → `pitch/old-run-of-show.md`
  - The three SVG architecture diagrams → `pitch/diagrams/`
- [ ] Add `pitch/` to git so it's reviewable; commit.

### Vegas plane time (April 30 morning)
- [ ] Read `pitch/VTEAI-DRAFT.md` carefully. Mark which terms (TaskSpec, ProofPayload, VerificationSpec) we keep verbatim and which we extend.
- [ ] Read the old long-form and deck. Extract 3–5 sentences of positioning language that are chain-neutral and lyrical enough to reuse.

### After Vegas, before Miami (May 2 morning, Phase 2.1 design docs)
- [ ] In the new Pydantic models for `TaskSpec` and `DerivationCert`, use VTEAI field names where they fit. Document the alignment in code comments.
- [ ] Extract the 5 → 2 service-type narrowing in a one-paragraph design note.

### Miami (Phase 3, May 6)
- [ ] Final pitch writing: start from `pitch/old-deck.md`, scrub Flare references, replace Cannes-vintage examples with the live XRPL demo. Keep the act structure if it works.

---

## What to leave behind, explicitly

So we never accidentally re-pull these:

- 540 MB of node_modules and `0G-agents/`
- All Solidity contracts (`contracts/`)
- All TypeScript demo agents (`demo-agents/`)
- All compiled artifacts (`artifacts/`, `cache/`, `typechain-types/`)
- The old frontend (`frontend/`, `dashboard/`, `frontend-v0/`)
- Hardhat config, deployment scripts, `ignition/`
- `.claude/`, `.codebuddy/`, etc. — local tooling configs (the new repo has its own)

These are sized at ~600 MB combined and contribute nothing to the new project.

---

## Open question for the user

The plan said to make this decision honestly. I came in assuming the old code might have prompts and schemas worth porting; the reality is it doesn't (it's deterministic agents on EVM). **Does that match your memory of what's there, or is there a directory or branch I missed?**

If yes — proceed with the port plan above. The Tier-1 list is small enough to copy in 5 minutes.

If no — point me at what I missed and I'll redo the inventory before we spend Phase 1 mental cycles on the wrong reference material.
