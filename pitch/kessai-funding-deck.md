# Kessai — Funding Deck (10 slides)

> **For: pre-seed / seed VC and strategic investor conversations.** Distinct from the Consensus hackathon deck, which lives in `pitch/uor-slide.md` + `pitch/old-deck-v2.md`. This deck leads with Kessai (the company) and uses AgentLevy as a single technical-proof slide. Convert to Keynote/Figma/Slides at Miami; the markdown below is the speaker-ready content.

---

## SLIDE 1 — Title

**Kessai**

*Enterprise-grade escrow with cryptographic audit*

*Verifiable from public keys alone.*

— Maura Clark · maurathat
— [contact info]
— Pre-seed · raising $1M–$2M

**Visual suggestion:** Single-line Braille glyph as a background motif (UOR address visual signature). Clean typography. No clutter.

---

## SLIDE 2 — The problem

> *"Auditing a 2020 KYC verification in 2026 typically requires the original vendor's API to still work, the original account to still be active, and the original compliance officer to vouch for what was done."*

**Compliance audit is built on vendor trust, not math.**

Three structural failures of the current architecture:

1. **Logged, not signed.** Compliance work is written to vendor databases. Verification requires the vendor still being in business, the API still working, the account still active.
2. **Vendor-locked.** Each provider has its own audit format. Cross-vendor reconciliation requires translation. Decade-old workflows.
3. **No transferable reputation.** A compliance officer's track record is trapped inside whichever vendor they used. Switching costs are weaponized.

**This doesn't scale to the agent economy.** When AI agents are doing the compliance work, "we promise we did it" stops being acceptable to regulators.

**Visual suggestion:** Side-by-side. Left: a SaaS audit dashboard with "Vendor X says this happened" framing. Right: a content-addressed cert with "Anyone can verify, forever" framing.

---

## SLIDE 3 — The solution

**Kessai is an enterprise escrow platform where every action produces a cryptographically-verifiable certificate.**

| What Kessai does | What it replaces |
|---|---|
| Public-key signed certs for KYC, AML, compliance, M&A escrow | Vendor logs, audit dashboards, "trust our database" |
| Content-addressed audit trail (UOR Passport-aligned, byte-identical to canonical reference) | Per-vendor formats, translation middleware |
| Visualization layer — the audit trail as an interactive graph | Spreadsheets, PDFs, vendor-portal screenshots |
| Open standards underneath (VTEAI + UOR-ADDR-1) | Proprietary tokens, walled-garden credentials |

**Same value the legacy compliance vendors deliver. Plus: verifiable in 2046, by anyone, without our cooperation, without us still existing.**

**Visual suggestion:** A diagram of the cert chain: input → agent → cert → escrow release. With a "verified by 3rd party" arrow shown as math, not as an API call.

---

## SLIDE 4 — The protocol underneath

**Kessai is the first reference implementation of a two-standard stack we authored.**

| Standard | What it does | Status |
|---|---|---|
| **VTEAI** (Verified Task Escrow + Attestation Interface) — ERC draft, CC0, April 2026 | The settlement-state-machine standard | Authored, published draft |
| **UOR-ADDR-1** (Universal Object Reference Address) — community proposal, April 2026 | Chain-agnostic content addressing for agent commerce | Co-contributing |
| **PRISM** (UOR Foundation reference implementation) | Algebraic content-addressed coordinate system | Vendored, MIT |

**Defensibility:** competitors who eventually want to be standards-aligned will have to implement specs *we wrote*. The protocol-author position is the moat.

**Empirical proof:** AgentLevy's content addresses are byte-identical to UOR Foundation's canonical reference implementation. Verified live May 3 2026 against `mcp.uor.foundation/encode_address`. Same canonical bytes → same SHA-256 → same address.

**Visual suggestion:** Stack diagram. From top: Kessai (commercial) → AgentLevy (open ref impl) → VTEAI + UOR-ADDR-1 (standards) → UOR Foundation primitives (PRISM, UOR Identity, UOR Certificate, UNS). Crisp layering.

---

## SLIDE 5 — Demo (1 slide of the technical proof, not 5)

**The Consensus EasyA hackathon demo, May 5–7 2026.**

A buyer agent and a compliance agent negotiate a KYC task. The compliance agent extracts beneficial-ownership from a synthetic corporate disclosure, subcontracts sanctions screening to a sanctions agent, assembles a multi-cert audit trail, and submits the final cert hash to an XRPL Smart Escrow. The escrow's WASM `FinishFunction` verifies the hash matches the value committed at escrow creation. Funds release.

**No oracles. No off-chain settlement. No trust in any agent. The audit trail verifies from public keys alone.**

**The demo is the proof. Kessai is the productization.**

**Visual suggestion:** A 30-second screen-recorded GIF of the demo. Or a single static screenshot of the audit trail visualizer with the cert chain laid out.

