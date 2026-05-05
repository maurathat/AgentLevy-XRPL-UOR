"""One-shot Hedera HCS topic creator for AgentLevy cert anchoring.

Creates a single HCS topic on the configured network, signed by the
operator account in .env, and prints the new topic ID for pasting into
``HEDERA_HCS_TOPIC_ID``.

Run once. The topic is permanent and reusable; every subsequent cert
anchor submits to this same topic.

Usage
-----
$ source .venv/bin/activate
$ python scripts/setup_hcs_topic.py

Prerequisites
-------------
.env must have:
  HEDERA_NETWORK             (testnet | mainnet | previewnet)
  HEDERA_OPERATOR_ID         (0.0.NNNNNN)
  HEDERA_OPERATOR_PRIVATE_KEY (DER-encoded hex from portal.hedera.com)

Topic configuration
-------------------
* memo: "AgentLevy cert anchor — Kessai Phase 2.X"
* admin key: operator (we keep ability to update the topic memo later)
* submit key: operator (only the operator can submit anchors; prevents
  third parties from polluting the topic with arbitrary cert hashes)

Cost: ~$0.01 worth of HBAR for topic creation. Trivial on testnet.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from hiero_sdk_python import (
    AccountId,
    Client,
    Network,
    PrivateKey,
)
from hiero_sdk_python.consensus.topic_create_transaction import (
    TopicCreateTransaction,
)

# Load the project's .env from the repo root (one level up from scripts/).
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

TOPIC_MEMO = "AgentLevy cert anchor — Kessai Phase 2.X"


def _require(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        sys.exit(
            f"FATAL: {name} is not set in {ENV_PATH}. "
            "Fill it in before running this script."
        )
    return val


def main() -> None:
    network_name = _require("HEDERA_NETWORK")
    operator_id_str = _require("HEDERA_OPERATOR_ID")
    operator_key_str = _require("HEDERA_OPERATOR_PRIVATE_KEY")

    print(f"Creating HCS topic on Hedera {network_name}...")
    print(f"  Operator: {operator_id_str}")

    operator_id = AccountId.from_string(operator_id_str)
    operator_key = PrivateKey.from_string(operator_key_str)

    client = Client(Network(network=network_name))
    client.set_operator(operator_id, operator_key)

    tx = (
        TopicCreateTransaction()
        .set_memo(TOPIC_MEMO)
        .set_admin_key(operator_key.public_key())
        .set_submit_key(operator_key.public_key())
    )
    receipt = tx.execute(client)
    topic_id = receipt.topic_id

    print()
    print("✓ Topic created successfully.")
    print(f"  Topic ID:   {topic_id}")
    print(f"  Memo:       {TOPIC_MEMO}")
    print(f"  Admin key:  operator (you)")
    print(f"  Submit key: operator (only you can publish anchors)")
    print()
    print("Paste this into .env:")
    print(f"  HEDERA_HCS_TOPIC_ID={topic_id}")
    print()
    print("Then flip MOCK_HEDERA=false to use the live topic.")


if __name__ == "__main__":
    main()
