# UOR MCP Server — connection config

> Source-of-truth config snippet for connecting MCP-aware clients (Claude Desktop, Claude CLI) to the canonical UOR Foundation MCP server.

## What this server is

`mcp-uor-server v0.2.1` — *"Canonical reference implementation of the UOR Passport Envelope"* — hosted at:

- **Endpoint:** `https://mcp.uor.foundation` (path: `/mcp`)
- **Protocol:** Streamable HTTP (MCP `2025-06-18`)
- **Server-Sent Events** transport for streaming responses

## Verified capabilities (from the live initialize handshake)

| Capability | Algorithm | Notes |
|---|---|---|
| `uor.passport` | `uor-sha256-v1` | **JCS canonicalization confirmed (`jcs: true`)** — RFC 8785 JSON Canonicalization Scheme. Aligns with `CANONICAL_FORM.md` recommendation. |
| `uor.mcps` | `ed25519` | Trust level default `L1`. Server's public key is broadcast in handshake. |
| `uor.verify` | enabled | — |

> Per server instructions: *"every tool response includes a `uor.passport` envelope in its `_meta` field. Use `uor.encode_address` to compute content addresses and `uor.verify_passport` to verify them."*

## Why connect

10+ tools become callable from any MCP-aware Claude session:

| Tool | Use |
|---|---|
| `uor_derive` | Compute prime factorization + content-addressed proof for any term |
| `uor_verify` | Re-verify a derivation by ID |
| `uor_query` | SPARQL against the UOR knowledge graph |
| `uor_correlate` | Spectral correlation between two integers |
| `uor_partition` | Partition a seed set into prime orbits |
| `uor_resolve` | Resolve a UOR content address to derivation data |
| `uor_certify` | **Issue a verifiable certificate (W3C VC-shaped) for a derivation** |
| `uor_trace` | Retrieve full derivation trace by proof ID |
| `uor_schema_bridge` | Bridge external schemas to UOR canonical representation |
| `uor_schema_coherence` | Check coherence of a schema mapping against UOR axioms |
| `uor.encode_address` | Compute the canonical content address for any input |
| `uor.verify_passport` | Verify a passport envelope on any tool response |

## Where to install on your machine

### Claude Desktop (macOS)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`. If the file exists, **merge** the `"uor"` entry into your existing `mcpServers` object (don't overwrite the file). If it doesn't exist, create it with the contents of `uor-mcp-config.json` in this directory.

