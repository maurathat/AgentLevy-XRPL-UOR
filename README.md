# AgentLevy — XRPL × PRISM × Hedera

> **Status: Phase 2.3 complete; Phase 2.4 next.** A from-scratch rebuild of AgentLevy on top of XRPL settlement, PRISM-based content addressing, and **Hedera Consensus Service for tamper-evident timestamping** of every cert. Targets the Consensus EasyA hackathon (May 5–7, 2026).

A protocol-layer demo: two AI agents negotiate and execute a KYC compliance task, sign each step with content-addressed derivation certificates (PRISM triads), settle on XRPL in **RLUSD**, and anchor every cert hash to a Hedera HCS topic for second-ledger audit-trail ordering — producing an audit trail that can be verified from public keys alone, across two independent ledgers, without trusting either agent.

## The two-ledger architecture

| Layer | Chain | Role |
|---|---|---|
| **Settlement** | XRPL (WASM Devnet) | XLS-100 Smart Escrow with WASM `FinishFunction` releases RLUSD when the cert hash matches the value committed at escrow creation. |
| **Audit anchor** | Hedera (testnet) | Every signed `DerivationCert` has its content address submitted to a Hedera Consensus Service topic. HCS provides an authoritative consensus timestamp + sequence number — a tamper-evident ordering of when each cert existed, on a chain independent of XRPL. |

Settlement says *the money moved*. The HCS anchor says *the cert existed at this exact moment, witnessed by Hedera's consensus*. Together: verifiable from public keys alone, across two independent ledgers.

---

## What's here right now

- ✅ **Phase 0.7** — repository scaffolding (directory tree, deps, env template, doc placeholders)
- ✅ **Phase 0.1** — venv on Python 3.13, all deps installed (`xrpl-py`, `pydantic`, `cryptography`, `httpx`, `click`, `anthropic`, `python-dotenv`)
- ✅ **Phase 0.2** — PRISM vendored at `vendor/prism.py` (pinned `6cafdac`), API verified, [CANONICAL_FORM.md](CANONICAL_FORM.md) filled in, `agentlevy/primitives/fingerprint.py` + `display.py` + `prism_layer/triad.py` implemented at **Q(31)** (UOR-canonical 32-byte width), `scripts/test_prism.py` passes (7/7 assertions). **★ Verified byte-for-byte against UOR Passport addresses** via live `mcp.uor.foundation/encode_address` — see [`docs/UOR_PASSPORT_VERIFIED.md`](docs/UOR_PASSPORT_VERIFIED.md).
- ✅ **Phase 0.4** — XRPL testnet wallets funded (10 XRP each), `scripts/test_xrpl.py` confirms `Wallet.from_seed` / `submit_and_wait` round-trip works on xrpl-py 4.5.0
- ✅ **Phase 0.6** — Anthropic API connectivity + tool use confirmed via `scripts/test_llm.py` (model `claude-sonnet-4-5`, structured-output extraction works end-to-end)
- ✅ **Phase 0.8** — XLS-100 `SmartEscrow` is **enabled on WASM Devnet** (rippled 3.2.0-b0), not on Testnet/Devnet (3.1.2). Phase 2.8 targets **Path A** (real WASM `FinishFunction`) on `wasm.devnet.rippletest.net`. See [docs/NETWORK_CHOICE.md](docs/NETWORK_CHOICE.md).
- ✅ **Phase 0.9** — existing AgentLevy code reviewed; decision = fresh-repo-with-narrative-port (code rewrites from scratch; pitch material + VTEAI spec ported). See [MIGRATION_NOTES.md](MIGRATION_NOTES.md).
- ✅ **Phase 2.3 — Primitives complete.** `agentlevy/primitives/` has `canonical`, `fingerprint`, `signing`, `task_spec`, `cert` (+ `display`). 87 tests pass. `TaskSpec.currency` defaults to **RLUSD** per Phase 2.8 decision; XRP also supported.
- ✅ **Phase 2.X (in progress) — Hedera HCS audit anchor.** Topic created on testnet (`0.0.8856047`), operator credentials configured in `.env`, [`scripts/setup_hcs_topic.py`](scripts/setup_hcs_topic.py) is one-shot reusable. Anchor module (`agentlevy/hedera_layer/anchor.py`) lands next; `MOCK_HEDERA=true` keeps the demo runnable without live testnet calls.

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
│   ├── xrpl_layer/         # XRPL settlement (RLUSD escrow on WASM Devnet)
│   ├── hedera_layer/       # HCS audit-trail anchor (cert hashes -> consensus timestamp)
│   ├── prism_layer/        # AgentLevy's PRISM wrapper (Q(31) engine, UOR-canonical width)
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
- **Phase 2.X** (May 4) — **Hedera HCS audit anchor**: every cert's content address submitted to a Hedera Consensus Service topic for tamper-evident timestamping + ordering. Topic created (`0.0.8856047`); anchor module + integration next.
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
python scripts/test_prism.py    # ✓ Phase 0.2 — passes (Q(31), all 7 assertions, UOR-canonical width)
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
> PRISM ring elements at quantum `Q(31)` (256-bit, UOR-canonical width).

