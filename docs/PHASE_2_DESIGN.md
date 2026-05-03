# Phase 2 Design — fill in on the plane, build from on Day 1

> **Use this doc.** Each section has questions and pre-filled answers from Phase 0 / `MIGRATION_NOTES.md`. Where there's a `TODO` marker, you decide. Decisions made on the plane unblock the Day 1 build at Consensus. Don't code on plane wifi — write decisions here, commit when you land on solid wifi.

## Compressed Phase 2 timeline (revised for Consensus arrival)

Original plan: 3 days (May 2–4) before Miami. Reality: 2 days at Miami before submission.

| Day | Morning | Afternoon | Evening |
|---|---|---|---|
| **May 5 (Day 1)** | Primitives: canonical, fingerprint (done), task_spec, cert, signing | LLM stack: client, cache, schemas, prompts | Agents + negotiation + end-to-end local demo |
| **May 6 (Day 2)** | XRPL escrow Path B (legacy), then Path A WASM if time | Polish, record backup video | Pitch rewrite informed by Vegas Q&A |
| **May 7 (Day 3)** | Submit | Pitch | — |

Aggressive but doable because all foundations are tested. The hard parts that usually steal 30% of a hackathon (LLM API auth, network endpoints, dependency conflicts, canonical-form drift) are already resolved.

---

## 1. KYC service narrowing — 5 → 2

Old AgentLevy had 5 generic services (sentiment-analysis, data-extraction, code-review, translation, data-validation). For the AgentLevy-XRPL-UOR demo we narrow to KYC-specific.

**Decision: 2 services**

- `kyc.beneficial_ownership_verify` — extract beneficial owners + percentages from a corporate disclosure document. Output: structured list of owners.
- `kyc.sanctions_screen` — given a list of names from beneficial ownership extraction, screen against a (synthetic) sanctions list. Output: signed attestation per name.

**Why two:** the demo's punchline is *subcontracting* — the compliance agent does ownership extraction, then subcontracts sanctions screening to a second agent, producing a nested derivation cert chain. Single-agent demos don't show the protocol value; three-agent demos cost too much to wire under deadline.

---

## 2. VTEAI vocabulary alignment

`pitch/VTEAI-DRAFT.md` defines protocol-layer types we should mirror. **Read it on the plane**, then fill in below:

```
TaskSpec fields VTEAI defines:    [TODO read VTEAI, list them]
ProofPayload fields VTEAI defines: [TODO]
VerificationSpec strategies:       [TODO]
```

**For each VTEAI field we need to decide:** keep verbatim / extend / replace.

**Default:** keep names verbatim where the semantics match. Extending the names with `prism_` or `xrpl_` prefixes only when needed to disambiguate.

The pitch line this enables: *"AgentLevy-XRPL-UOR is the canonical XRPL implementation of VTEAI, with content-addressed PRISM derivation certificates as the attestation layer and XLS-100 SmartEscrow as the verifier."*

---

## 3. TaskSpec Pydantic model

Per Phase 2.1 of the original plan plus VTEAI alignment. Fields:

```python
class TaskSpec(BaseModel):
    task_id: UUID                              # unique identifier
    task_type: Literal["kyc.beneficial_ownership_verify", "kyc.sanctions_screen"]
    inputs: list[InputRef]                     # list of {description, content_triad: Triad}
    expected_output_schema: dict               # JSON Schema describing the output shape
    price_drops: int                           # XRP drops; we settle in XRP for the demo
    seller_pubkey: bytes                       # Ed25519 public key, 32 bytes
    buyer_pubkey: bytes                        # Ed25519 public key, 32 bytes
    deadline: datetime                         # UTC, ISO 8601 in canonical form
    signature_buyer: bytes | None = None       # Ed25519 sig over canonical bytes, set when buyer signs
    signature_seller: bytes | None = None      # ditto, set when seller countersigns
    # Computed at sign-time:
    spec_triad: Triad | None = None            # PRISM triad of canonical bytes (excluding signatures)

    def to_canonical_bytes(self) -> bytes:
        # Strip signatures + spec_triad before canonicalizing.
        # Implementation in agentlevy/primitives/canonical.py.
```

**Decisions to confirm on the plane:**

- [ ] Do we settle in **XRP** or **RLUSD**? (Demo simpler in XRP; pitch stronger if RLUSD.) Default: **XRP** for Day 1; revisit Day 2 if time.
- [ ] Are signatures **detached** (separate field) or **embedded** (inside the canonical bytes)? Default: **detached** — canonical bytes are computed from everything *except* signatures.
- [ ] Is the `spec_triad` stored on the model or always recomputed? Default: **stored when signed**, but always recomputable from canonical bytes (this is a cache, not authority).

---

## 4. DerivationCert Pydantic model

