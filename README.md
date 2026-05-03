# AgentLevy — XRPL × PRISM Rebuild

> **Status: Phase 0 scaffolding.** This is a from-scratch rebuild of AgentLevy on top of XRPL settlement and PRISM-based content addressing, targeting the Consensus EasyA hackathon (May 5–7, 2026).

A protocol-layer demo: two AI agents negotiate and execute a KYC compliance task, sign each step with content-addressed derivation certificates (PRISM triads), and settle on XRPL — producing an audit trail that can be verified from public keys alone, without trusting either agent.

---

## What's here right now

- ✅ **Phase 0.7** — repository scaffolding (directory tree, deps, env template, doc placeholders)
- ✅ **Phase 0.1** — venv on Python 3.13, all deps installed (`xrpl-py`, `pydantic`, `cryptography`, `httpx`, `click`, `anthropic`, `python-dotenv`)
- ✅ **Phase 0.2** — PRISM vendored at `vendor/prism.py` (pinned `6cafdac`), API verified, [CANONICAL_FORM.md](CANONICAL_FORM.md) filled in, `agentlevy/primitives/fingerprint.py` placeholder, `scripts/test_prism.py` passes (Q(3), 6/6 assertions)
- ✅ **Phase 0.4** — XRPL testnet wallets funded (10 XRP each), `scripts/test_xrpl.py` confirms `Wallet.from_seed` / `submit_and_wait` round-trip works on xrpl-py 4.5.0
- ✅ **Phase 0.6** — Anthropic API connectivity + tool use confirmed via `scripts/test_llm.py` (model `claude-sonnet-4-5`, structured-output extraction works end-to-end)
- ✅ **Phase 0.8** — XLS-100 `SmartEscrow` is **enabled on WASM Devnet** (rippled 3.2.0-b0), not on Testnet/Devnet (3.1.2). Phase 2.8 targets **Path A** (real WASM `FinishFunction`) on `wasm.devnet.rippletest.net`. See [docs/NETWORK_CHOICE.md](docs/NETWORK_CHOICE.md).
- ✅ **Phase 0.9** — existing AgentLevy code reviewed; decision = fresh-repo-with-narrative-port (code rewrites from scratch; pitch material + VTEAI spec ported). See [MIGRATION_NOTES.md](MIGRATION_NOTES.md).

None of the application components below are implemented yet — only the layout.

```
AgentLevy-XRPL-UOR/
├── README.md               # this file
├── CANONICAL_FORM.md       # single source of truth for canonicalization
├── requirements.txt        # pinned core deps (incl. click for PRISM CLI)
├── .env.example            # template for API keys + XRPL seeds
├── .gitignore
├── vendor/                 # third-party code, vendored
│   ├── prism.py            #   from UOR-Foundation/prism @ 6cafdac (MIT)
│   └── LICENSE-prism
├── agentlevy/
│   ├── primitives/         # canonical bytes, fingerprint, task spec, cert, signing
│   ├── llm/                # LLM client, prompts, schemas, cache
│   ├── agents/             # buyer, compliance, sanctions
│   ├── xrpl_layer/         # XRPL integration, escrow logic
│   ├── prism_layer/        # AgentLevy's PRISM wrapper (Q(3) engine)
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
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and the three XRPL_*_SEED values.

# 3. PRISM is already vendored at vendor/prism.py — no separate install.
#    Pinned to commit 6cafdac (Feb 16, 2026); see vendor/__init__.py.

# 4. Verify
python scripts/test_prism.py    # ✓ Phase 0.2 — passes (Q(3), all 6 assertions)
python scripts/test_xrpl.py     # not yet written (Phase 0.3)
python scripts/test_llm.py      # not yet written (Phase 0.6)
```

> **Why vendor instead of `pip install -e .`?** PRISM is distributed as a
> single `prism.py` file with no `setup.py` or `pyproject.toml`. Vendoring the
> file (verified byte-identical to the pinned upstream commit) gives us a
> self-contained repo with no path coupling — anyone cloning AgentLevy gets a
> working `from vendor.prism import Q, ...` immediately, no `~/prism` setup
> required. See [CANONICAL_FORM.md](CANONICAL_FORM.md) for the full integration
> pattern, including the SHA-256 fingerprint that bridges canonical bytes to
> PRISM ring elements at quantum `Q(3)` (32-bit).

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
