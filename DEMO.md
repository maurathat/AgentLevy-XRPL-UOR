# RoyaltAI Demo

**Pay-per-call AI inference settling on XRPL Mainnet in RLUSD, with cryptographic royalty enforcement to model creators via XLS-20 dynamic NFTs. Built on the open AgentLevy protocol substrate. Live on Mainnet, May 16, 2026.**

## See it now

| Where | What you'll see |
|---|---|
| **Pitch deck (Vercel, static)** | `https://royaltai-deck-y40ab4g0s-maurathats-projects.vercel.app` — full deck, all 11 sections, dashboard showing post-demo snapshot |
| **Live Mainnet dNFT (Bithomp)** | https://bithomp.com/explorer/000800005C0D75FC05056348A634785AC427B30E2AAD1A60B2A688C20636D728 |
| **Live Mainnet dNFT (XRPL Livenet)** | https://livenet.xrpl.org/nft/000800005C0D75FC05056348A634785AC427B30E2AAD1A60B2A688C20636D728 |
| **dNFT metadata (full schema)** | https://raw.githubusercontent.com/maurathat/AgentLevy-XRPL-UOR/main/fixtures/model-card.json |
| **VTEAI spec** (ERC draft I authored) | [pitch/VTEAI-DRAFT.md](pitch/VTEAI-DRAFT.md) |
| **UOR-ADDR-1** (Foundation-adopted) | https://uor-foundation.github.io/UOR-Framework/ |

## What the demo proves

Each press of `1` triggers a real XRPL Mainnet payment that:
1. **Settles** — an agent wallet pays the inference server in RLUSD (verifiable on Bithomp)
2. **Computes** — the server calls Anthropic Claude Haiku 4.5
3. **Mints a cert** — `DerivationCert` content-addressed via UOR-ADDR-1 (JCS-RFC8785 + NFC + SHA-256)
4. **Anchors to Hedera** — cert hash submitted to HCS topic `0.0.8856047` (independent witness)
5. **Cross-validates against UOR Foundation MCP** — live byte-identity check against the canonical Rust reference
6. **Pays royalty** — 50/50 split between server operator and model NFT owner, atomic with the payment

Each press of `9` then fires nine more identical requests. **All nine are cache hits** — same UOR address, no Anthropic call, royalty still flows. That's the value: pay-per-call inference with cryptographic memoization.

**Final state after a full demo (1 cache miss + 9 cache hits = 10 served queries):**
- Anthropic spend: $0.0015 (one call)
- Cache savings: $0.0135 (nine calls avoided)
- Cache hit rate: 90%
- Royalty distributed: 0.0182 RLUSD to model NFT owner

## Live on-chain identifiers

| Role | Address (Mainnet) |
|---|---|
| Agent A (caller) | `r94gJ43Jb5rFdKZkg67jVdgnJNYZhdGG8M` |
| Agent B (caller) | `rN8S1J5LnsAnBwNJyFAU5BGpWivjMWi1Bi` |
| Inference Server (receives payment) | `rGJktGYrb8ynmPk5NiJm9dmcqsEXAZVTDp` |
| Model NFT Owner (receives royalty) | `r9PjHvj8kKwA61fTMx5ANpH6BrGmQdrQgf` |
| RLUSD Issuer | `rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De` |
| Hedera HCS Topic | `0.0.8856047` |
| Model dNFT | `000800005C0D75FC05056348A634785AC427B30E2AAD1A60B2A688C20636D728` |

All four addresses verifiable on Bithomp by clicking through.

## Run the demo locally

### Prerequisites
- macOS or Linux
- Python 3.13+
- Mainnet XRPL wallet seeds stored in macOS Keychain via the migration script (or in `.env` for Testnet)
- `ANTHROPIC_API_KEY` in `.env`

### One-command start
```bash
cd /path/to/AgentLevy-XRPL-UOR
pip3 install -r requirements.txt
bash scripts/start_demo_session.sh
```

This launches the FastAPI server on `localhost:8765` and opens the pitch deck at `http://localhost:8765/pitch`.

### Run the demo

Focus the browser tab and press:
- **`1`** → fire one cache-miss inference (real Mainnet payment, full pipeline animates)
- **`9`** → fire nine cache-hit inferences (royalty climbs, no Anthropic call)

That's the whole demo. Two keypresses.

### Verify on chain

Open Bithomp tabs for the four wallets and refresh after pressing `1`:
- Agent wallet balance drops by `0.010` RLUSD
- Server wallet balance rises by `0.005` RLUSD
- Model owner balance rises by `0.005` RLUSD (royalty)
- New `Payment` transaction in agent's tx history with memo = cert UOR address

## The standards stack

| Standard | Status | Author | Use |
|---|---|---|---|
| **VTEAI** | ERC draft, CC0, April 2026 | Maura Clark | Settlement interface (escrow + attestation) |
| **UOR-ADDR-1** | UOR Foundation–adopted, May 2026 | Maura Clark + Alex Flom | Content addressing (`sha256:<hex>`) |
| **PRISM** | UOR Foundation, MIT, vendored | UOR Foundation | Algebraic ring substrate (Q(31), 256-bit) |

VTEAI's `taskSpecHash` SHOULD use UOR-ADDR-1 (per the May 2026 v1.1 spec update). Same canonical input on any chain → same address. Cross-chain byte-identical task spec hashes by construction.

## Architecture in one diagram

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

Three independent witnesses on every cert: XRPL settles, Hedera consensus-timestamps, UOR Foundation signs an ed25519 receipt that the address matches the canonical reference.

## Contact

- Maura Clark — UOR Foundation member, co-author of UOR-ADDR-1
- GitHub: [@maurathat](https://github.com/maurathat)
- Email: enterpriseroofing@gmail.com
- Hiring: senior Python/TS engineer (founding engineer / co-founder track)
- Raising: pre-seed, open
