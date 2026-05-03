# Kessai

## Enterprise-grade escrow with cryptographic audit — verifiable from public keys alone

**Maura Clark · maurathat · [contact info]**
**Stage: pre-seed · Raising: $1M–$2M (placeholder; adjust to target)**

---

### The problem

Enterprise compliance audit is broken. Banks, corporates, and regulators rely on middleware vendors (LexisNexis, Refinitiv, Thomson Reuters) whose architecture predates the cryptographic primitives that would make audit *structurally* trustworthy. Compliance work is logged, not signed; verifiable only with vendor cooperation; tied to whichever provider issued it; and degrades as vendors get acquired, pivot, or sunset products. **Auditing a 2020 KYC verification in 2026 typically requires the original vendor's API to still work, the original account to still be active, and the original compliance officer to vouch for what was done.** That doesn't scale to the agent economy that's already arriving.

### The solution

**Kessai is an enterprise escrow platform with cryptographic audit baked in.** Every action — KYC checks, compliance attestations, multi-party agreements, M&A escrow — produces a content-addressed certificate signed with the agent or institution's public key. Anyone with the cert and the public key can verify the entire chain in milliseconds, **without contacting Kessai, without trusting any vendor, without permission.** The audit trail outlives Kessai, outlives the parties, outlives the chain it settled on.

The protocol underneath is open, standards-track, and **byte-identical to UOR Foundation's canonical reference implementation** (verified live May 3 2026). We authored the [VTEAI ERC draft](https://github.com/maurathat/AgentLevy-XRPL-UOR/blob/main/pitch/VTEAI-DRAFT.md) for verified-task-escrow-and-attestation-interface. We contribute to the [UOR-ADDR-1](https://github.com/maurathat/AgentLevy-XRPL-UOR/blob/main/pitch/UOR-ADDR-PROPOSAL.md) community standard for chain-agnostic content addressing. **The protocol is open; Kessai is the first enterprise-grade implementation, with an escrow visualizer on top.**

### Traction (May 2026)

- ✅ **VTEAI ERC draft authored** (CC0, April 2026; standards-track for verified-work settlement)
- ✅ **UOR-ADDR-1 community proposal** — co-contributing to chain-agnostic content addressing
- ✅ **Live byte-identical verification** against UOR Foundation's canonical MCP server — our content addresses are mathematically identical to UOR Passports
- ✅ **AgentLevy demo** — second iteration shipping at Consensus EasyA hackathon (May 5–7, 2026)
- ✅ **First reference implementation** of the two-standard stack (VTEAI + UOR-ADDR-1) on XRPL with PRISM addressing
- ⏳ **Sandbox submission** to UOR Foundation pending spec finalization
- ⏳ **First three enterprise pilots** are the use of funds

### Market

| Wedge | TAM signal |
|---|---|
| **KYC / AML / compliance audit** | $X B annual market for compliance vendors today; high regulatory pressure, multi-decade audit retention |
| **M&A escrow + multi-party agreements** | $X T annual flow through escrow agents, attorneys, title companies; legacy paper-and-API workflows |
| **AI/agent commerce** | New market emerging; Anthropic, OpenAI, Google all shipped agent SDKs in 2025–2026; settlement layer empty today |
| **AI inference provenance & memoization** | Frontier-tech adjacent; inference-cost reduction + audit trail for AI decisions; enterprise AI governance |
| **Long-tail: any enterprise escrow needing decade-scale audit** | Title insurance, IP licensing, supply chain attestations, regulatory holds |

The wedge is KYC compliance. The expansion path goes through agent commerce and AI provenance. The endgame is **the verifiable-settlement layer for the institutional internet.**

### Why now

| Convergence event | Effect |
|---|---|
| **XLS-100 Smart Escrow activated on XRPL WASM Devnet** (Feb 2026) | First production-ready WASM-verified escrow primitive on a regulated-finance-friendly chain |
| **UOR Foundation Sandbox program** with 12 active projects | Standards-track infrastructure maturing; partner-ready ecosystem |
| **Anthropic + OpenAI ship agent SDKs** | Enterprise agent procurement starts; settlement gap obvious |
| **Regulatory pressure on AI auditability** (EU AI Act, Colorado SB-205, BIS enforcement) | Compliance teams need *cryptographic* audit, not vendor-trust audit |
| **Post-Cambridge-Analytica institutional cynicism re: vendor data** | "Verifiable from public keys alone" lands with risk officers, not just engineers |

### Why us

- **Maura Clark** — sole founder. Two iterations of AgentLevy shipped (Flare/Cannes, XRPL/Consensus). VTEAI ERC author. UOR-ADDR-1 contributor.
- **Live cryptographic alignment** with the canonical UOR reference implementation is *not* a generic "we use crypto" claim; it's empirical proof of protocol membership.
- **Standards track record before product** is the defensible moat. Kessai isn't just an enterprise escrow tool; it's the company shipping the standards that competitors will eventually have to implement to stay relevant.

### Use of funds (12-month plan, $1M–$2M)

| Bucket | Approximate split |
|---|---|
| 2 senior engineers (Python/TypeScript SDK, XRPL settlement) | 50% |
| GTM / business development (3 enterprise pilots, design partners) | 20% |
| Security audit + regulatory advisory | 15% |
| Design / visualizer (the customer-facing UI for the audit trail) | 10% |
| Founder runway + ops | 5% |

**12-month milestones:**

1. **Three enterprise pilots** signed and live (initial focus: mid-market financial institutions, $X–$X B AUM range; international compliance vendors)
2. **Python + TypeScript SDKs published** (filling the gap in UOR Foundation's published bindings — they have Rust + Lean only)
3. **Sandbox → Incubating graduation** within UOR Foundation
4. **Security audit completed** by a top-tier firm (Trail of Bits, Veridise, or similar)
5. **First paid revenue** from at least one of the three pilots

### What I'm asking

A check between **$1M–$2M** in exchange for [equity terms: typically 10–20% for pre-seed]. Strategic preference for investors who can introduce mid-market financial institutions (regional banks, KYC vendors, escrow agents, title companies) for pilot conversation.

I am not raising for product-market-fit discovery. The market is identified; the protocol is built and verified; the first wedge customer profile is clear. The capital is for **executing the GTM the protocol unlocks.**

---

*Repo: https://github.com/maurathat/AgentLevy-XRPL-UOR*
*VTEAI ERC draft: [pitch/VTEAI-DRAFT.md](https://github.com/maurathat/AgentLevy-XRPL-UOR/blob/main/pitch/VTEAI-DRAFT.md) · CC0*
*UOR Passport verification milestone: [docs/UOR_PASSPORT_VERIFIED.md](https://github.com/maurathat/AgentLevy-XRPL-UOR/blob/main/docs/UOR_PASSPORT_VERIFIED.md)*
