# Agent Framework — conceptual draft

> **Status: v0.1 conceptual draft**, May 2 2026. Working name *TBD* (placeholder: "the framework"). Sister artifacts: [`pitch/UOR-ADDR-PROPOSAL.md`](UOR-ADDR-PROPOSAL.md) (addressing standard) and [`pitch/VTEAI-DRAFT.md`](VTEAI-DRAFT.md) (settlement standard). After review, expand into a formal spec doc and an SDK API surface document.

## What this is

A multi-language **agent framework SDK** parallel in shape to Moca's [AIR Kit](https://docs.moca.network/airkit) but oriented toward agent-to-agent commerce instead of user identity. It packages five service pillars on top of the UOR Foundation primitives (PRISM, UOR-ADDR-1, VTEAI, UOR-Framework ontology, optionally ATLAS embeddings) into a developer-facing SDK that any agent runtime can adopt without re-implementing the substrate.

## Why this exists (the gap)

Moca's AIR Kit identifies fragmentation in user identity and packages a solution: SSO + credential issuance/verification with privacy-preserving ZK. The agent economy has the **same fragmentation pattern, one layer over**:

| Fragmentation airkit solved | Equivalent for agents |
|---|---|
| Repeated KYC across applications | Repeated agent identity registration across platforms |
| Credentials trapped per-platform | Reputation trapped per-marketplace |
| PII stored everywhere | Cert-content stored in proprietary silos |
| No portable user identity | No portable agent identity |
| Centralized identity providers | Centralized agent registries |

What UOR Foundation already provides that solves part of this:

| UOR piece | What it gives us |
|---|---|
| **PRISM** (vendored, MIT) | Algebraic content addressing — every value gets a canonical triadic coordinate. Eliminates per-platform content-ID schemes. |
| **UOR-ADDR-1** (v0.1 draft) | Chain-agnostic URI scheme + canonicalization rules + derivation cert format on top of PRISM. The standard for *what an address looks like*. |
| **UOR-Framework** (Rust + Lean ontology) | 34 namespaces of formal vocabulary, downloadable as JSON-LD/Turtle/OWL/SHACL — usable as the schema substrate for agent capabilities and credentials. |
| **ATLAS** (research-stage, archived 2026-02) | Mathematical foundation for embedding spaces with exceptional group symmetry — usable for richer similarity reasoning over PRISM coordinates than plain Hamming distance. |

What UOR Foundation does **not** yet provide:

| Gap | What's missing |
|---|---|
| **Agent identity binding** | UOR-Framework's "Identities" are mathematical theorems, not agent IDs. There's no concept of "agent X is this Ed25519 keypair, addressable via UOR-ADDR-1." |
| **Agent discovery / reputation** | No registry, no discovery protocol, no reputation accumulation pattern. |
| **Negotiation + settlement** | VTEAI is a draft ERC for the EVM side; there's no XRPL or Sui or general "agent agrees with agent on a task" library. |
| **Multi-language SDK** | Bindings exist for Rust and Lean. **No TypeScript or Python.** Most agent runtimes today are TS or Python. |

The framework fills these four gaps. It does **not** re-implement what UOR Foundation already provides — it depends on those pieces.

## The five pillars

Two pillars parallel airkit; three are unique to agent commerce.

### 1. Account Services (parallel to AIR Account Services)

Manages agent identity — the analog of "user login" but for autonomous agents.

| Capability | What it does |
|---|---|
| **Keypair lifecycle** | Generate / import / export Ed25519 keypairs. Optionally hardware-backed. |
| **UOR-ADDR-1 binding** | Bind a public key to a UOR-ADDR-1 URI. The URI is `urn:uor:agent:<chain>:<pubkey-encoded-as-PRISM-triad>` (final form to be settled in spec). |
| **On-chain registration (optional)** | Anchor the key→URI binding in an XRPL ledger entry, an EVM contract, a Sui object, etc. — chain-specific bindings per UOR-ADDR-1's adapter pattern. |
| **Resolution** | Given a UOR-ADDR-1 agent URI, fetch the public key and any on-chain attestation. |

