"""Client agent — the 402-retry consumer of the inference server.

Two-call flow for one inference request:

1. ``POST /complete`` → server replies 402 with a :class:`PriceQuote` body
   (request UOR address, price in RLUSD, destination, required memo).
2. Agent constructs and submits an XRPL RLUSD ``Payment`` with the UOR
   address in the memo.
3. ``POST /complete`` with ``X-Payment: <txid>`` → server verifies the
   payment on-ledger and returns 200 with the signed cert + completion.

The agent is deliberately small — about 100 LOC — to make the protocol
read like the protocol it is, not a framework. Agents in production will
embed the same 402-retry pattern in their own HTTP clients with whatever
retry / observability / circuit-breaker conventions they already have.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

import httpx
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet

from agentlevy.inference.payment import (
    RLUSDConfig,
    pay_rlusd,
)


# ---------------------------------------------------------------------------
# Outcome
# ---------------------------------------------------------------------------

@dataclass
class InferenceCall:
    """The end-to-end result of one agent → server inference call."""
    completion: str
    request_uor_address: str
    cert: dict
    settlement: dict
    is_cache_hit: bool
    paid_rlusd: Decimal
    payment_txid: str
    elapsed_ms: int
    raw_quote: dict = field(default_factory=dict)
    raw_response: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class InferenceAgent:
    """Client of the AgentLevy inference server.

    Construction
    ------------

    >>> agent = InferenceAgent(
    ...     wallet=Wallet.from_seed(seed),
    ...     server_url="http://localhost:8000",
    ...     xrpl_client=JsonRpcClient(rpc_url),
    ...     rlusd_config=RLUSDConfig(issuer=...),
    ... )
    >>> result = agent.complete("What is the meaning of life?")
    >>> print(result.completion)

    The agent does not cache locally — caching is the server's job, keyed on
    UOR addresses so all agents share it.
    """

    def __init__(
        self,
        *,
        wallet: Wallet,
        server_url: str,
        xrpl_client: JsonRpcClient,
        rlusd_config: RLUSDConfig,
        name: str = "agent",
        http_timeout: float = 30.0,
    ) -> None:
        self.wallet = wallet
        self.server_url = server_url.rstrip("/")
        self.xrpl_client = xrpl_client
        self.rlusd_config = rlusd_config
        self.name = name
        self._http = httpx.Client(timeout=http_timeout)

    # --- lifecycle ---

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "InferenceAgent":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # --- the call ---

    def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: int | float = 0,
        max_tokens: int = 400,
        on_event: Optional[callable] = None,
    ) -> InferenceCall:
        """Execute the full 402-retry inference call.

        ``on_event(kind, payload)`` is called at each notable step:

        * ``"quote_received"`` after the 402 with the parsed :class:`PriceQuote`
        * ``"payment_submitted"`` after the XRPL Payment with the txid
        * ``"payment_validated"`` after submit_and_wait returns
        * ``"completion_received"`` after the 200 with the cert

        The callback can stream stage output for the demo.
        """
        t0 = time.time()
        body = {"prompt": prompt, "temperature": temperature, "max_tokens": max_tokens}
        if model is not None:
            body["model"] = model

        # 1. 402 — get the quote
        r1 = self._http.post(f"{self.server_url}/complete", json=body)
        if r1.status_code != 402:
            raise RuntimeError(f"expected 402, got {r1.status_code}: {r1.text[:200]}")
        quote = r1.json()
        if on_event:
            on_event("quote_received", quote)
        request_addr = quote["request_uor_address"]
        price = Decimal(str(quote["price_rlusd"]))
        destination = quote["destination"]

        # 2. RLUSD Payment with UOR memo
        pay_result = pay_rlusd(
            self.xrpl_client,
            from_wallet=self.wallet,
            to_address=destination,
            rlusd_amount=price,
            uor_memo_address=request_addr,
            config=self.rlusd_config,
        )
        if on_event:
            on_event("payment_submitted", {"txid": pay_result.txid, "validated": pay_result.validated})
        if not pay_result.succeeded:
            raise RuntimeError(
                f"payment did not succeed: {pay_result.transaction_result} "
                f"(validated={pay_result.validated}, txid={pay_result.txid})"
            )
        if on_event:
            on_event("payment_validated", {"txid": pay_result.txid})

        # 3. 200 — retry with payment header
        r2 = self._http.post(
            f"{self.server_url}/complete",
            json=body,
            headers={"X-Payment": pay_result.txid},
        )
        if r2.status_code != 200:
            raise RuntimeError(
                f"after payment, expected 200, got {r2.status_code}: {r2.text[:500]}"
            )
        response = r2.json()
        if on_event:
            on_event("completion_received", response)

        elapsed_ms = int((time.time() - t0) * 1000)
        return InferenceCall(
            completion=response["completion"],
            request_uor_address=response["request_uor_address"],
            cert=response["cert"],
            settlement=response["settlement"],
            is_cache_hit=response["is_cache_hit"],
            paid_rlusd=price,
            payment_txid=pay_result.txid,
            elapsed_ms=elapsed_ms,
            raw_quote=quote,
            raw_response=response,
        )


# ---------------------------------------------------------------------------
# Convenience constructor
# ---------------------------------------------------------------------------

def agent_from_env(
    *,
    role: str,
    server_url: str,
) -> InferenceAgent:
    """Build an :class:`InferenceAgent` from ``.env`` for a named demo role.

    ``role`` selects which wallet seed to load:

    * ``"a"`` → ``XRPL_INFERENCE_AGENT_A_SEED``
    * ``"b"`` → ``XRPL_INFERENCE_AGENT_B_SEED``

    All other config is read from environment via the usual helpers.
    """
    from . import wallets
    wallet = wallets.get_wallet(f"agent_{role.lower()}")
    return InferenceAgent(
        wallet=wallet,
        server_url=server_url,
        xrpl_client=JsonRpcClient(wallets.rpc_url()),
        rlusd_config=RLUSDConfig(issuer=wallets.rlusd_issuer()),
        name=f"agent_{role.upper()}",
    )
