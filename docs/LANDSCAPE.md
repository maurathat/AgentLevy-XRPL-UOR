# Landscape — where AgentLevy-XRPL-UOR sits

> **Pitch positioning doc.** This is "where we sit" content for the Consensus deck — the slide where you show 5–8 adjacent projects and demonstrate (a) you know the landscape, (b) you've consciously chosen your spot, (c) you compose with the others rather than fight them. Replaces the old Cannes slide that compared against x402 + Hedera.
>
> Use the table below as the slide content (visual). Use the per-project sections as Q&A prep — judges and VCs will ask about specific projects.

## Map

There are five layers to the agent-economy stack. Most projects live cleanly in one. Where AgentLevy is and isn't is the pitch:

```
            ┌─────────────────────────────────────────────────────────────┐
            │  SETTLEMENT  /  COORDINATION  (payment for verified work)   │
            │   ★ AgentLevy-XRPL-UOR    x402 (Coinbase)    AP2 (Google)   │
            │   Hedera AgentKit         Kite               Skyfire         │
            │   Standard: ★ VTEAI (ERC draft, Maura Clark, Apr 2026)      │
            └─────────────────────────────────────────────────────────────┘
            ┌─────────────────────────────────────────────────────────────┐
            │  ADDRESSING  /  IDENTITY  (canonical identity for content)  │
            │   ★ PRISM (UOR Foundation, MIT)    CAIP    DID    IPFS CIDs │
            │   Standard: ★ UOR-ADDR-1 (community proposal, Apr 27 2026)  │
            └─────────────────────────────────────────────────────────────┘
            ┌─────────────────────────────────────────────────────────────┐
            │  MEMORY / STORAGE  (what agents remember and share)         │
            │   MemWal (Walrus+Sui)     Mem0     Letta (ex-MemGPT)        │
            └─────────────────────────────────────────────────────────────┘
            ┌─────────────────────────────────────────────────────────────┐
            │  DISPUTE / VERIFICATION  (when work is contested)            │
            │   Kleros (Ethereum)    Flare FDC    Reality.eth   UMA        │
            └─────────────────────────────────────────────────────────────┘
            ┌─────────────────────────────────────────────────────────────┐
            │  COMPUTE / REASONING  (the LLM provider)                    │
            │   Anthropic    OpenAI    Google    open models               │
            └─────────────────────────────────────────────────────────────┘
```

**AgentLevy is at the settlement layer, implementing two open standards (VTEAI + UOR-ADDR-1) on XRPL with PRISM as the addressing primitive.** We compose with everything else rather than re-implement.

## Per-project notes (Q&A prep)

### Settlement / Coordination

#### x402 (Coinbase)
- HTTP 402 status code-based micropayment protocol. Buyer and seller exchange USDC over HTTP headers. Standard published 2025.
- **What it does well:** clean HTTP-native UX, standard for "machine pays machine over an API call."
- **What it doesn't do:** cryptographic chain of custody, on-chain settlement with programmable conditions, audit trail of *what work was done*. It's a payment standard, not a coordination protocol.
- **Relation to AgentLevy:** orthogonal at the framing level (HTTP layer vs settlement layer), but x402 is the *closest in mindshare* and the comparison judges will reach for first. **Q&A line:** *"x402 standardizes machine-to-machine payment over HTTP. We standardize cryptographic-chain-of-work over XRPL settlement. Same problem space, different layer — x402 says 'pay for an API call,' we say 'pay for a verifiable derivation chain that anyone with public keys can audit.'"*

#### AP2 (Google's Agent Payment Protocol)
- Google's analogous HTTP-based agent payment standard, published 2025.
- **Q&A line:** *"x402 from Coinbase, AP2 from Google — both are payment-rail standardization at the HTTP layer. We sit one layer below: the on-chain settlement primitive that either of those rails could call into."*

#### Hedera AgentKit
- Hedera's SDK for agents on the HBAR network. Native token settlement, low fees, good consensus latency.
- **What's distinctive:** Hedera's hashgraph consensus + low fixed fees make agent-scale microtransactions cheap.
- **Relation to AgentLevy:** different chain, similar ambition. The XRPL choice is defensible because XLS-100 SmartEscrow + WASM FinishFunction is the *exact* primitive we need (programmable conditional release tied to a content-addressed cert hash) — Hedera doesn't have that built-in.
- **Q&A line:** *"Hedera does microsecond-finality and low fees well. We picked XRPL because XLS-100 SmartEscrow with a WASM FinishFunction is the precise primitive our verification model needs — programmable, recently activated, no equivalent on Hedera today."*

#### Kite
- Agent network with native token (KITE) for coordination and payment.
- **Q&A line:** *"Kite is building an end-to-end agent network with their own token. We're protocol-only, settling on XRPL with RLUSD-adjacency. Different bet — we don't think the agent economy needs a new token; it needs better primitives on existing rails."*

