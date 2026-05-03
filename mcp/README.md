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
