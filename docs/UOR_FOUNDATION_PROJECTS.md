# UOR Foundation — project ecosystem & maturity model

> **Source:** UOR Foundation projects page (uor.foundation). Captured by user May 2 2026; saved here verbatim because the page is client-side rendered and not directly fetchable.
>
> **Use:** know what already exists in the UOR ecosystem before proposing new work. Sandbox-stage projects are open for collaboration; the agent framework would naturally enter through this same pathway.

---

## Maturity model (3 stages, CNCF-style)

| Stage | Name | Status | Criteria |
|---|---|---|---|
| **1** | **Sandbox** | Early-stage & experimental — new projects with high potential | • Aligns with UOR Foundation mission • Clear problem statement • At least one committed maintainer • Open-source license (**Apache 2.0 or MIT**) |
| **2** | **Incubating** | Growing adoption & active development | • Healthy contributor growth • Production use by at least 2 organizations • Clear governance model • Passing CI/CD and documentation standards |
| **3** | **Graduated** | Production-ready & proven | • Broad adoption across the ecosystem • Committer diversity from multiple organizations • Security audit completed • Stable release cadence with semantic versioning • Open governance |

## Sandbox projects (currently 11; first 6 visible in the page snapshot)

| Project | Category | One-liner |
|---|---|---|
| **Hologram** | Systems | A software layer that turns existing hardware into a high-performance computing engine. No new chips required. |
| **Hologram SDK** | Developer Tools | The developer toolkit for building, shipping, and running applications on the Hologram platform. One identity, one build, every device. |
| **Atlas Embeddings** | Open Science | Research proving that five of the most complex structures in mathematics share a single origin, revealing a hidden order that connects seemingly unrelated fields. |
| **Atomic Language Model** | Systems | A language model where every output follows defined rules and is fully traceable. No black boxes. Fits in under 50 kilobytes. |
| **Prism** | Core Infrastructure | The reference implementation of the UOR Framework. Assigns every piece of data a permanent, unique address based on what it is, not where it is stored. |
| **UOR MCP** | Developer Tools | A server that connects AI models to the UOR verification engine. Every response is graded, traceable, and independently verifiable. |
| *(5 more not shown in the snapshot)* | — | — |

## Submission pathway

> *"Open source projects that align with the UOR specification. Reviewed by our technical committee against published criteria."*

1. **Prepare** — Open-source repo on GitHub with a clear README
2. **Submit** — Fill in the short form on the UOR Foundation projects page
3. **Launch** — Accepted projects enter Sandbox; technical committee responds within 3 weeks

## Categories observed

- **Systems** (Hologram, Atomic Language Model)
- **Developer Tools** (Hologram SDK, UOR MCP)
- **Open Science** (Atlas Embeddings)
- **Core Infrastructure** (Prism)

## Key implications for the agent framework

1. **The framework should be designed for Sandbox submission from day one.** Apache 2.0 license, open repo, README, single committed maintainer (the user) — all match the criteria. AgentLevy itself can be the reference implementation cited in the framework's submission.

2. **The framework's category is most likely "Developer Tools"** (parallel to Hologram SDK and UOR MCP). It's not Core Infrastructure (PRISM is) and it's not pure Systems or Open Science.

3. **There is overlap to disambiguate:**
   - **UOR MCP** ("server that connects AI models to UOR verification engine") sounds adjacent to what the framework's Verification Services would do. Need to read UOR MCP's docs/repo before drafting the spec to avoid duplicating its scope.
   - **Hologram SDK** ("developer toolkit, one identity, one build") sounds adjacent to Account Services + Discovery Services. Same — read first.
   - **Atomic Language Model** ("output follows defined rules, fully traceable") could be a downstream consumer of the framework rather than overlap.

4. **Atlas Embeddings is in Sandbox** — confirms it's a real UOR Foundation project. The framework should reference it as Sandbox-tier (mature for research, not yet production).

5. **PRISM is in Sandbox.** That's notable — even the reference implementation is Sandbox-stage in this maturity model. Implies the whole ecosystem is early; the framework joining at Sandbox is appropriate, not premature.

## Open follow-ups (not blocking)

- **What are the other 5 Sandbox projects?** The page snapshot showed 6 of 11. Worth fetching the full list before final positioning.
- **What does UOR MCP actually do at the API level?** If it overlaps Verification Services, the framework should compose with it rather than duplicate.
- **What does Hologram SDK actually do at the API level?** Same — likely overlap with Account/Discovery Services to disambiguate.
- **Is there a UOR Foundation governance doc** (technical committee, voting model, IP policies)? Affects how the framework's spec phase navigates Foundation acceptance.
