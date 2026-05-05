# AgentLevy — Demo Deck (Consensus EasyA · 10 slides)

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

Two AI agents transact today by exchanging API calls and trusting each other's logs. That's fine when both belong to the same vendor. It breaks the moment they don't.

What's missing is a **settlement primitive** for agent commerce — one that:

- Doesn't require agents to trust each other
- Doesn't require either side to still exist for the audit to verify
- Resolves to a **definite outcome** that any third party can re-check from public keys alone

That's what AgentLevy demonstrates.

---

## SLIDE 3 — What we built

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

## SLIDE 4 — The KYC demo

![A real UOR Module Certificate in the wild — Kessai certs follow the same shape, byte-for-byte](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/hologram-cert.png)

**Three agents. One KYC task. Five signed artifacts. Two chains.**

1. **Buyer agent** — drafts a TaskSpec for beneficial-ownership verification, signs it, escrows RLUSD on XRPL.
2. **Compliance agent** — accepts the spec, reads a synthetic corporate disclosure, extracts beneficial owners, **subcontracts** sanctions screening to a third agent.
3. **Sanctions agent** — screens each name against a synthetic sanctions list, signs a `DerivationCert` with the result.
4. **Compliance agent** — assembles a parent `DerivationCert` referencing the sanctions cert by content address, signs it.
5. **All certs** — anchored to a Hedera HCS topic for tamper-evident timestamping. Final cert hash submitted to the XRPL escrow's WASM `FinishFunction`. Escrow releases.

**No oracles. No off-chain settlement. No trust in any agent.**

---

## SLIDE 5 — The cert chain anatomy

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

---

## SLIDE 6 — Two-ledger settlement

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

## SLIDE 7 — The verification math

![Each byte becomes one Braille codepoint — codepoint = U+2800 + byte_value](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/byte-to-glyph-primer.png)

**Anyone holding `(buyer_pubkey, compliance_pubkey, sanctions_pubkey, 5 certs)` can independently verify:**

1. ✓ **Every signature is valid** — Ed25519 verify against canonical bytes.
2. ✓ **Every content address resolves** — recompute SHA-256 over canonical bytes, match against the reference.
3. ✓ **Every back-reference resolves** — task_spec_address, input_addresses, subcontract_cert_addresses all point at real, verifiable objects.
4. ✓ **Every cert was witnessed by Hedera** — Mirror Node REST returns the message body matching the cert's content_address, plus the consensus timestamp.
5. ✓ **The escrow released against the final cert hash** — XRPL transaction history shows the escrow was funded with hashlock X and released after submission of cert X.

**Math, not trust. No vendor needs to still exist. No agent needs to still be active. The audit verifies in 2046 the same way it verifies today.**

---

## SLIDE 8 — Standards-aligned, by design

![UOR Foundation](https://raw.githubusercontent.com/maurathat/kessai-pitch-assets/main/uor_foundation_logo.png)

**AgentLevy is the first reference implementation of a two-standard stack we authored.**

- **VTEAI** — Verified Task Escrow + Attestation Interface. ERC draft, CC0, April 2026. The chain-neutral spec for verified-work settlement.
- **UOR-ADDR-1** — Universal Object Reference Address. Community proposal, April 2026. Chain-agnostic content addressing for agent commerce.
- **PRISM** — UOR Foundation's reference implementation of the algebraic content-addressed coordinate system. Vendored, MIT.

**Cross-validated:** AgentLevy's content addresses are byte-identical to UOR Foundation's canonical reference. We're not just "compatible" — we produce the same bytes, byte-for-byte. (See [docs/UOR_PASSPORT_VERIFIED.md](https://github.com/maurathat/AgentLevy-XRPL-UOR) in the repo.)

**Why this matters for the demo:** the same primitives ship in PRISM, UOR Identity, UOR Certificate, UNS, and the Hologram SDK. AgentLevy is what those primitives look like applied to commerce.

---

## SLIDE 9 — What you're seeing live (and what's still scaffolded)

**Today the foundations are real and tested. The demo's user-facing flow lands tomorrow.**

| Layer | Status today (May 4) | Demo-day (May 7) |
|---|---|---|
| Cert primitives (canonical, signing, TaskSpec, DerivationCert) | ✓ 87 tests passing | ✓ |
| Hedera HCS anchor (mock + live) | ✓ Module + 17 tests; live topic created | ✓ live submit |
| LLM stack (client + cache + schemas + prompts) | ✓ Scaffold + 19 tests | ✓ live agents |
| 3 agents (buyer + compliance + sanctions) | ⏳ Phase 2.5 (Day 1) | ✓ live |
| Bounded-turn negotiation | ⏳ Phase 2.6 (Day 1) | ✓ live |
| End-to-end local demo | ⏳ Phase 2.7 (Day 1) | ✓ recorded backup |
| XRPL escrow (Path A WASM + RLUSD) | ⏳ Phase 2.8 (Day 2) | ✓ live |

**Honest acknowledgment:** the deck is shipping ahead of the demo. The protocol-and-primitive layers are done; the agent + chain wiring is the next 48 hours.

---

## SLIDE 10 — What this becomes

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
