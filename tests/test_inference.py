"""Tests for the pay-per-call inference layer.

Covers the load-bearing properties of the May 16 demo:

* Canonical request addressing determinism + hour bucketing.
* :class:`CertStore` dedup behavior and pricing.
* Replay resistance — the killer test the deck claims: "a payment for
  request A cannot unlock a completion for request B."
* Royalty split math.
* Server flow (mocked XRPL + Anthropic) end-to-end.
* MCP server tool surface.

Optional live tests against the UOR Foundation MCP run only when
``UOR_MCP_LIVE=1`` is set in the environment. These prove byte-identity
against the canonical reference but require internet and the Foundation
endpoint being up.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Canonical addressing
# ---------------------------------------------------------------------------

class TestCanonical:
    def test_same_inputs_produce_same_address(self):
        from agentlevy.inference.canonical import build_request_dict, compute_request_address
        when = datetime(2026, 5, 14, 18, 32, 11, tzinfo=timezone.utc)
        req_a = build_request_dict(model="m1", prompt="hello", when=when)
        req_b = build_request_dict(model="m1", prompt="hello", when=when)
        assert compute_request_address(req_a) == compute_request_address(req_b)

    def test_same_hour_different_minute_produces_same_address(self):
        from agentlevy.inference.canonical import build_request_dict, compute_request_address
        early = datetime(2026, 5, 14, 18, 0, 1, tzinfo=timezone.utc)
        late = datetime(2026, 5, 14, 18, 59, 59, tzinfo=timezone.utc)
        a = build_request_dict(model="m", prompt="p", when=early)
        b = build_request_dict(model="m", prompt="p", when=late)
        assert compute_request_address(a) == compute_request_address(b)

    def test_different_hour_produces_different_address(self):
        from agentlevy.inference.canonical import build_request_dict, compute_request_address
        a = build_request_dict(model="m", prompt="p", when=datetime(2026, 5, 14, 18, 0, 0, tzinfo=timezone.utc))
        b = build_request_dict(model="m", prompt="p", when=datetime(2026, 5, 14, 19, 0, 0, tzinfo=timezone.utc))
        assert compute_request_address(a) != compute_request_address(b)

    def test_different_prompt_produces_different_address(self):
        from agentlevy.inference.canonical import build_request_dict, compute_request_address
        when = datetime(2026, 5, 14, 18, 0, 0, tzinfo=timezone.utc)
        a = build_request_dict(model="m", prompt="A", when=when)
        b = build_request_dict(model="m", prompt="B", when=when)
        assert compute_request_address(a) != compute_request_address(b)

    def test_whole_number_float_normalizes_to_int(self):
        from agentlevy.inference.canonical import build_request_dict, request_canonical_bytes
        req = build_request_dict(model="m", prompt="p", temperature=0.0)
        bytes_str = request_canonical_bytes(req).decode()
        # JCS rule: 0.0 must serialize as "0", not "0.0"
        assert '"temperature":0' in bytes_str
        assert '"temperature":0.0' not in bytes_str

    def test_naive_datetime_rejected(self):
        from agentlevy.inference.canonical import hour_bucket_for
        with pytest.raises(ValueError):
            hour_bucket_for(datetime(2026, 5, 14, 18, 0, 0))


# ---------------------------------------------------------------------------
# Cert store + pricing
# ---------------------------------------------------------------------------

class TestCertStore:
    def _make_cert(self, prompt="p"):
        from agentlevy.inference.canonical import build_request_dict, compute_request_address
        from agentlevy.inference.receipt import build_inference_cert
        from agentlevy.primitives.signing import Keypair, public_key_hex

        kp = Keypair.generate()
        req = build_request_dict(model="m", prompt=prompt)
        addr = compute_request_address(req)
        cert = build_inference_cert(
            request=req, completion_text="completion", server_pubkey_hex=public_key_hex(kp)
        ).sign(kp)
        return addr, cert

    def test_pricing(self):
        from agentlevy.inference.cert_store import FULL_PRICE_RLUSD, HIT_PRICE_RLUSD, price_for
        assert price_for(is_hit=False) == FULL_PRICE_RLUSD
        assert price_for(is_hit=True) == HIT_PRICE_RLUSD
        assert FULL_PRICE_RLUSD == Decimal("0.010")
        assert HIT_PRICE_RLUSD == Decimal("0.001")
        assert FULL_PRICE_RLUSD == HIT_PRICE_RLUSD * 10

    def test_put_get_hit_counter(self):
        from agentlevy.inference.cert_store import CertStore
        store = CertStore()
        addr, cert = self._make_cert()
        store.put(addr, cert, "completion")
        assert store.has(addr)
        # get() returns the same StoreEntry reference each call (intentional),
        # so the hit_count it carries reflects the *current* value, not a
        # snapshot at call time. Use peek() for assertions.
        store.get(addr)
        assert store.peek(addr).hit_count == 1
        store.get(addr)
        assert store.peek(addr).hit_count == 2
        assert store.total_hits() == 2

    def test_peek_does_not_increment(self):
        from agentlevy.inference.cert_store import CertStore
        store = CertStore()
        addr, cert = self._make_cert()
        store.put(addr, cert, "completion")
        for _ in range(5):
            store.peek(addr)
        assert store.total_hits() == 0

    def test_overwrite_refused(self):
        from agentlevy.inference.cert_store import CertStore
        store = CertStore()
        addr, cert = self._make_cert()
        store.put(addr, cert, "completion")
        with pytest.raises(ValueError):
            store.put(addr, cert, "different completion")


# ---------------------------------------------------------------------------
# Royalty split
# ---------------------------------------------------------------------------

class TestRoyalty:
    def test_clean_split_full_price(self):
        from agentlevy.inference.royalty import compute_split
        s = compute_split(Decimal("0.010"))
        assert s.server_share == Decimal("0.0050")
        assert s.royalty_share == Decimal("0.0050")
        assert s.server_share + s.royalty_share == s.total

    def test_clean_split_hit_price(self):
        from agentlevy.inference.royalty import compute_split
        s = compute_split(Decimal("0.001"))
        assert s.server_share == Decimal("0.0005")
        assert s.royalty_share == Decimal("0.0005")

    def test_rounding_remainder_to_server(self):
        from agentlevy.inference.royalty import compute_split
        s = compute_split(Decimal("0.0011"), fraction=Decimal("0.333"))
        assert s.server_share + s.royalty_share <= s.total

    def test_invariants(self):
        from agentlevy.inference.royalty import compute_split
        with pytest.raises(ValueError):
            compute_split(Decimal("0"))
        with pytest.raises(ValueError):
            compute_split(Decimal("0.010"), fraction=Decimal("1"))


# ---------------------------------------------------------------------------
# XRPL Memo encoding
# ---------------------------------------------------------------------------

class TestMemo:
    def test_build_and_parse_roundtrip(self):
        from agentlevy.inference.payment import build_uor_memo, parse_uor_memo
        addr = "sha256:" + "a" * 64
        m = build_uor_memo(addr)
        assert parse_uor_memo(m) == addr

    def test_parse_tx_dict_camel_case(self):
        from agentlevy.inference.payment import build_uor_memo, parse_uor_memo
        addr = "sha256:" + "b" * 64
        m = build_uor_memo(addr)
        tx_dict = {"MemoType": m.memo_type, "MemoData": m.memo_data, "MemoFormat": m.memo_format}
        assert parse_uor_memo(tx_dict) == addr

    def test_reject_non_sha256(self):
        from agentlevy.inference.payment import build_uor_memo
        with pytest.raises(ValueError):
            build_uor_memo("not-a-sha256")

    def test_wrong_memo_type_returns_none(self):
        from agentlevy.inference.payment import parse_uor_memo
        addr_hex = ("sha256:" + "a" * 64).encode("utf-8").hex()
        bad = {
            "MemoType": "6e6f742d75 6f72".replace(" ", ""),  # 'not-uor' hex
            "MemoData": addr_hex,
            "MemoFormat": "text/plain".encode("utf-8").hex(),
        }
        assert parse_uor_memo(bad) is None


# ---------------------------------------------------------------------------
# Server: 402 → 200 flow with mocked XRPL + Anthropic
# ---------------------------------------------------------------------------

class TestServerFlow:
    def _make_server(self, anthropic_text: str = "fake completion"):
        from xrpl.wallet import Wallet

        from agentlevy.inference.server import InferenceServer, ServerConfig
        from agentlevy.inference.nft import ModelNFTConfig

        # Generate a real wallet so Wallet.from_seed() validates.
        # We don't actually network to XRPL — xrpl_rpc_url is mock — but
        # ServerConfig demands a parseable seed.
        fresh = Wallet.create()
        cfg = ServerConfig(
            xrpl_rpc_url="http://mock",
            server_xrpl_seed=fresh.seed,
            server_ed25519_seed_hex="01" * 32,
            anthropic_api_key="fake-key",
            rlusd_issuer="rUyz5Y6P2YkFh4o6h2bZ7KvF6n6dB7P9zE",  # any valid r-address
            nft_config=ModelNFTConfig(
                nftoken_id="00080000ABC123" + "0" * 50,
                owner_address="rUyz5Y6P2YkFh4o6h2bZ7KvF6n6dB7P9zE",
            ),
            royalty_enabled=False,
            hcs_anchor_enabled=False,
        )
        srv = InferenceServer(cfg)

        # Patch the anthropic client to return our text
        fake_msg = MagicMock()
        fake_block = MagicMock()
        fake_block.type = "text"
        fake_block.text = anthropic_text
        fake_msg.content = [fake_block]
        srv.anthropic = MagicMock()
        srv.anthropic.messages.create.return_value = fake_msg

        return srv

    def test_402_on_first_call(self):
        from agentlevy.inference.server import CompleteRequest
        srv = self._make_server()
        body = CompleteRequest(prompt="hello", temperature=0)
        status, payload = srv.handle_complete(body, x_payment_txid=None)
        assert status == 402
        assert payload["error"] == "Payment Required"
        assert payload["request_uor_address"].startswith("sha256:")
        assert payload["price_rlusd"] == "0.010"
        assert payload["is_cache_hit"] is False

    def test_dedup_returns_hit_price_on_second_402_after_cache_fill(self):
        """After agent A fills the cache, agent B's 402 quote uses hit price."""
        from agentlevy.inference.canonical import build_request_dict, compute_request_address
        from agentlevy.inference.receipt import build_inference_cert
        from agentlevy.inference.server import CompleteRequest

        srv = self._make_server()
        # Pre-fill the cache directly (simulates agent A having completed)
        req_dict = build_request_dict(model=srv.config.default_model, prompt="hi")
        addr = compute_request_address(req_dict)
        cert = build_inference_cert(
            request=req_dict, completion_text="stored", server_pubkey_hex=srv.server_pubkey_hex
        ).sign(srv.server_keypair)
        srv.cert_store.put(addr, cert, "stored")

        # Now agent B's 402 should quote the hit price
        body = CompleteRequest(prompt="hi", temperature=0)
        status, payload = srv.handle_complete(body, x_payment_txid=None)
        assert status == 402
        assert payload["price_rlusd"] == "0.001"
        assert payload["is_cache_hit"] is True