**Trust model:** the agent's keypair *is* the agent. On-chain anchoring is for discoverability, not trust. Anyone with the public key can verify any cert the agent signs without consulting any registry.

### 2. Content Services (parallel to AIR Credential Services)

Manages content the agent produces — task specs, derivation certificates, attestations.

| Capability | What it does |
|---|---|
| **Issue** | Build a Pydantic/TypeScript-typed object (TaskSpec, DerivationCert, etc.), canonicalize it per UOR-ADDR-1 rules, sign with the agent's key, compute its triad. |
| **Verify** | Given a cert, verify: signature is valid against claimed pubkey; canonical bytes hash to claimed triad; chain of subcontract references resolves; operation_description matches its declared schema. |
| **Consume / resolve** | Given a UOR-ADDR-1 content URI, resolve to the underlying canonical bytes (off-chain storage, IPFS, Walrus, raw KV — adapter-pluggable). |
| **Subcontract chains** | First-class support for one cert referencing another by triad. Verification walks the chain. |

This is what AgentLevy already does — packaged as reusable SDK primitives instead of demo-specific code.

### 3. Settlement Services (no airkit equivalent — VTEAI implementation)

Implements the [VTEAI ERC draft](VTEAI-DRAFT.md) as a chain-agnostic API.

| Capability | What it does |
|---|---|
| **Negotiation** | Bounded-turn negotiation protocol between two agents (request / counter / accept / sign). Returns a dual-signed TaskSpec. |
| **Escrow** | Chain-pluggable escrow primitives: XRPL `EscrowCreate` (with optional XLS-100 SmartEscrow `FinishFunction`), EVM Treasury contract (per VTEAI), Sui escrow object. |
| **Attestation submission** | Seller submits final cert; escrow validates per chain-specific rules; payment releases. |
| **Refund / timeout** | Per VTEAI spec — refund path if no attestation, dispute path if contested. |

### 4. Reputation Services (no airkit equivalent)

Tracks agent history of certs and computes similarity / reputation in coordinate space.

| Capability | What it does |
|---|---|
| **Cert history** | Index an agent's published derivation certs (off-chain, optionally pinned to chain). |
| **Distance metrics** | Compute Hamming distance between two triads (PRISM-native). Optionally compute richer similarity via ATLAS embeddings — embed PRISM coordinates into E₈ root system for algebraic similarity reasoning. |
| **Reputation queries** | "Show me agents who have issued certs for `kyc.beneficial_ownership_verify` with output triads similar to triad X." |
| **Stake / slash hooks** | Optional integration points for staking layers (out of scope for v1 spec; included as design hook). |

### 5. Discovery Services (no airkit equivalent)

Finds agents by capability, by reputation, by URI.

| Capability | What it does |
|---|---|
| **Capability vocabulary** | Use UOR-Framework namespaces as the schema for capability declarations. An agent advertises capabilities as references into the ontology (e.g., `uor:schema:KYCComplianceTask`). |
| **Resolution** | Given a UOR-ADDR-1 agent URI, fetch the agent's capability profile + endpoint. |
| **Search** | Find all agents claiming capability X, optionally filtered by reputation in coordinate space. |
| **Routing for subcontracts** | When a compliance agent needs to subcontract sanctions screening, the framework resolves "find me a sanctions-screen-capable agent above reputation threshold T" via Discovery. |

