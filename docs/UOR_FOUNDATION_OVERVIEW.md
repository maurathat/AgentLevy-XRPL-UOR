# UOR Foundation — public architecture overview

> **Source:** https://uor.foundation/standard (or similar). The page is client-side rendered — WebFetch returned only the title. User pasted the canonical content into chat May 2 2026; saved here verbatim so it's not stuck in chat history.
>
> **Use:** authoritative source for UOR Foundation vocabulary and 6-layer architecture. Cite this when grounding the agent framework, pitch slides, or VTEAI/UOR-ADDR alignment.

---

## The Problem

Existing systems use location-dependent identifiers: URLs break, UUIDs collide across boundaries, database keys don't survive export.

Every integration layer adds translation code. UOR eliminates this by deriving identity from content structure. The address is the data, so there is nothing to translate.

## How It Works

**Fragmentation → Unification.** APIs, Databases, Files, AI Models, Graphs, Streams, Ledgers, Devices, Protocols — all currently isolated systems and formats — converge to one UOR universal address system.

## Example Use Case

When all data shares one address system, AI can find, verify, and use information across every source without custom connectors or translations.

The four AI capabilities this enables:

- **Reason**
- **Verify**
- **Compose**
- **Navigate**

> *"AI systems can find and connect information across different sources without needing custom adapters for each one."*

## Anatomy of an Address

Every piece of data in UOR is described by **three coordinates**. Together, they tell you everything about what the data is, how complex it is, and what it is made of.

| # | Coordinate | What it is | What it represents |
|---|---|---|---|
| 1 | **The Value** | The raw data itself, stored as a sequence of bytes. | The "what" — the actual content being addressed. |
| 2 | **The Weight** | How many "active" bits are in the value. | A measure of complexity. Weight 0 means empty; Weight 8 means fully packed (per byte). |
| 3 | **The Components** | Which specific building blocks make up the value. | Lets you reconstruct the original from its parts, with nothing lost. |

**Example: the number 85**
- Binary: `01010101`
- The Value: `01010101`
- The Weight: 4 (four 1-bits)
- The Components: positions `0, 2, 4, 6`

> *"These three pieces together form a complete fingerprint. Given any two of them, you can derive the third. This is what makes UOR addresses self-verifying: the data proves its own identity."*

**Mapping to PRISM technical vocabulary:**

| Public name (uor.foundation) | Technical name (PRISM `Triad` dataclass) |
|---|---|
| The Value | `datum` |
| The Weight | `stratum` |
| The Components | `spectrum` |

**Use the public names in pitch material; use the technical names in code.**

## Where It Applies

When every system shares one way to address data, new capabilities emerge.

| Domain | What UOR enables |
|---|---|
| **Semantic Web** | Make data understandable by both people and machines, so systems can work together without custom translations. |
| **Proof Based Computation** | Run a computation once and produce a receipt that anyone can check. No need to re-run it, no need to trust the person who ran it. |
| **★ Agentic AI** | Give AI systems a single, reliable map of all available data so they can find, verify, and use information on their own. |
| **Open Science** | Make research data findable, reproducible, and composable across institutions and fields. |
| **Cross Domain Unification** | Let different fields share data and ideas without losing meaning in translation. One shared system, many disciplines. |
| **Frontier Technologies** | Provide a foundation for emerging fields like quantum computing and next-generation AI, where reliable data identity is essential. |

**AgentLevy / the agent framework / VTEAI / UOR-ADDR-1 sit in the Agentic AI slot specifically.** This is a UOR-Foundation-named application domain, not something we invented. That framing strengthens the pitch position substantially.

## Framework Architecture — 6 Layers

> *"Six layers, each building on the one below it. Together they form a complete system: from the ground rules, to naming, to finding, proving, and transforming data."*

| Layer | Name | What it does |
|---|---|---|
| **0** | **The Foundation** | Mathematical rules that can be verified by anyone, on any machine, in under a second. Key rule: applying two simple reversible operations in sequence always produces the next value. This single fact guarantees every value is reachable; the system is complete. **The UOR Framework defines these rules formally. Prism executes them.** |
| **1** | **Identity** | Every piece of data gets one permanent name, based on what it is. |
| **2** | **Structure** | How things combine and break apart without losing information. |
| **3** | **Resolution** | Find anything by describing what you need. |
| **4** | **Verification** | Every claim is backed by proof, not promises. |
| **5** | **Transformation** | Convert between formats without losing meaning. |

## Quotable lines (for pitch + slides)

These land in 7 words or fewer and are taken verbatim from the public page. Use them directly:

- *"The address is the data, so there is nothing to translate."*
- *"Every claim is backed by proof, not promises."*
- *"The data proves its own identity."*
- *"Reason. Verify. Compose. Navigate."* (the four AI verbs)
- *"From the ground rules, to naming, to finding, proving, and transforming data."*