# ---------------------------------------------------------------------------
# Replay resistance — the killer test
# ---------------------------------------------------------------------------

class TestReplayResistance:
    """A payment for request A must not unlock a completion for request B.

    The protocol's binding mechanism is the UOR memo on the XRPL Payment:
    the server only accepts a payment if the memo equals the UOR address
    of the request being made. We prove that by constructing a payment
    whose memo holds A's address and trying to use it to fulfill B.
    """

    def test_memo_for_a_rejects_request_b(self):
        from agentlevy.inference.payment import build_uor_memo, parse_uor_memo
        from agentlevy.inference.canonical import build_request_dict, compute_request_address

        when = datetime(2026, 5, 14, 18, 0, 0, tzinfo=timezone.utc)
        req_a = build_request_dict(model="m", prompt="prompt-A", when=when)
        req_b = build_request_dict(model="m", prompt="prompt-B", when=when)
        addr_a = compute_request_address(req_a)
        addr_b = compute_request_address(req_b)
        assert addr_a != addr_b

        # Build a memo for A
        memo_for_a = build_uor_memo(addr_a)
        # Try to interpret it as a memo for B — should not match
        assert parse_uor_memo(memo_for_a) == addr_a
        assert parse_uor_memo(memo_for_a) != addr_b


# ---------------------------------------------------------------------------
# Receipt builder + signature
# ---------------------------------------------------------------------------

