# Slide: UOR — The Coordinate System the Agent Economy Has Been Missing

> **Slide-ready content + speaker notes.** Convert to actual slide in Figma/Keynote/Slides at Miami. The structure below assumes a **single slide** with optional **second "future unlocks" slide** if time permits.

---

## SLIDE 1 (primary, always show)

### Title
**PRISM / UOR — the coordinate system the agent economy has been missing**

### Opening line (display + speak together)
> *"GPS gave every point on Earth a unique address.*
> *PRISM gives every piece of digital information one too."*

### Visual (left/right split)

**Left half — what every triad gives you, today:**

```
  ┌──────────────────────────────────────┐
  │   any content                        │
  │      ↓ canonicalize                  │
  │   bytes → SHA-256 → ring element     │
  │      ↓ engine.triad()                │
  │   ╔══════════════════╗               │
  │   ║   datum          ║   identity    │
  │   ║   stratum        ║   magnitude   │
  │   ║   spectrum       ║   structure   │
  │   ╚══════════════════╝               │
  │      a unique coordinate             │
  │      for every value, ever           │
  └──────────────────────────────────────┘
```

**Right half — three properties that flow from this:**

| Property | What it gives the protocol |
|---|---|
| **Universal addressing** | Two systems with different schemas resolve identical values to the same coordinate. No translation layer. |
| **Closed algebraic space** | Operations stay inside the space. Computational confinement is *structural*, not just tested. |
| **Content-addressed certs** | Every computation produces a deterministic certificate. Verifiable independently — no re-running. |

### Bottom strip (the punchline)

> **AgentLevy uses UOR today as the audit-trail substrate for KYC settlement.**
> **Tomorrow it's the substrate for any verifiable agent work, on any chain, in any domain.**

---

## SLIDE 2 (optional second slide — "what UOR unlocks") — show only if time permits

### Title
**What UOR unlocks beyond AgentLevy**

### Six concrete unlocks

| # | Unlock | What it means in practice |
|---|---|---|
| **1** | **Cross-domain compliance composition** | Bank pulls KYC from one agent, sanctions from another, beneficial-ownership from a third — all resolve to the *same* PRISM coordinates. Compose certs across domains without reconciling schemas. |
| **2** | **Model-agnostic interoperability** | Different LLMs (Anthropic, OpenAI, open models) reasoning about the same document produce comparable certs. *Algebraic distance* between coordinates, not vibes. |
| **3** | **Long-lived audit trails** | A cert from 2026 is still verifiable in 2036. The algebra is invariant. Critical for regulatory tail (financial records, court evidence, medical disclosures). |
| **4** | **Standards-grade portability** | UOR-Framework is formalized in Lean (theorem prover), published as JSON-LD, Turtle, OWL. Off-the-shelf semantic-web tooling can reason about UOR data. Not a proprietary format. |
| **5** | **Cross-chain settlement** | UOR coordinates are chain-agnostic. XRPL today; Sui, Solana, Ethereum tomorrow without rewriting the protocol. The settlement layer is swappable below the substrate. |
| **6** | **Computational confinement for safety-critical AI** | Provable bounds on what an agent can produce — medical, legal, defense use cases require *structural* guarantees, not testing. UOR's closed-space property gives this. |

### Bottom strip

> *"AgentLevy demos KYC settlement on XRPL. The substrate underneath is universal —*
> *not domain-specific, not chain-specific. We ship the first production application;*
> *the next dozen follow without us."*

---

## Speaker notes

### What to say if you have only 30 seconds on UOR (Slide 1 only)

> *"Underneath AgentLevy's settlement layer sits a content addressing primitive called PRISM, an implementation of the UOR Foundation's algebra. Every cert, every input, every output gets a unique triadic coordinate — datum, stratum, spectrum. Same content, same coordinate. Always. The reason this matters: the audit trail isn't just a log file. It's a coordinate space. Anyone, anywhere, computing on the same content arrives at the same address. That's what makes our certs verifiable from public keys alone."*

### What to say if you have 90 seconds (Slide 1 + 2)