```python
class DerivationCert(BaseModel):
    cert_id: UUID
    task_spec_triad: Triad                     # which spec governed this work (back-reference)
    input_triads: list[Triad]                  # what inputs the agent actually consumed
    output_triad: Triad                        # PRISM triad of the produced output
    operation_description: dict                # structured: {"operation": "beneficial_ownership_extract",
                                               #              "inputs_described": [...], "outputs_described": [...]}
    subcontract_certs: list[UUID] = []         # nested cert IDs if work was subcontracted
    seller_pubkey: bytes
    signature: bytes                           # Ed25519 over canonical bytes
    timestamp: datetime
    # Self-referential triad: cert's canonical bytes also have a triad
    cert_triad: Triad | None = None

    def to_canonical_bytes(self) -> bytes: ...
```

**The key invariant:** anyone with `(buyer_pubkey, seller_pubkey, sanctions_pubkey, final_cert)` can verify the entire chain — every signature, every triad reference resolves, every operation_description matches the schema. No agent is trusted; the math is.

---

## 5. Canonicalization form

Already documented in `CANONICAL_FORM.md`. **Decision recap:**

- One module: `agentlevy/primitives/canonical.py`. Single function `to_canonical_bytes(obj) -> bytes`.
- Approach: **JCS-adjacent** — `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. Full RFC 8785 JCS only if a Day 1 test surfaces a number-formatting drift.
- Pydantic: each model exposes `to_canonical_bytes()` that calls `canonical.to_canonical_bytes(self.model_dump(mode="json"))` after stripping signature fields.
- Bridge: `agentlevy/primitives/fingerprint.py.content_to_ring_element()` (already written, Phase 0) + `agentlevy/prism_layer/triad.py.compute_triad()` (Day 1).

No decisions to make. Just execute.

---

## 6. Negotiation protocol

Bounded turns to keep the LLM convergence demo-stable.

**Decision: 4 turns max**

1. **Buyer → Compliance**: `request` containing draft TaskSpec (no signatures yet)
2. **Compliance → Buyer**: `accept` (signs) OR `counter` (modifies price, deadline, or expected_output_schema)
3. **Buyer → Compliance**: `accept` (signs) OR `cancel`
4. **Both sign** → spec is live, work begins

Hard cutoff at turn 4. If no agreement by then, demo prints "negotiation failed" and exits gracefully (this is a feature, not a bug — the audit trail of failed negotiations is itself valuable).

---

## 7. System prompts (sketch)

Each agent prompt fits in ~10 lines plus the tool schema. Sketch them on paper / here, refine on Day 1.

**Buyer agent**

```
You are the buyer agent in an AgentLevy KYC compliance task. Your role is to
write a clear TaskSpec describing the compliance work needed. You do NOT
perform the work; you only specify it.

Given a brief from the user, produce a TaskSpec by calling the
`propose_task_spec` tool. Include: task_type, inputs, expected_output_schema,
price_drops, deadline.

If the brief is too vague to specify, return {"status": "decline",
"reason": "..."} via the decline path. Never hallucinate fields.
```

**Compliance agent — negotiation**

```
You are the compliance agent in an AgentLevy KYC task. The buyer has sent
a TaskSpec. Your role is to either accept it (call `accept_spec`) or
counter-propose modifications (call `counter_spec` with specific field changes
and brief justifications).

Counter only if: price is below your stated rate, deadline is unrealistic,
or expected_output_schema is incompatible with what you can produce. Do not
counter on style preferences. Maximum one counter per negotiation.
```

**Compliance agent — execution (beneficial ownership)**

```
You are extracting beneficial ownership from a corporate disclosure document.
Read the document, identify all beneficial owners with >= 25% stake, and call
the `record_beneficial_ownership` tool with structured results.

If the document is incomplete or ambiguous, decline via the standard decline
path. Do not infer owners not explicitly named in the document. Sum of
ownership_percent should equal 100% unless the document indicates otherwise.
```

**Sanctions agent**

```
You are the sanctions screening agent. Given a list of names, screen each
against the provided synthetic sanctions list (passed in the tool schema).
Return a signed attestation per name via the `record_sanctions_screen` tool.

