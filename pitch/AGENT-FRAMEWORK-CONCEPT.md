# Agent Framework — conceptual draft (v0.2)

> **Status: v0.2 conceptual draft**, May 3 2026. Refactored from v0.1 after research on existing UOR Sandbox projects revealed the framework should *compose* existing infrastructure rather than re-implement it. Working name *TBD* (placeholder: "the framework"). Sister artifacts: [`pitch/UOR-ADDR-PROPOSAL.md`](UOR-ADDR-PROPOSAL.md) (addressing standard) and [`pitch/VTEAI-DRAFT.md`](VTEAI-DRAFT.md) (settlement standard).

## What this is

**An integration layer for the agent commerce stack.** Not a from-scratch SDK. Not a new identity system. The framework composes four existing UOR Foundation Sandbox projects (UOR Identity, UOR Certificate, UNS, UOR MCP) into a developer-facing kit that agent runtimes can adopt with minimal glue code, then adds the two layers UOR doesn't yet provide: **bounded-turn negotiation** and **VTEAI settlement integration**.

In one sentence: *"The framework is the smallest amount of code that turns four UOR Foundation primitives into an agent-economy SDK."*

## How v0.2 differs from v0.1

The v0.1 draft (commit `72cadf5`) proposed five service pillars — Account, Content, Settlement, Reputation, Discovery — designed as if from scratch. Research on UOR Foundation's actual Sandbox projects revealed that **three of those five pillars already exist as production projects** with active codebases. The v0.2 reframe:

| v0.1 pillar | v0.2 status | Reason |
|---|---|---|
| Account Services | **Compose UOR Identity directly** | UOR Identity explicitly covers AI agents; uses Dilithium-3 keypairs with content-addressed identity. We use it; we don't re-invent it. |
| Content Services | **Compose UOR Certificate directly** | UOR Certificate ships `cert:derivedFrom` chains, W3C VC interop, DID resolution. We use it; we don't re-invent it. |
| Discovery Services | **Compose UNS directly** | UNS already includes `UnsAgentGateway` with `AgentRegistration`, `AgentMessage`, `RouteResult`, `InjectionAlert`. We use it; we don't re-invent it. |
| Settlement Services | **Implement** (genuinely new) | No UOR project does VTEAI-style escrow or settlement. We add this layer. |
| Reputation Services | **Compose + thin add** | Reputation = aggregating an agent's history of UOR Certificates, queryable via UNS resolvers. The aggregation layer is thin. |
| (NEW) Negotiation | **Implement** (genuinely new) | Bounded-turn agent negotiation isn't in any UOR project. We add this layer. |
| (NEW) Agent commerce SDK packaging | **Implement** | UOR has Rust + Lean published bindings. **There is no published TypeScript or Python SDK.** Most agent runtimes are TS/Python. We package it. |

The v0.2 framework is therefore much smaller in scope than the v0.1 framing suggested — and that's the strength of the position, not a weakness. **It's a respectful integration layer, not a competitive re-invention.**

## Position in UOR's 6-layer architecture

The UOR Foundation defines a [6-layer architecture](../docs/UOR_FOUNDATION_OVERVIEW.md): Foundation (L0), Identity (L1), Structure (L2), Resolution (L3), Verification (L4), Transformation (L5). UOR Foundation also names six application domains where the architecture applies — and **"Agentic AI"** is one of them, defined as: *"Give AI systems a single, reliable map of all available data so they can find, verify, and use information on their own."*

This framework is **the canonical Agentic AI application of UOR's 6-layer architecture.** It binds the five layers UOR provides into a coherent agent-commerce SDK and adds two layers above (Settlement, Negotiation) that the agent economy needs but UOR doesn't address.

| UOR Layer | Implementation | Source |
|---|---|---|
| **L0 Foundation** | Algebraic primitives | PRISM (vendored at `vendor/prism.py`) |
| **L1 Identity** | Agent keypair binding to UOR address | UOR Identity (composed) |
| **L2 Structure** | Cert canonicalization, derivation chains, JCS+NFC | Implemented in `canonical.py`, byte-identical to UOR |
| **L3 Resolution** | Agent discovery, capability lookup, reputation queries | UNS (composed via `UnsClient`, `UnsAgentGateway`) |
| **L4 Verification** | Signature + chain + envelope verification | UOR Certificate + UOR MCP `uor.verify_passport` (composed) |
| **L5 Transformation** | Format adapters when content crosses formats | Pluggable; uses UOR-Framework ontology serializations from `vendor/uor-ontology/` |
| **(Above L5) Settlement** | XRPL Smart Escrow + VTEAI state machine | Implemented in this framework (genuinely new) |
| **(Parallel to L1) Negotiation** | Bounded-turn agent-to-agent negotiation protocol | Implemented in this framework (genuinely new) |