#### Skyfire
- Recently-funded agent payment infrastructure (institutional positioning).
- **Q&A line:** *"Skyfire is at the rails / billing layer. We're at the protocol layer — the cryptographic structure of what 'agent did work, here's the proof, release the funds' looks like."*

### Addressing / Identity

This is the layer for **canonical identity of content** — given a piece of agent-produced data, what's its globally-unique, chain-agnostic, cryptographically-derived address. Distinct from account/asset addressing (CAIP) and entity addressing (DID).

#### UOR-ADDR-1 (community proposal, April 27 2026 — Maura Clark + co.)
- **What it is:** v0.1 draft of a chain-agnostic standard for canonical content addressing built on PRISM. Defines URI scheme + wire format for portable triads, deterministic canonicalization rules, derivation cert format, minimal verification interface, chain-specific bindings (EVM, XRPL, Solana, Cosmos, Flare).
- **What gap it fills:** CAIP addresses chain accounts; DID addresses entities; IPFS CIDs are single-axis hashes without algebraic structure; Hugging Face IDs are centrally-namespaced; x402 isn't an identity standard at all. **None of these address agent-produced content with chain-agnostic canonical identity** — that's what UOR-ADDR-1 is for.
- **Status:** Rust crates published at https://crates.io/crates/uor-foundation. Spec at v0.1; goal v1.0 with reference implementations (Solidity, TypeScript) and chain bindings.
- **Relation to AgentLevy:** AgentLevy is the first reference implementation. Every triad in `agentlevy/prism_layer/triad.py` IS a UOR-ADDR-1-shaped address. We're producing v0.1 addresses today; the Phase 2 design doc (`docs/PHASE_2_DESIGN.md`) bakes the vocabulary in.
- **Q&A line:** *"UOR-ADDR-1 is to content what CAIP is to accounts and DID is to entities — chain-agnostic canonical identity, but for the data agents actually produce. AgentLevy is the first reference implementation. We're recruiting collaborators on Solidity and TypeScript impls and on chain bindings."*
- **Full proposal text:** [`pitch/UOR-ADDR-PROPOSAL.md`](../pitch/UOR-ADDR-PROPOSAL.md)

#### PRISM (UOR Foundation, MIT)
- The algebraic primitive UOR-ADDR-1 builds on. Single-file Python module; produces triadic coordinates (datum/stratum/spectrum) for any value in a closed modular ring. See `vendor/prism.py` (commit `6cafdac`, byte-identical to upstream).
- **Q&A line:** *"PRISM is the engine; UOR-ADDR-1 is the spec for how everyone uses the engine compatibly."*

#### CAIP, DID, IPFS CIDs, Hugging Face IDs
- **Each addressed in the table above** — relevant only as the gap UOR-ADDR-1 explicitly fills, not as competitors. **Q&A composite:** *"Each of these solves a piece. CAIP standardized account references across chains. DID standardized identity URIs. IPFS gave content-addressed hashes. None of them solve chain-agnostic canonical identity for agent-produced content with algebraic structure for similarity reasoning. UOR-ADDR-1 is precisely that gap."*

### Memory / Storage

#### MemWal (Walrus + Sui)
- Long-term verifiable memory layer for AI agents. Stores conversations, checkpoints, reasoning traces. Backed by Walrus blob storage + Sui smart-contract access control.
- **Trust model:** permissioned-by-default — fine-grained ACLs in Sui control who can read/write each memory container.
- **Composes naturally with AgentLevy.** Imagine a compliance agent that uses MemWal to remember "this counterparty was screened 3 months ago, here's what we found" and AgentLevy to charge / receive payment with an audit trail for each new screening. Different layers, no overlap.
- **Q&A line:** *"MemWal is the memory layer; we're the settlement layer. They compose — agents use MemWal to remember context across sessions, AgentLevy to get paid for verified work. Both projects share a thesis that the agent economy needs cryptographically-verifiable substrates, just at different levels of the stack."*
- **Subtle differentiation worth noting:** MemWal needs Sui ACLs because *conversation logs are private*. Our derivation certs are *meant* to be publicly verifiable — the pitch line "verifiable from public keys alone" is a feature MemWal explicitly cannot offer for its data type.

#### Mem0
- Vector-based memory layer (embeddings + retrieval). Centralized SaaS today, not blockchain-anchored.
- **Q&A line:** *"Mem0 is the centralized version of what MemWal is doing on-chain. Both solve memory; neither solves settlement. Different problem from us."*

#### Letta (ex-MemGPT)
- Managed agent memory + state framework.
- **Q&A line:** *"Same as Mem0 — agent memory infrastructure, no settlement story."*

