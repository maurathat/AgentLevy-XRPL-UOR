# AgentLevy — Demo Deck (Consensus EasyA · 12 slides)

> **For: Consensus EasyA hackathon judges + booth visitors + builder audience.** Distinct from the Kessai investor deck (`pitch/kessai-funding-deck.md`) which leads with the company. This deck leads with the **protocol and the live demo** — what you're about to see and why each piece matters.
>
> **Brand kit · for Gamma.** Same as the Kessai deck:
>
> | Setting | Value |
> |---|---|
> | Primary color | `#283A8C` (Ruri — deep indigo) |
> | Accent color | `#B0223A` (Karakurenai — crimson) |
> | Background — hero slides | Ruri |
> | Background — body slides | `#F6F7FA` (Paper) |
> | Body text on indigo | `#F4EFE4` (Washi — cream) |
> | Display font | Fraunces (SemiBold/Bold) |
> | Body font | DM Sans (Medium/SemiBold) |
> | Mono font | IBM Plex Mono (Medium) |
> | Cover logo | `agentlevy_logo_white.svg` (on Ruri ground) |

---

## SLIDE 1 — Title

![AgentLevy](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/agentlevy_logo_white.png)

**AgentLevy**

*The open-source reference protocol for verifiable agent commerce.*

— Consensus EasyA · May 5–7, 2026
— github.com/maurathat/AgentLevy-XRPL-UOR
— A working demo, with code.

---

## SLIDE 2 — The gap

> *"Agent commerce assumes good faith. Production cannot."*

Today's stack tells you **who** you're transacting with — same-vendor logs, DID registries, agent-platform credentials. **None of it tells you what was actually done.**

