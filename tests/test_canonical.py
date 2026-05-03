"""Tests for agentlevy.primitives.canonical.

Verifies UOR-Passport-compatible behavior:
  * Sorted keys
  * Compact separators
  * NFC normalization for non-ASCII content
  * Determinism (same input -> same bytes)
  * Byte-for-byte match against the live UOR MCP cross-check fixture
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Make the repo root importable so ``from agentlevy...`` resolves when this
# test is run via ``python -m pytest tests/`` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentlevy.primitives.canonical import to_canonical_bytes  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 — UOR cross-check (the empirical anchor)
# ---------------------------------------------------------------------------

def test_uor_passport_byte_identical():
    """The exact input we cross-checked live against mcp.uor.foundation/encode_address.

    Verified May 3 2026; result captured in docs/UOR_PASSPORT_VERIFIED.md.
    """
    obj = {"task_id": "abc", "price": 100, "buyer": "alice"}
    canonical = to_canonical_bytes(obj)
    assert canonical == b'{"buyer":"alice","price":100,"task_id":"abc"}'
    assert len(canonical) == 45  # UOR returned length: 45

    digest = hashlib.sha256(canonical).hexdigest()
    expected = "4cc1e2fc2d60c1e0ab7f6967a59e23ad04094cd3c01351971b8cb5aa26013e67"
    assert digest == expected, (
        f"Local canonicalization diverged from UOR MCP fixture. "
        f"Got {digest}, expected {expected}."
    )


# ---------------------------------------------------------------------------
# Test 2 — sort_keys
# ---------------------------------------------------------------------------

def test_keys_sorted_regardless_of_input_order():
    a = to_canonical_bytes({"task_id": "abc", "price": 100, "buyer": "alice"})
    b = to_canonical_bytes({"price": 100, "buyer": "alice", "task_id": "abc"})
    c = to_canonical_bytes({"buyer": "alice", "task_id": "abc", "price": 100})
    assert a == b == c


def test_nested_keys_also_sorted():
    obj = {"z": {"y": 1, "x": 2}, "a": {"d": 3, "c": 4}}
    canonical = to_canonical_bytes(obj)
    assert canonical == b'{"a":{"c":4,"d":3},"z":{"x":2,"y":1}}'


# ---------------------------------------------------------------------------
# Test 3 — compact separators (no whitespace)
# ---------------------------------------------------------------------------

def test_no_whitespace_in_canonical_form():
    canonical = to_canonical_bytes({"a": [1, 2, 3], "b": "hello"})
    s = canonical.decode("utf-8")
    assert " " not in s
    assert "\n" not in s
    assert "\t" not in s


# ---------------------------------------------------------------------------
# Test 4 — NFC normalization (the property tests for non-ASCII)
# ---------------------------------------------------------------------------

def test_nfc_collapses_composed_and_decomposed_unicode():
    """The whole reason we add NFC: same logical string in different
    Unicode normalization forms must hash to the same address."""
    composed = {"name": "café"}                                # é = U+00E9 (1 char)
    decomposed = {"name": "café"}                        # e + U+0301 (2 chars)
    # Sanity: the raw strings ARE different at the codepoint level
    assert composed["name"] != decomposed["name"]

    a = to_canonical_bytes(composed)
    b = to_canonical_bytes(decomposed)
    assert a == b, "NFC should collapse composed and decomposed forms to identical bytes"


def test_nfc_normalizes_dict_keys_too():
    """Keys with non-ASCII content must also NFC-normalize."""
    composed = {"café": 1}
    decomposed = {"café": 1}
    assert to_canonical_bytes(composed) == to_canonical_bytes(decomposed)


def test_nfc_in_nested_structures():
    composed = {"users": [{"name": "café"}]}
    decomposed = {"users": [{"name": "café"}]}
    assert to_canonical_bytes(composed) == to_canonical_bytes(decomposed)


# ---------------------------------------------------------------------------
# Test 5 — type passthrough
# ---------------------------------------------------------------------------

def test_int_passthrough():
    assert to_canonical_bytes(42) == b"42"


def test_str_passthrough():
    assert to_canonical_bytes("hello") == b'"hello"'


def test_bool_and_none():
    assert to_canonical_bytes(True) == b"true"
    assert to_canonical_bytes(False) == b"false"
    assert to_canonical_bytes(None) == b"null"


def test_list_passthrough():
    assert to_canonical_bytes([1, "a", None]) == b'[1,"a",null]'


def test_tuple_becomes_list():
    """Tuples are JSON-serialized as lists; the canonicalizer should not
    error and should produce the same bytes as the equivalent list."""
    assert to_canonical_bytes((1, 2, 3)) == to_canonical_bytes([1, 2, 3])


# ---------------------------------------------------------------------------
# Test 6 — refusals (NaN, Inf, non-string keys)
# ---------------------------------------------------------------------------

def test_rejects_nan():
    import pytest
    with pytest.raises(ValueError):
        to_canonical_bytes(float("nan"))


def test_rejects_inf():
    import pytest
    with pytest.raises(ValueError):
        to_canonical_bytes(float("inf"))


def test_rejects_negative_inf():
    import pytest
    with pytest.raises(ValueError):
        to_canonical_bytes(float("-inf"))


# ---------------------------------------------------------------------------
# Test 7 — determinism across runs
# ---------------------------------------------------------------------------

def test_idempotent_within_run():
    obj = {"x": 1, "y": [2, 3], "z": {"a": "b"}}
    a = to_canonical_bytes(obj)
    b = to_canonical_bytes(obj)
    assert a == b


def test_canonical_bytes_already_canonical_roundtrips():
    """Canonical bytes parsed back into Python and re-canonicalized must
    produce the same bytes. Important for cache-key invariants."""
    original = {"task_id": "abc", "price": 100}
    bytes_a = to_canonical_bytes(original)
    parsed = json.loads(bytes_a)
    bytes_b = to_canonical_bytes(parsed)
    assert bytes_a == bytes_b


if __name__ == "__main__":
    # Allow `python tests/test_canonical.py` to run a quick smoke without pytest.
    import unittest
    loader = unittest.TestLoader()
    # Generate test cases from the module-level functions
    suite = unittest.TestSuite()
    for name in sorted(globals()):
        if name.startswith("test_"):
            fn = globals()[name]
            tc = unittest.FunctionTestCase(fn)
            suite.addTest(tc)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