### Dispute / Verification

This is the layer that handles **"the cert is signed and well-formed, but is the content semantically correct?"** — the question the chain cannot answer for non-deterministic LLM tasks. Important because AgentLevy is non-deterministic-by-default (see [`docs/PHASE_2_DESIGN.md`](PHASE_2_DESIGN.md) section on determinism).

#### Kleros (Ethereum)
- Decentralized dispute-resolution protocol, live since 2018, native token PNK. Anyone can submit a dispute; the protocol randomly draws jurors who stake PNK to vote; wrong-side jurors lose stake. Used in production for content moderation, escrow disputes, insurance claims, court-style arbitration.
- **Why it matters to AgentLevy:** the natural composable layer for *contested* certs. The XRPL escrow can verify a cert is signed by the right agent and matches a committed hash; Kleros-style arbitration can verify the cert content is *semantically correct* when a buyer disputes it. Small-but-important fraction of cases.
- **Q&A line:** *"In production, when a buyer disputes that the agent actually did the work correctly — not whether the cert is well-formed, but whether the beneficial-ownership extraction was right — Kleros-style decentralized arbitration is the natural composable layer. We don't need it for the demo because cached LLM responses make outputs deterministic, but it's the right answer for production."*
- **Stronger version of the Q&A line if asked specifically about LLM non-determinism:** *"Two-layer answer. (1) Most cases never need dispute — the cert is signed, the work is reasonable, the buyer accepts and the escrow releases. (2) For the small fraction that's contested, Kleros (or any equivalent staked-arbitration protocol) handles it. We're not trying to solve dispute resolution; we're trying to solve cryptographic settlement, which is the easier and bigger problem."*

#### Flare FDC (Flare Data Connector)
- Flare's oracle attestation layer using Merkle proofs. The *old* AgentLevy used this for cross-chain data attestation.
- **Q&A line:** *"FDC is Flare-native and the old AgentLevy depended on it. The new design replaces it with PRISM derivation certificates + Ed25519 signatures, which are stronger because they don't require trust in a Flare-specific oracle layer."*

#### Reality.eth, UMA
- Optimistic Q&A / oracle layers ("post a question, post an answer, anyone can challenge during the dispute window").
- **Q&A line:** *"Optimistic oracles are good for 'is this fact true' questions. We're handling 'did this agent do this specific work' which is more about cryptographic chain integrity than fact verification — different shape of problem."*

### Compute / Reasoning

We use **Anthropic Claude with tool use** — verified working in `scripts/test_llm.py`. That's a swap-in choice; the rest of the stack is provider-agnostic (with appropriate rewrite of `agentlevy/llm/client.py`).

- **Q&A line if asked about provider lock-in:** *"The protocol is provider-agnostic. We use Anthropic for the demo because tool use + structured-output reliability is best-in-class today, but the LLM is one swappable component below the canonicalization layer. Switching providers means rewriting one file."*

## The punchline (for the slide)

| Layer | Problem | Project picks one bet |
|---|---|---|
| Compute | Reason about messy inputs | Anthropic / OpenAI / open |
| Memory | Remember across sessions | **MemWal** (verifiable) / Mem0 (centralized) |
| **Settlement** | **Pay for verified work, with audit trail** | **★ AgentLevy-XRPL-UOR ★** (impl) + **★ VTEAI ★** (spec) |
| **Addressing** | **Canonical identity for content** | **★ PRISM ★** (engine) + **★ UOR-ADDR-1 ★** (spec) |
| Dispute | Resolve contested outputs | Kleros (decentralized arbitration) |

**AgentLevy occupies the settlement layer AND co-authors the two open standards underneath it (VTEAI for settlement, UOR-ADDR-1 for addressing). We compose upward with memory, downward with dispute, sideward with compute providers. The bet is that the settlement+addressing layers are currently empty for agent commerce, that XRPL Smart Escrow + PRISM content addressing is the right primitive to fill them, and that the protocol layer should be open standards anyone can implement.**

## What we explicitly do NOT do (out of scope)

So we never get cornered into defending positions we don't hold:

- **Not a payment standard at the HTTP layer** (that's x402 / AP2)
- **Not an agent network with native tokens** (that's Kite)
- **Not a memory store** (that's MemWal / Mem0 / Letta)
- **Not a dispute-resolution protocol** (that's Kleros / UMA)
- **Not a chain** (we *use* XRPL)
- **Not an LLM provider** (we *use* Anthropic)
- **Not a smart-contract language or runtime** (we *use* XLS-100 SmartEscrow + WASM)

What we ARE: the cryptographic-settlement protocol for agent-to-agent compliance work, with content-addressed derivation certificates as the audit-trail substrate, settled on XRPL, currently demoing KYC beneficial-ownership + sanctions screening.