```bash
# Open the config file (create if missing)
open -a TextEdit "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

After saving, **restart Claude Desktop** (Cmd+Q, then reopen). The 10+ UOR tools will appear as callable from any new conversation.

### Claude Desktop (Windows)

Edit `%APPDATA%\Claude\claude_desktop_config.json` with the same merge logic.

### Claude CLI

If/when you install the `claude` CLI:

```bash
claude mcp add uor --url https://mcp.uor.foundation --transport streamableHttp
```

Or paste the contents of `uor-mcp-config.json` into your `claude` settings.

## Usage from a Claude session (once connected)

```
Use the uor tools to derive a content address for the canonical bytes of
this JSON: {"task_id":"abc","price":100}. Show me the derivation ID.
```

The model will call `uor.encode_address` (or `uor_derive`), return the content address, and include the `uor.passport` envelope in its `_meta`. You can then verify the envelope independently with `uor.verify_passport`.

## How AgentLevy might compose with this (Phase 2.4 design hook)

Two non-blocking integration patterns to consider for Day 1+ at Consensus:

1. **Use `uor_certify` to issue derivation certs in the canonical UOR format.** AgentLevy's compliance agent currently signs Pydantic-shaped certs locally with Ed25519. A production overlay could call `uor_certify` to wrap each cert in a W3C-VC-shaped UOR Passport Envelope. Stronger pitch story; minor extra latency. **Optional for the demo.**

2. **Use `uor_query` for capability discovery.** When the buyer agent describes "I need a KYC compliance task," it could SPARQL against the UOR ontology to find the canonical schema for that task type, instead of hardcoding it. **Optional for the demo; nice for the production roadmap pitch.**

Both are layered on top of AgentLevy, not replacements for the local PRISM. Keep MCP off the critical demo path — network failures at the venue would break a demo that depends on it. Demonstrate the integration; don't depend on it.

## Security note

The server's public key (`oZJ32H/wro7SagCI17vMOM8BRhI72yGgAni+DbXlozk=`) is broadcast in the initialize handshake. To trust the server, an MCP client would pin this key. For dev/demo work the convenience of trust-on-first-use is fine. For production you'd want a published, signed key fingerprint somewhere on uor.foundation that clients can verify against.

## Example UOR certificate (real)

A live `cert:ModuleCertificate` for the Hologram SDK project is at [`example-module-certificate.json`](example-module-certificate.json). Verbatim shape:

```json
{
  "@context": "https://uor.foundation/contexts/uor-v1.jsonld",
  "@type": "cert:ModuleCertificate",
  "cert:subject": "project:hologram-sdk",
  "cert:cid": "baguqeerapqnkdb22c7y5cqrtzpifnqo4k7eapz4ft7jhhpilmwn4msi6rdrq",
  "store:uorAddress": {
    "u:glyph": "⡼⠚⢡⢇⡚⠗⣱⣑⡂⠳⣋⣐⡖⣁⣜⡗⣈⠇⣧⢅⢟⣒⡳⢽⠋⡥⢛⣆⡉⠞⢈⣣",
    "u:length": 32
  },
  "cert:specification": "1.0.0"
}
```

What this tells us about UOR's canonical address format:

| Field | What it is | Decode |
|---|---|---|
| `@context` | UOR's published JSON-LD context, version 1 | `https://uor.foundation/contexts/uor-v1.jsonld` — **AgentLevy certs should reference this for protocol alignment** |
| `@type` | Cert subtype — `cert:ModuleCertificate` for projects/modules | AgentLevy will likely need `cert:DerivationCertificate` (or similar) — same envelope, different subtype |
| `cert:cid` | Base32-multibase content identifier (IPFS-style) | `baguqeera...` — one of UOR's address representations |
| `store:uorAddress.u:glyph` | Braille-encoded 32-char string, each character `U+2800 + byte` | The 32-byte address rendered as a visible string. Verified hex: `7c1aa1875a17f1d14233cbd056c1dc57c807e7859fd273bd0b659bc6491e88e3` |
| `store:uorAddress.u:length` | **32** (bytes) | **The canonical UOR address width is 32 bytes (256 bits)** |

## ★ Architectural decision flag (for AgentLevy Phase 2.3)

**AgentLevy is currently configured at `Q(3)` (32-bit, 4-byte datums) — UOR's canonical format is 32-byte (`Q(31)`).** That's a real width mismatch. Three ways to resolve it:

| Option | Pros | Cons |
|---|---|---|
| **A. Stay at Q(3)** | Demo audit trail more readable (4-byte datums) | Our certs aren't directly UOR-Passport-verifiable without a width-conversion layer — weakens the "protocol-aligned" pitch |
| **B. Switch to Q(31)** | Full UOR canonical-width alignment; certs verifiable with `uor.verify_passport` directly; effectively unlimited collision resistance | 32-byte datums look noisier in console output; need a display-layer to keep the demo readable |
| **C. Hybrid — Q(31) internal, projected display** | Protocol-aligned AND demo-readable. Internal addresses are 32-byte; the audit-trail printer shows the Braille glyph (32 visible chars) or a 4-byte projection for compactness | Slight extra complexity in the display layer (one helper function) |

**Recommendation: Option C (hybrid).** Concretely:
- `agentlevy/prism_layer/triad.py` switches from `Q(3)` to `Q(31)` (single line change)
- `agentlevy/primitives/fingerprint.py` already takes the engine width as a parameter — switching `quantum=3` to `quantum=31` is a single-line change
- A new `agentlevy/primitives/display.py` provides `glyph(triad)` (32-char Braille) and `compact(triad, n=4)` (first n bytes hex) helpers for the audit trail printer
- `CANONICAL_FORM.md` updates the quantum decision; `scripts/test_prism.py` updates the assertions

This is a Day-1-morning, ~30-minute refactor. It's much cheaper to do before Phase 2.3 cements the Q(3) decision in agent code.

**Pending user confirmation before making the change.**