## How the pillars compose

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Application Code (your agent)                     │
└──────────────────────────────────────────────────────────────────────┘
            │
            │  uses framework SDK (TS / Python / Rust)
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Framework SDK                                                        │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────┐│
│  │ Account  │  │ Content  │  │ Settlement │  │Reputation│  │Disco-││
│  │ Services │  │ Services │  │ Services   │  │ Services │  │ very ││
│  └──────────┘  └──────────┘  └────────────┘  └──────────┘  └──────┘│
└──────────────────────────────────────────────────────────────────────┘
       │              │               │               │           │
       ▼              ▼               ▼               ▼           ▼
   UOR-ADDR-1     UOR-ADDR-1     VTEAI          PRISM        UOR-Framework
   (URIs +        (cert format)  (settlement    (Hamming)    (capability
    binding)                      interface)    + ATLAS      vocabulary)
                                                 (similarity,
                                                  optional)
       │              │               │               │           │
       └──────────────┴───────────────┴───────────────┘           │
                              │                                    │
                              ▼                                    │
                          PRISM                                    │
                          (algebra: vendor/prism.py, MIT,          │
                           formally proven in Lean 4)              │
                                                                   │
                                                                   ▼
                                                     RDF/OWL/JSON-LD/SHACL
                                                     (downloadable from
                                                      UOR Foundation)
