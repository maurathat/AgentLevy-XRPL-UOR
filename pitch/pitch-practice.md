# Pitch practice — Internet of Agents Build Day (May 16, 2026)

> Private prep document for the AGI House hackathon pitch. Not for the slide deck. Not for publication. Live reference while practicing — read it three times, internalize the structure, then put it down on stage.

---

## The event

| Field | Value |
|---|---|
| Date | Saturday, May 16, 2026 |
| Hours | 10:00 AM – 10:00 PM Pacific |
| Location | 1868 Floribunda Ave, Hillsborough, CA 94010 (AGI House) |
| Theme | *"The web is still built for humans, not agents. Soon, for every human, there will be 100 agents using the internet. The internet isn't ready."* |
| Suggested topics | AX (Agent UX), simulations / RL environments, **x402 and agentic payments**, agent auth, computer use agents |
| Pitch slot length | 5–7 minutes based on AGI House YouTube precedent — confirm Saturday |
| Prizes | 🥇 $5K (Coframe) · 🥈 $3K (OpenHome) · 🥉 $2K |
| Rule | All attendees must ship code |

Schedule:

| Time | What |
|---|---|
| 10:00 | Doors open |
| 11:00 | Welcome to AGI House |
| 11:05 | Keynotes (Josh Payne / Div Garg / Nischal Nadhamuni / secret guests) |
| 12:00 | Project proposals from hackers — *use this 2-min slot to plant the RoyaltAI name* |
| 12:30 | Hacking begins |
| 16:00 | Project check-in |
| 18:00 | Dinner |
| **20:00** | **Demos** |

---

## Who's in the room — intelligence

### Keynote speakers (likely judges)