> *"Underneath the settlement layer sits PRISM — a content addressing primitive from the UOR Foundation. Think of it as GPS for digital information.*
>
> *Every value, regardless of size or format, gets a unique three-coordinate address: identity, magnitude, structure. Same content always lands at the same address. Different content always lands at different addresses. The algebra is closed and proven — there's a Lean formalization in their public repo.*
>
> *That's what we use today. The audit trail of an AgentLevy settlement isn't a JSON log; it's a coordinate chain. Verifiable from public keys alone, without trusting any agent.*
>
> *What it unlocks beyond our demo: any compliance task across domains can compose, because everyone's working in the same coordinate space. Different LLM vendors produce comparable certs because the coordinates don't care who reasoned. Long-lived audit trails because the algebra is invariant — a 2026 cert is still verifiable in 2036. Cross-chain settlement because the coordinates are chain-agnostic.*
>
> *We're not just building a KYC demo on XRPL. We're shipping the first production-grade agent settlement protocol that uses universal content addressing. The next dozen follow without us."*

### Q&A bait this slide intentionally sets up

| Likely Q | Speak this answer |
|---|---|
| *"Is UOR your invention?"* | "No — UOR is from the UOR Foundation, MIT-licensed, formally proven in Lean. PRISM is their Python implementation. We're the first production application to a settlement protocol. Their work, our integration." |
| *"Why not just use a hash?"* | "Hashes are 1-D — collision-resistant, but no structure. UOR coordinates are 3-D — algebraically meaningful. You can measure distance between two values, you can reason about transformations as algebraic operations, you can prove computational confinement. A hash gives you 'are these the same?' UOR gives you 'how related are these and is this transformation provably bounded?'" |
| *"Why does the algebraic structure matter for KYC?"* | "For the demo it's about cryptographic chain integrity. For the longer roadmap it's about model-agnostic semantic comparison — when two different LLMs extract beneficial ownership, you can measure how close their answers are in coordinate space, instead of doing fuzzy string matching. That's the unlock for AI interoperability across vendors." |
| *"What about quantum-resistance / future-proofing?"* | "UOR's algebra is bit-level over a finite ring; SHA-256 is the bridge but it's swappable. If SHA-256 is ever broken, the substrate moves to a quantum-resistant hash with no protocol change. The coordinates and the algebra survive." |
| *"Sounds abstract — what's the concrete benefit today?"* | "Concretely today: our certs are deterministic, content-addressed, cross-system comparable, and small (4 bytes of datum + a few bytes of stratum/spectrum). A judge or regulator with our public keys can verify the entire chain in milliseconds, without any of our infrastructure. That's what 'universal coordinate system' delivers in practice." |

### What NOT to say (anti-patterns the slide protects you from)

- **Don't claim PRISM/UOR as your invention.** Always cite the UOR Foundation. Builds credibility (you read the spec) and avoids the inevitable "this isn't really yours, is it?" sucker punch.
- **Don't oversell the future unlocks as guaranteed.** Frame as roadmap and adjacent possible, not as "we will deliver this in Q3." Saying "this composes with X" is honest; saying "we will integrate X by next year" creates a commitment you may not keep.
- **Don't get into the algebra in detail on stage.** "GPS for data, three coordinates, closed space, algebraically proven" is the depth that lands. Anything deeper goes in Q&A or the README.
- **Don't compare PRISM to embeddings.** They're different things (embeddings are statistical/learned; UOR coordinates are algebraic/deterministic). If asked, say "complementary — embeddings give you semantic similarity, UOR coordinates give you cryptographic identity. Both can compose."

## Visual design notes for slide creator

- **Color**: PRISM brand cover image at `~/prism/docs/cover.png` is a good visual reference for color palette (likely deep blues + spectral accents).
- **Triadic visual**: the three-coordinate breakdown (datum/stratum/spectrum) is the strongest visual anchor. Could be three concentric rings, three axes of a 3D plot, or three intersecting circles. Avoid making it look like a Venn diagram (the three are *constraints*, not *overlapping sets*).
- **Avoid**: walls of text, code blocks, or the 64-line `prism.py` snippet. The slide is about *what UOR is for the audience*, not *how it works under the hood*.
- **Citations footer**: small text on the slide should credit "PRISM/UOR Foundation, MIT" with a URL — defends against "did you ask permission?" questions and signals open-source maturity.

## References to embed in slide footer

- UOR Foundation: https://uor.foundation
- PRISM repo (MIT): https://github.com/UOR-Foundation/prism
- UOR-Framework (Rust + Lean ontology, MIT): https://github.com/UOR-Foundation/UOR-Framework
- AgentLevy uses: PRISM @ commit `6cafdac`, vendored at `vendor/prism.py`