## What we COMPOSE — and where it lives

For each composed UOR project, the framework provides a thin wrapper that exposes the project's primitives as Python/TypeScript-ergonomic objects, hides the cross-project plumbing, and provides sensible defaults for agent-commerce use cases.

### UOR Identity (Sandbox; in `UOR-Foundation/website` repo)

Pipeline: keypair generation (Dilithium-3 default, Ed25519 supported) → URDNA2015 canonicalization → SHA-256 → canonical ID. The canonical ID *is* the agent's identifier; works for both humans and AI agents (verbatim from the project page: *"agents prove their existence through computation"*).

**Framework wrapper:** `agent.identity.create()`, `agent.identity.from_seed(seed)`, `agent.identity.to_uor_address()`, `agent.identity.sign(canonical_bytes)`. Returns `IdentityRecord` shaped exactly as UOR Identity defines.

### UOR Certificate (Sandbox)

API: `generateCertificate`, `verifyCertificate`, `verifyCertificateFull`, `decodeCertificate`, `certificateToTriword`, `enforceBoundary`, `deriveCoherenceWitness`. W3C VC interop via `wrapAsVerifiableCredential`. Cert subtypes: `cert:TransformCertificate`, `cert:InvolutionCertificate`, `cert:IsometryCertificate`, `cert:SessionCertificate` (defined in the Rust `uor-foundation` crate / `spec/src/namespaces/cert.rs`).

**Framework wrapper:** `agent.cert.issue(content)`, `agent.cert.verify(cert)`, `agent.cert.chain(cert)` (walks `cert:derivedFrom` references), `agent.cert.subtype("DerivationCertificate")` for AgentLevy-specific certs.

### UNS (Sandbox; the largest composed project)

`UnsClient` SDK + CLI + HTTP node + Supabase edge functions. Eleven services: Resolver, Shield, Compute, Cache, Store, KV, Ledger, Trust, Conduit, Mesh, Agent. Critically: `UnsAgentGateway` with `AgentRegistration`, `AgentMessage`, `RouteResult`, `InjectionAlert`, `MorphismType`. CRYSTALS-Dilithium-3 (FIPS 204 ML-DSA-65) for signing throughout.

**Framework wrapper:** `agent.discovery.publish(profile)`, `agent.discovery.resolve(name)`, `agent.discovery.find_by_capability(capability_uri)`, `agent.discovery.subcontract(target_role, requirements)`. All methods delegate to `UnsClient`.

### UOR MCP (Sandbox; hosted at `mcp.uor.foundation`)

10+ tools: `uor_derive`, `uor_verify`, `uor_query` (SPARQL over UOR ontology), `uor_correlate`, `uor_partition`, `uor_resolve`, `uor_certify`, `uor_trace`, `uor_schema_bridge`, `uor_schema_coherence`, `uor.encode_address`, `uor.verify_passport`. Streamable HTTP transport.

**Framework wrapper:** `agent.canonical.encode_address(content)` (calls `uor.encode_address`), `agent.canonical.verify_passport(envelope)` (calls `uor.verify_passport`), `agent.canonical.local()` (uses local PRISM at Q(31)). The local path is the demo default — no network dependency on stage. The MCP path is the production overlay — uses canonical reference implementation for cross-attestation.

## What we ADD — the two genuinely new layers

These are not in any existing UOR Sandbox project. They are the framework's actual contribution.

### Settlement (VTEAI implementation)

Implements the [VTEAI ERC draft](VTEAI-DRAFT.md) as a chain-pluggable settlement primitive.

| Concern | API |
|---|---|
| Escrow create | `agent.settle.escrow(spec, amount, chain="xrpl")` |
| Attestation submission | `agent.settle.attest(escrow_id, cert)` |
| Status query | `agent.settle.status(escrow_id)` |
| Refund / timeout | `agent.settle.cancel(escrow_id, reason)` |

Chain bindings: XRPL Smart Escrow (XLS-100) + WASM `FinishFunction` for Path A; XRPL legacy `EscrowCreate` with crypto-conditions for Path B. Future bindings (EVM, Sui, Solana, Cosmos) follow the same interface — adapter pattern per UOR-ADDR-1's chain-binding convention.

