"""AgentLevy Inference — pay-per-call LLM inference with content-addressed memoization.

The first MCP-native trust layer for agent commerce. Demonstrates the deck's
Slide 11 Phase 3 claim: *AI model pay-per-inference with cryptographic enforcement*.

Architecture
------------

* Every inference request canonicalizes to a UOR address via JCS-RFC8785 + NFC +
  SHA-256. Byte-identical to ``uor.encode_address`` against the UOR Foundation
  MCP server (``https://mcp.uor.foundation/mcp``). Two agents asking the same
  question produce the same address.

* Every served inference produces a signed :class:`DerivationCert` whose
  ``task_spec_address`` is the request's UOR address. The cert is the receipt
  the agent gets in exchange for the RLUSD payment.

* Cert-store dedup: when a second agent's request UOR matches a stored cert,
  the server returns the prior cert at a 10× discount. *The prior cert IS the
  citation* — the cached receipt is itself a verifiable artifact.

* Three independent witnesses bind each cert: XRPL Payment txid (settlement),
  Hedera HCS sequence number (consensus timestamp), UOR Foundation MCPS
  receipt (ed25519-signed by the canonical reference server).

Subpackage layout
-----------------

* ``canonical``    — request canonicalization, hour-bucket dedup key derivation.
* ``receipt``      — :class:`DerivationCert` builders for inference completions.
* ``cert_store``   — in-process keyed by request UOR address; serves cache hits.
* ``payment``      — XRPL RLUSD Payment build + verify, UOR memo encoding.
* ``nft``          — XLS-20 model NFT lookup; resolves royalty recipient.
* ``royalty``      — second RLUSD Payment to NFT owner.
* ``mcp_client``   — streamable HTTP client of the UOR Foundation MCP.
* ``mcp_server``   — AgentLevy as MCP server; exposes inference.* tools.
* ``server``       — FastAPI ``/complete`` endpoint with x402 + dedup.
* ``agent``        — client-side 402 retry + RLUSD payment submission.
* ``demo``         — end-to-end demo orchestrator.
"""

__all__ = [
    "canonical",
    "receipt",
    "cert_store",
    "payment",
    "nft",
    "royalty",
    "mcp_client",
    "mcp_server",
    "server",
    "agent",
]