For each name produce: name, match_status (clear / partial_match / direct_match),
match_details (if any), confidence_score. Be conservative — flag partial
matches rather than hiding them.
```

**Decisions to make:**
- [ ] Are these prompts OK or do you want to tweak the persona / constraints?
- [ ] Synthetic sanctions list: how many entries? **Default: 10** (3 are designed to match, 7 are noise).

---

## 8. Synthetic data plan

Per the original plan: no real OFAC data, no real KYC docs.

**Decision: synthetic fixtures (1-2 KB each)**

- `fixtures/synthetic/acme_holdings_disclosure.txt` — a fake 1-page corporate disclosure with named beneficial owners
- `fixtures/synthetic/global_bvi_inc_disclosure.txt` — a second fake disclosure with one name that matches the synthetic sanctions list (drives the *interesting* demo case)
- `fixtures/synthetic/sanctions_list.json` — 10-entry list of fake names. 3 designed to partial- or direct-match.

**Decision to make on plane:**
- [ ] Do you want me to draft these fixtures Day 1 morning, or do you prefer to write them yourself for tone control?

---

## 9. Demo flow (act structure)

Pulling from `pitch/old-live-demo-script.md` act structure, adapted to the new architecture:

**Act 1 — setup (30 sec)**
- "I'm a financial institution. I need to verify the beneficial owners and sanctions status of a counterparty before settling a payment. Today this takes weeks of human review. Watch this."

**Act 2 — the demo (90 sec)**
1. Show the user brief: "Verify Acme Holdings LLC, settle 1000 RLUSD"
2. Show the buyer agent producing a signed TaskSpec → triad printed
3. Show negotiation: compliance agent counters on price, both sign → spec triad
4. Show compliance agent extracting beneficial owners → output triad + signed cert
5. Show subcontracting: sanctions agent gets the names → output triad + signed cert
6. Show compliance agent assembling final deliverable → final cert with subcontract_certs
7. Buyer verifies the chain from public keys alone — every signature, every triad, every reference

**Act 3 — settlement (45 sec)**
- Show the WASM Devnet escrow being created with the expected final-cert hash
- Show the seller submitting the cert hash
- Show the FinishFunction returning true → escrow auto-releases → payment lands
- "No oracles. No off-chain settlement layer. No trust in either agent. Verifiable from public keys alone, settled on a network that activated this primitive less than a month ago."

**Act 4 — punchline (15 sec)**
- "This is VTEAI on XRPL with PRISM. The substrate for agent-mediated compliance settlement at internet scale. Three months from a thousand-dollar bank wire to a five-cent automated settlement, on a network designed for it."

**Decisions to make on plane:**
- [ ] Settlement currency: XRP (simpler) or RLUSD (stronger pitch). Default XRP for Day 1, revisit.
- [ ] If WASM FinishFunction can't compile by Day 2 morning: fall back to Path B (legacy crypto-conditions hashlock). Pitch line shifts from "FinishFunction" to "crypto-conditional escrow" but still works.

---

## 10. Cut list (if Day 1 goes long)

In priority order — drop from the bottom up:

1. **Demo UI polish** (Phase 3.1) — CLI output is fine for judges; web frontend is gravy
2. **Record backup video** (Phase 3.1) — only if Day 2 has 30+ min spare
3. **WASM FinishFunction (Path A)** — fall back to Path B (legacy escrow with crypto-conditions); pitch story is still strong
4. **Subcontract chain** (sanctions agent) — drop sanctions screening, run only beneficial-ownership extraction. Single-agent demo is weaker but still works.
5. **Negotiation** — hardcode the TaskSpec instead of negotiating. Removes 1 LLM call per run, makes demo deterministic. Big simplification if anything blows up.

If you're cutting #4 and #5, you have a 60-second demo of "agent does KYC, signs cert, escrow releases" — still hackathon-worthy.

---

## 11. Open issues to resolve Day 1 morning

These are unfinished items from `docs/PHASE_2_8_TOOLCHAIN.md` that block escrow:

1. Install Rust + `wasm32-unknown-unknown` (or `wasm32v1-none`) target
2. Read `xrpl-wasm-std` crate's docs to confirm the FinishFunction signature
3. Install Craft CLI (or skip and build with raw `cargo` + `wasm-opt`)
4. Verify gas/size limits on WASM Devnet with a no-op deploy first

If any of 1-3 takes >60 minutes, drop to Path B without regret.

---

## 12. Anti-anxiety checklist

Things you do NOT need to worry about because they're already done:

- [x] PRISM works (`Q(3)`, deterministic triads)
- [x] Both XRPL networks accept transactions
- [x] Anthropic API + tool use works
- [x] Canonical-form discipline is documented
- [x] Phase 2.8 toolchain is identified
- [x] Pitch material is in `pitch/`
- [x] All env vars are in `.env`
- [x] Repo is on GitHub, private, no secrets leaked

Things you DO need to do at Consensus:

- [ ] Implement Phase 2.3 primitives (4 small files + tests)
- [ ] Implement Phase 2.4 LLM stack (4 small files + a cache invariant test)
- [ ] Implement Phase 2.5 agents (3 thin agents)
- [ ] Wire Phase 2.6 negotiation
- [ ] Run Phase 2.7 end-to-end local demo
- [ ] Wire Phase 2.8 escrow (Path A or B)
- [ ] Pitch (drawing from `pitch/`)