### Negotiation (bounded-turn agent protocol)

Bounded-turn negotiation between two agents to produce a dual-signed `TaskSpec`. Maximum 4 turns: `request → counter → accept → finalize`. Hard cutoff prevents LLM convergence loops at demo time.

| Concern | API |
|---|---|
| Buyer initiates | `agent.negotiate.propose(task_spec_draft)` |
| Seller responds | `agent.negotiate.respond(spec, action="accept" or "counter", changes={...})` |
| Buyer finalizes | `agent.negotiate.finalize(spec)` (both sigs must be present) |
| Cancel / timeout | `agent.negotiate.cancel(spec, reason)` |

This is the layer that makes agents *commerce* (negotiate price, terms, scope) rather than just exchanging payments for arbitrary work.

## Form factors

| Language | Status | Why this priority |
|---|---|---|
| **Python** | **Highest priority — gap in UOR ecosystem** | Most agent runtimes today are Python-first (Anthropic SDK, LangChain, LlamaIndex). UOR has no published Python package. AgentLevy's Phase 2.3 implementation seeds this SDK. |
| **TypeScript** | **High priority — gap in UOR ecosystem** | Node.js agent runtimes, browser-side verification, and pairing with airkit's Web SDK. UOR has TS modules in the website monorepo but no published `@uor/*` npm package. |
| **Rust** | Already in flight — extend existing crate | The `uor-foundation` crate publishes typed traits and constants (no_std-compatible). Framework adds a higher-level `agent-commerce` crate that depends on it. |
| **(Optional later)** Flutter / mobile | Out of scope v1 | Mobile agents are a niche today; airkit's mobile pillar can be referenced/composed if needed. |

The Python and TypeScript SDKs are the **highest-value contributions to recruit** at Consensus. They fill a gap UOR Foundation has not yet filled and the ecosystem actively needs.

## Differentiators vs AIR Kit

| Aspect | AIR Kit | This framework |
|---|---|---|
| **Subject** | Users (people) | Agents (autonomous services) |
| **Primary identity primitive** | User-controlled SSO + wallet (custodial-style) | Agent-controlled keypair, optionally chain-anchored (sovereign) |
| **Credential model** | ZK-proven attributes ("user is over 21"), private by default | Content-addressed derivation certs, **public verification by default** |
| **Crypto layers** | Zero-knowledge proofs | Ed25519 (cert layer) + Dilithium-3 (deep identity) + PRISM triadic addresses |
| **Signing primitive** | Not stated | Ed25519 at the cert layer (UOR-MCP-compatible verified live), Dilithium-3 forward path for post-quantum |
| **Standards underneath** | Implied / proprietary | **Open: VTEAI (ERC draft, CC0) + UOR-ADDR-1 (authored by Maura Clark, contributed to UOR Foundation May 2026; reference impl on crates.io) + UOR-Framework (RDF/OWL ontology, Apache-2.0)** |
| **Formal verification** | Not stated | PRISM + ATLAS Lean 4 formalizations (1,454 lines, 54 theorems, 0 sorrys in ATLAS) |
| **Settlement integration** | Not built-in | First-class via VTEAI; XRPL Smart Escrow today, multi-chain via UOR-ADDR-1 bindings |
| **Reputation model** | User-portable credentials | Agent-keypair-bound, transferable across platforms (a property no platform-locked rating system can match) |
| **Form factors** | Web SDK (JS), Flutter SDK | Python + TypeScript + Rust SDKs (fills the published-binding gap) |
| **Cross-attestation with canonical reference** | N/A | Optional `uor_certify` MCP overlay → certs cross-signed by UOR Foundation's reference implementation |

The two-line pitch differentiation:

> *"AIR Kit packaged user identity for the consumer Web3 stack. We're packaging the agent-economy stack — agent identity, content, settlement, reputation, discovery, and negotiation — by composing four existing UOR Foundation Sandbox projects and adding the two layers nobody else has built. Open standards, published Python and TypeScript bindings, and certs verified byte-identical to UOR's canonical reference implementation."*

## Path into the UOR Foundation ecosystem (Sandbox submission)

UOR Foundation runs a [3-stage maturity program](../docs/UOR_FOUNDATION_PROJECTS.md): **Sandbox → Incubating → Graduated** (CNCF-style). Existing Sandbox-stage projects include PRISM, Atlas Embeddings, Hologram, Hologram SDK, UOR MCP, UOR Identity, UOR Certificate, UNS, UOR Privacy, UOR Name Service, QR Cartridge, Atomic Language Model.