| Person | Company | What they care about | What lands with them |
|---|---|---|---|
| **Josh Payne** | Coframe (host, $5K prize) — AI platform that auto-generates and tests website variants. **Co-developed UI code-gen model + benchmark with OpenAI.** Customers: Replit, StartEngine, LaunchDarkly, MasterClass. SOC 2 Type II. | Agents generating brand-controlled UI artifacts; per-variant attribution as a revenue event; co-developer relationship with OpenAI means he understands LLM economics from both supply and demand sides | Position RoyaltAI as the cryptographic identity layer underneath AI-generated brand artifacts. Winning variants = on-chain provenance + creator-royalty-routable. *"Every variant that wins is a row in Coframe's database today. If it carries a UOR address, it's cryptographically attributable, reusable across customers, and royalty-routes to whichever agent created it."* |
| **Div Garg** | AGI Inc. (The AGI Company) — **on-device superintelligence**, fully-private local-running agents. Product is **AGI-0** ("personalized proactive AI co-worker on your smartphone"). Investors: Menlo, Point72, **Visa**, Qualcomm, Lenovo. Pivot from MultiOn's cloud computer-use thesis. | On-device agents that need to pay external services without having credit cards. Visa being in cap table = payment infrastructure is in his investor thesis. | **On-device agents have a structural settlement problem.** Subscriptions don't work; the device can't hold a card. Per-call payment with cryptographic receipts is the only viable rail. RoyaltAI is the protocol underneath. *"Your phone holds a wallet, the wallet pays per call, the cert proves what the agent did so the user can audit their own agent's behavior."* |
| **Nischal Nadhamuni** | Klarity — **workflow intelligence platform** (NOT contract review — that's a different YC Klarity). Products: AI Companion (passive workflow monitoring), AI Interviewer (surfaces tribal knowledge), AI Intake (ingests SOPs), Process Index. Customer example: DoorDash, 3,800+ processes indexed in 14 weeks. SOC 2 Type II. YC S18, Forbes 30U30 AI 2025. | Cryptographic substrate for **process-execution audit** — when AI agents execute the workflows Klarity indexes, the audit trail needs to be externally verifiable, not just rows in Klarity's database. | *"Klarity tells you what your processes are. If AI agents are executing them, the audit trail needs to be cryptographically verifiable — not just vendor-logged. RoyaltAI's cert chain proves the process actually ran with the expected inputs and outputs. Klarity discovers the workflow; we prove the execution."* |
| **Cory Waddingham** | Principal/Staff TPM, Platform & Infrastructure (GenAI, Cloud, Enterprise Systems) | Production-grade infra, scalability, operational rigor | The 154-test suite, byte-identity verification, the standards-author position. He's the *"does this actually run?"* judge. |
| **Secret guests** | Unknown | — | Don't pre-commit to a guess; stay flexible |

### Sponsors

| Sponsor | Who they are | What they care about | How to position |
|---|---|---|---|
| **Coframe** | Host. Silver Sponsor. $5K prize. AI platform auto-generating + testing website variants. **OpenAI co-development partnership.** Customers Replit, StartEngine, LaunchDarkly, MasterClass | Per-variant attribution as a revenue event; AI-generated brand artifact economics | You're aligned — RoyaltAI is the cryptographic identity layer for AI-generated brand artifacts. Variant winners as content-addressed receipts, creator-royalty-routable |
| **Khosla Ventures** | Top-tier early-stage VC, technically deep, category-defining theses. **Invested in Guild.ai** (see Guild row below — they're on the agent-control-plane thesis already) | Billion-dollar TAM frames, protocol-level defensibility, mechanism elegance | Lead with mechanism, not Bloomberg-framing. *"You backed Guild.ai for the governance plane. RoyaltAI is the settlement plane underneath — the layer that lets Guild's enterprise customers actually pass external audit"* |
| **Topology Ventures** | **$75M Fund I (Dec 2024), Casey Caruso** — ex-Google engineer, ex-Bessemer, ex-Paradigm. LPs include **Marc Andreessen, Bob Goodman, an OpenAI cofounder.** Miami Beach. Hands-on technical (built own AI CRM "Fiber"). Thesis: frontier-tech investors with deep technical understanding win | **Explicit thesis names: (a) "frameworks that facilitate multiple agents working together" — literally RoyaltAI; (b) "keep AGI open" — matches your CC0 standards posture** | **Most aligned investor in the room.** Lean into multi-agent coordination language + open-standards framing. Paradigm experience makes her allergic to thin token wrappers — emphasize that protocol stays open, no token, standards are the moat |
| **Nat Friedman** | Solo angel, ex-GitHub CEO, AI Grant founder, famously rigorous, prefers shipped code over slideware | Mechanism elegance, code that compiles on stage, honest founders | Lead with the working demo on a real ledger. He notices when something is real. He values intellectual honesty. |
| **HF0** | Hacker Fellowship — founder-focused accelerator | Technical founders shipping fast, depth over breadth, no fluff | The *"Foundation-adopted standard authored in weeks, working code on Mainnet"* arc is exactly their template |
| **OpenHome** | $3K prize. Voice-first agent platforms (home assistants, etc.) | Pay-per-call for autonomous voice agents, identity-bound usage | Mention voice agents in Q&A: *"a kitchen assistant calling Claude 50 times a day is the canonical agents-can't-subscribe problem"* |
| **Guild.ai** | **Enterprise agent control plane.** TypeScript SDK + Agent Hub marketplace + governance/audit for production agent fleets. Model-agnostic (OpenAI/Anthropic/Google). Investors include **GV, NFX, Khosla Ventures, Scribble, Theory, Webb.** | Their audit logs live in their database — not on-chain, not third-party-verifiable. They have a regulatory ceiling RoyaltAI doesn't. | **Channel partner, not competitor.** *"Guild's audit log lives in Guild's database. Useful for governance, insufficient for regulatory audit. RoyaltAI's cert chain lives on XRPL + Hedera — outside any vendor's platform. Same stack, different layer, no overlap."* |

#### The Guild.ai / RoyaltAI off-platform-audit comparison (memorize)

| Property | Guild.ai audit log | RoyaltAI cert chain |
|---|---|---|
| Storage | Guild.ai's database | XRPL + Hedera public ledgers |
| Verifiability | Requires Guild's API + your login | Anyone with public keys can verify |
| Persistence | Disappears if Guild shuts down | Survives any vendor going away |
| Regulatory grade | Enterprise governance use | Third-party-verifiable audit (FRE 902(13), EU AI Act, BIS) |
| Trust model | Vendor-trusted | Math-trusted |

This is the single sharpest framing the project has. **Guild.ai has a regulatory ceiling that RoyaltAI structurally doesn't.** Not because Guild is worse — because they're a different layer in the stack.

### Investor-composition takeaway (very important)

The combined sponsor lineup — **Khosla + Topology + Nat Friedman + HF0 + an OpenAI cofounder LP'ing Topology** — is one of the most technically sophisticated venture audiences a hackathon has ever assembled. They will get the mechanism. They will get the standards. They will get the dNFT.

**The challenge is not convincing them the agent economy is real.** Topology's thesis names multi-agent coordination explicitly. Khosla has already backed the agent-control-plane category (Guild). Nat Friedman has been writing checks into AI infra for two years. **The challenge is showing your specific implementation deserves the bet.**

That points to **mechanism first, business framing second.** Lead with the technical surprise (byte-identity vs Foundation MCP, three-witness audit, dNFT royalty), let the standards moat fall out as a natural consequence, save the TAM-and-Bloomberg framing for booth conversations.

---

## The pitch opening — first 30 seconds

Lead with the host's own framing. Coframe's site says *"for every human, there will be 100 agents using the internet."* Use that as the first sentence so the room feels seen, not lectured to:

> *"Coframe's site says 100 agents per human. If every one of those agents has its own Claude or OpenAI subscription, the economy collapses — subscriptions don't scale to autonomous buyers. If they share memory via content-addressed receipts, the economy works. I'm Maura Clark. I built **RoyaltAI** — pay-per-call AI inference with cryptographic royalty enforcement to model creators. Built on standards I authored that are now part of the UOR Foundation. Live demo, real ledger, watch."*

Then start the visual demo. The graph plays out behind you while you narrate.

### Alternative opening — Google searches frame

If the room feels skeptical or the Coframe framing has already been overused by previous pitchers, swap to this. Lands with anyone who's ever used the internet:

> *"Google handles 8.5 billion searches a day. The top 100 of them get asked millions of times — weather, news, login pages, conversions. When agents are the buyers instead of humans, the same long-tail concentration exists — except today every agent pays full price for the same answer. RoyaltAI changes that. First agent pays full price. Every subsequent agent shares the cached cert at a tenth the cost. The model creator earns royalty on every hit. Watch."*

### Third opening — MCP-native / multi-agent coordination (recommended primary for this room)

Given the actual investor composition (Topology's thesis explicitly names *"frameworks for multiple agents working together"*, Khosla backs the agent-control-plane thesis via Guild, Nat Friedman cares about mechanism), the **mechanism-first** opener probably lands hardest:

> *"I built the first MCP-native trust layer for agent commerce. Two MCP servers — one consuming the UOR Foundation's canonical reference, one exposing my own — share a content-addressed cert chain. Two agents can ask the same question, the second one pays a tenth as much, and the model creator gets paid royalty on both. Standards I authored, adopted by the UOR Foundation last week. Live demo, real ledger, watch."*

Lead with **infrastructure language** (*"MCP-native trust layer"*, *"content-addressed cert chain"*) over **business language** (*"Bloomberg for agent economy"*, *"$200B TAM"*). The room rewards the former, suspects the latter.

### Choosing between the three openers in real time

| Room signal | Use |
|---|---|
| You're 4th or 5th pitcher; Coframe framing already used; audience tired | **Google searches** — universal handle |
| Technical investors visible front-row (Topology, Nat Friedman, Khosla partner); engineers in audience | **MCP-native / multi-agent** — mechanism-first |
| First few pitchers; audience fresh; host front-and-center | **Coframe / 100 agents per human** — meets them where they are |

Practice all three. Pick on the walk to the stage.

---

## The 5–7 minute spoken structure

Time-coded beats. The dashboard provenance graph plays out behind you for the first ~3 minutes; the metrics panel + standards stack land in the last ~3 minutes.

| Time | What's on screen | What you say |
|---|---|---|
| 0:00–0:30 | Empty dashboard, all actor positions visible but inactive | The opening above (Coframe or Google framing). Land the name *RoyaltAI* by 0:20. |
| 0:30–1:30 | Agent A submits → XRPL payment edge animates → Anthropic node pulses → CERT materializes (Ruri blue) → Hedera anchor edge → UOR MCP verify edge → royalty edge to model NFT owner → Agent A balance updates | *"Agent A asks a question. Pays 0.010 XRP on XRPL — real ledger, real validated transaction, you can verify the txid. Server runs the inference, signs a cert with its keypair, anchors the cert on Hedera, splits the payment — half to the server, half to the model NFT owner. The model has a verifiable on-chain identity; the creator gets paid in the same atomic flow."* |
| 1:30–2:30 | Agent B submits → UOR address label flashes "MATCHES" → **CERT node flashes karakurenai** → Agent B edge labeled "0.001 XRP" → royalty edge fires again | *"Agent B asks the same question. Different wallet. They've never heard of Agent A. But the UOR address is identical, so the cert is already there. Agent B pays a tenth the price. Anthropic was not called — that's pure margin for the server. Model creator still gets royalty. Cache hits still pay the creator. That's the property that gets Anthropic to sign on rather than oppose this."* |
| 2:30–3:30 | Metrics panel populates: total inferences = 2, cache hit rate = 50%, XRP volume, royalty distributed. Sidebar shows recent events with timestamps. UOR Foundation MCPS receipt indicator lights up. | *"Three independent witnesses bind every cert. XRPL settles the money. Hedera consensus-timestamps the moment. UOR Foundation's MCP signs an ed25519 receipt that the address I computed matches their canonical reference. Trust level L1. No single vendor needs to be online for any of this to verify."* |
| 3:30–4:30 | Standards stack panel slides in: VTEAI · UOR-ADDR-1 · Prism framework | *"Underneath: VTEAI — verified-task-escrow standard, ERC draft, CC0. I authored it. UOR-ADDR-1 — content-addressing standard, officially adopted by the UOR Foundation this month. I authored it. Both standards sit on the Foundation's Prism framework — published Rust SDK on crates.io. Anyone who wants standards-aligned royalty enforcement implements specs I wrote on a substrate I contribute to. That's the long-term moat."* |
| 4:30–5:30 | Aggregate metrics + bloomberg-note panel | *"What you just saw is two inferences. Scale it to 100K a day across 50 model providers and you have a cryptographic agent economy with built-in royalty enforcement. Every query produces a content-addressed receipt. Every receipt is a row in a knowledge graph nobody has to maintain. Bloomberg for the agent economy. Three commercial vectors on the same substrate — settlement, analytics, and standards licensing."* |
| 5:30–6:00 | Final state lingering | *"The protocol is open. Code's on GitHub. Standards are CC0. I'm raising and hiring. Find me at the booth after."* |
| 6:00–7:00 | — | Buffer for delays, Q&A overflow, applause. |

Don't memorize this verbatim — internalize the beats and improvise the connective tissue.

---

## Live demo run-of-show (read this before every dry-run)

**The most important reframe:** the dashboard animation is *punctuation*, not content. The full 10-call flow takes ~20 seconds of motion total. Your narration is 4+ minutes. **Don't time your talk to the animation** — let the animation be a beat, then describe what's now visible.

### Two-batch structure (use this)

Don't run all 10 calls in one continuous sweep. Two button presses, ~90 seconds of narration in between:

```bash
# Batch 1 — single cache miss (whole pipeline lights up)
python3 scripts/run_inference_demo.py --total-calls=1

# [you talk for 60–90 seconds while the dashboard sits on the resulting state]

# Batch 2 — 9 cache hits (the climax)
python3 scripts/run_inference_demo.py --total-calls=9
```

Run them in separate terminal panes (or have both ready as up-arrow history) so you can fire each one without typing.

### Click-by-click choreography

| Phase | Time | What's on screen | What you do |
|---|---|---|---|
| **Setup** | 0:00–0:30 | Static dashboard, "awaiting first request" | Talk only. Land the opening hook. Land the name *RoyaltAI* by 0:20. |
| **Click 1** | 0:30 | — | Press Enter on Batch 1 command. Say *"watch."* |
| **Animation 1** | 0:30–0:35 | Payment edge → server → Anthropic → cert mints → HCS anchor → UOR receipt → royalty | **Be silent.** Let it land. Look at the audience, not the screen. |
| **Frozen state 1** | 0:35–2:00 | Cert visible, addresses populated, all witnesses lit | Walk the audience through what just happened. Point at each node. *"Cert is signed by the server. Address is byte-identical to UOR Foundation's reference computation — that's how someone in 2030 verifies this happened with no vendor in the loop. Hedera HCS sequence number is your tamper-evident timestamp. Royalty already moved to the model NFT owner — atomic with the payment."* |
| **Click 2** | 2:00 | — | Press Enter on Batch 2. Say *"Now watch what happens when nine more agents ask the same question."* |
| **Animation 2** | 2:00–2:15 | Nine rapid cache-hit pulses, payment edges flash, royalty edges fire, counter ticks 1→10 | Mostly silent. One throwaway line: *"watch the counter."* Or *"watch the royalty climb."* Let the visual carry it. |
| **Frozen state 2** | 2:15–3:30 | Final metrics: 90% hit rate, ~$0.0135 Anthropic saved, royalty distributed | The punchline. *"One Anthropic call. Nine reuses. 90% margin captured. Royalty enforced cryptographically — the model owner cannot be cut out, and no vendor needs to be online for the audit to verify."* |
| **Standards close** | 3:30–4:30 | Sidebar standards stack | *"Underneath: VTEAI — ERC draft, CC0, I authored it. UOR-ADDR-1 — Foundation-adopted this month, I co-authored. Prism framework on the UOR Foundation Rust SDK. The standards are the long-term moat — not the demo."* |
| **The ask** | 4:30–5:30 | Final state | *"Code is open, standards are CC0, I'm raising and hiring. Find me at the booth."* |
| **Buffer** | 5:30–7:00 | — | Q&A, applause, overflow. |

Total demo motion: ~20 seconds. Total narration: ~5 minutes. The animation is for *them*, not you.

### Three rules for live demo nerves

1. **Don't watch the animation while you talk.** Look at the audience. The animation is finishing for them. If you watch it, you'll race the clock.
2. **Click, then breathe, then talk.** A 2-second silence after each click feels much shorter to the audience than to you. Use it.
3. **If something errors, narrate the error.** *"Looks like the network's choppy — let me re-run it"* beats panicking. You have backup paths.

### Backup paths (if things break)

| Failure | Fallback | Time cost |
|---|---|---|
| Mainnet RPC slow / timing out | Flip `XRPL_INFERENCE_NETWORK='testnet'` in `.env`, restart server. Testnet has been bulletproof through dozens of runs. | ~30s recovery |
| Anthropic API rate-limited mid-demo | Server falls back to fixture response; cert still mints; story still works | invisible |
| Cloudflared tunnel down | Run on `127.0.0.1:8765`, judges crowd around your laptop. Booth is more intimate that way anyway. | none — switch to local URL |
| Total crash, can't recover | Phone screenshot of the final state. *"Here's what the dashboard looks like after a successful run — let me walk you through it."* You still have the story. | demo becomes a screenshot tour, but the message lands |

### What to verify in every dry-run

- Click → animation completes → metrics tick. If counter doesn't increment, hard refresh dashboard before the real run.
- 9-call batch finishes in <20 seconds. If slower, you'll need to talk faster or pre-set expectations.
- Bithomp link to your Mainnet wallet shows the actual transactions appearing as the demo runs (have one tab open as proof, judges may ask).

### What to say if a judge asks "is this on Mainnet?"

*"Yes. These are real XRPL Mainnet payments and real RLUSD moving. Wallets are funded with [$X total]; you can verify any transaction on Bithomp at [URL]. The reason I built it on Mainnet for the booth is precisely because Testnet demos let you handwave the real-money question. Royalty enforcement only matters if the money is real."*

---

## Hostile / likely questions + 30-second answers

Practice each of these out loud at least three times. If a question isn't here, the answer is *"Honest answer — I haven't thought through that completely. Let me give you the best version I have and follow up after."* Never bluff.

### On the business model

**Q: *"Isn't this just another web3 middleman taking a fee on every transaction?"***
A: The protocol takes zero. There's no token, no toll, no rent. The cert chain is public on XRPL and Hedera — anyone can read it. Revenue comes from the productized analytics layer (Kessai) on top, not from tolling the protocol. Same separation as Stripe and Visa — Stripe sells the dashboard and the integration, the networks underneath stay open.

**Q: *"Why would Anthropic or OpenAI agree to this rather than oppose it?"***
A: Three things. (1) They still get paid on cache hits via the dNFT royalty mechanism, so total revenue from the long tail goes *up*, not down. (2) It unlocks markets they can't reach — autonomous agents that don't have credit cards. (3) The enterprise compliance story (FRE 902(13)-admissible inference receipts) sells more Claude to Fortune 500 customers, and they don't have to build the audit substrate themselves.

**Q: *"What happens to your business if Anthropic ships their own caching layer?"***
A: They'll cover their own models. Cross-provider aggregation still needs neutral infrastructure. Multi-model royalty splits for fine-tunes still need a standard. Standards-aligned enterprise customers still implement the spec I authored. Anthropic shipping internal caching is the world I'm building infrastructure for — not the world that kills it.

**Q: *"What's the unit economics? Where does Kessai actually make money?"***
A: Three streams. (1) Per-inference settlement fee — small percentage at the protocol layer, the volume play. (2) dNFT minting onboarding — flat fee per model. (3) Enterprise SaaS for the analytics dashboard, compliance exports, and channel licensing to KYC vendors. Same pattern as Stripe's pricing — small fee on rails, premium on dashboard + integrations.

### On the technical

**Q: *"Why XRPL specifically?"***
A: Two reasons. Cost — XLS-20 dNFT + XLS-100 SmartEscrow are protocol-level primitives at $0.0002/tx, no custom contracts to audit. **Currency agnosticism** — the protocol can settle in native XRP (which the demo uses) or any IOU on XRPL including RLUSD (Ripple's regulated stablecoin on the same chain), USDC-on-XRPL, XSGD, etc. At inference scale, the cost matters; the currency choice is a deployment configuration. The protocol layer is also chain-agnostic via UOR-ADDR-1 binding adapters; XRPL ships first because the primitives are ready, Sui is the natural second chain for Move's resource-typed model assets.

**Q: *"Why use UOR addressing instead of just SHA-256?"***
A: It is SHA-256 underneath. UOR-ADDR-1 specifies the canonicalization rules — JCS-RFC8785 plus NFC normalization — so the same logical content produces the same address across implementations, languages, and ecosystems. The Foundation's Prism framework is the algebraic reference. Live byte-identity verified against `mcp.uor.foundation/encode_address`. If anyone in the room wants to test it during Q&A, they can.

**Q: *"How is replay resistance enforced?"***
A: The XRPL Payment carries a memo with the request's UOR address. The server only accepts a payment whose memo equals the address of the request being made. A payment for question A cannot unlock question B because the canonical bytes — and therefore the address — differ. We have a unit test specifically for this; happy to share the file.

**Q: *"Cache hits could serve stale or incorrect responses. How is freshness handled?"***
A: Requests canonicalize with an hour-bucket timestamp, so two queries within the same UTC hour collide; queries in different hours don't. That's the freshness SLA — configurable per deployment (could be 5 minutes, could be 24 hours). For non-deterministic LLM output, the cache trades determinism for cost — and the audit trail records exactly which cert produced each answer, so freshness is auditable rather than assumed.

**Q: *"What about the privacy implications of caching prompts publicly?"***
A: The cert stores the UOR address of the request, not the request itself. Recovering the prompt from the address is computationally infeasible — it's a SHA-256 hash. The completion preview is bounded to 120 chars in the cert; the full completion stays out of band. Sensitive prompts would canonicalize on per-user salt rather than a shared hour bucket — protocol supports it; that's a deployment configuration, not a protocol change.

### On the standards

**Q: *"What does Foundation adoption of UOR-ADDR-1 actually mean? Is this a real standards body or a side project?"***
A: UOR Foundation is a research foundation publishing peer-reviewable architectural specifications (arc42 + C4 + ISO/IEC/IEEE 15288 lifecycle docs). Their flagship project, the Prism framework, has a canonical Rust SDK on crates.io. They have a Sandbox → Incubating → Graduated lifecycle for proposed standards. UOR-ADDR-1 is in their org now alongside Prism. I'm a Foundation member and co-implementer with Alex Flom on the Rust reference. The exact same algebraic primitives ship in Hologram SDK and other UOR projects — this is not a side project.

**Q: *"Why should I believe these standards will get adopted broadly?"***
A: I shouldn't ask anyone to believe it on faith. The reference implementation exists, it's byte-identical to the canonical Foundation reference, and adoption is happening — UOR-ADDR-1 already shipped into the Foundation org with a Rust SDK and Lean 4 proofs. Adoption is upside; my position doesn't depend on it.

**Q: *"What if a fork of your protocol takes off instead of yours?"***
A: Forks of the protocol are encouraged — it's open. The standards-author position isn't forkable; the Foundation adoption is dated and public. The reference-implementation distribution head start is 12–18 months. Forks would have to either implement the standards I wrote (in which case they validate the moat) or break them (in which case they lose interoperability).

### On the team

**Q: *"Solo founder — how do you handle that?"***
A: The work shipped over the past 6 weeks is six weeks of building on three years of standards work that landed in the Foundation. The raise is for the team, not the discovery — two senior engineers, GTM, security audit, design. Solo at pre-seed is a stage, not a permanent posture. Foundation contributorship + working code is what I bring; capital plus introductions is what I'm asking for.

**Q: *"Who's the next hire?"***
A: A senior Python/TypeScript engineer for the SDK layer (the Foundation publishes Rust + Lean; I'm filling the Python and TS gap and want a senior IC to lead that). After that, GTM/BD for the first three enterprise pilots.

### On specific players in the room

**Q: *"How does this relate to Guild.ai?"*** (likely from Khosla partner since Guild is in portfolio)
A: Guild handles the agent control plane — deployment, governance, audit logs. RoyaltAI handles the settlement plane underneath. Guild's audit logs live in Guild's database. Useful for enterprise governance, structurally insufficient for regulatory audit because the auditor still has to trust Guild's database. RoyaltAI's cert chain lives on XRPL and Hedera — outside any vendor's platform, third-party-verifiable, persists if any single vendor goes away. **Channel partner, not competitor.** Their model-agnostic routing (OpenAI / Anthropic / Google) is exactly the case where cross-provider royalty aggregation matters.

**Q: *"How does this work for on-device agents like AGI-0?"*** (Div Garg's product)
A: On-device agents have a structural settlement problem. They run privately on the phone, so they can't hold a vendor's credit card or maintain a subscription. They need per-call payment with cryptographic receipts. RoyaltAI is the protocol underneath. The phone holds a wallet; the wallet pays per call; the cert proves what the agent did so the user can audit their own agent's behavior. Visa being in your cap table means this is in your investor thesis already — payment rails for autonomous agents.

**Q: *"How does this map to Coframe's variant testing?"*** (Josh Payne)
A: Every variant Coframe generates that wins is a row in your database. If that variant carries a UOR address, three things change: (1) it's cryptographically attributable across customers, not just within Coframe; (2) reuse routes royalty to whichever agent created the original variant, opening a creator-economy primitive; (3) the audit trail of which variant produced which conversion outcome is verifiable externally — useful for the brand-safety and attribution conversations enterprise customers want. Same product, different identity substrate underneath.

**Q: *"How does Klarity benefit?"*** (Nischal Nadhamuni — workflow intelligence, not contracts)
A: Klarity discovers and indexes enterprise processes. If AI agents are now executing those processes — and they increasingly will be — the audit trail of execution needs to be cryptographically verifiable, not just rows in Klarity's database. RoyaltAI's cert chain is that substrate. Klarity tells you what the process is; RoyaltAI proves the process actually ran with the expected inputs, the expected model, and the expected outputs. Process discovery + cryptographic execution audit = the complete story for regulated workflow automation.

**Q: *"What about OpenHome and voice agents?"*** (OpenHome sponsor — $3K prize)
A: A voice assistant in someone's kitchen calls Claude 50+ times a day to handle requests. Same structural problem as Div's on-device agents — the kitchen device can't hold a credit card, can't maintain a subscription, but it's doing real economic activity per call. Per-call payment with cryptographic receipts is the answer. The voice device holds a small wallet that the household funds; every call produces a receipt the household can audit; the model creator gets paid royalty on each call.

### On the market

**Q: *"What's the wedge customer for the first pilot?"***
A: Two-sided market. Supply: an independent fine-tuner or research lab with a commercially valuable model that wants royalty enforcement they can audit. Demand: an inference platform (Together AI, Replicate, an enterprise self-hosted gateway) that wants to differentiate on cryptographic billing. First three pilots target both sides simultaneously — one model on the supply side connecting to one inference platform on the demand side, demonstrating the cross-platform royalty aggregation property.

**Q: *"Aren't enterprise sales cycles too long for a pre-seed company?"***
A: That's why the wedge is mid-market (banks $1-10B AUM, fine-tune labs, agent platform infra) where procurement is 6-9 months not 24. Free-tier proof-of-concept is the foot in the door — one workflow, 30-day pilot, no commitment. Then SaaS subscription tiers above. Channel partnership with KYC compliance vendors is the parallel path that doesn't require us to do enterprise sales directly.

---

## Competitive landscape (Q&A only — never volunteer this)

> Your auto-memory says: *Kessai pitch deck excludes landscape — competitive landscape stays in Q&A prep only; don't propose adding it to the deck.* This section is for memorization, not slide use.

| Category | Player | One-sentence differentiator |
|---|---|---|
| Crypto x AI inference | **Bittensor** | Token-incentive model market; closest competitor on AI side but focused on incentivizing model improvement via tokens, not enforcing royalties to existing creators selling into traditional markets. Different go-to-market. |
| Crypto x AI inference | **Render Network**, **Akash** | Distributed *compute* marketplaces; don't address inference billing or model-creator royalty. Adjacent, not competitive. |
| Model marketplaces | **Hugging Face** | Vendor-trusted, centralized, no cryptographic royalty enforcement. We're what they should have been. |
| Agent commerce | **Virtuals Protocol (ACP)**, **Olas Network** | Platform-bound to specific chains (Base, Gnosis) and tokens. Token economics are marketplace primitives, not settlement primitives. AgentLevy is chain-neutral and token-free. |
| HTTP-layer payments | **Coinbase x402**, **Google AP2** | HTTP rails for per-request payments. We're at the cryptographic-settlement layer *below* them. Composable, not competitive — x402 could call RoyaltAI as its verifier. |
| Custodial crypto escrow | **Coinbase Commerce escrow** | Coinbase IS the trust anchor. The point of our protocol is removing the trust anchor. |
| DID / KYC | **Civic**, **Worldcoin**, **Moca AIR Kit** | Package user/agent *identity*. We package work-integrity *attestation*. **Moca AIR Kit is a partnership target**, not a competitor — UOR-ADDR-1 names it as the agent-identity primitive. |
| Web3 oracles | **Chainlink** | Trusted-oracle model. AgentLevy needs no oracle — the cert chain IS the oracle. |
| Vendor compliance | **LexisNexis**, **Refinitiv**, **Thomson Reuters** | Vendor-trust audit; architecture predates the cryptographic primitives. We sell math-trust audit. |
| AI governance | **Credo AI**, **Holistic AI**, **Datalogue** | Process tooling for AI teams. We provide the cryptographic substrate they could use as their audit format. Potential channel partner, not competitor. |

**The defensible bundle:** AgentLevy is the only protocol that solves usage tracking + royalty enforcement + cryptographic provenance + cross-platform aggregation *simultaneously*, sitting on a three-layer standards stack (Prism + UOR-ADDR-1 + VTEAI) where two of the three are mine.

---

## What NOT to say

- ❌ *"We're a small team"* — leaks insecurity. Say *"six weeks of building on three years of standards work"* instead.
- ❌ *"I'm a solo founder"* — same. The work speaks. Mention solo-stage only if directly asked.
- ❌ *"We take a cut of every transaction"* — false and dilutes the standards-author moat. Protocol takes zero.
- ❌ *"This is a token play"* — actively contradicted by the deck. Standards stay open; commercial layer is SaaS.
- ❌ *"At scale, our infrastructure costs are…"* — don't get drawn into capacity-planning conversations. Say *"Phase 4 of the roadmap covers Merkle aggregation; cost-per-tx is never the binding constraint"* and move on.
- ❌ *"Anthropic could just build this"* — defensive framing. Even if they do, the cross-provider story stands.
- ❌ Any apology, hedge, or qualifier in the first 30 seconds. Just deliver the opening line clean.

---

## Memory-seeder business model (Q&A bonus)

Useful as a confident answer to *"what other businesses does this enable?"*:

> *"The natural follow-on is memory-seeder agents — services whose job is to pre-cache the predictable head of the agent-query distribution. Think Google Trends, but for what agents ask. The seeder pays full price for the first inference of each popular query; they earn royalties from every cache hit downstream. New role in the economy, same protocol underneath. The mechanism is already supported by the dNFT royalty split — production deployment of that variant is in the Phase 3 roadmap."*

---

## Research-paper / content-integrity verification (Q&A bonus)

The protocol is **content-agnostic** — inference is just the first application. The same SHA-256 + JCS canonical-bytes pipeline that addresses an inference request also addresses a research paper, a contract, a piece of model training data, a regulatory filing. UOR-ADDR-1 doesn't care what the bytes are.

This is the strongest extension to mention on stage because it lands especially hard with:

- **Nischal Nadhamuni (Klarity)** — workflow intelligence buyers need cryptographic proof their indexed documents haven't been modified between submission and audit
- **Anyone aware of the AI-IP-litigation wave** — NYT v. OpenAI, Getty v. Stability, Disney v. Midjourney all turn on *"what content existed at what moment."*

### The mechanism (same primitive, different content)

| Step | What happens |
|---|---|
| 1. Content | A paper, contract, training-data file, regulatory filing — anything canonicalizable to bytes |
| 2. Compute UOR address | `sha256(JCS(content))` — the exact same operation as for an inference request |
| 3. Anchor on-chain | Author / publisher posts an XRPL Payment with the address in memo, or a Hedera HCS message. The cert chain can sign an attestation as well. |
| 4. Verify any time later | Anyone holding the document recomputes the address locally, compares to the on-chain anchor. Match = unaltered. Mismatch = tampered. **No vendor needs to be online.** |

The on-chain anchor outlives the original publisher, archive, vendor, or even the specific chain (UOR-ADDR-1 is chain-agnostic). FRE 902(13) admissible without testimony.

### Two Q&A answer variants

**General:** *"What else does this enable beyond inference?"*

> *"The protocol is content-agnostic. Inference is the first application — same SHA-256 over JCS-canonical bytes addresses any document. Picture every paper you cite getting a UOR address that goes on-chain at publication. Three years later, opposing counsel claims the paper was modified — you recompute the address from your copy, point at the on-chain record, done. The same primitive that lets agents share memory makes 'this is the version I trusted' a cryptographic fact, not a vendor's claim."*

**Klarity-flavored** (for Nischal specifically):

> *"Klarity discovers processes. A natural follow-on for your workflow customers: every regulated document — KYC submission, board-approved policy, training data manifest — gets a UOR address at the moment of approval. The cert chain anchors it. Years later, an auditor or regulator computes the address from their copy of the document, checks the on-chain anchor, knows whether it's the version that was approved. **Same primitive that proves the AI ran correctly proves the document wasn't tampered with.** Process-discovery + cryptographic execution audit + content integrity, one substrate."*

### Build status — Phase 2, not Saturday

Buildable as a `POST /verify-document` endpoint on top of the existing protocol — ~60-100 LOC of new code (file canonicalization → SHA-256 → cross-check against cert store + Foundation MCP + on-chain anchor → return verification result + signed receipt). **Don't ship before Saturday.** Mention as roadmap when asked. Demonstrate at Series A.

---

## Pre-demo checklist (Friday May 15 + Saturday morning)

### Friday evening

- [ ] Set `INFERENCE_SERVER_ED25519_SEED_HEX` in `.env` (generate via `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Confirm `XRPL_RPC_URL` (Mainnet for stage; Testnet for rehearsal), `INFERENCE_USE_XRP_FALLBACK=true` (settles in native XRP), `ANTHROPIC_API_KEY` set
- [ ] Fund 4 wallets: agent A, agent B, server, model owner — each ~12 XRP for reserve + buffer
- [ ] *(skipped — demo settles in native XRP, no IOU faucet or trust lines needed)* ~~Acquire RLUSD~~
- [ ] Confirm all 4 wallets hold ≥ 10 XRP (Testnet faucet auto-funded ~100; Mainnet you fund from an exchange — ~12 XRP per wallet covers reserve + payments + headroom)
- [ ] Run `python scripts/mint_model_nft.py` — populates `MODEL_NFT_ID` + owner address in `.env`
- [ ] Run `python scripts/run_inference_demo.py` end-to-end — confirm it completes without errors
- [ ] Open `http://localhost:8765/dashboard` in a browser — confirm the graph animates correctly during the demo
- [ ] Take screenshot of working dashboard for backup if Wi-Fi fails on stage
- [ ] Three dry-run pitches in front of a mirror (or recording)

### Saturday morning (before doors)

- [ ] 15 min on Topology's website — one-sentence summary memorized
- [ ] 15 min on Guild.ai's website — one-sentence summary memorized
- [ ] Check AGI House YouTube for one recent pitch to confirm exact slot length
- [ ] Final dashboard dry-run, then close browser tab so the demo opens fresh
- [ ] Charge laptop fully; carry power adapter
- [ ] Have the demo's expected duration timed (CLI run-through ~45s, narration overlaps the rest)

### Saturday at venue

- [ ] Project test once between 4:00 check-in and 8:00 demos — projector resolution / aspect ratio
- [ ] Browser zoom set to fit projector (likely 90-100%)
- [ ] Confirm "Do Not Disturb" mode on laptop — no notifications during pitch
- [ ] One physical backup: printed one-pager with QR codes to GitHub + the live demo URL

---

## Handoff materials (carry to the venue)

- **One-liner for the badge:** *"Maura Clark — RoyaltAI · UOR Foundation member · pay-per-call AI inference with cryptographic royalty"*
- **Repo URL:** `github.com/maurathat/AgentLevy-XRPL-UOR`
- **Standards repo:** `github.com/UOR-Foundation/uor-addr-1`
- **Live demo URL (post-deploy):** TBD — write on cards
- **Contact:** enterpriseroofing@gmail.com (per user memory)

---

## After the demo — landing the conversation

When someone walks up to the booth:

| They say | You say |
|---|---|
| *"That was interesting."* | *"What part stood out?"* — let them name the angle they care about; tailor follow-up |
| *"How do I try it?"* | Point to the GitHub repo. Offer to onboard them as a pilot inference platform if relevant |
| *"How can I help?"* | Three asks: introductions to inference platforms / fine-tune labs, capital, or a senior Python/TypeScript engineer |
| *"How is this different from [competitor]?"* | Use the landscape table above. **Never volunteer competitive comparisons** — only when asked |
| *"Are you raising?"* | Yes — pre-seed, $1–2M target, 12-month runway, three pilot conversion. Ask for their preferred follow-up channel |

### Judge / sponsor-specific booth one-liners

These are higher-leverage — pre-loaded for the specific people most likely to walk up:

**If a Khosla partner walks up:**
> *"You backed Guild.ai for the agent control plane. RoyaltAI is the settlement plane underneath. Guild's audit log lives in Guild's database — that's enterprise governance. RoyaltAI's cert chain lives on XRPL and Hedera — that's regulatory-grade audit that exists outside any vendor's platform. Same stack, different layer, no overlap. Their enterprise customers gain external-auditable receipts; you get a portfolio piece that fills the regulated-vertical gap."*

**If Casey Caruso or anyone from Topology walks up:**
> *"Your thesis names frameworks for multiple agents working together. That's exactly what I built. Standards stay open — UOR-ADDR-1 was adopted by the Foundation last week, CC0, I co-authored it. The protocol is the moat, not a token, not a network effect. The Bessemer + Paradigm pattern recognition you have for protocol-author positions is what I'm trading on."*

**If Josh Payne walks over:**
> *"You're already generating winning variants with Coframe. RoyaltAI is the cryptographic identity layer for those variants. Each one carries a UOR address; reuse across your customer base routes royalty back to the generating agent. The OpenAI co-development relationship you have for the code-gen model is exactly the supply-side relationship the dNFT royalty mechanism is built for."*

**If Div Garg comes by:**
> *"On-device agents at AGI-0 have a structural settlement problem — your phone can't hold a credit card. Per-call payment with cryptographic receipts is the only viable rail. RoyaltAI is the protocol. Visa being on your cap table tells me this is already in your investor thesis."*

**If Nischal Nadhamuni stops by:**
> *"Klarity discovers what enterprise processes are. RoyaltAI proves they ran correctly. When AI agents start executing the workflows you index, the audit trail needs cryptographic provenance, not database rows. Process discovery + cryptographic execution audit — that's the complete loop for regulated workflow automation."*

**If Nat Friedman comes by:**
> *"Live demo, real ledger, 154 tests passing, byte-identical verification against the canonical Foundation MCP. I'd rather show you the code than pitch it. Want to look at the cert builder?"*

**If anyone from OpenHome:**
> *"Voice agents in a kitchen have the same agents-can't-subscribe problem as on-device agents. Per-call payment is the only rail. Want to talk integration?"*

**If anyone from HF0:**
> *"Six weeks of building on three years of standards work. Foundation adoption last week. Working code on Mainnet by demo time. That arc is your template, not the exception."*

---

*Last updated: 2026-05-14 (post-research pass on Klarity, Coframe, AGI Inc., Guild.ai, Topology). Update Saturday morning if anything material changes (sponsor lineup, pitch slot duration, secret guest reveals).*
