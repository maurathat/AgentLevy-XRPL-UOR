# Terminology — what to call things, and when

> Reference for AgentLevy / UOR Passport / framework writing. Three layers of vocabulary; each layer is correct for a specific audience. Discipline: pick the right layer for the audience; don't mix layers within a single passage.

## Coordinates vs the system that produces them

**Strictly correct usage:**

| Term | Refers to |
|---|---|
| **UOR (Universal Object Reference)** | The mathematical framework. Defined in the UOR-Framework ontology. Owned by UOR Foundation. |
| **UOR coordinate system** | The framework's addressing model — the math. |
| **UOR coordinates / UOR address / UOR triad** | A specific point in the system; a particular address. |
| **PRISM** | The reference *engine* that computes UOR coordinates. One of multiple possible implementations. Single-file Python module, MIT-licensed. |
| **PRISM triad** | The data structure PRISM returns from `engine.triad(value)` — implementation type. |

**Common error to avoid:** *"PRISM coordinates."* The coordinates belong to UOR; PRISM is the algorithm that computes them. Use **UOR coordinates** (or **UOR addresses**, or **UOR triadic coordinates**) instead.

## The three names of the triad's three parts

The triad has three components. Each has three different names depending on audience.

| Public-facing name (uor.foundation/standard) | Conceptual (PRISM CONCEPTS.md) | Technical (PRISM Triad dataclass attribute) | What it is |
|---|---|---|---|
| **The Value** | Identity | `datum` | The raw bytes — the "what" |
| **The Weight** | Magnitude | `stratum` | Number of active bits per byte — complexity |
| **The Components** | Structure | `spectrum` | Which specific bit positions are active — internal structure |

## When to use which layer

| Audience | Use this layer | Example |
|---|---|---|
| **Pitch deck on stage** | Public-facing | *"Every value has a Value, a Weight, and Components — three coordinates that uniquely identify any data."* |
| **VC investor / regulator / journalist** | Public-facing | Same as above. |
| **Standards / architecture talk** | Conceptual | *"The triad consists of Identity (what the data is), Magnitude (how complex), and Structure (which parts compose it)."* |
| **Whitepaper / spec doc** | Conceptual or Public-facing — pick one and stick with it within the document | — |
| **Code / API docs / developer reference** | Technical | `triad.datum`, `triad.stratum`, `triad.spectrum` (these are the actual attribute names in PRISM's `Triad` dataclass; don't rename them in code) |

## The cardinal rule

**Never mix layers within a single passage.** A slide that uses "Value / Weight / Components" should not also say "datum" two lines later. A code comment that uses "stratum" should not also say "Magnitude" in the next sentence. Pick the layer for the audience and keep it consistent.

The only exception: **a one-time mapping table** at the top of a document that introduces the technical names if a developer will need to read the code afterwards. Like the table in this very doc.

## How this maps onto AgentLevy's documents

| Document | Layer it should use | Status (May 3 2026) |
|---|---|---|
| `pitch/uor-slide.md` | Public-facing | ⚠️ mixes layers — needs scrub |
| `pitch/AGENT-FRAMEWORK-CONCEPT.md` | Public-facing (consumed by recruiters / Foundation) | ⚠️ uses some technical names — needs scrub |
| `pitch/VTEAI-DRAFT.md` | Conceptual (it's a standards-track ERC) | ✓ does not use any of these names; refers to canonical-bytes hash directly |
| `docs/WHY_PUBLIC_KEY_CERTIFICATION.md` | Public-facing | ✓ does not lean on triad terminology |
| `docs/UOR_FOUNDATION_OVERVIEW.md` | Mixed (it captures the public spec verbatim, then maps to technical names) | ✓ correct — has explicit mapping table |
| `docs/UOR_PASSPORT_VERIFIED.md` | Conceptual / technical (it's a verification milestone for engineers) | ✓ correct |
| `CANONICAL_FORM.md` | Technical (it's the implementation discipline doc) | ✓ correct |
| `agentlevy/primitives/display.py` | Technical (Python attribute names) | ✓ correct |
| `agentlevy/prism_layer/triad.py` | Technical | ✓ correct |
| `scripts/test_prism.py` | Technical | ✓ correct |

The pitch-material docs flagged with ⚠️ should be scrubbed to use only public-facing names where they describe the triad to non-technical readers. The technical names belong only in code-adjacent docs.

## Bonus: address representations vs the address itself

UOR addresses have multiple equivalent representations (verified against `mcp/example-module-certificate.json` and the `uor.encode_address` MCP tool):

| Representation | Format | Use |
|---|---|---|
| **CID** | `baguqee...` (base32 multibase) | Storage/IPFS-style addressability |
| **sha256: prefix** | `sha256:<64-hex>` | UOR Passport canonical format |
| **Hex** | 64-char hexadecimal | Diagnostic / cross-system comparison |
| **Braille glyph** | 32-char Unicode (U+2800 + byte) | Human-visible compact form |
| **IPv6** | (truncated representation) | Routing-layer addressing |

The same UOR address has all five of these forms simultaneously. Each is a re-encoding of the same 32 underlying bytes. Picking which form to display depends on the audience and surface — the **address itself** is implementation-agnostic.
