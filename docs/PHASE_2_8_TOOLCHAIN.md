# Phase 2.8 — WASM Smart Escrow Toolchain

> **Status: research notes, not yet bootstrapped.** This document captures the toolchain we'll need when Phase 2.8 starts (May 4 afternoon). Bootstrapping is ~30 min of work; doing it pre-emptively before Vegas would only invite breakage from Rust toolchain churn during the trip.

## What we're building

A minimal Rust → WebAssembly module that serves as the `FinishFunction` of an [XLS-100 SmartEscrow](https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html). When the buyer's compliance agent submits a final derivation certificate, the WASM checks that the cert's hash matches a stored value and returns `true`, releasing the escrowed XRP.

XLS-100's contract surface is intentionally tiny:

- The function takes the finishing transaction and returns `bool`
- 4 KB data field per escrow (we use it to store the expected cert hash)
- Gas limits exist (size and execution); WASM modules are typically run through `wasm-opt` to fit
- Details of the WASM execution engine are specified in a separate XLS (community references this as XLS-102; see "open questions" below)

## Toolchain inventory

Per Ripple's published guidance (compiled from XRPL devhub + community sources):

| Component | Purpose | Notes |
|---|---|---|
| **Rust toolchain** (`rustup`, `cargo`) | Build the WASM module | Stable channel is fine; nightly only if a chosen library requires it |
| **`wasm32v1-none` target** | Rust target for XRPL WASM | Some flows still use the older `wasm32-unknown-unknown` — verify which the chosen stdlib expects |
| **`xrpl-wasm-std`** | Rust standard library + reference patterns for smart escrows / hooks on XRPL | Provides typed access to the transaction context and the data field; precludes hand-rolled FFI |
| **`xrpl-wasm-stdlib`** | Lower-level Rust crate for "Smart Features" / hooks | Likely consumed transitively by `xrpl-wasm-std` |
| **`wasm-opt`** (Binaryen) | Size and gas optimization on the compiled WASM | Standard step; reduces module to fit ledger size limits |
| **Craft CLI** (Ripple) | Interactive CLI for building, testing, and deploying XLS-100 modules | Wraps the above into a single workflow |
| **WASM Devnet** | Network where SmartEscrow is currently activated | rippled 3.2.0-b0; verified 2026-04-28 |

## Bootstrap steps (when Phase 2.8 starts)

```bash
# 1. Install Rust if missing
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# 2. Add the WASM target
rustup target add wasm32-unknown-unknown
# (or wasm32v1-none, per chosen stdlib's requirements)

# 3. Install wasm-opt (via Binaryen)
# Either: download a release binary from https://github.com/WebAssembly/binaryen/releases
# or: brew install binaryen   (once Homebrew is set up)

# 4. Install Craft CLI
# Verify the canonical install command from Ripple docs at Phase 2.8 start;
# at this writing the URL points to the published RippleX devhub.

# 5. Skeleton crate
cargo new --lib agentlevy-finish-fn --vcs none
cd agentlevy-finish-fn
# Add xrpl-wasm-std as dependency in Cargo.toml
# Implement: read 32-byte cert-hash from escrow's Data field,
#            read submitted cert-hash from tx,
#            return Data == submitted
cargo build --release --target wasm32-unknown-unknown
wasm-opt -Oz target/wasm32-unknown-unknown/release/agentlevy_finish_fn.wasm \
  -o agentlevy_finish_fn.opt.wasm
```

## Open questions

These need to be resolved on the morning of May 4 (Phase 2.8 start). Each is small but un-skippable:

1. **Which Rust target?** `wasm32-unknown-unknown` is the universal default; `wasm32v1-none` was mentioned as XRPL-specific. Verify against the latest `xrpl-wasm-std` README.
2. **Exact `xrpl-wasm-std` API.** What's the function signature for the entry point? How is the escrow's `Data` field accessed? What's the transaction context type? Read the crate docs or examples directly.
3. **XLS-102 / WASM ABI spec status.** Search the [XRPL-Standards repo](https://github.com/XRPLFA/XRPL-Standards) for the formal WASM-execution specification. If unpublished, fall back to whatever the `xrpl-wasm-std` crate's docs say is canonical.
4. **Gas / size limits on WASM Devnet.** Run a test deploy of a no-op module first; observe the size limit and gas reservation policy before assembling the real contract.
5. **"AlphaNet" terminology.** Some Ripple docs reference "AlphaNet" as the home of XLS-100; community sources call it "WASM Devnet." Verify these are the same network (the activated `SmartEscrow` amendment + rippled 3.2.0-b0 build version strongly suggests yes; double-check before the demo).
6. **Deploy mechanism.** Is the WASM module included inline in the `EscrowCreate` transaction, or is there a separate "deploy" step that registers the module first? Per XLS-100 the FinishFunction field carries the WASM directly, but the practical limit on inline transaction size matters.

## What we DON'T need to install pre-Vegas

Bootstrapping the Rust + WASM toolchain *now* would be mostly waste: it has zero use until May 4, and Rust toolchains drift. Save it for Phase 2.8's first hour.

The one exception: **read the `xrpl-wasm-std` crate's docs sometime before Vegas** if you have idle plane time. That's mental work, not setup work — it tells us whether our 4 KB data plan is workable and whether the cert hash comparison is one line or a small saga.

## References

- [XLS-100 Smart Escrows spec](https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html)
- [XLS-101 Smart Contracts proposal (broader, not activated)](https://github.com/XRPLF/XRPL-Standards/discussions/271)
- [XLS-100 launch announcement](https://en.cryptonomist.ch/2026/04/10/xrpl-smart-escrows/)
- [Smart Escrows blog series, RippleX](https://dev.to/ripplexdev/smart-escrows-post-1-what-are-smart-escrows-34le)
- [Known XRPL amendments (cross-reference for activation status)](https://xrpl.org/resources/known-amendments)
- [Binaryen / wasm-opt releases](https://github.com/WebAssembly/binaryen/releases)
- Network choice rationale: [`docs/NETWORK_CHOICE.md`](NETWORK_CHOICE.md)
