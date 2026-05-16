"""Royalty split — second RLUSD Payment from server to model NFT owner.

Per-inference royalty mechanics for the May 16 demo:

1. Agent pays the server the full per-call price (RLUSD, with the request's
   UOR address in memo). This is the primary payment.
2. Server validates and runs the inference.
3. **Server dispatches a second RLUSD Payment** to the model NFT owner for
   the royalty share. Same UOR memo binds it to the same request.

Result: every paid inference produces two on-chain Payments, both carrying
the same UOR address. Pulling them up in the explorer side-by-side is the
visual proof of "three economic actors, one transaction logically — agent
pays server, server pays model creator, both audit-bound to one request."

Cache hits still pay royalty
----------------------------

Even when the cache hit collapses the server's marginal cost to ~zero, the
royalty *still flows* — because the agent's payment was real and the model's
on-chain identity is what authorized the cached completion to count as that
model's output. This is the "cache hits still pay the creator" property the
deck Slide 11 names. The cached cert's ``operation_description.model`` field
identifies the model; the NFT lookup resolves the recipient.

Failure handling
----------------

The royalty dispatch is **best-effort fire-and-forget** for the demo: the
inference response is returned to the agent as soon as the primary payment
is verified; the royalty Payment is submitted asynchronously and logged.
If it fails (network blip, ledger congestion), the demo continues. A retry
queue is documented but not implemented; production would use a durable
queue + idempotency keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional

from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet

from agentlevy.inference.payment import (
    PaymentResult,
    RLUSDConfig,
    pay_rlusd,
)


# ---------------------------------------------------------------------------
# Royalty fraction
# ---------------------------------------------------------------------------

#: Fraction of every per-call payment that flows to the model NFT owner.
#: 50% by default — clean for the demo. Production servers may tune this;
#: the protocol does not mandate a specific split.
ROYALTY_FRACTION = Decimal("0.5")

#: Smallest unit we'll meaningfully split to. Below this we don't dispatch
#: a royalty (the XRPL fee would exceed the amount). RLUSD supports many
#: decimals on-chain, but for the demo the floor is 0.0001 RLUSD.
MIN_ROYALTY_RLUSD = Decimal("0.0001")


# ---------------------------------------------------------------------------
# Split computation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoyaltySplit:
    """The result of splitting a per-call payment into server + royalty shares.

    Invariant: ``server_share + royalty_share <= total`` (the inequality
    accounts for rounding when the split lands between RLUSD's smallest unit).
    """
    total: Decimal
    server_share: Decimal
    royalty_share: Decimal
    fraction: Decimal


def compute_split(
    total: Decimal,
    fraction: Decimal = ROYALTY_FRACTION,
) -> RoyaltySplit:
    """Split a per-call total into the server share and the royalty share.

    Quantizes both shares to 4 decimal places (RLUSD's practical precision
    on XRPL for the demo) and rounds the royalty *down* — so the server's
    share absorbs any rounding remainder. That way ``server_share + royalty_share``
    can equal but never exceed ``total``.
    """
    if total <= 0:
        raise ValueError(f"total must be > 0, got {total}")
    if not (Decimal(0) < fraction < Decimal(1)):
        raise ValueError(f"fraction must be in (0, 1), got {fraction}")
    quantum = Decimal("0.0001")
    royalty = (total * fraction).quantize(quantum, rounding=ROUND_DOWN)
    server = (total - royalty).quantize(quantum, rounding=ROUND_DOWN)
    return RoyaltySplit(total=total, server_share=server, royalty_share=royalty, fraction=fraction)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

@dataclass
class RoyaltyDispatchResult:
    """Outcome of attempting to send the royalty Payment."""
    dispatched: bool
    skipped_reason: Optional[str]
    payment_result: Optional[PaymentResult]

    @property
    def txid(self) -> Optional[str]:
        return self.payment_result.txid if self.payment_result else None

    @property
    def succeeded(self) -> bool:
        return self.dispatched and self.payment_result is not None and self.payment_result.succeeded


def dispatch_royalty(
    client: JsonRpcClient,
    *,
    server_wallet: Wallet,
    recipient_address: str,
    royalty_amount: Decimal,
    uor_memo_address: str,
    config: Optional[RLUSDConfig] = None,
) -> RoyaltyDispatchResult:
    """Send a royalty RLUSD Payment from the server wallet to the NFT owner.

    Returns a :class:`RoyaltyDispatchResult`. Callers should log the outcome
    but not block the inference response on a royalty failure — the agent
    has already paid for and received the completion.

    Skips with ``dispatched=False`` if:

    * The recipient is the same as the server (self-payment is meaningless).
    * The royalty amount is below ``MIN_ROYALTY_RLUSD``.
    """
    if recipient_address == server_wallet.classic_address:
        return RoyaltyDispatchResult(
            dispatched=False,
            skipped_reason="recipient is the server wallet itself",
            payment_result=None,
        )
    if royalty_amount < MIN_ROYALTY_RLUSD:
        return RoyaltyDispatchResult(
            dispatched=False,
            skipped_reason=f"royalty {royalty_amount} below minimum {MIN_ROYALTY_RLUSD}",
            payment_result=None,
        )

    result = pay_rlusd(
        client,
        from_wallet=server_wallet,
        to_address=recipient_address,
        rlusd_amount=royalty_amount,
        uor_memo_address=uor_memo_address,
        config=config,
    )
    return RoyaltyDispatchResult(
        dispatched=True,
        skipped_reason=None,
        payment_result=result,
    )
