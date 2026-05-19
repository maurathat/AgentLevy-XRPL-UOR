# AgentLevy → RoyaltAI

> ### ▶ **[Watch the 6-minute demo video](https://www.loom.com/share/fb8499e5300b41c18072d36dc66af30a)** — Maura runs the full RoyaltAI demo on XRPL Mainnet.
>
> 📦 **[Live pitch deck (Vercel)](https://royaltai-deck-y40ab4g0s-maurathats-projects.vercel.app)** · 🪙 **[Mainnet dNFT on Bithomp](https://bithomp.com/explorer/000800005C0D75FC05056348A634785AC427B30E2AAD1A60B2A688C20636D728)** · 📖 **[How to run the demo (DEMO.md)](DEMO.md)**

**RoyaltAI** — pay-per-call AI inference settling on XRPL Mainnet in RLUSD, with cryptographic royalty enforcement to model creators via XLS-20 dynamic NFTs. Built on the open AgentLevy protocol substrate, using UOR-ADDR-1 (Foundation-adopted, May 2026) for canonical content addressing.

**Submitted to:** AGI House Internet of Agents Build Day · May 16, 2026.

---

## What this proves

Every inference request triggers one real XRPL Mainnet transaction that:

1. **Settles** — agent wallet pays the inference server in RLUSD (verifiable on Bithomp)
2. **Computes** — server calls Anthropic Claude Haiku 4.5
3. **Mints a cert** — `DerivationCert` content-addressed via UOR-ADDR-1 (JCS-RFC8785 + NFC + SHA-256)
4. **Anchors to Hedera** — cert hash submitted to HCS topic `0.0.8856047` (independent witness)
5. **Cross-validates against UOR Foundation MCP** — live byte-identity check against the canonical Rust reference
6. **Pays royalty** — 50/50 split between server operator and model NFT owner, atomic with the payment

When a second agent asks the same question, the canonical UOR address matches and the server returns the prior cert at a 10× discount — no Anthropic call, but the royalty still flows. *The prior cert is the citation.* That is the value: pay-per-call inference with cryptographic memoization.

Three independent witnesses bind every cert: XRPL Payment txid (settlement), Hedera HCS sequence number (consensus timestamp), UOR Foundation MCP receipt (ed25519-signed by the canonical reference server). Verifiable from public keys alone, across three independent systems, without trusting any single agent.

See [DEMO.md](DEMO.md) for the full run-through, on-chain identifiers, and verification steps.

## The standards stack

| Standard | Status | Author | Use |
|---|---|---|---|
| **VTEAI** | ERC draft, CC0, April 2026 | Maura Clark | Settlement interface (escrow + attestation) |
| **UOR-ADDR-1** | UOR Foundation–adopted, May 2026 | Maura Clark + Alex Flom | Content addressing (`sha256:<hex>`) |
| **PRISM** | UOR Foundation, MIT, vendored | UOR Foundation | Algebraic ring substrate (Q(31), 256-bit) |

VTEAI's `taskSpecHash` uses UOR-ADDR-1 (per the May 2026 v1.1 spec update). Same canonical input on any chain → same address. Cross-chain byte-identical task spec hashes by construction.

## Repo layout

```
AgentLevy-XRPL-UOR/
├── README.md                   # this file
├── DEMO.md                     # how to run the Mainnet demo end-to-end
├── CANONICAL_FORM.md           # single source of truth for canonicalization
├── MIGRATION_NOTES.md          # Phase 2 history (KYC demo) → Phase 3 (RoyaltAI)
├── requirements.txt
├── .env.example
├── vendor/
│   ├── prism.py                # UOR-Foundation/prism @ 6cafdac (MIT)
│   └── LICENSE-prism
├── agentlevy/
│   ├── primitives/             # canonical, fingerprint, signing, task_spec, cert
│   ├── prism_layer/            # PRISM wrapper (Q(31), UOR-canonical width)
│   ├── llm/                    # Anthropic client, prompts, schemas, deterministic cache
│   ├── xrpl_layer/             # XRPL settlement (RLUSD Payments on Mainnet)
│   ├── hedera_layer/           # HCS anchor — cert hashes → consensus timestamp
│   └── inference/              # ★ Phase 3 — RoyaltAI: server, agent, cert store,
│                               #   NFT, payment, royalty, dashboard, MCP client
├── web/
│   ├── pitch.html              # static pitch deck (also served by FastAPI)
│   ├── dashboard.html          # post-demo snapshot dashboard
│   ├── api/                    # Vercel serverless wrappers
│   ├── static/                 # CSS, fonts, brand assets
│   └── vercel.json
├── scripts/
│   ├── start_demo_session.sh   # one-command demo launcher
│   ├── run_inference_demo.py   # CLI driver for the inference flow
│   ├── setup_inference_demo.py # one-shot bootstrap
│   ├── setup_rlusd_trust_lines.py
│   ├── mint_model_nft.py       # mints the XLS-20 dynamic model NFT
│   ├── check_inference_balances.py
│   ├── migrate_seeds_to_keychain.py  # moves Mainnet seeds to macOS Keychain
│   ├── setup_hcs_topic.py
│   ├── test_prism.py | test_xrpl.py | test_llm.py
│   └── make_braille_visuals.py
├── docs/                       # LANDSCAPE, NETWORK_CHOICE, TERMINOLOGY,
│                               # UOR_PASSPORT_VERIFIED, PHASE_2_DESIGN, …
├── pitch/                      # decks, whitepaper, VTEAI draft, UOR-ADDR proposal,
│                               # diagrams, talk-track material
├── fixtures/                   # cached LLM responses, model-card.json, synthetic KYC
├── mcp/                        # MCP server configs
└── tests/                      # 157 tests (canonical, cert, signing, task_spec,
                                #   hedera anchor, inference, LLM stack)
```

## Quick start

**Prerequisites:** Python 3.13+, `ANTHROPIC_API_KEY` in `.env`, and either Mainnet wallet seeds in the macOS Keychain (via `scripts/migrate_seeds_to_keychain.py`) or Testnet seeds in `.env`.

```bash
git clone https://github.com/maurathat/AgentLevy-XRPL-UOR.git
cd AgentLevy-XRPL-UOR
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cp .env.example .env   # fill in keys

bash scripts/start_demo_session.sh
# → FastAPI on localhost:8765, pitch deck at http://localhost:8765/pitch
# → focus the tab, press 1 (cache miss) then 9 (cache hits)
```

Full walkthrough, on-chain identifiers, and verification steps in [DEMO.md](DEMO.md).

## Architecture

```
                    ┌──────────────────────────┐
                    │  pitch.html  (browser)   │
                    │  press 1 / press 9       │
                    └──────────────────────────┘
                                ↓
                                POST /demo/run
                                ↓
        ┌──────────────────────────────────────────────────┐
        │   FastAPI server (uvicorn :8765)                 │
        │   - x402-style 402 → quote → retry pattern       │
        │   - UOR-ADDR-1 canonicalization                  │
        │   - DerivationCert mint (Ed25519)                │
        │   - Cert store (in-memory, keyed by UOR address) │
        └──────────────────────────────────────────────────┘
                                ↓
              ┌─────────────────┴─────────────────┐
              ↓                                   ↓
       ┌─────────────┐                     ┌─────────────┐
       │   XRPL      │                     │   Hedera    │
       │   Mainnet   │                     │   HCS       │
       │ (settlement)│                     │  (anchor)   │
       └─────────────┘                     └─────────────┘
              ↑                                   ↑
              │                                   │
              │       ┌─────────────────┐         │
              │       │ Anthropic Claude│         │
              │       │   Haiku 4.5     │         │
              │       └─────────────────┘         │
              │                                   │
              └─── UOR Foundation MCP ───────────┘
                   (live byte-identity check)
```

## Critical reading before touching code

Read [CANONICAL_FORM.md](CANONICAL_FORM.md) **first**. The single class of bug most likely to break this system is canonical-form drift between modules, which produces silent triad / address mismatches that take hours to diagnose. The discipline is: one module produces canonical bytes, everything else consumes its output.

## Phase history

This repo was originally an AgentLevy KYC-compliance demo built for Consensus EasyA (May 5–7, 2026). The Phase 3 RoyaltAI inference work lives in [`agentlevy/inference/`](agentlevy/inference/). See [MIGRATION_NOTES.md](MIGRATION_NOTES.md) for the Phase 2 → Phase 3 narrative.

| Phase | Window | Deliverable |
|---|---|---|
| 0 | Apr 27–29 | Environment, PRISM verification, XRPL testnet wallets, LLM connectivity |
| 2 | May 2–4 | Primitives, PRISM wrapper, LLM cache, KYC agent skeletons, XRPL escrow |
| 2.X | May 4 | Hedera HCS audit anchor (topic `0.0.8856047`) |
| **3** | **May 5 – May 16** | **RoyaltAI: Mainnet inference + XLS-20 dNFT + royalty split + MCP cross-validation** |

## Pitch & reference material

- [`docs/LANDSCAPE.md`](docs/LANDSCAPE.md) — where AgentLevy/RoyaltAI sits in the agent-economy stack (x402, AP2, Hedera AgentKit, MemWal, Kleros, Flare FDC, etc.)
- [`docs/TERMINOLOGY.md`](docs/TERMINOLOGY.md) — glossary for the standards stack
- [`docs/NETWORK_CHOICE.md`](docs/NETWORK_CHOICE.md) — why Mainnet RLUSD vs WASM Devnet SmartEscrow
- [`docs/UOR_PASSPORT_VERIFIED.md`](docs/UOR_PASSPORT_VERIFIED.md) — byte-identity verification against the UOR Foundation reference
- [`pitch/WHITEPAPER.md`](pitch/WHITEPAPER.md) — AgentLevy whitepaper v1.0
- [`pitch/VTEAI-DRAFT.md`](pitch/VTEAI-DRAFT.md) — VTEAI ERC draft (CC0)
- [`pitch/UOR-ADDR-PROPOSAL.md`](pitch/UOR-ADDR-PROPOSAL.md) — UOR-ADDR-1 proposal

## References

- PRISM: https://github.com/UOR-Foundation/prism
- UOR Framework (Foundation-adopted): https://uor-foundation.github.io/UOR-Framework/
- xrpl-py: https://github.com/XRPLF/xrpl-py
- XLS-20 NFTs: https://xrpl.org/non-fungible-token-overview.html
- XLS-100 Smart Escrows: https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html
- XRPL Mainnet explorer (Bithomp): https://bithomp.com/
- Hedera Consensus Service (HCS): https://docs.hedera.com/hedera/sdks-and-apis/sdks/consensus-service
- Hiero Python SDK: https://github.com/hiero-ledger/hiero-sdk-python
- This project's HCS topic: https://hashscan.io/testnet/topic/0.0.8856047

## Contact

- **Maura Clark** — UOR Foundation member, co-author of UOR-ADDR-1
- GitHub: [@maurathat](https://github.com/maurathat)
- Email: mauraclark@proton.me
- Hiring: senior Python/TS engineer (founding engineer / co-founder track)
- Raising: pre-seed, open

## License

Apache License 2.0 — see [LICENSE](LICENSE). Vendored PRISM (`vendor/prism.py`) retains its upstream MIT license; see [vendor/LICENSE-prism](vendor/LICENSE-prism).