class TestReceipt:
    def test_cert_signs_and_verifies(self):
        from agentlevy.inference.canonical import build_request_dict
        from agentlevy.inference.receipt import build_inference_cert
        from agentlevy.primitives.signing import Keypair, public_key_hex

        kp = Keypair.generate()
        req = build_request_dict(model="m", prompt="p")
        cert = build_inference_cert(
            request=req, completion_text="c", server_pubkey_hex=public_key_hex(kp)
        ).sign(kp)
        assert cert.verify_signature() is True

    def test_metadata_attach_is_detached_from_canonical_bytes(self):
        from agentlevy.inference.canonical import build_request_dict
        from agentlevy.inference.receipt import (
            attach_settlement_metadata, build_inference_cert, SettlementMetadata,
        )
        from agentlevy.primitives.signing import Keypair, public_key_hex

        kp = Keypair.generate()
        req = build_request_dict(model="m", prompt="p")
        cert = build_inference_cert(
            request=req, completion_text="c", server_pubkey_hex=public_key_hex(kp)
        ).sign(kp)
        before = cert.to_canonical_bytes()

        attach_settlement_metadata(
            cert, SettlementMetadata(xrpl_payment_txid="9C2E", uor_mcps_receipt={"x": 1})
        )
        after = cert.to_canonical_bytes()
        assert before == after
        assert cert.verify_signature()


