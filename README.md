# AgentLevy — XRPL × PRISM Rebuild

> **Status: Phase 0 scaffolding.** This is a from-scratch rebuild of AgentLevy on top of XRPL settlement and PRISM-based content addressing, targeting the Consensus EasyA hackathon (May 5–7, 2026).

A protocol-layer demo: two AI agents negotiate and execute a KYC compliance task, sign each step with content-addressed derivation certificates (PRISM triads), and settle on XRPL — producing an audit trail that can be verified from public keys alone, without trusting either agent.

---

## What's here right now

- ✅ **Phase 0.5** — directory tree, deps, env template, doc placeholders
- ✅ **Phase 0.1** — venv on Python 3.13, all deps installed
- ✅ **Phase 0.2** — PRISM cloned, API verified, [CANONICAL_FORM.md](CANONICAL_FORM.md) filled in, `scripts/test_prism.py` passes
- ⏳ **Phase 0.3** — XRPL testnet wallets (next)
- ⏳ **Phase 0.7** — LLM API connectivity test (next)

None of the application components below are implemented yet — only the layout.

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

**Requires Python ≥ 3.10** (PRISM uses `int.bit_count()`). On macOS, the system
Python is typically 3.9 — use a python.org install or `pyenv`/`asdf`.

```bash
# 1. Python 3.10+ venv (using 3.13 here)
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt click   # click is for PRISM's CLI

# 2. Environment
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and the three XRPL_*_SEED values.

# 3. PRISM (single-file module — clone, then add to PYTHONPATH via .pth)
cd .. && git clone https://github.com/UOR-Foundation/prism.git
echo "$(pwd)/prism" > AgentLevy-XRPL-UOR/.venv/lib/python3.13/site-packages/prism_repo.pth
cd AgentLevy-XRPL-UOR

# 4. Verify
python scripts/test_prism.py    # ✓ Phase 0.2 — runs now
python scripts/test_xrpl.py     # not yet written (Phase 0.3)
python scripts/test_llm.py      # not yet written (Phase 0.7)
```

> **Why a `.pth` file instead of `pip install -e .`?** PRISM is distributed as a
> single `prism.py` file with no `setup.py` or `pyproject.toml`. The standard
> Python pattern for adding such a directory to a venv is a `.pth` file in
> `site-packages/`, which adds the path on Python startup. See [CANONICAL_FORM.md](CANONICAL_FORM.md)
> for the full integration pattern.

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