## Critical reading before touching code

Read [CANONICAL_FORM.md](CANONICAL_FORM.md) **first**. The single most likely class of bug to lose this hackathon to is canonical-form drift between modules, which produces silent triad mismatches that take hours to diagnose. The discipline is: one module produces canonical bytes, everything else consumes its output.

## Pitch & landscape reference

- [`docs/LANDSCAPE.md`](docs/LANDSCAPE.md) — where AgentLevy sits in the agent-economy stack. Covers x402, AP2, Hedera AgentKit, MemWal, Kleros, Flare FDC, etc. Use as Q&A prep at Consensus.
- [`docs/PHASE_2_DESIGN.md`](docs/PHASE_2_DESIGN.md) — design decisions for Phase 2 build, including determinism trade-offs and demo scenarios.
- [`pitch/`](pitch/) — narrative material ported from old AgentLevy (VTEAI ERC draft, decks, demo scripts, architecture diagrams).

## Standards

AgentLevy's content addressing builds on **UOR-ADDR-1** — a chain-agnostic canonical content-addressing standard for verifiable agent-produced content, authored by Maura Clark and **contributed to the UOR Foundation in May 2026**. The standard specifies a deterministic SHA-256 over JCS-RFC8785 + Unicode NFC canonicalization pipeline producing a 71-byte content address (`sha256:<64hex>`) that is byte-identical across any compliant implementation. The reference Rust implementation, co-authored with Alex Flom, is hosted at [github.com/UOR-Foundation/uor-addr-1](https://github.com/UOR-Foundation/uor-addr-1) and published on crates.io as [`uor-addr-1`](https://crates.io/crates/uor-addr-1) v0.1.0 under Apache-2.0.

AgentLevy is the first reference implementation of the two-standard stack: [VTEAI](pitch/VTEAI-DRAFT.md) (settlement) over UOR-ADDR-1 (addressing) over PRISM (primitive).

## References

- PRISM: https://github.com/UOR-Foundation/prism
- xrpl-py: https://github.com/XRPLF/xrpl-py
- XLS-100 Smart Escrows: https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html
- XRPL testnet: https://testnet.xrpl.org/
- XRPL devnet: https://devnet.xrpl.org/
- Hedera Consensus Service (HCS): https://docs.hedera.com/hedera/sdks-and-apis/sdks/consensus-service
- Hiero Python SDK: https://github.com/hiero-ledger/hiero-sdk-python
- HashScan (Hedera testnet explorer): https://hashscan.io/testnet/
  - This project's anchor topic: https://hashscan.io/testnet/topic/0.0.8856047

## License

Apache License 2.0 — see [LICENSE](LICENSE). Vendored PRISM (`vendor/prism.py`) retains its upstream MIT license; see [vendor/LICENSE-prism](vendor/LICENSE-prism).