---

## SLIDE 6 — Why now

Five convergence events in the last 12 months make this possible only now:

1. **XLS-100 Smart Escrow** activated on XRPL WASM Devnet (Feb 2026) — first production-ready WASM-verified escrow on a regulated-finance-friendly chain
2. **UOR Foundation Sandbox program** matured to 12 active projects (PRISM, UOR Identity, UOR Certificate, UNS, …) — partner-ready ecosystem
3. **Anthropic + OpenAI ship agent SDKs** mainstream — enterprise agent procurement starts, settlement gap obvious
4. **Regulatory pressure on AI auditability** (EU AI Act enforcement, Colorado SB-205, BIS supervision) — compliance teams need *cryptographic* audit, not vendor-trust audit
5. **Post-Cambridge-Analytica institutional cynicism** re: vendor data custody — "verifiable from public keys alone" lands with risk officers, not just engineers

**The window is open now and won't stay open. Standards consolidate fast once a category coalesces.**

---

## SLIDE 7 — Market expansion path

**The wedge is KYC compliance. The protocol is general.**

| Stage | Wedge | TAM order of magnitude |
|---|---|---|
| **Year 1** | Mid-market financial institutions; KYC + AML compliance audit | $X B annual compliance-vendor market |
| **Year 2** | M&A escrow, multi-party agreements, IP licensing | $X T annual escrow flow |
| **Year 3** | AI/agent commerce settlement (the Consensus demo, productized) | New market; estimated $X B by 2030 |
| **Year 4+** | AI inference provenance + memoization for enterprise AI governance | Frontier-tech, but enterprise AI spend is in the $X B range now and growing |
| **Endgame** | The verifiable-settlement layer for the institutional internet | — |

**Each stage uses the same protocol. The product surface (escrow visualizer, SDK, cert APIs) extends; the cryptographic substrate stays constant.**

**Visual suggestion:** Funnel or expanding-triangle visual. KYC at the bottom (narrow, deep); the institutional internet at the top (wide, broad).

---

## SLIDE 8 — Why us

**Maura Clark** — sole founder. Track record (in priority order):

- **VTEAI ERC author** (April 2026, CC0). The chain-neutral standard for verified-work settlement.
- **UOR-ADDR-1 community contributor** (April 2026). Standards-track participation in chain-agnostic content addressing.
- **AgentLevy v1** (Cannes hackathon, Flare). First production reference implementation of the spec.
- **AgentLevy v2** (Consensus hackathon, XRPL+UOR). Second iteration. Live byte-identical verification with UOR Foundation.
- **Cryptographic alignment** with the canonical UOR reference implementation is empirical proof, not aspiration.

**The defensible moat is the protocol-author position.** When VTEAI and UOR-ADDR-1 mature into standards that competitors must implement, Kessai is the company shipping the reference implementation, the SDK, and the productized commercial offering simultaneously.

**Hiring plan with funds:** 2 senior engineers (Python SDK + XRPL settlement); GTM/BD lead; design contractor for visualizer; security audit firm; regulatory advisory retainer.

**Honest acknowledgment:** solo founder pre-seed. Strong protocol-and-standards traction; no enterprise revenue yet. The funding ask is to *convert* protocol traction into the first three pilots, not to *discover* product-market fit.

---

## SLIDE 9 — Go-to-market

**Initial customer profile (3 pilots in 12 months):**

- Mid-market regional banks ($X–$X B AUM) who do enough KYC volume to feel the pain and have enough autonomy to pilot a new vendor without a 24-month procurement cycle
- KYC compliance vendors looking for a differentiated cryptographic-audit story to sell to *their* enterprise customers (channel/whitelabel play)
- International compliance teams subject to non-US regulatory regimes that already accept cryptographic-evidence formats (EU eIDAS, Singapore MAS)

**The wedge:** *"Same compliance work you're doing today. Plus: cryptographically auditable for 30 years. Plus: the audit trail outlives any vendor relationship. Plus: a visualizer your regulator will love."*

**Conversion strategy:**

1. Free-tier proof-of-concept (one workflow, one entity type, 30-day pilot)
2. Enterprise SaaS pricing ($X–$X K / month per seat tier)
3. Compliance-vendor channel licensing (whitelabel; revenue share)

**Strategic investor preference:** anyone with introductions to mid-market regional banks, KYC vendors, escrow agents, or AI governance teams at large enterprises. Capital is necessary but introductions are higher-leverage at this stage.

---

## SLIDE 10 — Ask

**$1M–$2M pre-seed**

For 12 months runway. Use of funds:

- 50% — 2 senior engineers (Python/TypeScript SDK, XRPL settlement, visualizer backend)
- 20% — GTM / business development (3 enterprise pilots, channel partnerships)
- 15% — Security audit + regulatory advisory
- 10% — Design / visualizer UI
- 5% — Founder runway + ops