**The framework is designed for Sandbox submission from day one.** Submission criteria match what we have:

| Sandbox criterion | This framework's status |
|---|---|
| Aligns with UOR Foundation mission | ✓ — implements UOR L1–L5 for the Agentic AI domain (a UOR-named application slot) |
| Clear problem statement | ✓ — "compose the four UOR primitives plus add settlement + negotiation as a developer-facing SDK" |
| At least one committed maintainer | ✓ — Maura Clark, with AgentLevy as the working reference implementation (live-verified byte-identical to UOR Passport) |
| Open-source license (Apache 2.0 or MIT) | ✓ — recommend **Apache 2.0** for explicit patent grant (right for protocol/cryptographic work, matches UOR-Framework) |

**Likely category:** Developer Tools (parallel to Hologram SDK and UOR MCP). Not Core Infrastructure (PRISM, UOR Identity, UOR Certificate, UNS, UOR Privacy hold those slots) and not pure Systems or Open Science.

**Submission timing recommendation:** Sandbox submission AFTER spec doc is drafted (not just the conceptual draft). Technical committee evaluation is much easier with a real spec to reference. AgentLevy demoing at Consensus is a strong "production usage" signal even at Sandbox stage. The byte-for-byte verification milestone (`docs/UOR_PASSPORT_VERIFIED.md`) is the strongest possible alignment evidence.

## Adjacent UOR Sandbox projects — relationship to the framework

| Project | Relationship |
|---|---|
| **PRISM** | Vendored at `vendor/prism.py`; framework's L0 foundation |
| **UOR Identity** | Composed; framework's L1 (agent keypair binding) |
| **UOR Certificate** | Composed; framework's L4 (cert issuance + verification) |
| **UNS** | Composed; framework's L3 (agent discovery via `UnsAgentGateway`) |
| **UOR MCP** | Composed (optional production overlay); framework's L4 cross-attestation |
| **UOR Privacy** | Adjacent; could compose if agent-content needs user privacy enforcement (out of scope v1) |
| **Hologram / Hologram SDK** | Sister project; same UOR primitives, different application domain (deployment platform vs agent commerce) |
| **Atlas Embeddings** | Optional similarity engine for the Reputation thin-add layer (uses E₈ root system for content similarity); archived read-only Feb 2026 — treat as research input, not runtime dependency |
| **Atomic Language Model** | Likely downstream consumer of the framework (not overlap); a traceable LLM that could *use* the framework to certify its outputs |
| **UOR Name Service (UNS)** | (Same as UNS above) |
| **QR Cartridge** | Tangential; could optionally render an agent's identity or a cert as a QR code |

## Open questions for spec-phase

These should be resolved before the framework moves from concept to formal spec:

