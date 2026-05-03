# XRPL Network Choice — Phase 0.8 finding

> **TL;DR.** Phase 2.1–2.7 runs on **Testnet** (`s.altnet.rippletest.net`). Phase 2.8 escrow demo runs on **WASM Devnet** (`wasm.devnet.rippletest.net`) — the only XRPL network where `XLS-100 SmartEscrow` is currently activated.

## Evidence

Queried the `feature` JSON-RPC method on each network on 2026-04-28 (commit pinning this finding: `<this commit>`):

| Network | rippled build | `SmartEscrow` | `TokenEscrow` | `fixTokenEscrowV1` |
|---|---|---|---|---|
| Testnet (`s.altnet.rippletest.net`) | 3.1.2 | not in registry | enabled | enabled |
| Devnet (`s.devnet.rippletest.net`) | 3.1.2 | not in registry | enabled | enabled |
| **WASM Devnet (`wasm.devnet.rippletest.net`)** | **3.2.0-b0** | **enabled** | enabled | enabled |

To re-verify at any time:

```python
import httpx
r = httpx.post(
    "https://wasm.devnet.rippletest.net:51234",
    json={"method": "feature", "params": [{}]},
    timeout=15,
)
features = r.json()["result"]["features"]
smart = [(v["name"], v.get("enabled", False)) for v in features.values() if "smart" in v["name"].lower() or "escrow" in v["name"].lower()]
for name, enabled in sorted(smart):
    print(name, "ENABLED" if enabled else "supported")
```

## Why this matters

The original task list flagged XLS-100 activation status as a Phase 0.8 unknown that gates Phase 2.8 strategy. We now have ground truth:

- **Path A (the strong demo path) is unlocked.** Compile a minimal WASM `FinishFunction` that verifies the AgentLevy final-derivation-cert hash matches a stored value, deploy via `EscrowCreate` with the FinishFunction field, finalize via `EscrowFinish` when the seller submits the matching cert. Runs on WASM Devnet only.
- **Path B remains as fallback** in case WASM Devnet is unavailable on demo day. Legacy `EscrowCreate`/`EscrowFinish` with a crypto-condition (hashlock) on the cert preimage. Works on Testnet and Devnet too.

The `Escrow` amendment listed as "supported (not active)" on all three networks is a labeling quirk for foundational amendments that predate the modern feature-flag system. Legacy escrow primitives are universally available.

## Operational separation

To avoid accidentally signing transactions on the wrong network during development:

- **`.env` keeps `XRPL_RPC_URL=https://s.altnet.rippletest.net:51234/`** as the default, with the three already-funded testnet seeds. All Phase 0 / Phase 2.1–2.7 work targets this.
- **WASM Devnet seeds are commented out** in `.env.example` as `XRPL_WASM_*_SEED`. They get filled in only when Phase 2.8 starts, alongside an alternative client construction that points at `wasm.devnet.rippletest.net`.
- The Phase 2.8 escrow code reads `XRPL_WASM_RPC_URL` and `XRPL_WASM_*_SEED`, never the default `XRPL_*_SEED`. This makes the network switch explicit in code, not implicit in env state.

## Open questions for Phase 2.8

These are not blocking now; flagging so they're not surprises:

1. **WASM toolchain.** Compiling a `FinishFunction` to WASM requires Rust + `wasm32-unknown-unknown` target (or AssemblyScript). We don't have Rust installed. ~30 min to bootstrap when we get there.
2. **WASM ABI / interface.** What signature does the `FinishFunction` see? What's the gas/stack limit? rippled's WASM host interface is documented somewhere in the rippled repo or a follow-up XLS spec — verify before writing the contract.
3. **WASM Devnet faucet.** Wallets the user has provided will need balance verification at the start of Phase 2.8. Faucet URL: `https://faucet.wasm.devnet.rippletest.net/accounts` (per `scripts/test_xrpl.py` hint table).
4. **TokenEscrow on WASM Devnet** is also enabled, so we have the option of escrowing in RLUSD (or any issued currency) rather than XRP. Decide later whether to lean into that for the pitch.

## References

- XLS-100 Smart Escrows spec: https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html
- Known amendments page: https://xrpl.org/resources/known-amendments
- WASM Devnet explorer: https://wasm.devnet.rippletest.net (direct API), https://devnet.xrpl.org
- Faucet: https://faucet.wasm.devnet.rippletest.net/accounts
