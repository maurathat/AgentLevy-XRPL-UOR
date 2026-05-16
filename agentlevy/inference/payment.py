"""XRPL RLUSD payment helpers for the inference demo.

Three jobs:

1. **Establish trust lines.** Every wallet that holds RLUSD needs a ``TrustSet``
   to the RLUSD issuer. One-shot per wallet, done in the setup script.
2. **Build + submit RLUSD payments** with the UOR memo. The memo binds the
   payment to a specific request UOR address, which is the replay-resistance
   property: a payment for request A cannot unlock a completion for request B.
3. **Verify payments** by txid. Given a tx hash, fetch it from the ledger,
   confirm sender / recipient / amount / memo all match the expectation.

Memo encoding
-------------

XRPL ``Memo`` fields are hex-encoded UTF-8. We use three fields:

* ``memo_data``   → hex(UOR address) e.g. ``hex("sha256:7a4f...d3a2")``
* ``memo_format`` → hex("text/plain")
* ``memo_type``   → hex("uor-addr-1")

The ``memo_type`` makes the memo self-identifying: any explorer or auditor
parsing the transaction sees ``uor-addr-1`` and knows what the data field is.

Network and issuer
------------------

Defaults to the project's regular Testnet (``XRPL_RPC_URL`` from ``.env``).
RLUSD issuer is read from ``RLUSD_TESTNET_ISSUER`` env var — keep this
configurable because issuer addresses change as Ripple promotes test
deployments. Operator-side documentation lives in
``.env.example``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from xrpl.clients import JsonRpcClient
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import Tx
from xrpl.models.transactions import Memo, Payment, TrustSet
from xrpl.transaction import autofill_and_sign, submit_and_wait
from xrpl.utils import xrp_to_drops
from xrpl.wallet import Wallet


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: RLUSD currency code in XRPL 40-hex form (non-standard 4+ char codes
#: require the full 20-byte / 40-hex representation).
#: ``RLUSD`` -> ``524C555344`` then zero-padded to 40 hex chars.
RLUSD_CURRENCY_HEX = "524C555344000000000000000000000000000000"

#: A high trust line limit so the demo doesn't bump into ceilings. Operators
#: paying real money should pick a tighter limit.
DEFAULT_TRUST_LIMIT = Decimal("1000000")

MEMO_TYPE_UOR_ADDR_1 = "uor-addr-1"
MEMO_FORMAT_TEXT_PLAIN = "text/plain"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RLUSDConfig:
    """Where RLUSD lives on this network.

    Read ``RLUSD_TESTNET_ISSUER`` from env (set in ``.env``). Falls back to
    a documented placeholder so import-time failures are obvious if config
    is missing.
    """
    issuer: str
    currency_hex: str = RLUSD_CURRENCY_HEX

    @classmethod
    def from_env(cls) -> "RLUSDConfig":
        from . import wallets
        return cls(issuer=wallets.rlusd_issuer())


def get_xrpl_client(rpc_url: Optional[str] = None) -> JsonRpcClient:
    """Open an XRPL JSON-RPC client.

    Network selection routes through :mod:`agentlevy.inference.wallets` —
    Mainnet uses ``XRPL_MAINNET_RPC_URL`` (default xrplcluster), Testnet uses
    ``XRPL_RPC_URL``. Pass ``rpc_url`` to override explicitly.
    """
    if rpc_url:
        return JsonRpcClient(rpc_url)
    from . import wallets
    return JsonRpcClient(wallets.rpc_url())


# ---------------------------------------------------------------------------
# Memo encoding
# ---------------------------------------------------------------------------

def _hex(s: str) -> str:
    return s.encode("utf-8").hex().upper()


def build_uor_memo(uor_address: str) -> Memo:
    """Build an XRPL :class:`Memo` carrying a UOR address.

    The memo binds the payment to a specific request UOR address. Auditors
    parsing the transaction can identify the memo by ``memo_type=uor-addr-1``
    and decode ``memo_data`` as UTF-8 to recover the address.
    """
    if not uor_address.startswith("sha256:"):
        raise ValueError(f"uor_address must start with 'sha256:', got {uor_address!r}")
    return Memo(
        memo_data=_hex(uor_address),
        memo_format=_hex(MEMO_FORMAT_TEXT_PLAIN),
        memo_type=_hex(MEMO_TYPE_UOR_ADDR_1),
    )


def parse_uor_memo(memo: dict | Memo) -> Optional[str]:
    """Extract the UOR address from a Memo dict if it's a ``uor-addr-1`` memo.

    Returns ``None`` if the memo type isn't ``uor-addr-1`` or the data
    can't be decoded as a UOR address.
    """
    if isinstance(memo, Memo):
        d = {
            "memo_type": memo.memo_type,
            "memo_data": memo.memo_data,
            "memo_format": memo.memo_format,
        }
    else:
        # Tx response uses CamelCase keys
        d = {
            "memo_type": memo.get("MemoType") or memo.get("memo_type"),
            "memo_data": memo.get("MemoData") or memo.get("memo_data"),
            "memo_format": memo.get("MemoFormat") or memo.get("memo_format"),
        }
    try:
        if not d["memo_type"] or not d["memo_data"]:
            return None
        memo_type = bytes.fromhex(d["memo_type"]).decode("utf-8")
        if memo_type != MEMO_TYPE_UOR_ADDR_1:
            return None
        addr = bytes.fromhex(d["memo_data"]).decode("utf-8")
        if not addr.startswith("sha256:"):
            return None
        return addr
    except (ValueError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# Trust line
# ---------------------------------------------------------------------------

def establish_trust_line(
    client: JsonRpcClient,
    wallet: Wallet,
    config: RLUSDConfig,
    limit: Decimal = DEFAULT_TRUST_LIMIT,
) -> dict:
    """Submit a TrustSet so ``wallet`` can hold RLUSD from ``config.issuer``.

    Idempotent at the protocol level — re-running just updates the limit.
    Returns the submit_and_wait result dict.
    """
    if wallet.classic_address == config.issuer:
        raise ValueError("Issuer cannot trust itself")
    ts = TrustSet(
        account=wallet.classic_address,
        limit_amount=IssuedCurrencyAmount(
            currency=config.currency_hex,
            issuer=config.issuer,
            value=str(limit),
        ),
    )
    signed = autofill_and_sign(ts, client, wallet)
    resp = submit_and_wait(signed, client)
    return resp.result


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

@dataclass
class PaymentResult:
    """The outcome of a submit_and_wait Payment."""
    txid: str
    validated: bool
    transaction_result: str
    ledger_index: Optional[int]
    raw: dict

    @property
    def succeeded(self) -> bool:
        return self.validated and self.transaction_result == "tesSUCCESS"


def build_rlusd_payment(
    *,
    from_address: str,
    to_address: str,
    rlusd_amount: Decimal,
    uor_memo_address: str,
    config: RLUSDConfig,
) -> Payment:
    """Construct an unsigned RLUSD :class:`Payment` carrying a UOR memo."""
    if rlusd_amount <= 0:
        raise ValueError(f"amount must be > 0, got {rlusd_amount}")
    return Payment(
        account=from_address,
        destination=to_address,
        amount=IssuedCurrencyAmount(
            currency=config.currency_hex,
            issuer=config.issuer,
            value=str(rlusd_amount),
        ),
        memos=[build_uor_memo(uor_memo_address)],
    )


def submit_rlusd_payment(
    client: JsonRpcClient,
    wallet: Wallet,
    payment: Payment,
) -> PaymentResult:
    """Autofill + sign + submit_and_wait. Returns the parsed result."""
    signed = autofill_and_sign(payment, client, wallet)
    resp = submit_and_wait(signed, client)
    r = resp.result
    return PaymentResult(
        txid=signed.get_hash(),
        validated=bool(r.get("validated", False)),
        transaction_result=r.get("meta", {}).get("TransactionResult", "?"),
        ledger_index=r.get("ledger_index"),
        raw=r,
    )


def pay_rlusd(
    client: JsonRpcClient,
    *,
    from_wallet: Wallet,
    to_address: str,
    rlusd_amount: Decimal,
    uor_memo_address: str,
    config: Optional[RLUSDConfig] = None,
) -> PaymentResult:
    """One-call wrapper: build, sign, submit, return result.

    Honors the ``INFERENCE_USE_XRP_FALLBACK`` env flag — when set, dispatches
    to native-XRP settlement instead of RLUSD IssuedCurrency. The flag exists
    because Testnet RLUSD faucets gate behind wallet-connect UX that doesn't
    play well with seed-generated demo wallets. Production / Mainnet runs
    with the flag off (or unset) settle in RLUSD as designed.
    """
    if _xrp_fallback_enabled():
        return pay_xrp_native(
            client,
            from_wallet=from_wallet,
            to_address=to_address,
            xrp_amount=rlusd_amount,
            uor_memo_address=uor_memo_address,
        )
    cfg = config or RLUSDConfig.from_env()
    p = build_rlusd_payment(
        from_address=from_wallet.classic_address,
        to_address=to_address,
        rlusd_amount=rlusd_amount,
        uor_memo_address=uor_memo_address,
        config=cfg,
    )
    return submit_rlusd_payment(client, from_wallet, p)


# ---------------------------------------------------------------------------
# XRP-native fallback
# ---------------------------------------------------------------------------

def _xrp_fallback_enabled() -> bool:
    """Whether to settle in native XRP instead of RLUSD.

    Set ``INFERENCE_USE_XRP_FALLBACK=true`` in ``.env`` to flip on. Used for
    Testnet validation when RLUSD faucet access is gated. Mainnet demo runs
    with the flag off so settlement is real RLUSD.
    """
    from . import wallets
    return wallets.settlement_currency() == "XRP"


def build_xrp_payment(
    *,
    from_address: str,
    to_address: str,
    xrp_amount: Decimal,
    uor_memo_address: str,
) -> Payment:
    """Construct an unsigned native-XRP :class:`Payment` with a UOR memo.

    Uses the same UOR memo encoding as :func:`build_rlusd_payment` so the
    audit-trail invariants and replay-resistance properties hold identically.
    """
    if xrp_amount <= 0:
        raise ValueError(f"amount must be > 0, got {xrp_amount}")
    drops = xrp_to_drops(float(xrp_amount))
    return Payment(
        account=from_address,
        destination=to_address,
        amount=str(drops),
        memos=[build_uor_memo(uor_memo_address)],
    )


def pay_xrp_native(
    client: JsonRpcClient,
    *,
    from_wallet: Wallet,
    to_address: str,
    xrp_amount: Decimal,
    uor_memo_address: str,
) -> PaymentResult:
    """Native-XRP one-call wrapper. Same return shape as :func:`pay_rlusd`."""
    p = build_xrp_payment(
        from_address=from_wallet.classic_address,
        to_address=to_address,
        xrp_amount=xrp_amount,
        uor_memo_address=uor_memo_address,
    )
    return submit_rlusd_payment(client, from_wallet, p)  # autofill+sign+submit is generic


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

@dataclass
class PaymentVerification:
    """Result of verifying a payment against an expectation."""
    valid: bool
    reason: Optional[str]
    txid: str
    from_address: Optional[str]
    to_address: Optional[str]
    amount_value: Optional[str]
    amount_currency: Optional[str]
    amount_issuer: Optional[str]
    uor_memo_address: Optional[str]


def fetch_tx(client: JsonRpcClient, txid: str) -> dict:
    """Fetch a transaction by hash. Raises if not found / not validated."""
    resp = client.request(Tx(transaction=txid))
    if not resp.is_successful():
        raise RuntimeError(f"Tx lookup failed for {txid}: {resp.result}")
    return resp.result


def verify_rlusd_payment(
    client: JsonRpcClient,
    *,
    txid: str,
    expected_from: Optional[str],
    expected_to: str,
    expected_amount: Decimal,
    expected_uor_memo_address: str,
    config: Optional[RLUSDConfig] = None,
) -> PaymentVerification:
    """Fetch a transaction by hash and verify it matches the expectation.

    Checks (in order):

    1. Transaction exists and is validated.
    2. ``TransactionType == Payment``.
    3. ``Account == expected_from``.
    4. ``Destination == expected_to``.
    5. ``Amount.currency`` and ``Amount.issuer`` match the configured RLUSD.
    6. ``Amount.value >= expected_amount`` (paying more is allowed; paying
       less is not). Using ``>=`` rather than ``==`` because an agent might
       round up or pre-pay; the server only insists the threshold was met.
    7. Memo with ``memo_type=uor-addr-1`` and data matching
       ``expected_uor_memo_address`` is present.

    Any check failure produces ``valid=False`` and a human-readable ``reason``.
    """
    cfg = config or RLUSDConfig.from_env()
    try:
        r = fetch_tx(client, txid)
    except RuntimeError as exc:
        return PaymentVerification(
            valid=False, reason=f"tx fetch failed: {exc}",
            txid=txid, from_address=None, to_address=None,
            amount_value=None, amount_currency=None, amount_issuer=None,
            uor_memo_address=None,
        )

    tx = r.get("tx_json") or r  # xrpl-py 4.x returns tx_json subtree
    meta = r.get("meta") or {}

    def _bad(reason: str) -> PaymentVerification:
        return PaymentVerification(
            valid=False, reason=reason,
            txid=txid,
            from_address=tx.get("Account"),
            to_address=tx.get("Destination"),
            amount_value=(tx.get("Amount") or {}).get("value") if isinstance(tx.get("Amount"), dict) else None,
            amount_currency=(tx.get("Amount") or {}).get("currency") if isinstance(tx.get("Amount"), dict) else None,
            amount_issuer=(tx.get("Amount") or {}).get("issuer") if isinstance(tx.get("Amount"), dict) else None,
            uor_memo_address=None,
        )

    if not r.get("validated"):
        return _bad("transaction not yet validated")
    if meta.get("TransactionResult") != "tesSUCCESS":
        return _bad(f"transaction did not succeed: {meta.get('TransactionResult')}")
    if tx.get("TransactionType") != "Payment":
        return _bad(f"not a Payment (got {tx.get('TransactionType')!r})")
    if expected_from is not None and tx.get("Account") != expected_from:
        return _bad(f"wrong sender: {tx.get('Account')!r} != {expected_from!r}")
    if tx.get("Destination") != expected_to:
        return _bad(f"wrong destination: {tx.get('Destination')!r} != {expected_to!r}")

    amt = tx.get("DeliverMax") or tx.get("Amount")
    # XRP-fallback mode: Amount is a string of drops, not an issued-currency dict.
    if isinstance(amt, str):
        if not _xrp_fallback_enabled():
            return _bad(
                f"amount is native XRP (drops={amt}) but server is in RLUSD mode"
            )
        try:
            drops = Decimal(amt)
            paid = drops / Decimal(1_000_000)
        except Exception as exc:
            return _bad(f"unparseable XRP drops: {exc}")
        if paid < expected_amount:
            return _bad(f"underpaid: {paid} XRP < {expected_amount} XRP")
        # Currency = "XRP" sentinel for the verification result; no issuer.
        amount_currency_for_result = "XRP"
        amount_issuer_for_result = None
    elif isinstance(amt, dict):
        if _xrp_fallback_enabled():
            return _bad(
                f"amount is issued-currency {amt!r} but server is in XRP-fallback mode"
            )
        if amt.get("currency") != cfg.currency_hex:
            return _bad(
                f"wrong currency: {amt.get('currency')!r} != {cfg.currency_hex!r}"
            )
        if amt.get("issuer") != cfg.issuer:
            return _bad(
                f"wrong issuer: {amt.get('issuer')!r} != {cfg.issuer!r}"
            )
        try:
            paid = Decimal(str(amt.get("value", "0")))
        except Exception as exc:
            return _bad(f"unparseable amount: {exc}")
        if paid < expected_amount:
            return _bad(f"underpaid: {paid} < {expected_amount}")
        amount_currency_for_result = cfg.currency_hex
        amount_issuer_for_result = cfg.issuer
    else:
        return _bad(f"amount is neither drops-string nor issued-currency dict: {amt!r}")

    # Memo check
    memos = tx.get("Memos") or []
    found_addr: Optional[str] = None
    for m in memos:
        memo = m.get("Memo") or {}
        addr = parse_uor_memo(memo)
        if addr is not None:
            found_addr = addr
            break
    if found_addr is None:
        return _bad("no uor-addr-1 memo present")
    if found_addr != expected_uor_memo_address:
        return _bad(
            f"wrong uor address in memo: {found_addr!r} != {expected_uor_memo_address!r}"
        )

    return PaymentVerification(
        valid=True, reason=None,
        txid=txid,
        from_address=expected_from or tx.get("Account"),
        to_address=expected_to,
        amount_value=str(paid),
        amount_currency=amount_currency_for_result,
        amount_issuer=amount_issuer_for_result,
        uor_memo_address=found_addr,
    )
