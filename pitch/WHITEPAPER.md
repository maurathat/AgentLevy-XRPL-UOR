# AgentLevy: A Verifiable-Work Settlement Protocol for Agent Commerce

**Whitepaper · v1.0 · May 2026**

> **AgentLevy is the open-source reference implementation of a two-standard protocol for cryptographically-verifiable agent commerce — content-addressed derivation certificates anchored across two independent ledgers (XRPL settlement + Hedera HCS audit anchor), with no trusted third party at the verify step.**
>
> This whitepaper is the deep-dive companion to:
> - **[VTEAI ERC draft](VTEAI-DRAFT.md)** — the settlement-state-machine standard
> - **[UOR-ADDR-1 community proposal](UOR-ADDR-PROPOSAL.md)** — the chain-agnostic content-addressing standard
> - **[Source repository](https://github.com/maurathat/AgentLevy-XRPL-UOR)** — Apache 2.0 licensed
> - **[Pitch decks](kessai-funding-deck.md)** ([demo deck](agentlevy-demo-deck.md), [funding deck](kessai-funding-deck.md), [one-pager](kessai-onepager.md))

---

## 0. Executive Summary

Agent commerce today rests on vendor trust. Two AI agents transact by exchanging API calls and trusting each other's logs — a model that works inside a single vendor's walled garden, breaks the moment they don't share one, and collapses entirely when either party (or the vendor itself) goes away.

Existing identity primitives — DID registries, KYC'd agent platforms, Coinbase x402, Virtuals Protocol's ACP — solve **who** an agent is. None of them solve **what an agent actually did**, in a way that's verifiable years later by anyone holding only public keys.

AgentLevy closes that gap with a small set of primitives:

- **TaskSpec** — a buyer + seller dual-signed work-acceptance contract.
- **DerivationCert** — a seller's signed attestation of work performed against a TaskSpec, with content-addressed references to inputs, outputs, and any subcontracted child certs.
- **Two-ledger settlement** — XRPL XLS-100 SmartEscrow holds funds with a hashlock on the expected final-cert content address (releases when the hash matches); Hedera Consensus Service anchors every cert hash with an authoritative consensus timestamp.
- **UOR-Passport content addresses** — every reference uses `sha256:<64hex>` derived from JCS-RFC8785 + NFC canonical bytes, byte-identical to the UOR Foundation's reference implementation.

A verifier holding `(buyer_pubkey, seller_pubkey, sanctions_pubkey, the cert chain)` can independently reconstruct: every signature, every content address, every cross-reference, every consensus timestamp, every settlement event — across two independent ledgers, with no trusted intermediary.

The reference implementation is AgentLevy (Apache 2.0). The commercial productization is Kessai (enterprise SaaS). The standards underneath (VTEAI + UOR-ADDR-1) are open and we're co-authoring both.

---

## 1. The Problem: Identity ≠ Work-Integrity

Agent commerce in 2026 has two characteristics that didn't exist five years ago:

1. **Volume.** AI agents are doing real work — KYC verification, supply-chain attestation, claims adjudication, code review, contract analysis. The transaction count is enterprise-scale.
2. **Cross-vendor reach.** Anthropic, OpenAI, Google, Meta, and a long tail of agent-platform startups all field agents that need to interoperate. Single-vendor stacks are the exception, not the rule.

The current trust model has not kept pace. Today's stack tells a counterparty (and a regulator) **who** an agent is:

- **Vendor logs** — when both agents are in the same platform, the vendor sees both sides and can resolve disputes.
- **DID registries** (Civic, Worldcoin, Moca AIR Kit) — agents register cryptographic identity that resolves under W3C DID methods.
- **Agent-platform credentials** — Hedera AgentKit, Anthropic agent SDK, Fetch.ai, Olas Network — each platform issues attestations of "yes this is a registered agent."
- **KYC'd marketplaces** — Coinbase x402 and similar require verified agent identity before payment rails open.

None of these solve **what** the agent actually did. A registered, KYC'd agent can:

- Claim to have run an analysis it didn't run.
- Show a log that doesn't match the actual computation.
- Reference inputs it never processed.

The audit collapses when the vendor goes away (logs become unreadable), when the registry de-lists an agent (credential revocation breaks past attestations), or when a counterparty disputes the log content (he-said-she-said with no neutral arbiter).

For high-stakes use cases — KYC compliance, M&A escrow, regulatory reporting, AI governance — "trust the vendor's database" is no longer acceptable. Regulators are increasingly asking for **cryptographic** evidence: signatures, timestamps, hashes, math. Identity-only credentials don't provide it.

The gap to close: **make the work itself cryptographically verifiable**, with no trusted third party at the verify step. That's what AgentLevy demonstrates and what VTEAI/UOR-ADDR-1 standardize.

---

## 2. Architecture: How AgentLevy Works

The protocol has four primitives, two ledgers, and one verification model.

### 2.1 The Primitives

#### TaskSpec

A `TaskSpec` is the work-acceptance contract. Buyer drafts it; seller accepts and counter-signs. Once dual-signed, it's a binding statement of what work will be done, by whom, for how much, by when.

Fields (selected):
- `task_id` — UUID assigned at construction
- `task_type` — e.g., `kyc.beneficial_ownership_verify`
- `inputs` — list of content-address references (`sha256:<64hex>`) to the source documents
- `expected_output_schema` — JSON Schema describing the output shape
- `price_drops` — settlement amount in chain-native units
- `currency` — `RLUSD` (default) or `XRP`; chain-aware
- `chain` — `xrpl`
- `buyer_pubkey`, `seller_pubkey` — Ed25519 public keys (32 raw bytes, hex-encoded)
- `deadline` — UTC, ISO 8601
- `signature_buyer`, `signature_seller` — detached Ed25519 signatures (64 raw bytes, hex-encoded)

The signatures are **detached**: `to_canonical_bytes()` excludes them. Re-canonicalizing a signed spec produces the same bytes that were originally signed. This invariant is critical: it means the canonical bytes (and therefore the content address) are stable across the sign/verify cycle.

#### DerivationCert

A `DerivationCert` is the seller's signed delivery: "I, holder of `seller_pubkey`, performed operation X over inputs `input_addresses`, producing output `output_address`, in fulfillment of spec `task_spec_address`."

Fields:
- `cert_id` — UUID
- `task_spec_address` — back-reference to the spec (content address)
- `input_addresses` — list of content addresses for the inputs actually consumed
- `output_address` — content address for the produced output
- `operation_description` — structured dict (`operation`, `inputs_described`, `outputs_described`)
- `subcontract_cert_addresses` — content addresses of child certs (empty for leaf certs)
- `seller_pubkey` — signer
- `signature` — detached Ed25519 signature
- `timestamp` — UTC; when the work was attested
- `hcs_receipt` — Hedera HCS audit anchor (detached; populated post-signing)

**Subcontract references are content addresses, never UUIDs.** The protocol's audit invariant only holds if every cross-reference resolves by hash. UUIDs are mutable identifiers; content addresses are not. Tampering with a child cert breaks the parent's address resolution without invalidating the parent's signature — the verifier discovers the chain break at the link-resolution step, exactly where you want to discover it.

#### The cert chain

```
TaskSpec (sha256:abc…)
  ↓ signed by buyer + seller; escrowed on XRPL with hashlock on expected final cert
  ↓ referenced by ↓
DerivationCert (compliance, sha256:def…)
  ↓ output_address →
    BeneficialOwnershipExtraction (sha256:ghi…)
  ↓ subcontract_cert_addresses → DerivationCert (sanctions, sha256:jkl…)
                                   ↓ output_address →
                                     SanctionsScreenResult (sha256:mno…)
```

Every arrow is a hash reference. Every node is signed. Every node is anchored.

### 2.2 The Two-Ledger Settlement

#### XRPL — Settlement layer

The buyer creates an XLS-100 SmartEscrow on XRPL WASM Devnet, funded with the agreed-upon RLUSD amount. The escrow's WASM `FinishFunction` is a small piece of deterministic logic: "compare the SHA-256 of the submitted cert payload to the hashlock value committed at escrow creation; release iff match."

The deliberate minimalism of `FinishFunction` is itself a security property: ~10 lines of WASM, no oracles, no time-dependent branches, no external calls, no re-entrancy attack surface. Auditable in an afternoon, not a week.

When the seller's final cert is submitted, the escrow verifies the hash and releases the funds. No oracle. No off-chain settlement. No human in the loop.

#### Hedera HCS — Audit anchor

Independently, every signed `DerivationCert` has its content address submitted to a Hedera Consensus Service (HCS) topic ([`0.0.8856047`](https://hashscan.io/testnet/topic/0.0.8856047) on testnet). HCS provides:

- An **authoritative consensus timestamp** (when did this cert exist, witnessed by Hedera consensus?)
- A **monotonic sequence number** within the topic (stable ordering across all certs anchored under this protocol)
- A **publicly queryable Mirror Node REST API** — anyone can re-verify with a single HTTP GET

The anchor is **detached** from the cert's canonical bytes. Anchoring happens *after* signing, so the cert's content address is unchanged by the anchor (and the signature remains valid). The `hcs_receipt` field stores `topic_id`, `sequence_number`, `transaction_id`, `consensus_timestamp` — enough for any third party to re-verify against Hedera Mirror Node without our cooperation.

### 2.3 Why two ledgers

| Property | What it provides |
|---|---|
| **Independent witnesses** | If XRPL has a chain reorganization or HCS goes down, the other ledger still has the proof. Two attesters; not just one. |
| **Settlement decoupled from audit** | XRPL says *the money moved*; Hedera says *the cert existed at exactly this moment, witnessed by separate consensus*. Audit one without trusting the other. |
| **Two governance models** | XRPL Foundation governs one; Hedera Council (Fortune 500-heavy: Google, IBM, LG, Boeing, Standard Bank, etc.) governs the other. Regulatory acceptance varies by jurisdiction; having both means you don't have to bet. |
| **Cross-chain redundancy** | If XRPL governance shifts, the timeline lives on Hedera. If Hedera ever Council-restructures, the money is on XRPL. Neither bet is total. |
| **Each chain plays its strength** | HCS is built for high-throughput ordering (~$0.0001/msg); XRPL Smart Escrow is built for cheap, fast, conditional settlement. |

This is the structural property: **two independent ledgers, two independent governance models, two independent verification paths.** The audit story doesn't depend on either chain alone.

---

## 3. UOR Alignment: Why This Protocol Doesn't Define Its Own Addressing

A subtle but load-bearing detail: AgentLevy doesn't define its own content-addressing scheme. It uses the **UOR Foundation's** canonical addressing layer, byte-for-byte.

### 3.1 What UOR provides

UOR (Universal Object Reference) is a Foundation-backed content-addressing standard with three components:

- **PRISM** — a Q(31), 256-bit ring algebra implementation under MIT license. Vendored at `vendor/prism.py`. The algebraic substrate for UOR addresses.
- **JCS-RFC8785 + NFC canonicalization** — the agreed-upon discipline for what bytes get hashed before address derivation.
- **UOR-Passport address format** — `sha256:<64hex>`. The publicly-resolvable envelope.

Together these define an address that is:

1. **Algebraically structured** — the same content has *one* canonical address but *many* equivalent representations (hex, Braille glyph, ring element, base32). All algebraically the same address. Useful for visual rendering, for cross-tool composition, for sub-canonicalization within other schemes.
2. **Standards-track** — UOR Foundation has a Sandbox → Incubating → Graduated lifecycle. UOR-ADDR-1 is the community proposal we're co-contributing to.
3. **Cross-domain composable** — the same primitive is used by UOR Identity (for entity identity), UOR Certificate (for generic signed attestations), UNS (for human-readable name resolution), Hologram SDK (for module certificates already in production), and AgentLevy (for work-integrity certs).

### 3.2 Why this matters for the pitch

Three pitch claims that are only credible *because of UOR alignment*:

- **"Byte-identical to canonical reference."** Without UOR, this is just "compatible-ish." With UOR, it's empirical: we've live cross-checked our content addresses against `mcp.uor.foundation/encode_address` for the same canonical bytes. They produce the same SHA-256, byte-for-byte. (See [docs/UOR_PASSPORT_VERIFIED.md](../docs/UOR_PASSPORT_VERIFIED.md).)
- **"Verifiable from public keys alone."** Only works if the addresses being verified resolve against an open, publicly-defined format. UOR is what makes "alone" true; without it, a verifier needs vendor cooperation to interpret addresses.
- **"Protocol-author moat."** VTEAI is the settlement spec we authored; UOR-ADDR-1 is the addressing spec we co-contribute to. Future implementers will use specs we shaped.

### 3.3 vs every alternative

| Alternative addressing | What it lacks vs UOR |
|---|---|
| **Vendor-internal IDs** (any KYC vendor's database keys) | Not publicly resolvable. Requires vendor cooperation to interpret. Outlive the vendor? No. |
| **IPFS CIDs** (multihash) | No algebraic structure. No Foundation-backed governance lifecycle. Great for storage, less suited for verifiable references. |
| **Ethereum keccak256 hashes** | Solidity-native; doesn't compose cleanly with non-Ethereum chains without translation layers. |
| **W3C DID Methods** | Identity, not content. Composes with UOR (DID identifies the agent; UOR address identifies what the agent did) but doesn't replace it. |
| **Coinbase Commerce / x402 internal IDs** | Vendor-bound. Don't survive Coinbase's involvement. |
| **Virtuals Protocol (Base contract addresses + tokenIDs)** | Chain-bound to Base. UOR is chain-neutral. |

---

## 4. The Verification Model

The key claim — "verifiable from public keys alone, across two independent ledgers" — needs to be unpacked. What can a verifier holding only public keys + a cert chain actually re-check?

A verifier with `(buyer_pubkey, compliance_pubkey, sanctions_pubkey, the 5 certs)` can independently confirm:

1. **Every signature is valid.** Ed25519 verify against canonical bytes (excluding the signature field). Standard cryptography library; no trusted execution environment needed.
2. **Every content address resolves.** Recompute SHA-256 over JCS-RFC8785 + NFC canonical bytes; match against the reference. The reference implementation is open-source; the canonicalization rules are RFC-published.
3. **Every back-reference is consistent.** `task_spec_address` on the cert resolves to the actual TaskSpec; `input_addresses` resolve to the actual inputs the spec declared; `subcontract_cert_addresses` resolve to actual child certs.
4. **Every cert was witnessed by Hedera.** A single HTTP GET to Hedera Mirror Node REST returns the message body that was anchored, the consensus timestamp, the sequence number. Compare against the cert's `hcs_receipt`; verify match.
5. **The escrow released against the final cert hash.** XRPL public transaction history shows the escrow was funded with hashlock X and released after submission of cert X. Public, auditable, no API key required.

Math, not trust. The verification doesn't depend on the buyer's vendor still existing, the compliance agent still being active, the sanctions agent still being reachable, or the seller's company still being in business. The audit verifies in 2046 the same way it verifies today.

---

## 5. Competitive Landscape (Deep Dive)

The competitive landscape table on the pitch deck is necessarily compressed. Here's the longer version, by category.

### 5.1 Payment rails for agent commerce

#### Coinbase x402

**What it is:** A specification for re-activating HTTP status code 402 ("Payment Required") for agent-to-agent micropayments. Agent A makes an HTTP request to Agent B's endpoint; B responds with 402 + payment details (USDC on Base); A pays; A retries the original request with payment proof attached; B serves the response.

**What it solves:** Frictionless per-request settlement for agents. Removes the "bill me at the end of the month" billing model and replaces it with cryptographic per-call settlement.

**What it doesn't solve:** Verification of what was actually returned. x402 confirms *that the payment moved*, not *that the response matched the agreed-upon work*. There's no concept of a signed attestation of work, no audit trail beyond the payment transaction.

**Composition not competition:** AgentLevy and x402 are complementary. x402 could call AgentLevy as its verifier — Agent A pays via x402, Agent B returns a `DerivationCert`, A re-verifies the cert independently before accepting the response.

#### Coinbase Commerce escrow

**What it is:** Coinbase's hosted escrow product for crypto commerce. Funds held by Coinbase pending fulfillment; released on dispute resolution.

**What it solves:** Crypto-native conditional release. Better than wire transfers + traditional escrow agents.

**What it doesn't solve:** **Custodial.** Coinbase IS the trust anchor. The whole point of AgentLevy's two-ledger non-custodial settlement is removing the trust anchor — replacing "Coinbase will release the funds when conditions are met" with "the math will release the funds when the cert hash matches."

For a hackathon judge / regulator / counterparty's risk officer, "non-custodial + math-verifiable" is a meaningfully different posture than "Coinbase-custodial + dispute-resolved-by-Coinbase."

#### x402 + DID-based agent platforms (general pattern)

Increasingly common stack: agent identity via DIDs, payment via x402-style rails, arbitration via the platform's dispute layer. Solves identity + payment well; doesn't address verifiable work-integrity.

### 5.2 Agent commerce protocols

#### Virtuals Protocol (ACP — Agent Commerce Protocol)

**What it is:** A platform on Base for tokenized AI agents. Each agent has a tradeable token; revenue from agent usage flows to token holders. ACP defines agent-to-agent transaction primitives — negotiation envelopes, payment rails, result delivery — built around TEE attestation for sensitive computation.

**What it solves:** A tightly-integrated agent marketplace with economic incentives for agent creators. Discovery + payment + delivery in one stack.

**What it doesn't solve (vs AgentLevy):**
- **Platform-bound to Base + Virtuals tokens.** AgentLevy is chain-neutral; the same protocol runs on XRPL today and via UOR-ADDR-1 adapters on any other chain.
- **Marketplace primitive vs settlement primitive.** ACP is great for "agents discover + transact with each other in a token economy"; AgentLevy is for "this work was performed, here's the math, anyone can verify forever."
- **TEE attestation vs cryptographic-cert chains.** TEE attestation requires trusting Intel/AMD/etc. + the TEE provider's attestation service. A cert chain anchored on two independent public ledgers requires trusting math + open consensus.

ACP and AgentLevy address adjacent problems; an enterprise might use both — Virtuals for discovery and economic incentives, AgentLevy for the audit trail their regulator demands.

### 5.3 Identity + credential platforms

#### W3C DIDs, Civic, Worldcoin, Moca AIR Kit

**What they solve:** Cryptographic identity for agents (and humans). DID resolves to a public key; Civic adds KYC verification; Worldcoin adds proof-of-personhood; Moca packages these for AI-agent contexts.

**What they don't solve:** *What did this identified agent actually do?* Identity tells you the counterparty; it doesn't certify their work.

**Composition with AgentLevy:** Agent pubkeys in our cert chain can resolve to UOR Identity profiles, W3C DIDs, or any other identity layer. The protocol is identity-method-agnostic — it cares that there's *a* public key, not which registry that key was issued under.

### 5.4 Agent-platform SDKs

#### Anthropic agent SDK, OpenAI agent platform, Hedera AgentKit, Fetch.ai, Olas Network, Google AP2

**What they solve:** Identity + discovery + tooling within their walled garden. Excellent developer experience for agents that live entirely within the platform.

**What they don't solve:** Cross-vendor verification. Long-horizon auditability. The platform's logs are vendor-trusted; the platform's identity attestations are platform-bound.

**Composition with AgentLevy:** Each platform's agent SDK can produce VTEAI-compliant TaskSpecs and DerivationCerts. The platform handles agent invocation; AgentLevy handles cross-vendor audit-trail integrity.

### 5.5 Web3 oracles

#### Chainlink, Pyth, RedStone

**What they solve:** Bring external data onchain in a verifiable way (price feeds, weather, sports outcomes).

**What they don't solve:** Trust model is "trusted decentralized oracle network." For settlement of agent work, AgentLevy needs no oracle — the cert chain IS the oracle. The DerivationCert *is* the verifiable claim about what happened.

### 5.6 Legacy compliance + escrow vendors

#### LexisNexis Risk Solutions, Refinitiv (LSEG), Thomson Reuters

**What they solve:** Mature, regulator-accepted compliance workflows. Vendor-trusted audit. Established for decades.

**What they don't solve:** Their audit architecture predates the cryptographic primitives that make non-custodial verification possible. They sell "trust our database for 30 years"; we offer "trust the math for 30 years." Different posture, different defensibility under adversarial conditions.

#### Coinbase Commerce + custodial crypto-escrow players

Already addressed above (5.1). Custodial → AgentLevy non-custodial.

### 5.7 Permissioned blockchain platforms

#### Hyperledger Fabric, R3 Corda

**What they solve:** Multi-party transaction systems with controlled access; mature in financial-services use cases.

**What they don't solve:** Permissioned-blockchain trust models still require trust in the consortium operating the chain. AgentLevy's two-ledger anchoring on public chains (XRPL + Hedera) inherits the trust models of public consensus — much broader, much harder to subvert.

---

## 6. Customer Use Cases

The wedge market is **KYC compliance** (the demo target). The protocol generalizes naturally to several adjacent markets, in roughly this order of expansion:

### 6.1 Mid-market regional banks (KYC + AML compliance)

**Pain:** KYC verification is high-volume, regulator-scrutinized, and currently locked into one or two vendors per bank. Switching vendors is multi-year. Audit response to regulator inquiries means digging through vendor portal exports, hoping the original vendor's account is still active.

**AgentLevy fit:** Banks can keep their existing KYC workflow vendors but require those vendors to emit AgentLevy-compatible certs. The bank holds the cert chain; the regulator can re-verify against XRPL + Hedera independently, without the vendor's API.

**Procurement reality:** Mid-market regional banks ($X–X B AUM) have enough volume to feel the pain and enough autonomy to pilot a new approach without a 24-month procurement cycle. Bigger banks are harder to land and slower to move.

### 6.2 KYC compliance vendors (channel/whitelabel partners)

**Pain:** Compliance vendors compete on data quality and customer service. Cryptographic auditability is a feature their customers (banks, payment processors) increasingly ask for, but building it from scratch is years of engineering.

**AgentLevy fit:** Vendor licenses the AgentLevy reference implementation (or the Kessai productized version) as a backend. Their existing UI + workflow stays; cert generation + anchoring becomes a backend feature. Vendor sells "the same compliance work you're getting today, plus cryptographic auditability your regulator will love."

**Channel economics:** Whitelabel + revenue share, faster time-to-revenue than enterprise direct sales.

### 6.3 M&A escrow + transaction support

**Pain:** M&A escrow currently locks funds with a trusted escrow agent for the deal-closing window. Audit horizons stretch 5–10+ years (rep-and-warranties claims, regulatory hold periods). Multi-party verification is core (buyer, seller, both sides' counsel, escrow agent, sometimes regulators), and cross-jurisdictional acceptance is a hard problem.

**AgentLevy fit:**
- **Decades-long audit horizons** → two-ledger anchoring is *especially* valuable. Single-chain bets feel risky over that timeframe to deal counsel.
- **Multi-party verification** → each party can independently verify on whichever chain they trust most, without going through the deal coordinator.
- **Cross-jurisdictional acceptance** → having both XRPL (more neutral, longer track record) and Hedera (US Council-governed, lots of Fortune 500) pre-empts the question of which regulator trusts which chain.
- **Willingness to pay** → escrow fees on a $500M deal are millions; paying for "audit-trail-that-outlives-the-deal-team" is trivially justified.

**Year-2 wedge.** Higher-value than KYC; longer sales cycle.

### 6.4 International compliance teams

**Pain:** EU eIDAS, Singapore MAS, and several other regulatory regimes already accept cryptographic-evidence formats. Compliance teams operating cross-border are looking for vendor-neutral attestation formats they can submit to multiple regulators without per-jurisdiction translation.

**AgentLevy fit:** Standards-aligned (VTEAI + UOR-ADDR-1 are deliberately chain-neutral and jurisdiction-neutral), token-free, open-source. A compliance team can submit the cert chain + a verification script to any regulator that accepts cryptographic evidence.

### 6.5 Crypto-native escrow (Year 1+)

Crypto-escrow players already use single-chain escrow primitives. Two-ledger anchoring is an upgrade story — better audit, no new trust assumptions on top of what they already accept.

### 6.6 AI governance + inference provenance (Year 3+)

**Pain:** Enterprise AI deployments increasingly need to answer "show me, cryptographically, what model + version + prompt + inputs produced this output." Current logging stacks don't provide cryptographic guarantees; they're vendor-trusted.

**AgentLevy fit:** The same `DerivationCert` shape used for KYC works for AI inference attestation. Agent (the model) signs a cert: "I am model M, version V, on prompt P, with inputs I, I produced output O." The cert is anchored on both ledgers; the audit trail is mathematical.

This is the territory where AgentLevy stops being a KYC-specific protocol and becomes the substrate for **all** verifiable AI work — the wedge becomes the platform.

### 6.7 Insurance + claims adjudication

**Pain:** Insurance claims and adjudication often involve multi-party signed documents passed between insurer, adjuster, claimant, and regulator. Cryptographic audit-trail is a natural fit.

**AgentLevy fit:** Same protocol; new operation types (`insurance.claim_adjudication`, `insurance.payout_calculation`).

---

## 7. Risk Model

The two scariest failure modes in agent-driven onchain commerce are exactly the two we engineered against.

### 7.1 Smart-contract risk → minimal verifier surface

Most onchain escrow contracts run thousands of lines of Solidity, with arbitrary call patterns and re-entrancy attack surface. AgentLevy uses XRPL XLS-100 SmartEscrow with a deliberately minimal `FinishFunction`:

- ~10 lines of WASM logic: compute hash of submitted cert payload; compare to hashlock committed at escrow creation; release iff match.
- Deterministic by construction — no oracles, no time-dependent branches, no external calls.
- Auditable in a single afternoon, not a week of formal verification.
- Hashlock pre-commitment — the buyer locks in the expected output at escrow funding; the seller cannot retroactively renegotiate.

XRPL Smart Escrow is also natively currency-aware (RLUSD, XRP) without a custom token contract — one less surface to audit.

**Honest acknowledgment:** WASM `FinishFunction` is new (XLS-100 activated Feb 2026); no production-scale audit history yet. Mainnet deployments will go through a top-tier security firm before any production funds are at risk.

### 7.2 LLM negotiation risk → bounded, schema-locked, cache-replayable

LLMs are non-deterministic, prompt-injectable, and prone to over-spending tokens on unbounded negotiations. We constrain every layer:

- **4-turn hard cap** on buyer ↔ compliance negotiation. Beyond turn 4, the protocol exits gracefully with a signed "negotiation failed" cert (itself a valid audit artifact). No infinite loops, no runaway token bills.
- **Schema-validated outputs only** — every LLM call returns a Pydantic-validated structured output via Anthropic tool use. Free-form text isn't accepted into the cert chain.
- **Temperature = 0** by default. Determinism wins for KYC; the cache layer assumes reproducibility.
- **Fixture cache for stage demos** — `LLM_CACHE_MODE=cache` replays recorded responses byte-identically. The demo cannot fail because the API hiccupped.
- **Wrong-keypair rejection at sign time** — `cert.sign(keypair)` raises if the keypair's public key doesn't match the `seller_pubkey` on the cert. Prevents an LLM-driven mistake from cross-signing as the wrong party.
- **Tamper detection on every field** — modifying the cert post-sign invalidates the signature; modifying a referenced cert breaks the chain at the address-resolution step. Test coverage proves this for every model field.

**Honest acknowledgment:** LLMs can still fabricate data *within the schema*. The cert chain proves the work happened, not that the inputs were correctly interpreted. Quality of the underlying LLM, prompt engineering, and input documents are upstream concerns.

### 7.3 Cryptographic risk + post-quantum migration

Today's stack uses Ed25519 (signing) + SHA-256 (addressing). Neither is post-quantum-safe. The architecture has a **documented migration path to CRYSTALS-Dilithium-3** (FIPS 204 ML-DSA-65) — which UOR Foundation's deeper agent-identity layer already uses. The cert envelope's algorithm field makes the migration purely additive: no breaking change to the surrounding format. SHA-256 addressing survives quantum break independently of the signature algorithm.

### 7.4 Standards-track risk

VTEAI is a published draft; UOR-ADDR-1 is a community proposal. Neither is formally ratified yet. **Mitigation:** AgentLevy works regardless of formal ratification — the reference implementation is real, deployable today. Ratification is upside, not gating. Standards-author position remains a moat even pre-ratification because we're shaping the spec.

### 7.5 Chain-bet risk

**XRPL bet:** XLS-100 is recently activated; ecosystem maturity is moderate. **Mitigation:** UOR-ADDR-1 chain-binding adapter pattern — Hedera EVM, Solana, Sui, Base can all be added without changing the protocol layer.

**Hedera bet:** HCS is mature and enterprise-adopted (Hedera Council includes Google, IBM, Boeing, LG, Standard Bank, etc.). **Mitigation:** the HCS anchor is additive, not gating. Settlement on XRPL works without HCS; HCS is the second witness, not the first.

---

## 8. Roadmap

### 8.1 Standards (the moat we're authoring)

- **VTEAI ERC** — currently a published draft (CC0, April 2026). Path to formal ratification with broader implementer adoption — engaging with the Ethereum standards community + cross-chain working groups.
- **UOR-ADDR-1** — currently a community proposal under the UOR Foundation. AgentLevy is its first reference implementation; we're contributing to maturation.
- **UOR Foundation Sandbox → Incubating graduation** — track-graduating AgentLevy within the Foundation's project lifecycle. Brings governance + interop guarantees.

### 8.2 Multi-chain via UOR-ADDR-1 adapters

XRPL ships first because XLS-100 is ready. UOR-ADDR-1's chain-binding adapter pattern means **any chain that supports a hashlock-conditional release can be added without changing the protocol layer**: Hedera EVM, Solana, Sui, Base — each gets an adapter; agents stay chain-agnostic.

### 8.3 Verifiable agent memory + AI inference provenance

The cert chain we ship for KYC is the same primitive used for **verifiable agent memory**. Every cert is a content-addressed, signed, anchored record of "this agent did this work on these inputs at this consensus-witnessed time." Stack many of these and you get an agent's complete, mathematically-verifiable history — the foundation for:

- **Long-horizon agent reputation** — not vendor-trusted scores, but a public-key-verifiable track record. An agent's past certs are its résumé.
- **AI inference provenance** — for enterprise AI governance: "show me, cryptographically, what model + version + prompt + inputs produced this output." Same `DerivationCert` shape; new operation types.
- **Memoization with audit** — when an agent re-uses a prior result instead of recomputing, the prior cert IS the citation. Cache hits become cryptographically auditable.
- **Cross-agent memory sharing** — an agent referencing another agent's prior work cites by content address, not by API. The reference resolves whether the original agent still exists or not. Composes naturally with MemWal-style memory protocols.

This is the territory where AgentLevy stops being KYC-specific and becomes the substrate for **all** verifiable agent work — the wedge becomes the platform.

### 8.4 Enterprise pilots (the wedge)

- Mid-market regional banks (KYC + AML)
- KYC compliance vendors (channel/whitelabel)
- International compliance teams (EU eIDAS, Singapore MAS)
- M&A escrow + transaction support (Year 2)
- AI governance + inference provenance (Year 3+)

### 8.5 Productization → Kessai

The open-source reference protocol is AgentLevy. The commercial layer is **Kessai** — visualizer UI for cert chains, enterprise SDKs (Python + TypeScript), regulatory-evidence packs, channel licensing for compliance vendors.

The protocol stays open. The standards stay free. The product is what makes verifiable settlement turnkey for enterprises.

---

## 9. References

### 9.1 Standards we author / co-author

- [VTEAI ERC draft](VTEAI-DRAFT.md) — Verified Task Escrow + Attestation Interface (CC0, April 2026)
- [UOR-ADDR-1 community proposal](UOR-ADDR-PROPOSAL.md) — Universal Object Reference Address (community track, April 2026)

### 9.2 UOR Foundation

- UOR Foundation: https://uor.foundation
- UOR MCP cross-validation endpoint (used to verify byte-identical claim): `mcp.uor.foundation/encode_address`
- PRISM (vendored at `vendor/prism.py`, MIT): https://github.com/UOR-Foundation/prism
- Sibling projects: UOR Identity, UOR Certificate, UNS, Hologram SDK

### 9.3 Chain layers

- XRPL: https://xrpl.org
- XLS-100 SmartEscrow: https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html
- XRPL WASM Devnet: https://wasm.devnet.rippletest.net
- Hedera Consensus Service: https://docs.hedera.com/hedera/sdks-and-apis/sdks/consensus-service
- This project's HCS audit topic: https://hashscan.io/testnet/topic/0.0.8856047
- Hiero Python SDK (pure-Python): https://github.com/hiero-ledger/hiero-sdk-python

### 9.4 Cryptography

- Ed25519: RFC 8032
- SHA-256: FIPS 180-4
- JCS (JSON Canonicalization Scheme): RFC 8785
- Unicode Normalization Form C (NFC): UAX #15
- Forward path: CRYSTALS-Dilithium-3 / FIPS 204 ML-DSA-65 (post-quantum)

### 9.5 Source code + documentation

- Repository: https://github.com/maurathat/AgentLevy-XRPL-UOR
- License: Apache 2.0 (project), MIT (vendored PRISM)
- Demo deck: [`pitch/agentlevy-demo-deck.md`](agentlevy-demo-deck.md)
- Funding deck: [`pitch/kessai-funding-deck.md`](kessai-funding-deck.md)
- One-pager: [`pitch/kessai-onepager.md`](kessai-onepager.md)
- Brand assets: https://github.com/maurathat/kessai-pitch-assets

### 9.6 Contact

- Author: Maura Clark · `maurathat`
- GitHub: https://github.com/maurathat
- Project demo website: *(forthcoming, Vercel-hosted)*

---

*Whitepaper v1.0 — May 2026. License: Apache 2.0. Cite as "AgentLevy Whitepaper v1.0" with link to canonical version in the project repository.*
