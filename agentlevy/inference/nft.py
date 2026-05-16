"""XLS-20 model NFT — on-chain identity for the LLM provider.

The NFT represents the model itself: ``Claude Haiku 4.5`` (for the May 16 demo)
or in production any model an LLM provider chooses to register. The NFT's
**owner field** is what the inference server reads to decide where to route
the royalty portion of each RLUSD payment.

Why this matters for the demo
-----------------------------

The audience can verify the demo's claims live, on-chain:

1. Stage output shows the NFTokenID.
2. Audience pastes the NFTokenID into the XRPL Testnet explorer
   (``https://testnet.xrpl.org/nft/<NFTokenID>``).
3. They see the NFT exists, who owns it (the ``model_owner_wallet``),
   and the metadata URI pointing at a model card.
4. They see royalty payments arriving at that owner wallet.

That's the "exists irl" moment — the model has a verifiable on-chain
identity, not a database row.

Per-call royalty mechanics
--------------------------

The standard XRPL ``TransferFee`` on an XLS-20 NFT applies only on
``NFTokenAcceptOffer`` transfers, **not on third-party Payments**. So we
do **not** rely on it for per-inference royalty. Instead:

* The server reads the NFT owner from the ledger.
* On each successful inference, the server sends a separate RLUSD Payment
  to the owner wallet for the royalty portion of the per-call price.
* Both payments carry the same UOR memo, binding the royalty to the specific
  inference request.

This is the "manual royalty split" pattern the deck Slide 11 names. A future
extension swaps this for ``XLS-100 SmartEscrow`` with a ``FinishFunction``
that splits at release time — strictly bigger scope, deferred past May 16.

Config
------

Two env vars, written by ``scripts/mint_model_nft.py`` during one-shot setup:

* ``MODEL_NFT_ID``            — the NFTokenID hex (16 bytes / 64 hex chars).
* ``MODEL_NFT_OWNER_ADDRESS`` — classic XRPL address holding the NFT.

The setup script also stores the owner wallet seed at
``XRPL_INFERENCE_MODEL_OWNER_SEED`` so the server (or audit code) can sign
the second payment if it needs to. For the May 16 demo, the model owner is
a stand-in wallet for "the LLM provider"; in production, the provider would
mint to their own wallet and keep the seed private.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountNFTs


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelNFTConfig:
    """The model NFT identity, loaded from env after setup."""
    nftoken_id: str
    owner_address: str
    metadata_uri: Optional[str] = None
    model_name: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ModelNFTConfig":
        nftoken_id = os.environ.get("MODEL_NFT_ID", "").strip()
        owner = os.environ.get("MODEL_NFT_OWNER_ADDRESS", "").strip()
        if not nftoken_id or not owner:
            raise RuntimeError(
                "MODEL_NFT_ID and MODEL_NFT_OWNER_ADDRESS must be set in .env. "
                "Run scripts/mint_model_nft.py to populate them."
            )
        return cls(
            nftoken_id=nftoken_id,
            owner_address=owner,
            metadata_uri=os.environ.get("MODEL_NFT_METADATA_URI", "").strip() or None,
            model_name=os.environ.get("MODEL_NFT_NAME", "").strip() or None,
        )


# ---------------------------------------------------------------------------
# Live ownership verification
# ---------------------------------------------------------------------------

@dataclass
class NFTOwnershipCheck:
    """Outcome of verifying that the NFT is still held by the expected wallet."""
    confirmed: bool
    reason: Optional[str]
    nftoken_id: str
    expected_owner: str
    metadata_uri_hex: Optional[str] = None


def verify_owner_holds_nft(
    client: JsonRpcClient,
    *,
    nftoken_id: str,
    expected_owner: str,
) -> NFTOwnershipCheck:
    """Confirm that ``expected_owner`` currently holds ``nftoken_id``.

    Walks pages of the owner's ``account_nfts`` list looking for the NFTokenID.
    Returns ``confirmed=True`` plus the hex-encoded metadata URI if found.

    Note: this only checks the *expected* owner. If the NFT has been
    transferred to a different wallet, this returns ``confirmed=False`` —
    we don't try to discover the new owner. For the demo, the NFT lives on
    the model_owner_wallet and never transfers; production should re-verify
    or use a different discovery mechanism.
    """
    marker: Optional[dict] = None
    while True:
        req = AccountNFTs(
            account=expected_owner,
            ledger_index="validated",
            marker=marker,
        )
        resp = client.request(req)
        if not resp.is_successful():
            return NFTOwnershipCheck(
                confirmed=False,
                reason=f"account_nfts request failed: {resp.result}",
                nftoken_id=nftoken_id,
                expected_owner=expected_owner,
            )
        for nft in resp.result.get("account_nfts", []):
            if nft.get("NFTokenID") == nftoken_id:
                return NFTOwnershipCheck(
                    confirmed=True,
                    reason=None,
                    nftoken_id=nftoken_id,
                    expected_owner=expected_owner,
                    metadata_uri_hex=nft.get("URI"),
                )
        marker = resp.result.get("marker")
        if not marker:
            break
    return NFTOwnershipCheck(
        confirmed=False,
        reason=f"NFTokenID not found on {expected_owner}",
        nftoken_id=nftoken_id,
        expected_owner=expected_owner,
    )


# ---------------------------------------------------------------------------
# Royalty recipient lookup
# ---------------------------------------------------------------------------

def lookup_royalty_recipient(
    client: Optional[JsonRpcClient] = None,
    config: Optional[ModelNFTConfig] = None,
    *,
    verify_live: bool = False,
) -> str:
    """Return the XRPL address that should receive the model royalty.

    Parameters
    ----------
    client
        If ``verify_live=True``, used to confirm the owner still holds the
        NFT. Optional when ``verify_live=False``.
    config
        Model NFT config; defaults to ``ModelNFTConfig.from_env()``.
    verify_live
        If True, call ``account_nfts`` against the owner to confirm they
        still hold the NFT. Raises if the live check fails. Default False
        for hot-path use; the demo runs this with True at the audit step.
    """
    cfg = config or ModelNFTConfig.from_env()
    if verify_live:
        if client is None:
            raise ValueError("verify_live=True requires a JsonRpcClient")
        check = verify_owner_holds_nft(
            client,
            nftoken_id=cfg.nftoken_id,
            expected_owner=cfg.owner_address,
        )
        if not check.confirmed:
            raise RuntimeError(
                f"NFT {cfg.nftoken_id} not held by {cfg.owner_address}: {check.reason}"
            )
    return cfg.owner_address
