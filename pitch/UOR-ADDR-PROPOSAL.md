# UOR-ADDR-1 — Universal Addressing Standard for Agent Content

> **Source:** community proposal from "ODE to LOVE" channel, April 27, 2026 (5 days before Consensus). User (Maura Clark) is contributor.
>
> **Status:** v0.1 draft. Goal: advance to v1.0 with reference implementations and chain bindings. Rust crates published at https://crates.io/crates/uor-foundation.
>
> **Pitch posture:** mention prominently at Consensus. Goal is to **recruit collaborators** for spec finalization, reference implementations, and chain-specific bindings.

---

## The proposal (verbatim from the community message)

> **tldr:** Proposal to establish **UOR-ADDR-1**: a minimal, chain-agnostic standard for canonical content addressing built on PRISM's triadic coordinate system.
>
> It provides universal, verifiable identities for the content and outputs that agents produce and exchange.
>
> **The Problem (Why)**
>
> The agentic economy is scaling fast — agents are already buying services, paying for information, and settling work on-chain. However, every platform, chain, and framework is creating its own ad-hoc identity conventions for content. Without a shared standard, these will harden into incompatible silos, mirroring stablecoin fragmentation. Current solutions (CAIP, DID, IPFS CIDs, Hugging Face, x402) leave a critical gap: **chain-agnostic canonical identity for agent-produced content**.
>
> **The Solution (How)**
>
> UOR-ADDR-1 delivers a precisely-scoped standard analogous to CAIP or DID:
>
> - URI scheme + wire format for portable PRISM triads
> - Deterministic canonicalization rules
> - Derivation certificate format for cryptographic provenance
> - Minimal verification interface
> - Chain-specific bindings (EVM, XRPL, Solana, Cosmos, Flare)
>
> It sits on top of existing primitives **without replacing them**, enabling any compliant chain, wallet, contract, or agent framework to interoperate.
>
> **Components Needed (What)**
>
> - Finalization of the specification from v0.1 draft to v1.0
> - Reference implementations (Rust core, Solidity, TypeScript)
> - Initial integrations with agent commerce frameworks and chain ecosystems
> - Chain-specific bindings as adoption grows
>
> **Call to collaborate:** This is high-leverage infrastructure that can become the default identity layer for agent commerce.
>
> We have RUST Crates built. https://crates.io/crates/uor-foundation

---

## Where UOR-ADDR-1 sits relative to existing standards

UOR-ADDR-1 explicitly positions itself in the gap left by current options:

| Standard | What it addresses | What it leaves out |
|---|---|---|
| **CAIP** (Chain Agnostic Improvement Proposals) | Account/asset references across chains | No semantics for content content addressing; assumes pre-existing chain identity |
| **DID** (Decentralized Identifiers) | Subject-as-URI, resolved via DID method | No notion of *content* identity, only entity identity |
| **IPFS CIDs** | Content-addressed by hash | Single-axis (just a hash); no algebraic structure for similarity / transformation reasoning |
| **Hugging Face model IDs** | Centrally-namespaced model artifacts | Not chain-agnostic; not cryptographic; not content-derived |
| **x402** | HTTP-layer payment for resources | Not an identity standard |

UOR-ADDR-1 specifically delivers **chain-agnostic canonical identity for agent-produced content** — which none of the above do.

---

## How AgentLevy-XRPL-UOR composes with UOR-ADDR-1

This is the pitch line: AgentLevy is the **first reference implementation** of the two-standard stack.

```
┌─────────────────────────────────────────────────────────┐
│  VTEAI (Verified Task Escrow + Attestation Interface)  │   "settlement"
│   — ERC draft, Maura Clark, April 4, 2026             │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ taskSpecHash, attestationHash, outputHash
                          │ are addressed via...
                          ▼
┌─────────────────────────────────────────────────────────┐
│  UOR-ADDR-1 (Universal Addressing for Agent Content)   │   "addressing"
│   — community proposal, April 27, 2026                 │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ built on...
                          ▼
┌─────────────────────────────────────────────────────────┐
│  PRISM (UOR Foundation, MIT)                            │   "primitive"
│   — algebraic content-addressed coordinate system      │
└─────────────────────────────────────────────────────────┘
```