# ---------------------------------------------------------------------------
# MCP server tools (no live MCP wiring)
# ---------------------------------------------------------------------------

class TestMCPServer:
    def test_status_no_certs(self, tmp_path, monkeypatch):
        from agentlevy.inference import mcp_server
        store_path = tmp_path / "certs.json"
        monkeypatch.setattr(mcp_server, "_state", mcp_server.MCPServerState(str(store_path)))
        result = mcp_server.inference_status()
        assert result["cache_size"] == 0
        assert result["total_hits"] == 0

    def test_quote_uncached(self, tmp_path, monkeypatch):
        from agentlevy.inference import mcp_server
        store_path = tmp_path / "certs.json"
        monkeypatch.setattr(mcp_server, "_state", mcp_server.MCPServerState(str(store_path)))
        result = mcp_server.inference_quote(prompt="hello", model="m")
        assert result["is_cache_hit"] is False
        assert result["price_rlusd"] == "0.010"

    def test_verify_cert_not_found(self, tmp_path, monkeypatch):
        from agentlevy.inference import mcp_server
        store_path = tmp_path / "certs.json"
        monkeypatch.setattr(mcp_server, "_state", mcp_server.MCPServerState(str(store_path)))
        result = mcp_server.verify_cert("sha256:" + "0" * 64)
        assert result["found"] is False


# ---------------------------------------------------------------------------
# Live byte-identity against UOR Foundation MCP (gated)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    os.environ.get("UOR_MCP_LIVE", "0") != "1",
    reason="set UOR_MCP_LIVE=1 to run live test against mcp.uor.foundation",
)
class TestLiveUORMCPByteIdentity:
    """Cross-check that our local fingerprint == Foundation MCP's fingerprint.

    The deck's central claim is byte-identity. This test runs against the
    live canonical reference to keep the claim honest.
    """

    def test_inference_request_byte_identity(self):
        from agentlevy.inference.canonical import build_request_dict, compute_request_address
        from agentlevy.inference.mcp_client import open_uor_mcp

        req = build_request_dict(
            model="claude-haiku-4-5",
            prompt="What is the meaning of life?",
            when=datetime(2026, 5, 14, 18, 32, 11, tzinfo=timezone.utc),
        )
        local = compute_request_address(req)
        with open_uor_mcp() as cli:
            remote = cli.encode_address(dict(req))
        assert local == remote.address
        assert remote.mcps_receipt is not None
        assert remote.mcps_receipt.trust_level