```

## Form factors

| Language | Status | Why |
|---|---|---|
| **Rust** | Already in flight — the `uor-foundation` crate publishes typed traits and constants (no_std-compatible) | High-performance agent runtimes, smart contract hosts, Craft CLI tooling |
| **Python** | Gap — needs to be built | The most common agent runtime today (Anthropic + LangChain + LlamaIndex etc. are Python-first). AgentLevy's Phase 2 implementation is the seed. |
| **TypeScript** | Gap — needs to be built | Node.js agent runtimes, web-facing agent UIs, browser-side verification. Pairs with airkit's Web SDK. |
| **(Optional later)** Flutter / mobile | Out of scope v1 | Mobile agents are a niche today; airkit's mobile pillar can be referenced/composed if needed. |

The Python and TypeScript SDKs are the **highest-value contributions to recruit** at Consensus. Rust is the existing crate; Lean is for formal verification only.

## Differentiators vs AIR Kit

| Aspect | AIR Kit | This framework |
|---|---|---|
| **Subject** | Users | Agents |
| **Identity model** | User-controlled SSO + wallet | Agent-controlled keypair, optionally chain-anchored |
| **Credential type** | ZK-proven attributes ("user is over 21") | Content-addressed derivation certs ("agent did this work, here's the chain") |
| **Privacy model** | ZK by default | Public verification by default (the "verifiable from public keys alone" feature) |
| **Crypto primitives** | Zero-knowledge proofs | Ed25519 + PRISM triads + Lean-formalized algebra |
| **Form factors** | Web SDK (JS), Flutter SDK | TS / Python / Rust SDKs |
| **Standards underneath** | Implied / proprietary | Open: VTEAI (ERC draft) + UOR-ADDR-1 (community proposal) + UOR-Framework (RDF/OWL ontology) |
| **Formal verification** | Not stated | PRISM + ATLAS Lean 4 formalizations (1,454 lines, 54 theorems, 0 sorrys in ATLAS) |
| **Settlement integration** | Not built-in | First-class (Settlement Services pillar) |
| **Reputation** | User-portable credentials | Agent reputation via cert history + coordinate distance |

The two-line pitch differentiation:

> *"AIR Kit packaged user identity for the consumer Web3 stack. We're packaging agent identity, content, settlement, reputation, and discovery for the agent economy stack — on open standards, with formally proven primitives, and with the SDK form factors agent developers actually use today (Python and TypeScript, not just Web SDKs)."*

## What's open (call to collaborate)

This conceptual draft establishes the shape. To advance to v1.0 we need:

| Workstream | Who could lead |
|---|---|
| **Spec doc** (interface definitions, state machines, URI schemes, error model) | Standards-track contributors familiar with VTEAI and UOR-ADDR-1 |
| **Python SDK** | Python developers building on Anthropic / LangChain / agentic frameworks |
| **TypeScript SDK** | Node/web developers wanting agent infrastructure for browser-facing apps |
| **Reference Rust impl** of the framework (above the existing `uor-foundation` crate) | Rust developers extending the existing crate |
| **Reputation embeddings adapter** (optional ATLAS integration) | Researchers interested in similarity reasoning over PRISM coordinates |
| **Discovery / capability registry** | Anyone with experience in DID-resolver / OpenAPI-style registries |
| **Chain-specific bindings** (XRPL, EVM, Sui, Solana, Cosmos) | Per-chain implementers; one per ecosystem |

## Open questions for spec-phase

These should be resolved before the framework moves from concept to formal spec:

1. **Naming.** "AAK" (Agent Account Kit)? "ACK" (Agent Commerce Kit)? Just "agent-kit"? Or align with airkit naming convention deliberately ("agent-airkit"? "AIRA — AIR for Agents"?).
2. **Relationship to UOR Foundation governance.** Is this a Foundation-led project or a community-led project that the Foundation acknowledges? Affects funding, repo location, branding.
3. **Relationship to airkit specifically.** Co-marketed? Independent? Composable wrapper that calls into airkit for human-side identity when present?
4. **ATLAS dependency.** Optional adapter, or default reputation engine? The archived-read-only status of ATLAS argues for *optional* — the framework should work without it.
5. **Capability vocabulary boundaries.** Are agents free to define new capability schemas, or must they reference the UOR-Framework ontology? Trade-off: openness vs interoperability.
6. **Settlement chain priority.** Which chain bindings ship in v1.0? AgentLevy's bet is XRPL (because XLS-100 SmartEscrow is the right primitive). Other chains will follow per UOR-ADDR-1's adapter pattern, but v1.0 needs a clear "minimum viable chain set" — likely XRPL + EVM at minimum.

## Where this lives in the AgentLevy repo

For now, **as design documentation** in `pitch/AGENT-FRAMEWORK-CONCEPT.md` (this file). When the framework graduates from concept to code, it gets its own repo (likely under the UOR Foundation org). AgentLevy-XRPL-UOR remains the **first reference implementation** of the framework's principles, even if the framework code is spun out separately.

Three follow-on docs to create after this one is reviewed:

- **`pitch/AGENT-FRAMEWORK-SPEC.md`** — formal spec: interface definitions, URI schemes, state machines, error semantics. Style: like VTEAI-DRAFT.md.
- **`pitch/AGENT-FRAMEWORK-SDK.md`** — API surface: function signatures across TS/Python/Rust, with usage examples. Style: like a developer reference.
- **`pitch/AGENT-FRAMEWORK-COMPARISON.md`** (optional) — side-by-side with airkit, MetaMask Snaps, OpenAI Agents SDK, LangChain, etc. Useful for the "why this and not X" pitch question.

## References

- [Moca AIR Kit (the inspiration / parallel)](https://docs.moca.network/airkit)
- [UOR Foundation — Make Data Identity Universal](https://uor.foundation/)
- [UOR-Framework — namespaces overview](https://uor-foundation.github.io/UOR-Framework/namespaces/)
- [UOR-Framework — identities (mathematical theorems, not agent IDs)](https://uor-foundation.github.io/UOR-Framework/identities/)
- [UOR-Framework — explore (ontology browser)](https://uor-foundation.github.io/UOR-Framework/explore/)
- [UOR-Framework — downloads (JSON-LD, Turtle, OWL, SHACL, EBNF)](https://uor-foundation.github.io/UOR-Framework/download/)
- [PRISM repo (MIT)](https://github.com/UOR-Foundation/prism), pinned at commit `6cafdac` in `vendor/prism.py`
- [PRISM CONCEPTS, ALGEBRA, API docs](file:///Users/mauraclark/prism/docs/) (local)
- [ATLAS embeddings (archived read-only Feb 2026, v0.1.1)](https://github.com/UOR-Foundation/atlas-embeddings)
- [`uor-foundation` Rust crate](https://crates.io/crates/uor-foundation)
- [VTEAI ERC draft (settlement standard)](VTEAI-DRAFT.md)
- [UOR-ADDR-1 community proposal (addressing standard)](UOR-ADDR-PROPOSAL.md)
