# AgentLevy — XRPL × PRISM Rebuild

> **Status: Phase 0 scaffolding.** This is a from-scratch rebuild of AgentLevy on top of XRPL settlement and PRISM-based content addressing, targeting the Consensus EasyA hackathon (May 5–7, 2026).

A protocol-layer demo: two AI agents negotiate and execute a KYC compliance task, sign each step with content-addressed derivation certificates (PRISM triads), and settle on XRPL — producing an audit trail that can be verified from public keys alone, without trusting either agent.

---

## What's here right now

Phase 0.5 scaffolding only. None of the components below are implemented yet.

```
AgentLevy-XRPL-UOR/
├── README.md               # this file
├── CANONICAL_FORM.md       # single source of truth for canonicalization (PLACEHOLDER)
├── requirements.txt        # pinned core deps
├── .env.example            # template for API keys + XRPL seeds
├── .gitignore
├── agentlevy/
│   ├── primitives/         # canonical bytes, task spec, derivation cert, signing
│   ├── llm/                # LLM client, prompts, schemas, cache
│   ├── agents/             # buyer, compliance, sanctions
│   ├── xrpl/               # XRPL integration, escrow logic
│   ├── prism/              # PRISM wrapper
│   └── protocol/           # bounded-turn negotiation
├── scripts/                # test_prism.py, test_xrpl.py, test_llm.py
├── fixtures/               # cached LLM responses (deterministic demo)
│   └── synthetic/          # synthetic KYC documents
└── tests/
```

## Phase plan

- **Phase 0** (Apr 27–29) — environment setup, PRISM verification, XRPL testnet wallets, LLM API connectivity
- **Phase 1** (Apr 30 – May 1) — Vegas pitch buffer, no build expected
- **Phase 2** (May 2 – May 4) — primitives, PRISM wrapper, LLM cache layer, agent skeletons, negotiation protocol, end-to-end local demo, XRPL escrow
- **Phase 3** (May 5–7) — Consensus hackathon polish + ship

## Setup (Phase 0)

```bash
# 1. Python venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and the three XRPL_*_SEED values.

# 3. PRISM (separate clone)
cd .. && git clone https://github.com/UOR-Foundation/prism.git
cd prism && pip install -e .
cd ../AgentLevy-XRPL-UOR

# 4. Verify
python scripts/test_prism.py    # not yet written
python scripts/test_xrpl.py     # not yet written
python scripts/test_llm.py      # not yet written
```

## Critical reading before touching code

Read [CANONICAL_FORM.md](CANONICAL_FORM.md) **first**. The single most likely class of bug to lose this hackathon to is canonical-form drift between modules, which produces silent triad mismatches that take hours to diagnose. The discipline is: one module produces canonical bytes, everything else consumes its output.

## References

- PRISM: https://github.com/UOR-Foundation/prism
- xrpl-py: https://github.com/XRPLF/xrpl-py
- XLS-100 Smart Escrows: https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html
- XRPL testnet: https://testnet.xrpl.org/
- XRPL devnet: https://devnet.xrpl.org/

## License

Private repo, no license selected. Add Apache-2.0 or MIT before flipping public for hackathon submission.
