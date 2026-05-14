# UOR-ADDR-1 — Universal Addressing Standard for Agent Content

> **Source:** Authored by Maura Clark (originating as a community proposal in the "ODE to LOVE" channel, April 27, 2026) and **contributed to the UOR Foundation in May 2026**. The reference Rust implementation was co-authored with Alex Flom of the UOR Foundation.
>
> **Status:** Reference implementation published as [`uor-addr-1` v0.1.0](https://crates.io/crates/uor-addr-1) on crates.io under Apache-2.0 (May 2026), hosted at [github.com/UOR-Foundation/uor-addr-1](https://github.com/UOR-Foundation/uor-addr-1). Carries a numbered conformance contract, Lean-mechanized proofs, and live byte-identity cross-validation against the UOR Foundation's canonical reference endpoint. Spec finalization (v0.1 → v1.0), additional language bindings (Solidity, TypeScript), and chain-specific bindings remain open for community contribution.
>
> **Pitch posture:** position as a UOR Foundation-hosted standard with a live reference implementation. Recruit collaborators for spec finalization, additional language bindings, and chain-specific integrations.

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
| **Rust core implementation** | ✅ **Published** — [`uor-addr-1` v0.1.0](https://crates.io/crates/uor-addr-1) on crates.io, hosted at [UOR-Foundation/uor-addr-1](https://github.com/UOR-Foundation/uor-addr-1). Future versions / advanced features ongoing. | UOR Foundation core team |
| **Solidity reference implementation** | Not started | EVM developers |
| **TypeScript reference implementation** | Not started | Web3 frontend / SDK developers |
| **Chain-specific bindings (EVM, XRPL, Solana, Cosmos, Flare)** | Not started | Chain implementers per ecosystem |
| **Integration with agent commerce frameworks** | Not started | Founders of agent platforms (Moca, Hedera AgentKit, Kite, Skyfire, etc.) |

**Concrete ask for Consensus:** *"If you're building agent infrastructure and you'd be a fool to keep reinventing content addressing, talk to me at Consensus. We're recruiting collaborators on UOR-ADDR-1's reference implementations and chain bindings."*

---

## Where to follow up post-Consensus

- **UOR-ADDR-1 reference implementation:** [crates.io/crates/uor-addr-1](https://crates.io/crates/uor-addr-1) (v0.1.0, Apache-2.0)
- **UOR-ADDR-1 repo:** [github.com/UOR-Foundation/uor-addr-1](https://github.com/UOR-Foundation/uor-addr-1)
- **UOR Foundation org:** [github.com/UOR-Foundation](https://github.com/UOR-Foundation)
- **Underlying foundation crates:** [`uor-foundation`](https://crates.io/crates/uor-foundation), [`uor-foundation-sdk`](https://crates.io/crates/uor-foundation-sdk)
- **AgentLevy demo as proof-of-concept:** this repo
- **Moca airkit (proposed framework):** [docs.moca.network/airkit](https://docs.moca.network/airkit)

When meeting collaborators in person at Consensus, capture:
- Name + handle + ecosystem
- What chain / framework they'd implement
- Whether they're interested in spec review, reference impl, or integration
- Best follow-up channel (Discord, email, GitHub)

---

## Open questions to resolve post-Consensus (out of scope for the demo)

These came up while reading the proposal and don't block the pitch — flag for follow-up:

1. **Where does the v1.0 spec text live?** The reference implementation is published, but the normative specification text (v0.1 → v1.0) is still being finalized. A public GitHub markdown mirror under the UOR Foundation org is the natural destination.
2. **Is "UOR-ADDR-1" the canonical name?** ✅ **Resolved (May 2026):** Confirmed as the canonical name. The crate `uor-addr-1` is published on crates.io and hosted at the UOR Foundation org under that designation.
3. **What's the relationship to UOR Foundation governance?** ✅ **Resolved (May 2026):** Standard authored by Maura Clark and **contributed to the UOR Foundation**; reference implementation hosted at [UOR-Foundation/uor-addr-1](https://github.com/UOR-Foundation/uor-addr-1). Framing: "contributed to" the foundation. Maura is a UOR Foundation contributor; Alex Flom of the UOR Foundation co-authored the reference implementation.
4. **Moca airkit specifically** — is there an existing conversation with Moca, or is this proposing a target without Moca's endorsement yet? Affects whether the pitch can name them or should be more abstract ("agent-identity frameworks").