**12-month milestones:**

1. ✓ Three enterprise pilots signed and live
2. ✓ Python + TypeScript SDKs published (filling the UOR Foundation binding gap)
3. ✓ Sandbox → Incubating graduation within UOR Foundation
4. ✓ Security audit completed by top-tier firm
5. ✓ First paid revenue from at least one pilot

**Strategic preferences:** standards-aware investors who can place mid-market financial introductions; deep-tech / infra funds; not aggregator marketplaces.

**To follow up:** [contact info] · GitHub: maurathat/AgentLevy-XRPL-UOR

---

## Appendix slides (for Q&A or deeper conversations)

These don't go in the 10-slide read; they're for follow-up meetings or hostile-question responses.

### A1 — Why XRPL specifically?

XLS-100 SmartEscrow with WASM `FinishFunction` is the precise primitive Kessai needs: programmable conditional release tied to a cert hash. **Hedera doesn't have it. Sui doesn't have it. Solana doesn't have it.** XRPL just activated it (Feb 2026, on WASM Devnet). The chain choice was driven by primitive availability, not chain ideology. We can multi-chain via UOR-ADDR-1 chain-binding adapters; XRPL ships first because the primitive is ready.

### A2 — What about post-quantum?

Ed25519 (cert layer) and SHA-256 (addressing layer) are not post-quantum-safe. **The architecture has a documented migration path to CRYSTALS-Dilithium-3** (FIPS 204 ML-DSA-65) — which is what UOR Foundation's deeper agent-identity layer already uses. The cert envelope's algorithm field makes the migration purely additive: no breaking change to the surrounding format. We migrate when the ecosystem migrates; the SHA-256 addressing layer survives quantum break independently of signature algorithm.

### A3 — Why not a token?

Two reasons. (1) Kessai is a SaaS / B2B platform; the value capture is enterprise contracts, not token speculation. (2) **Tokens are platform plays; the protocol is intentionally token-free.** VTEAI and UOR-ADDR-1 are open standards. If we issued a Kessai token we'd weaken the standards story by introducing an economic gating mechanism. Cleaner business: charge for the platform; let the standards stay open.

### A4 — Competitor analysis

| Category | Player | Why we differ |
|---|---|---|
| Legacy compliance vendors | LexisNexis, Refinitiv, Thomson Reuters | They sell vendor-trust audit; we sell math-trust audit. Their architecture predates the cryptographic primitives. |
| Web3 identity / credential platforms | Moca AIR Kit, Civic, Worldcoin | They package *user* identity. We package *agent and institutional* attestation with public-key audit. Adjacent, not competing. |
| Agent payment standards | Coinbase x402, Google AP2 | HTTP-layer payment standards. We're at the cryptographic-settlement layer below them. Composable, not competitive. |
| Enterprise blockchain platforms | Hyperledger Fabric, R3 Corda | Permissioned-blockchain platforms. We're protocol + product, chain-agnostic, public-key-verifiable by default. |
| AI governance startups | Credo AI, Holistic AI, Datalogue | Audit-process tooling for AI teams. We provide the cryptographic substrate they could use *as* their audit format. Potential channel partner, not competitor. |

### A5 — Risks

Honest list:

1. **Solo founder.** Mitigated by funding-the-team-not-the-founder framing in the ask.
2. **Standards ratification timing.** VTEAI is a draft; UOR-ADDR-1 is community-proposed. Mitigated by reference-implementation-first strategy: Kessai works regardless of formal ratification; ratification is upside, not gating.
3. **XRPL bet.** XLS-100 is recently activated; ecosystem maturity is moderate. Mitigated by chain-agnostic protocol design (UOR-ADDR-1 adapters).
4. **Enterprise-sales cycle length.** Mid-market regional banks have 6-9-month procurement. Mitigated by free-tier-PoC wedge and channel-licensing path.
5. **Foundation governance dependency.** UOR Foundation maturity affects standards story. Mitigated by Sandbox-track participation; we're a community contributor, not subordinate.

### A6 — What if a big player builds this?

The realistic scenario isn't "Coinbase clones Kessai" — it's "a big player adopts the standards we wrote." If Anthropic, Coinbase, or Google decides to ship VTEAI-compliant settlement, **that's a win for us**, because:

- The standard becomes ubiquitous (network effects favor incumbents)
- We're the reference-implementation provider (first-mover positioning)
- We have 12-18 month head start on the productized form (visualizer, SDK ergonomics, enterprise pilots)
- We're contributing to the standards' evolution; competitors using the standards are downstream of us

The defensible position is **standards-author + protocol-aligned reference + first commercial implementation**, not a defensive moat against clones.

---

*Last updated: May 3 2026 (en route to Consensus). To be converted to slides at Miami before any investor conversations.*
