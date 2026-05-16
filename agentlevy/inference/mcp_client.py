"""Thin streamable-HTTP MCP client for the UOR Foundation MCP server.

Target: ``https://mcp.uor.foundation/mcp`` — *Canonical reference implementation
of the UOR Passport Envelope*.

This is **not** a full MCP SDK. It implements just enough of the streamable HTTP
transport (MCP 2025-03-26) to call the three tools the Foundation exposes:

* ``encode_address(content)`` — compute the UOR address of any JSON value.
* ``verify_passport(content, passport)`` — verify a passport against content.
* ``verify_receipt(receipt)`` — verify an ed25519-signed MCPS receipt.

Every tool response carries a ``_meta.uor.mcps.receipt`` field — an ed25519
signature over the response's content, with public key, nonce, timestamp,
and trust level. We surface that to callers via :class:`MCPSReceipt` so it
can be attached to the inference cert as a third notarization (alongside
XRPL settlement and Hedera HCS witness).

Wire format
-----------

Streamable HTTP MCP responses arrive as Server-Sent Events
(``Content-Type: text/event-stream``). Each tool response is one or two
``data:`` lines; we read them with ``httpx.Client.stream`` and extract the
JSON-RPC payload from the non-empty ``data:`` line. The session id from
``initialize`` is passed back as the ``mcp-session-id`` header on every
subsequent request.

GitHub OAuth authentication may be required for some tools (write paths,
e.g.). The three tools we use are unauthenticated as of 2026-05-14 — verified
by live probe — so this client does not handle OAuth. If the Foundation
gates a tool in future, this client will return the server's 401 and the
caller can decide whether to re-implement with auth.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

import httpx


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

DEFAULT_URL = os.environ.get("UOR_MCP_URL", "https://mcp.uor.foundation/mcp")
PROTOCOL_VERSION = "2025-03-26"
CLIENT_NAME = "agentlevy-inference"
CLIENT_VERSION = "0.1.0"

DEFAULT_TIMEOUT_SECONDS = 30.0


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------

@dataclass
class MCPSReceipt:
    """An ed25519-signed MCPS receipt from the UOR Foundation MCP server.

    This is what makes the Foundation MCP a "third notarization" — every
    tool response is itself a signed attestation by the canonical reference
    server. Attach to your inference cert via
    :func:`agentlevy.inference.receipt.attach_settlement_metadata`.
    """

    passport: dict
    signature: str
    public_key: str
    nonce: str
    timestamp: str
    trust_level: str
    algorithm: str
    #: The raw receipt as returned by the server, for re-submission to
    #: ``verify_receipt`` if needed.
    raw: dict = field(repr=False)


@dataclass
class EncodeAddressResult:
    """Result of an ``encode_address`` call."""

    address: str
    fingerprint: str
    canonical_form: str
    algorithm: str
    version: str
    length: int
    canonicalization: str
    mcps_receipt: Optional[MCPSReceipt] = None


# ---------------------------------------------------------------------------
# Wire helpers
# ---------------------------------------------------------------------------

def _parse_sse_response(text: str) -> dict:
    """Extract the JSON-RPC payload from an SSE-formatted MCP response body.

    The response looks like::

        data:
        id: 0/0
        retry: 3000

        data: {"jsonrpc":"2.0","id":N,"result":{...}}
        id: 1/0

    We scan for ``data:`` lines, skip empty ones, and parse the first one
    that contains JSON. Raises if no JSON line is found.
    """
    for raw_line in text.splitlines():
        if not raw_line.startswith("data:"):
            continue
        body = raw_line[5:].strip()
        if not body:
            continue
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"no JSON data line in SSE response: {text!r}")


def _extract_mcps_receipt(envelope: dict) -> Optional[MCPSReceipt]:
    """Pull the ``_meta.uor.mcps.receipt`` field out of a JSON-RPC result envelope.

    Returns ``None`` if the response did not carry a receipt (which is unusual
    — the canonical server emits one for every tool call, but be defensive).
    """
    meta = envelope.get("_meta") or {}
    raw = meta.get("uor.mcps.receipt")
    if not raw:
        return None
    return MCPSReceipt(
        passport=raw.get("passport") or {},
        signature=raw.get("signature", ""),
        public_key=raw.get("public_key", ""),
        nonce=raw.get("nonce", ""),
        timestamp=raw.get("timestamp", ""),
        trust_level=raw.get("trust_level", ""),
        algorithm=raw.get("algorithm", ""),
        raw=raw,
    )


def _extract_inner_json(tool_result: dict) -> Optional[dict]:
    """The Foundation MCP returns two ``content`` items: the bare address
    string and a JSON-serialized passport dict. Pull the dict out."""
    content = tool_result.get("content") or []
    for item in content:
        if item.get("type") != "text":
            continue
        text = item.get("text", "")
        if not text.startswith("{"):
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue
    return None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class UORMCPClient:
    """Streamable-HTTP MCP client targeting the UOR Foundation server.

    Use as a context manager so the session is properly torn down::

        with UORMCPClient() as cli:
            result = cli.encode_address({"hello": "world"})
            print(result.address)
            # MCPSReceipt available at result.mcps_receipt
    """

    def __init__(
        self,
        url: str = DEFAULT_URL,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self._http: Optional[httpx.Client] = None
        self._session_id: Optional[str] = None

    # --- lifecycle ---

    def __enter__(self) -> "UORMCPClient":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def open(self) -> None:
        """Open the HTTP client, run the initialize handshake, store session id."""
        if self._http is not None:
            return
        self._http = httpx.Client(timeout=self.timeout)
        init_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
            },
        }
        resp = self._post(init_req)
        self._session_id = resp.headers.get("mcp-session-id")
        if not self._session_id:
            raise RuntimeError(
                "UOR MCP initialize did not return mcp-session-id; "
                f"headers={dict(resp.headers)}"
            )
        # Server confirms initialization is complete; we send the required notify.
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None
            self._session_id = None

    # --- tools ---

    def encode_address(self, content: Any) -> EncodeAddressResult:
        """Compute the UOR address of any JSON-serializable value via the Foundation MCP.

        Returns
        -------
        EncodeAddressResult
            Includes the bare address, the canonical form the server hashed,
            and the ed25519-signed MCPS receipt for the call.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": "encode_address", "arguments": {"content": content}},
        }
        resp = self._post(payload)
        envelope = self._parse_jsonrpc_result(resp.text)
        inner = _extract_inner_json(envelope) or {}
        receipt = _extract_mcps_receipt(envelope)
        return EncodeAddressResult(
            address=inner.get("address", ""),
            fingerprint=inner.get("fingerprint", ""),
            canonical_form=inner.get("canonical_form", ""),
            algorithm=inner.get("algorithm", ""),
            version=inner.get("version", ""),
            length=int(inner.get("length", 0)),
            canonicalization=inner.get("canonicalization", ""),
            mcps_receipt=receipt,
        )

    def verify_passport(self, content: Any, passport: dict) -> dict:
        """Verify a UOR Passport envelope's fingerprint against content.

        Returns the server's ``{valid, reason?}`` dict.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "verify_passport",
                "arguments": {"content": content, "passport": passport},
            },
        }
        resp = self._post(payload)
        envelope = self._parse_jsonrpc_result(resp.text)
        return _extract_inner_json(envelope) or {}

    def verify_receipt(self, receipt: dict) -> dict:
        """Verify an MCPS receipt (the ``_meta.uor.mcps.receipt`` value).

        Fully local on the server side — no PKI, no network. Returns
        ``{valid, reason?}``.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": "verify_receipt", "arguments": {"receipt": receipt}},
        }
        resp = self._post(payload)
        envelope = self._parse_jsonrpc_result(resp.text)
        return _extract_inner_json(envelope) or {}

    # --- internals ---

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            h["mcp-session-id"] = self._session_id
        return h

    def _post(self, payload: dict) -> httpx.Response:
        if self._http is None:
            raise RuntimeError("UORMCPClient is not open — use `with UORMCPClient() as cli:`")
        return self._http.post(self.url, headers=self._headers(), json=payload)

    def _parse_jsonrpc_result(self, body: str) -> dict:
        """Parse JSON-RPC envelope from SSE body, raise on JSON-RPC error,
        return the ``result`` dict."""
        envelope = _parse_sse_response(body)
        if "error" in envelope:
            raise RuntimeError(f"UOR MCP error: {envelope['error']}")
        result = envelope.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(f"UOR MCP result missing or malformed: {envelope}")
        return result


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

@contextmanager
def open_uor_mcp(url: str = DEFAULT_URL) -> Iterator[UORMCPClient]:
    """Context-manager convenience for the common one-shot path::

        with open_uor_mcp() as cli:
            result = cli.encode_address(...)
    """
    cli = UORMCPClient(url=url)
    cli.open()
    try:
        yield cli
    finally:
        cli.close()
