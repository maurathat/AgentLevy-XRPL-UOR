"""Tests for the Phase 2.4 LLM stack scaffold (schemas, cache, client).

Covers:
  * agentlevy.llm.schemas — Pydantic round-trips, validation
  * agentlevy.llm.cache — key determinism, miss/hit, mode switching
  * agentlevy.llm.client — tool-name derivation, cache-mode roundtrip
    using a hand-written fixture (no API key required)

The live-API path is exercised only when both ANTHROPIC_API_KEY is set
AND RUN_LIVE_LLM_TESTS=true. This keeps the suite green on contributors'
machines and CI without hitting the API.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Make repo root importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentlevy.llm.cache import CacheMiss, LLMCache  # noqa: E402
from agentlevy.llm.client import LLMClient, _tool_name_for  # noqa: E402
from agentlevy.llm.schemas import (  # noqa: E402
    BeneficialOwner,
    BeneficialOwnershipExtraction,
    NegotiationTurn,
    SanctionsHit,
    SanctionsScreenResult,
)


# ---------------------------------------------------------------------------
# Schemas — BeneficialOwnership
# ---------------------------------------------------------------------------

def test_beneficial_owner_constructs():
    o = BeneficialOwner(name="Alice Corp", ownership_percentage=51.0, role="UBO")
    assert o.name == "Alice Corp"
    assert o.ownership_percentage == 51.0


def test_beneficial_owner_percentage_bounds():
    with pytest.raises(ValueError):
        BeneficialOwner(name="X", ownership_percentage=-1.0)
    with pytest.raises(ValueError):
        BeneficialOwner(name="X", ownership_percentage=101.0)


def test_beneficial_owner_extra_fields_rejected():
    with pytest.raises(ValueError):
        BeneficialOwner(name="X", ownership_percentage=10.0, surprise="nope")


def test_extraction_round_trip():
    e = BeneficialOwnershipExtraction(
        subject_entity="Acme Holdings Ltd",
        owners=[
            BeneficialOwner(name="Alice", ownership_percentage=60.0),
            BeneficialOwner(name="Bob", ownership_percentage=40.0),
        ],
    )
    d = e.model_dump(mode="json")
    e2 = BeneficialOwnershipExtraction.model_validate(d)
    assert e2 == e


# ---------------------------------------------------------------------------
# Schemas — Sanctions
# ---------------------------------------------------------------------------

def test_sanctions_hit_severity_whitelist():
    SanctionsHit(name_screened="Alice", severity="clear")
    SanctionsHit(name_screened="Alice", severity="exact_match",
                 matched_sanctions_entry="OFAC SDN: Alice Smith")
    with pytest.raises(ValueError):
        SanctionsHit(name_screened="Alice", severity="probably_ok")


def test_sanctions_screen_has_any_hit():
    clean = SanctionsScreenResult(
        sanctions_list_version="OFAC-SDN-2026-04-15",
        screened_at=datetime.now(timezone.utc),
        hits=[SanctionsHit(name_screened="Alice", severity="clear")],
    )
    assert clean.has_any_hit() is False

    flagged = SanctionsScreenResult(
        sanctions_list_version="OFAC-SDN-2026-04-15",
        screened_at=datetime.now(timezone.utc),
        hits=[
            SanctionsHit(name_screened="Alice", severity="clear"),
            SanctionsHit(name_screened="Bob", severity="strong_match",
                         matched_sanctions_entry="EU SAN: Robert Q."),
        ],
    )
    assert flagged.has_any_hit() is True


# ---------------------------------------------------------------------------
# Schemas — Negotiation
# ---------------------------------------------------------------------------

def test_negotiation_turn_index_bounds():
    NegotiationTurn(turn_index=1, actor="buyer", action="request", message="")
    NegotiationTurn(turn_index=4, actor="compliance", action="accept", message="")
    with pytest.raises(ValueError):
        NegotiationTurn(turn_index=0, actor="buyer", action="request", message="")
    with pytest.raises(ValueError):
        NegotiationTurn(turn_index=5, actor="buyer", action="request", message="")


def test_negotiation_action_whitelist():
    with pytest.raises(ValueError):
        NegotiationTurn(turn_index=1, actor="buyer", action="haggle", message="")


# ---------------------------------------------------------------------------
# Cache — key determinism + miss/hit
# ---------------------------------------------------------------------------

def test_cache_key_is_deterministic(tmp_path):
    cache = LLMCache(mode="live", cache_dir=tmp_path)
    req = {"model": "claude-sonnet-4-5", "messages": [{"role": "user", "content": "hi"}]}
    k1 = cache.key_for(req)
    k2 = cache.key_for(req)
    assert k1 == k2
    assert len(k1) == 64  # sha256 hex


def test_cache_key_changes_with_request(tmp_path):
    cache = LLMCache(mode="live", cache_dir=tmp_path)
    a = cache.key_for({"prompt": "hello"})
    b = cache.key_for({"prompt": "world"})
    assert a != b


def test_cache_put_then_get_roundtrip(tmp_path):
    cache = LLMCache(mode="live", cache_dir=tmp_path)
    req = {"prompt": "test"}
    resp = {"tool_input": {"foo": "bar"}, "raw": {}}
    cache.put(req, resp)
    assert cache.has(req) is True
    assert cache.get(req) == resp


def test_cache_miss_raises(tmp_path):
    cache = LLMCache(mode="cache", cache_dir=tmp_path)
    with pytest.raises(CacheMiss):
        cache.get({"prompt": "never recorded"})


def test_invalid_cache_mode_rejected(tmp_path):
    with pytest.raises(ValueError, match="LLM_CACHE_MODE"):
        LLMCache(mode="banana", cache_dir=tmp_path)


def test_cache_mode_from_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_CACHE_MODE", "cache")
    cache = LLMCache(cache_dir=tmp_path)
    assert cache.mode == "cache"


# ---------------------------------------------------------------------------
# Client — tool-name derivation
# ---------------------------------------------------------------------------

def test_tool_name_snake_case():
    assert _tool_name_for(BeneficialOwnershipExtraction) == "emit_beneficial_ownership_extraction"
    assert _tool_name_for(SanctionsScreenResult) == "emit_sanctions_screen_result"
    assert _tool_name_for(NegotiationTurn) == "emit_negotiation_turn"


# ---------------------------------------------------------------------------
# Client — cache-mode end-to-end (no API key needed)
# ---------------------------------------------------------------------------

def test_complete_structured_replays_from_cache(tmp_path):
    """Pre-seed a cache fixture, then verify the client reads it back as
    a validated Pydantic model — no API call."""
    cache = LLMCache(mode="cache", cache_dir=tmp_path)
    client = LLMClient(model="claude-sonnet-4-5", cache=cache)

    system = "You are a test agent."
    user = "Extract beneficial ownership from: Alice 60%, Bob 40%."
    schema = BeneficialOwnershipExtraction

    # Build the same request envelope the client would build.
    request = {
        "model": "claude-sonnet-4-5",
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "tool": {
            "name": _tool_name_for(schema),
            "input_schema": schema.model_json_schema(),
        },
        "max_tokens": 4096,
        "temperature": 0.0,
    }
    fixture = {
        "tool_input": {
            "subject_entity": "Acme Test",
            "owners": [
                {"name": "Alice", "ownership_percentage": 60.0},
                {"name": "Bob", "ownership_percentage": 40.0},
            ],
        },
        "raw": {},
    }
    cache.put(request, fixture)

    # Now the client should replay it.
    result = client.complete_structured(system=system, user=user, schema=schema)
    assert isinstance(result, BeneficialOwnershipExtraction)
    assert result.subject_entity == "Acme Test"
    assert len(result.owners) == 2
    assert result.owners[0].name == "Alice"


def test_complete_structured_validates_response_against_schema(tmp_path):
    """If the cached fixture is malformed, validation raises."""
    cache = LLMCache(mode="cache", cache_dir=tmp_path)
    client = LLMClient(cache=cache)

    system = "S"
    user = "U"
    schema = BeneficialOwner
    request = {
        "model": "claude-sonnet-4-5",
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "tool": {
            "name": _tool_name_for(schema),
            "input_schema": schema.model_json_schema(),
        },
        "max_tokens": 4096,
        "temperature": 0.0,
    }
    bad_fixture = {"tool_input": {"name": "Alice", "ownership_percentage": 200.0}, "raw": {}}
    cache.put(request, bad_fixture)

    with pytest.raises(ValueError):  # Pydantic ValidationError subclasses ValueError
        client.complete_structured(system=system, user=user, schema=schema)


def test_cache_miss_propagates(tmp_path):
    cache = LLMCache(mode="cache", cache_dir=tmp_path)
    client = LLMClient(cache=cache)
    with pytest.raises(CacheMiss):
        client.complete_structured(
            system="S", user="U", schema=BeneficialOwner,
        )


# ---------------------------------------------------------------------------
# Live API (skipped by default)
# ---------------------------------------------------------------------------

LIVE_LLM_ENABLED = (
    os.environ.get("RUN_LIVE_LLM_TESTS", "").lower() == "true"
    and os.environ.get("ANTHROPIC_API_KEY", "")
)


@pytest.mark.skipif(
    not LIVE_LLM_ENABLED,
    reason="Live LLM test disabled. Set RUN_LIVE_LLM_TESTS=true and ANTHROPIC_API_KEY.",
)
def test_live_complete_structured_smoke(tmp_path):
    """Hits the real API. Costs a few cents per run."""
    client = LLMClient(cache=LLMCache(mode="live", cache_dir=tmp_path))
    result = client.complete_structured(
        system="You are a precise extractor. Output only what is asked.",
        user='Subject entity: "Acme Holdings". Owners: Alice (60%), Bob (40%). '
             "Extract the beneficial ownership.",
        schema=BeneficialOwnershipExtraction,
    )
    assert isinstance(result, BeneficialOwnershipExtraction)
    assert "Acme" in result.subject_entity
    assert len(result.owners) >= 2