The audit collapses the moment:
- The vendor goes away (or just can't reproduce the original API call)
- The registry de-lists the agent
- The counterparty disputes the log contents

**Identity ≠ work-integrity.** A registered, KYC'd agent can still lie about what it computed — and you have no way to re-check.

A settlement primitive for agent commerce needs to make the **work itself** cryptographically verifiable, with no trusted third party at the verify step.

---

## SLIDE 3 — Why we built it (vs what exists)

**Yes, things exist in this space. None of them solve the work-integrity problem.**

| Player | What they solve | What they don't |
|---|---|---|
| **Coinbase x402** | HTTP-layer payment rail (HTTP 402 reactivation; per-request USDC on Base) | Payment ≠ verification. x402 says *the money moved*; AgentLevy says *the work matched the spec, here's the math*. **Composable, not competitive** — x402 could call AgentLevy as its verifier. |
| **Coinbase Commerce escrow** | Crypto escrow for traditional commerce | **Custodial.** Coinbase IS the trust anchor. The whole point of AgentLevy is removing the trust anchor. |
| **Virtuals Protocol (ACP)** | Agent commerce on Base; tokenized agents; TEE attestation | Platform-bound to Base + Virtuals tokens. Agent-token economics are a *marketplace* primitive, not a *settlement* primitive. AgentLevy is chain-neutral, token-free, audit-first. |
| **DID / KYC registries** (Civic, Worldcoin, Moca) | "Who is this agent" | "What did this agent actually do" — silent. |
| **Agent-platform SDKs** (Anthropic, OpenAI, Hedera AgentKit, Fetch.ai, Olas) | Agent identity + discovery within their walled garden | Cross-vendor verification; long-horizon auditability. |
| **Web3 oracles** (Chainlink, etc.) | Bridge external data onchain | Trusted-oracle model. AgentLevy needs no oracle — the cert chain IS the oracle. |
| **Vendor-bound content addressing** (any KYC/compliance vendor with internal doc IDs) | "Trust our database" identifiers; format is proprietary | AgentLevy uses **UOR-Passport-format** addresses (`sha256:<64hex>`, JCS-RFC8785 + NFC canonical bytes), publicly resolvable by any UOR-aware tool with **no translation**. Verified live byte-identical against UOR Foundation's canonical reference (`mcp.uor.foundation/encode_address`). The address outlives the vendor. |

**AgentLevy sits one layer below all of these.** They're each great at their own job. None of them give you "verifiable from public keys alone, across two independent ledgers, no trusted intermediary, byte-identical to a published reference standard." That's the gap we built into.

**The pitch line we earn:** *"They tell you who. We tell you what — verifiably, forever."*

---

## SLIDE 4 — What we built

**AgentLevy is a protocol-layer demo where two AI agents negotiate and execute a KYC compliance task, sign each step with content-addressed derivation certificates, and settle on XRPL — producing an audit trail verifiable from public keys alone, across two independent ledgers.**

| Component | What it does | Open-source? |
|---|---|---|
| **TaskSpec** | Buyer + seller dual-signed work contract | ✓ Apache 2.0 |
| **DerivationCert** | Seller's signed attestation of work performed | ✓ Apache 2.0 |
| **PRISM ring algebra** | UOR Foundation content addressing (vendored) | ✓ MIT (UOR Foundation) |
| **XRPL XLS-100 SmartEscrow** | Conditional settlement on cert hash | ✓ XRPL community |
| **Hedera HCS audit anchor** | Tamper-evident cert timestamping | ✓ Hedera/Hiero |
| **VTEAI + UOR-ADDR-1** | Standards we authored | ✓ CC0 / community |

**The whole stack is open. The whole stack is reproducible. The whole stack is real on testnet today.**

---

## SLIDE 5 — The KYC demo

![A real UOR Module Certificate in the wild — Kessai certs follow the same shape, byte-for-byte](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/hologram-cert.png)

**Three agents. One KYC task. Five signed artifacts. Two chains.**

1. **Buyer agent** — drafts a TaskSpec for beneficial-ownership verification, signs it, escrows RLUSD on XRPL.
2. **Compliance agent** — accepts the spec, reads a synthetic corporate disclosure, extracts beneficial owners, **subcontracts** sanctions screening to a third agent.
3. **Sanctions agent** — screens each name against a synthetic sanctions list, signs a `DerivationCert` with the result.
4. **Compliance agent** — assembles a parent `DerivationCert` referencing the sanctions cert by content address, signs it.
5. **All certs** — anchored to a Hedera HCS topic for tamper-evident timestamping. Final cert hash submitted to the XRPL escrow's WASM `FinishFunction`. Escrow releases.

**No oracles. No off-chain settlement. No trust in any agent.**

---

## SLIDE 6 — The cert chain anatomy

![One UOR address, four representations — verified byte-identical to UOR Foundation's canonical reference](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/hero-uor-address.png)

**Every artifact has a content address — `sha256:<64 hex>` — derived from JCS-RFC8785 + NFC canonical bytes. Verified byte-identical to UOR Foundation's reference implementation (live cross-check via `mcp.uor.foundation/encode_address`, May 3, 2026).**

```
                     TaskSpec (sha256:abc…)
                        ↓ signed by buyer + seller
                        ↓ referenced by ↓
                                    DerivationCert (compliance, sha256:def…)
                                        ↓ output_address →
                                            BeneficialOwnership (sha256:ghi…)
                                        ↓ subcontract_cert_addresses →
                                            DerivationCert (sanctions, sha256:jkl…)
                                                ↓ output_address →
                                                    SanctionsResult (sha256:mno…)
```

**Every arrow is a hash reference. Every cert is signed. Every cert is anchored. Tampering with any one breaks the chain at the address-resolution step — not the signature step — which is exactly the audit-trail invariant we want.**

### Why UOR-Passport format specifically

Every address in this chain is **publicly resolvable** by any UOR-aware tool — no translation, no vendor-specific format, no proprietary middleware. We don't define our own addressing scheme; we use UOR's:

- **PRISM ring algebra** (Q(31), 256-bit, MIT-licensed) — the algebraic substrate that makes "one address, four representations" structurally true. Hex / Braille glyph / ring element / base32 are all algebraically the same address.
- **JCS-RFC8785 + NFC canonicalization** — the cross-ecosystem standard for what bytes get hashed.
- **Live cross-validated** byte-for-byte against UOR Foundation's canonical reference (`mcp.uor.foundation/encode_address`).

The address outlives the vendor. It outlives the agent. It outlives any single chain. That's the property no proprietary content-addressing scheme can match.

---

## SLIDE 7 — Two-ledger settlement

**XRPL settles. Hedera anchors. Two independent witnesses.**

| Layer | Chain | What it provides |
|---|---|---|
| **Settlement** | XRPL WASM Devnet | XLS-100 SmartEscrow with WASM `FinishFunction`. Buyer escrows RLUSD with a hashlock on the expected final-cert content address. Seller submits the cert; escrow verifies the hash matches; funds release. |
| **Audit anchor** | Hedera Testnet | Every cert's content address is submitted to a Hedera Consensus Service topic ([`0.0.8856047`](https://hashscan.io/testnet/topic/0.0.8856047)) producing an authoritative consensus timestamp + sequence number. Settlement says *the money moved*; HCS says *the cert existed at this exact moment, witnessed by Hedera consensus*. |

*Built on:*

![XRPL](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/xrpl_horizontal_white.png)
![Hedera](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/hedera_logo_white.png)
![Ripple](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/ripple_logo.png)
![Anthropic](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/anthropic_logo.png)

---

## SLIDE 8 — The verification math

![Each byte becomes one Braille codepoint — codepoint = U+2800 + byte_value](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/byte-to-glyph-primer.png)

**Anyone holding `(buyer_pubkey, compliance_pubkey, sanctions_pubkey, 5 certs)` can independently verify:**

1. ✓ **Every signature is valid** — Ed25519 verify against canonical bytes.
2. ✓ **Every content address resolves** — recompute SHA-256 over canonical bytes, match against the reference.
3. ✓ **Every back-reference resolves** — task_spec_address, input_addresses, subcontract_cert_addresses all point at real, verifiable objects.
4. ✓ **Every cert was witnessed by Hedera** — Mirror Node REST returns the message body matching the cert's content_address, plus the consensus timestamp.
5. ✓ **The escrow released against the final cert hash** — XRPL transaction history shows the escrow was funded with hashlock X and released after submission of cert X.

**Math, not trust. No vendor needs to still exist. No agent needs to still be active. The audit verifies in 2046 the same way it verifies today.**

---

## SLIDE 9 — Risk mitigations (smart contracts + LLMs)

**The two scariest failure modes in agent-driven onchain commerce are exactly the two we engineered away from.**

### 1. Smart-contract risk → minimal verifier surface

Most onchain escrow contracts run thousands of lines of Solidity, with arbitrary call patterns and re-entrancy attack surface. AgentLevy uses **XLS-100 SmartEscrow** with a deliberately minimal `FinishFunction`:

- ~10 lines of WASM logic: *compute hash of submitted cert, compare to hashlock committed at escrow creation, release iff match*
- **Deterministic by construction** — no oracles, no time-dependent branches, no external calls
- **Auditable in a single afternoon** — not a week of formal verification
- **Hashlock pre-commitment** — the buyer locks in the expected output at escrow funding; the seller cannot retroactively renegotiate

XRPL Smart Escrow is also natively currency-aware (RLUSD, XRP) without a custom token contract — one less surface to audit.

### 2. LLM negotiation risk → bounded, schema-locked, cache-replayable

LLMs are non-deterministic, prompt-injectable, and prone to over-spending tokens on unbounded back-and-forths. We constrain every layer:

- **4-turn hard cap** on buyer↔compliance negotiation. Beyond turn 4, the protocol exits gracefully with a signed "negotiation failed" cert (itself a valid audit artifact). No infinite loops, no runaway token bills.
- **Schema-validated outputs only** — every LLM call returns a Pydantic-validated `BeneficialOwnershipExtraction` or `SanctionsScreenResult` via Anthropic tool use. Free-form text isn't accepted into the cert chain.
- **Temperature = 0** by default. Determinism wins for KYC; the cache layer assumes reproducibility.
- **Fixture cache for stage demos** — `LLM_CACHE_MODE=cache` replays recorded responses byte-identically. The demo cannot fail because the API hiccupped.
- **Wrong-keypair rejection at sign time** — `cert.sign(keypair)` raises if the keypair's public key doesn't match the `seller_pubkey` on the cert. Prevents an LLM-driven mistake from cross-signing as the wrong party.
- **Tamper detection on every field** — modifying the cert post-sign invalidates the signature; modifying a referenced cert breaks the chain at the address-resolution step. Test coverage proves this for every model field (87 tests across primitives + 17 for HCS anchor + 19 for LLM stack).

### Honest acknowledgments

- LLMs can still fabricate data *within the schema*. The cert chain proves the work happened, not that the inputs were correctly interpreted.
- WASM `FinishFunction` is new (XLS-100 activated Feb 2026); no production-scale audit history yet. Pilots go through a top-tier security firm before mainnet.

---

## SLIDE 10 — Standards-aligned, by design

![UOR Foundation](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/uor_foundation_logo.png)

**Foundation-backed standard, not a startup spec.**

The UOR Foundation is a 501(c)(3)-equivalent governance body with a Sandbox → Incubating → Graduated project lifecycle. AgentLevy isn't aligned to a vendor's whitepaper — it's aligned to a published, governed standard with multi-implementer adoption already underway.

**The two-standard stack we co-authored + the substrate we vendor:**

- **VTEAI** — *Verified Task Escrow + Attestation Interface.* ERC draft, CC0, April 2026. **We authored it.** The chain-neutral spec for verified-work settlement. AgentLevy is the first reference implementation; future competitors who want standards-alignment will implement a spec we shaped.
- **UOR-ADDR-1** — *Universal Object Reference Address.* Community proposal, April 2026. **We co-contribute.** Chain-agnostic content addressing for agent commerce. The addressing layer underneath every cert, every input, every reference.
- **PRISM** — UOR Foundation's reference implementation of the algebraic ring-coordinate system. **MIT-licensed, vendored.** What makes "one address, four representations" structurally true (hex, Braille glyph, ring element, base32 — all algebraically the same address).

### Same primitives, many surfaces

The whole point of UOR is that the same content-addressing primitives compose across domains. AgentLevy is what they look like applied to *commerce*; sibling UOR projects apply them elsewhere:

| UOR project | Applies UOR primitives to | How AgentLevy composes with it |
|---|---|---|
| **UOR Identity** | Cryptographic identity for agents + entities | Agent pubkeys in our cert chain can resolve to UOR Identity profiles |
| **UOR Certificate** | Generic signed-attestation envelopes | Our `DerivationCert` is a domain-specialized UOR Certificate |
| **UNS** (Universal Naming Service) | Human-readable names → UOR addresses | Lets a regulator look up a cert by name without trusting any vendor |
| **Hologram SDK** | Real-world UOR Module Certificates (in production today) | The deck visual on slide 4 is a real Hologram cert — same shape, byte-for-byte |

### Why this is a moat (not just a citation)

Standards consolidate fast once a category coalesces. Today's specs are published drafts; tomorrow's specs are de-facto requirements. **The protocol-author position means competitors who eventually want to be standards-aligned will have to implement specs we wrote.** The reference implementation is in our repo.

**Cross-validated:** AgentLevy's content addresses are byte-identical to UOR Foundation's canonical reference. Not "interoperable" — *byte-identical*. Live cross-checked May 3, 2026 against `mcp.uor.foundation/encode_address`. See [`docs/UOR_PASSPORT_VERIFIED.md`](https://github.com/maurathat/AgentLevy-XRPL-UOR/blob/main/docs/UOR_PASSPORT_VERIFIED.md).

---

## SLIDE 11 — Roadmap

**The protocol ships with the demo. The bigger build is partnerships, standards ratification, and the productization path.**

### Standards (the moat we're authoring)

- **VTEAI ERC** — currently a published draft (CC0, April 2026). Path to formal ratification with broader implementer adoption — engaging with the Ethereum standards community + cross-chain working groups.
- **UOR-ADDR-1** — currently a community proposal under the UOR Foundation. AgentLevy is its first reference implementation; we're contributing to maturation toward formal acceptance.
- **UOR Foundation Sandbox → Incubating** — track-graduating AgentLevy within the Foundation's project lifecycle. Brings governance + interop guarantees.

### Ecosystem partnerships

- **UOR Foundation alignment** — composability with sibling projects: UOR Identity, UOR Certificate, UNS, Hologram SDK. Same primitives, different surfaces.
- **XRPL ecosystem** — XLS-100 SmartEscrow community, RLUSD adoption pathways, XRPL Foundation grants/integrations.
- **Hedera ecosystem** — HCS expansion beyond the testnet anchor; Hashgraph Association compliance-focused initiatives.
- **Anthropic + LLM-platform partnerships** — agent-SDK alignment; structured-output + tool-use patterns that fit cleanly into VTEAI's negotiation envelope.

### Enterprise pilots (the wedge)

- **Mid-market regional banks** ($X–X B AUM) — high KYC volume, autonomy to pilot without 24-month procurement cycles.
- **KYC compliance vendors** — channel/whitelabel; let them sell *verifiable* audit to their existing customers.
- **International compliance teams** — EU eIDAS, Singapore MAS, jurisdictions that already accept cryptographic-evidence formats.

### Multi-chain via UOR-ADDR-1 adapters

XRPL ships first because XLS-100 is ready. UOR-ADDR-1's chain-binding adapter pattern means **any chain that supports a hashlock-conditional release can be added without changing the protocol layer**: Hedera EVM, Solana, Sui, Base — each gets an adapter; agents stay chain-agnostic.

### Verifiable agent memory + AI inference provenance

The cert chain we ship for KYC is the same primitive used for **verifiable agent memory**. Every cert is a content-addressed, signed, anchored record of "this agent did this work on these inputs at this consensus-witnessed time." Stack many of these and you get an agent's complete, mathematically-verifiable history — the foundation for:

- **Long-horizon agent reputation** — not vendor-trusted scores, but a public-key-verifiable track record. An agent's past certs are its résumé.
- **AI inference provenance** — for enterprise AI governance: "show me, cryptographically, what model + version + prompt + inputs produced this output." Same `DerivationCert` shape; new operation types.
- **Memoization with audit** — when an agent re-uses a prior result instead of recomputing, the prior cert IS the citation. Cache hits become cryptographically auditable.
- **Cross-agent memory sharing** — an agent referencing another agent's prior work cites by content address, not by API. The reference resolves whether the original agent still exists or not. Composes naturally with MemWal-style memory protocols.

### Productization → Kessai (next slide)

The open-source reference protocol is AgentLevy. The commercial layer is Kessai — visualizer UI, enterprise SDKs, regulatory-evidence packs, channel licensing. **Same protocol, productized.**

---

## SLIDE 12 — What this becomes

![Kessai logo](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/kessai_logo_primary.png)

**AgentLevy is the open reference implementation. Kessai is the productization.**

- **AgentLevy** — open-source, CC0/Apache 2.0, MIT-vendored. The protocol other people can build on. Standards-aligned. Auditable. Forkable.
- **Kessai** — the commercial layer: enterprise SaaS, KYC + AML + M&A escrow visualizer, regulatory-evidence packs, channel-licensed to compliance vendors.

**The protocol stays open. The standards stay free. The product is what makes verifiable settlement turnkey for enterprises.**

**Try it · Read the code · Help shape the standards:**

- 📦 GitHub: github.com/maurathat/AgentLevy-XRPL-UOR
- 🌐 Standards: VTEAI ERC draft + UOR-ADDR-1 community proposal
- 💬 Pitch on file: ask any judge or booth visitor; we love a hard question
- 🤝 Hiring: 2 senior engineers (Python SDK + XRPL/Hedera settlement) — pre-seed open

— Maura Clark · maurathat
— [contact info]

---

*AgentLevy v2 (XRPL × PRISM × Hedera). Brand visuals + ecosystem logos hosted at github.com/maurathat/kessai-pitch-assets. Apache License 2.0.*