1. **Naming.** Some candidates the spec-phase will choose between:
   - **AAK** — Agent Account Kit (parallel to AIR Kit naming)
   - **ACK** — Agent Commerce Kit
   - **agent-kit** — neutral, descriptive
   - **AIRA** — AIR for Agents (composes airkit's brand recognition)
   - **uor-agent** — explicit UOR alignment, signals composition-first
   - Recommendation: **`uor-agent`** for the package names, **"Agent Commerce Kit"** as the human-readable name. Aligns with the composition story; the SDK package is `uor-agent` on PyPI/npm; Foundation people recognize the prefix; "Agent Commerce Kit" is the friendly version.

2. **Relationship to UOR Foundation governance.** Is this a Foundation-led project or a community-led project that the Foundation acknowledges? Affects funding, repo location, branding. **Best path:** community-led (faster, no governance friction), with a published submission to Sandbox after spec is drafted.

3. **Relationship to airkit specifically.** Composable wrapper that calls into airkit for human-side identity when present? Co-marketed? Independent? Recommendation: **independent but composable** — airkit handles human identity, framework handles agent identity, the two interoperate via UOR Identity at the substrate level.

4. **ATLAS dependency.** Optional adapter, or default reputation engine? The archived-read-only status of ATLAS argues for **optional** — the framework should work without it, and the Reputation thin-add layer should have a Hamming-distance baseline that doesn't need ATLAS.

5. **Capability vocabulary boundaries.** Are agents free to define new capability schemas, or must they reference the UOR-Framework ontology? Trade-off: openness vs interoperability. Recommendation: **anchored vocabulary by default** (use UOR-Framework namespaces), with documented extension points for new capability types.

6. **Settlement chain priority.** Which chain bindings ship in v1.0? AgentLevy's bet is XRPL (because XLS-100 SmartEscrow is the right primitive). Other chains follow per UOR-ADDR-1's adapter pattern, but v1.0 needs a clear "minimum viable chain set" — recommendation: **XRPL + EVM at v1.0**, with Sui / Solana / Cosmos in v1.1+.

## Where this lives in the AgentLevy repo

For now, **as design documentation** in `pitch/AGENT-FRAMEWORK-CONCEPT.md` (this file). When the framework graduates from concept to code, it gets its own repo (likely under the UOR Foundation org or a new Foundation-aligned org). AgentLevy-XRPL-UOR remains the **first reference implementation** of the framework's principles, even if the framework code is spun out separately.

Three follow-on docs to create after this one is reviewed:

- **`pitch/AGENT-FRAMEWORK-SPEC.md`** — formal spec: interface definitions, URI schemes, state machines, error semantics. Style: like VTEAI-DRAFT.md.
- **`pitch/AGENT-FRAMEWORK-SDK.md`** — API surface: function signatures across TS/Python/Rust, with usage examples. Style: like a developer reference.
- **`pitch/AGENT-FRAMEWORK-COMPARISON.md`** (optional) — side-by-side with airkit, MetaMask Snaps, OpenAI Agents SDK, LangChain, etc. Useful for the "why this and not X" pitch question.

## What's open (call to collaborate)

The framework is much smaller in v0.2 than the v0.1 framing suggested — most of it is **composition glue, not new infrastructure.** The recruitment ask is correspondingly tighter:

| Workstream | Who could lead |
|---|---|
| **Spec doc** (interface definitions, state machines, URI schemes, error model) | Standards-track contributors familiar with VTEAI and UOR-ADDR-1 |
| **Python SDK** (compose UOR Identity / Certificate / UNS / MCP + add settlement + negotiation) | Python developers building on Anthropic / LangChain / agentic frameworks |
| **TypeScript SDK** (same shape, JS ecosystem) | Node/web developers wanting agent infrastructure for browser-facing apps |
| **XRPL settlement binding** (UOR-ADDR-1 chain-binding pattern, XLS-100 SmartEscrow + WASM FinishFunction) | XRPL developers; AgentLevy seeds this for the demo |
| **EVM settlement binding** (Treasury-style escrow, ERC-VTEAI compliant) | EVM/Solidity developers (the original AgentLevy on Flare seeds this design) |
| **Discovery integration** (compose UNS `UnsAgentGateway` for capability lookup) | UNS contributors |
| **Reputation thin-add** (aggregate UOR Certificate history; optional ATLAS embeddings) | Researchers interested in similarity reasoning over UOR coordinates |

## References

- [UOR Foundation public architecture overview (6 layers, vocabulary, application domains)](../docs/UOR_FOUNDATION_OVERVIEW.md)
- [UOR Foundation project ecosystem (Sandbox/Incubating/Graduated)](../docs/UOR_FOUNDATION_PROJECTS.md)
- [UOR Passport verification milestone (byte-identical to AgentLevy)](../docs/UOR_PASSPORT_VERIFIED.md) ★
- [Why public-key certification matters (8 advantages, contrast cases)](../docs/WHY_PUBLIC_KEY_CERTIFICATION.md)
- [Moca AIR Kit (the inspiration / parallel)](https://docs.moca.network/airkit)
- [UOR Foundation — Make Data Identity Universal](https://uor.foundation/)
- [UOR-Framework — namespaces / identities / explore / download](https://uor-foundation.github.io/UOR-Framework/)
- [PRISM repo (MIT)](https://github.com/UOR-Foundation/prism), pinned at commit `6cafdac` in `vendor/prism.py`
- [ATLAS embeddings (archived read-only Feb 2026, v0.1.1)](https://github.com/UOR-Foundation/atlas-embeddings)
- [`uor-foundation` Rust crate](https://crates.io/crates/uor-foundation)
- [VTEAI ERC draft (settlement standard)](VTEAI-DRAFT.md)
- [UOR-ADDR-1 (addressing standard, authored by Maura Clark; contributed to UOR Foundation May 2026)](UOR-ADDR-PROPOSAL.md) · reference impl: [`uor-addr-1` v0.1.0](https://crates.io/crates/uor-addr-1)
- [UOR MCP connection guide](../mcp/README.md)