**AgentLevy demos all three:**
- VTEAI's state machine and interface (TaskSpec, attestation, settlement)
- UOR-ADDR-1's coordinate identities (`spec_triad`, `cert_triad`, `output_triad` are early UOR-ADDR-1-shaped addresses)
- PRISM as the underlying primitive

If we wanted to be precise about it: every triad we compute in `agentlevy/prism_layer/triad.py` IS what UOR-ADDR-1 will eventually formalize as a canonical PRISM address. We're producing UOR-ADDR-1 v0.1-shaped addresses already.

---

## Framework / integration target: Moca airkit

Per user direction, the proposed framework underlying UOR-ADDR-1's agent-identity binding is **Moca Network's airkit** (https://docs.moca.network/airkit).

Why airkit makes sense as the framework:
- Moca is a Web3 identity/credentials platform with existing agent infrastructure
- airkit provides agent identity primitives that UOR-ADDR-1 can build on rather than reinvent
- Aligns with UOR-ADDR-1's "sits on top of existing primitives, doesn't replace them" design principle

**Pitch caveat:** mention airkit as the *intended* framework, not as already-integrated. The Phase 2 build does not include airkit (out-of-scope per the original plan). At Consensus, frame as forward composition.

---

## Components needed (open call to collaborate)

From the proposal, what's specifically open for contribution:

| Component | Status | Who could help |
|---|---|---|
| **Spec finalization v0.1 → v1.0** | Draft exists; needs review/refinement | Standards-track contributors, protocol designers |
| **Rust core implementation** | In progress (crates.io published) | Rust developers, library authors |
| **Solidity reference implementation** | Not started | EVM developers |
| **TypeScript reference implementation** | Not started | Web3 frontend / SDK developers |
| **Chain-specific bindings (EVM, XRPL, Solana, Cosmos, Flare)** | Not started | Chain implementers per ecosystem |
| **Integration with agent commerce frameworks** | Not started | Founders of agent platforms (Moca, Hedera AgentKit, Kite, Skyfire, etc.) |

**Concrete ask for Consensus:** *"If you're building agent infrastructure and you'd be a fool to keep reinventing content addressing, talk to me at Consensus. We're recruiting collaborators on UOR-ADDR-1's reference implementations and chain bindings."*

---

## Where to follow up post-Consensus

- Crates.io: https://crates.io/crates/uor-foundation (Rust crates already live)
- UOR Foundation org: https://github.com/UOR-Foundation
- AgentLevy demo as proof-of-concept: this repo
- Moca airkit (proposed framework): https://docs.moca.network/airkit

When meeting collaborators in person at Consensus, capture:
- Name + handle + ecosystem
- What chain / framework they'd implement
- Whether they're interested in spec review, reference impl, or integration
- Best follow-up channel (Discord, email, GitHub)

---

## Open questions to resolve post-Consensus (out of scope for the demo)

These came up while reading the proposal and don't block the pitch — flag for follow-up:

1. **Where does the v0.1 draft live?** Is there a public document we can link from the slide footer? If on a wiki / Notion / Discord — Consensus visibility justifies a public GitHub markdown/PDF mirror.
2. **Is "UOR-ADDR-1" the canonical name** or is the community still settling? Consistent naming matters for adoption.
3. **What's the relationship to UOR Foundation governance?** Is the proposal community-driven with Foundation acknowledgment, or Foundation-driven with community input? Affects how the pitch frames it ("contributing to" vs "co-authoring with").
4. **Moca airkit specifically** — is there an existing conversation with Moca, or is this proposing a target without Moca's endorsement yet? Affects whether the pitch can name them or should be more abstract ("agent-identity frameworks").
