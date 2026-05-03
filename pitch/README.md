# pitch/ — narrative reference material from old AgentLevy

> **Read-only on this side.** These files are copies from `~/AgentLevy/` (the prior Cannes-hackathon project, TypeScript on Flare). They're here as **reference material for the Consensus pitch**, not as code to integrate.
>
> Per [`MIGRATION_NOTES.md`](../MIGRATION_NOTES.md): the rule is **don't edit them in place**. Read on the plane during Vegas (April 30–May 1), then *write new pitch artifacts* in `pitch/v2/` (or wherever — but in a new file, not by overwriting these). That way we always have the original next to whatever we're producing for Consensus.

## Files

### Core spec — port the vocabulary, not the implementation

| File | What it is | How to use during the rebuild |
|---|---|---|
| `VTEAI-DRAFT.md` | "Verified Task Escrow and Attestation Interface" — chain-neutral ERC draft from old AgentLevy. Defines `TaskSpec`, `ProofPayload`, `VerificationSpec`, `AttestationHash` as protocol-layer types. | **Highest-value file.** Phase 2.1 design docs should align our Pydantic models with the VTEAI vocabulary. The pitch then becomes "we extend the VTEAI pattern from EVM to XRPL with content-addressed PRISM derivation certificates" instead of "we built another agent demo." |

### Positioning & long-form

| File | Source | Notes |
|---|---|---|
| `old-readme.md` | `~/AgentLevy/README.md` | Project overview + problem framing. Mine for chain-neutral language. **Scrub** any references to Flare, Coston2, C2FLR, USDT0, FDC, TEE, 0G, MasterAccountController, ftso_price_bound when porting copy to the new README. |
| `old-longform.md` | `~/AgentLevy/docs/AGENTLEVY_LONGFORM.md` | Long-form positioning narrative. Same scrub rules. |

### Pitch decks (V1 and V2; V2 is the refined version)

| File | Source | Notes |
|---|---|---|
| `old-deck-v1.md` | `~/AgentLevy/demo/HACKATHON_DECK.md` | First-pass 3-minute deck. Has more context. |
| `old-deck-v2.md` | `~/AgentLevy/demo/HACKATHON_DECK_V2.md` | Refined 3-minute deck. Tighter; closer to what the new Consensus deck should look like structurally. |

### Demo scripts

| File | Source | Notes |
|---|---|---|
| `old-video-script-v1.md` | `~/AgentLevy/demo/VIDEO_SCRIPT_3MIN.md` | Backup video script — first version. |
| `old-video-script-v2.md` | `~/AgentLevy/demo/VIDEO_SCRIPT_3MIN_V2.md` | Backup video script — refined. |
| `old-live-demo-script.md` | `~/AgentLevy/demo/LIVE_DEMO_SCRIPT.md` | On-stage demo flow. The act-1/act-2/act-3 framing transfers cleanly. |
| `old-run-of-show.md` | `~/AgentLevy/demo/RUN_OF_SHOW.md` | Run-of-show cues for the live demo. Very short; useful as a checklist template. |

### Architecture diagrams

| File | Source | Notes |
|---|---|---|
| `diagrams/x402-comparison.svg` | `~/AgentLevy/demo/x402-comparison.svg` | x402 vs AgentLevy flow side-by-side. SVG is editable in Figma/Inkscape — relabel the AgentLevy side to show XRPL Smart Escrow + PRISM derivation cert. |
| `diagrams/verifier-process.svg` | `~/AgentLevy/demo/verifier-process.svg` | TEE verification pipeline. Replace TEE node with "PRISM derivation cert + Ed25519 signature" node. |
| `diagrams/agentlevy-workflow-slide.svg` | `~/AgentLevy/demo/agentlevy-workflow-slide.svg` | High-level workflow. Lightest edit needed — this one's mostly chain-neutral already. |

## What was deliberately NOT ported

Per `MIGRATION_NOTES.md` Tier 3: no Solidity, no TypeScript, no `0G-agents/`, no React frontend, no node_modules, no Hardhat config, no compiled artifacts. Code is rewritten from scratch in the new repo's Python tree.

## Optional follow-up

The old repo also has AgentLevy brand SVG logos (horizontal, stacked, robot icon, full-dark, full-light, banner) at:

```
~/AgentLevy/assets/logos/
~/AgentLevy/demo/Logos/files/
```

If you want logo continuity in the new Consensus pitch, copy them into `pitch/diagrams/logos/` later. Not critical for plane-time reading — that's why they aren't here yet.

## What to do during Vegas plane time (April 30 morning)

1. Read `VTEAI-DRAFT.md` carefully. Mark which terms (TaskSpec, ProofPayload, VerificationSpec) we keep verbatim and which we extend.
2. Read `old-longform.md` and `old-deck-v2.md`. Extract 3–5 sentences of positioning language that is chain-neutral and lyrical enough to reuse verbatim.
3. Skim the demo scripts. Note act-structure that survives the chain swap.

Don't try to write the new pitch on the plane. Just read and absorb. New pitch writing happens at Miami in Phase 3.2 (May 6), informed by Vegas Q&A.
