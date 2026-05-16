"""One-shot setup: mint the XLS-20 model NFT and write its ID to .env.

Usage::

    python scripts/mint_model_nft.py
    python scripts/mint_model_nft.py --owner-seed s... --metadata-uri https://...

What it does
------------

1. Loads ``.env``.
2. Reads or generates the model-owner wallet seed
   (``XRPL_INFERENCE_MODEL_OWNER_SEED``).
3. Confirms the wallet is funded with XRP (XLS-20 NFTokenMint needs the
   reserve + a tiny fee — about 10 XRP is plenty for the demo).
4. Submits an ``NFTokenMint`` with:

   * ``Account``: the owner wallet
   * ``NFTokenTaxon``: ``1`` (arbitrary; group identifier for related NFTs)
   * ``Flags``: ``TF_TRANSFERABLE`` (``8``)
   * ``URI``: hex-encoded metadata URI

5. Reads back the resulting ``NFTokenID`` from the transaction metadata.
6. Appends ``MODEL_NFT_ID`` + ``MODEL_NFT_OWNER_ADDRESS`` (+ optional
   ``MODEL_NFT_METADATA_URI`` and ``MODEL_NFT_NAME``) to ``.env`` for
   the inference server to load at startup.

Idempotency
-----------

This script is **not** idempotent: each run mints a new NFT and overwrites
the .env entries with the new NFTokenID. The previous NFT is left on the
ledger but stops being the "demo model NFT" once the new one is recorded.
Run once per fresh demo run, or read existing values from .env and skip
minting if already present.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv, set_key  # noqa: E402
from xrpl.clients import JsonRpcClient  # noqa: E402
from xrpl.models.requests import AccountInfo  # noqa: E402
from xrpl.models.transactions import NFTokenMint, NFTokenMintFlag  # noqa: E402
from xrpl.transaction import autofill_and_sign, submit_and_wait  # noqa: E402
from xrpl.utils import drops_to_xrp  # noqa: E402
from xrpl.wallet import Wallet  # noqa: E402


DEFAULT_METADATA_URI = (
    "https://raw.githubusercontent.com/maurathat/AgentLevy-XRPL-UOR/"
    "main/fixtures/model-card.json"
)
DEFAULT_MODEL_NAME = "RoyaltAI Demo LLM NFT — Claude Haiku 4.5"
NFT_TAXON = 1


def _hex(s: str) -> str:
    return s.encode("utf-8").hex().upper()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--owner-seed", help="Override XRPL_INFERENCE_MODEL_OWNER_SEED.")
    parser.add_argument(
        "--metadata-uri",
        default=DEFAULT_METADATA_URI,
        help="URI to embed in the NFT (default: repo-hosted model card).",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
        help="Human-readable model name to record in .env.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Mint but skip writing the result back to .env (dry run).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    dotenv_path = repo_root / ".env"
    load_dotenv(dotenv_path, override=True)

    # Route through the wallets module so Mainnet seeds come from macOS Keychain
    # with correct algorithm auto-detection (Xaman default is secp256k1; xrpl-py's
    # Wallet.from_seed defaults to ed25519 which would derive wrong addresses).
    from agentlevy.inference import wallets  # noqa: E402

    if args.owner_seed:
        # Explicit override path (Testnet only — Mainnet seeds should never be on CLI)
        from xrpl.constants import CryptoAlgorithm
        algo = CryptoAlgorithm.ED25519 if args.owner_seed.startswith("sEd") else CryptoAlgorithm.SECP256K1
        owner = Wallet.from_seed(args.owner_seed, algorithm=algo)
    else:
        owner = wallets.get_wallet("model_owner")

    rpc_url = wallets.rpc_url()
    network_name = wallets.network()
    print(f"Network: {network_name} ({rpc_url})")
    print(f"Model owner wallet: {owner.classic_address}")
    print(f"Metadata URI:       {args.metadata_uri}")
    print(f"Model name:         {args.model_name}")
    print()

    client = JsonRpcClient(rpc_url)

    # Confirm the wallet is funded
    info = client.request(AccountInfo(account=owner.classic_address, strict=True, ledger_index="validated"))
    if not info.is_successful():
        err = info.result.get("error", "")
        if err == "actNotFound":
            raise SystemExit(
                f"Owner wallet {owner.classic_address} is unfunded. "
                "Use the XRPL Testnet faucet to fund it before minting."
            )
        raise SystemExit(f"AccountInfo failed: {info.result}")
    balance_drops = int(info.result["account_data"]["Balance"])
    print(f"Balance: {drops_to_xrp(str(balance_drops))} XRP")
    print()

    # Build the mint
    mint = NFTokenMint(
        account=owner.classic_address,
        nftoken_taxon=NFT_TAXON,
        flags=NFTokenMintFlag.TF_TRANSFERABLE,
        uri=_hex(args.metadata_uri),
    )
    print("Minting NFTokenMint...")
    signed = autofill_and_sign(mint, client, owner)
    resp = submit_and_wait(signed, client)
    r = resp.result
    tx_result = r.get("meta", {}).get("TransactionResult", "?")
    validated = r.get("validated", False)
    print(f"  validated={validated}  TransactionResult={tx_result}")
    if not validated or tx_result != "tesSUCCESS":
        raise SystemExit("Mint did not validate as tesSUCCESS")

    # Pull NFTokenID out of meta
    nft_id = _find_minted_nftoken_id(r)
    if not nft_id:
        raise SystemExit(
            "Could not locate NFTokenID in transaction metadata. "
            "Check the tx by hash on the explorer."
        )

    explorer_host = "bithomp.com/explorer" if network_name == "mainnet" else "testnet.xrpl.org/nft"
    print()
    print(f"NFTokenID: {nft_id}")
    print(f"Owner:     {owner.classic_address}")
    print(f"Explorer:  https://{explorer_host}/{nft_id}")
    print(f"           (also viewable at https://livenet.xrpl.org/nft/{nft_id})" if network_name == "mainnet" else "")
    print()

    if args.no_write:
        print("(--no-write specified; .env not updated)")
        return

    set_key(str(dotenv_path), "MODEL_NFT_ID", nft_id)
    set_key(str(dotenv_path), "MODEL_NFT_OWNER_ADDRESS", owner.classic_address)
    set_key(str(dotenv_path), "MODEL_NFT_METADATA_URI", args.metadata_uri)
    set_key(str(dotenv_path), "MODEL_NFT_NAME", args.model_name)
    print(f"Wrote MODEL_NFT_* to {dotenv_path}")


def _find_minted_nftoken_id(result: dict) -> str | None:
    """Pull NFTokenID from CreatedNode entries in transaction metadata.

    xrpl-py exposes NFTokenID in two places depending on rippled version:
    - At ``result['meta']['nftoken_id']`` (newer rippled)
    - Inside CreatedNode entries in AffectedNodes (older / always-present)
    """
    meta = result.get("meta") or {}
    direct = meta.get("nftoken_id") or meta.get("NFTokenID")
    if direct:
        return direct
    for affected in meta.get("AffectedNodes", []):
        created = affected.get("CreatedNode") or {}
        if created.get("LedgerEntryType") == "NFTokenPage":
            nftokens = created.get("NewFields", {}).get("NFTokens", [])
            for entry in nftokens:
                token = entry.get("NFTokenID") or (entry.get("NFToken") or {}).get("NFTokenID")
                if token:
                    return token
        modified = affected.get("ModifiedNode") or {}
        if modified.get("LedgerEntryType") == "NFTokenPage":
            final = modified.get("FinalFields", {}).get("NFTokens", [])
            previous = modified.get("PreviousFields", {}).get("NFTokens", [])
            prev_ids = {
                (e.get("NFTokenID") or (e.get("NFToken") or {}).get("NFTokenID"))
                for e in previous
            }
            for entry in final:
                token = entry.get("NFTokenID") or (entry.get("NFToken") or {}).get("NFTokenID")
                if token and token not in prev_ids:
                    return token
    return None


if __name__ == "__main__":
    main()
