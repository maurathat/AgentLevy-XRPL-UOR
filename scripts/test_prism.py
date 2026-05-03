"""Phase 0.2 verification — confirms PRISM is wired up and triads are deterministic.

Run from the repo root with the venv active:

    python scripts/test_prism.py

This script tests three content types (plain string, JSON object, small file)
through the project's integration pattern:

    canonical bytes
        -> agentlevy.primitives.fingerprint.content_to_ring_element  (SHA-256, low N bytes)
        -> agentlevy.prism_layer.triad.compute_triad                  (Q(31) engine)
        -> Triad

It confirms:

  * same input -> same triad (deterministic)
  * different inputs -> different triads (collision-resistant)

It also exercises the display helpers (glyph + compact) so the audit trail
shows the same Braille glyph form UOR uses in published cert examples.

It does NOT yet enforce the project's canonical form for JSON; that lives in
agentlevy/primitives/canonical.py once Phase 2 starts. For Phase 0 we use a
JCS-adjacent stand-in (sort_keys + compact separators) just to prove the
projection pipeline is deterministic given identical bytes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the repo root importable so `from agentlevy...` and `from vendor.prism...` work
# regardless of where the script is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentlevy.primitives.display import compact, glyph, hex_full  # noqa: E402
from agentlevy.prism_layer.triad import (  # noqa: E402
    QUANTUM,
    compute_triad,
    engine_info,
)


def triad_summary(t):
    """Audit-trail-friendly summary of a triad. Uses display helpers so the
    32-byte datum doesn't dominate console output."""
    return {
        "datum_compact": compact(t.datum, n=4),
        "glyph": glyph(t.datum),
        "total_stratum": t.total_stratum,
        "width": t.width,
    }


def assert_eq(name, a, b):
    ok = a == b
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print(f"    a = {a}")
        print(f"    b = {b}")
        raise SystemExit(1)


def assert_neq(name, a, b):
    ok = a != b
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print(f"    a == b == {a}")
        raise SystemExit(1)


def main() -> None:
    info = engine_info()
    print(
        f"PRISM engine: Q({info['quantum']}) "
        f"width={info['width_bytes']} bytes "
        f"bits={info['bits']} "
        f"(UOR-canonical width matches cert:ModuleCertificate)"
    )
    print("Q0 algebra was verified by the engine on import.")
    print()

    # --- Content type 1: plain string ---
    print("[1/3] plain string")
    s1 = "hello world"
    s2 = "hello world"
    s3 = "hello world!"
    t1 = compute_triad(s1.encode("utf-8"))
    t2 = compute_triad(s2.encode("utf-8"))
    t3 = compute_triad(s3.encode("utf-8"))
    print(f"      triad(s1) = {triad_summary(t1)}")
    assert_eq("identical strings -> identical triads", t1.datum, t2.datum)
    assert_neq("different strings -> different triads", t1.datum, t3.datum)
    print()

    # --- Content type 2: JSON object ---
    # NOTE: This uses sort_keys/separators as a STAND-IN for canonical form.
    # The real project canonical form is defined in CANONICAL_FORM.md and
    # implemented in agentlevy/primitives/canonical.py. For Phase 0 we only
    # need to confirm the projection is deterministic given identical bytes.
    print("[2/3] JSON object (sort_keys+compact as placeholder canonical form)")
    j1 = {"task_id": "abc", "price": 100, "buyer": "alice"}
    j2 = {"price": 100, "buyer": "alice", "task_id": "abc"}  # same content, different key order
    j3 = {"task_id": "abc", "price": 101, "buyer": "alice"}  # one field different
    b1 = json.dumps(j1, sort_keys=True, separators=(",", ":")).encode("utf-8")
    b2 = json.dumps(j2, sort_keys=True, separators=(",", ":")).encode("utf-8")
    b3 = json.dumps(j3, sort_keys=True, separators=(",", ":")).encode("utf-8")
    t1, t2, t3 = compute_triad(b1), compute_triad(b2), compute_triad(b3)
    print(f"      triad(j1) = {triad_summary(t1)}")
    assert_eq("same content / different key order -> same triad", t1.datum, t2.datum)
    assert_neq("one field differs -> different triad", t1.datum, t3.datum)
    print()

    # --- Content type 3: small file ---
    print("[3/3] small file")
    here = Path(__file__).resolve().parent
    f1 = here / "test_prism.py"      # this file
    f2 = here.parent / "README.md"   # different file
    b1 = f1.read_bytes()
    b1_again = f1.read_bytes()
    b2 = f2.read_bytes()
    t1 = compute_triad(b1)
    t2 = compute_triad(b1_again)
    t3 = compute_triad(b2)
    print(f"      triad(test_prism.py) = {triad_summary(t1)}")
    print(f"      triad(README.md)     = {triad_summary(t3)}")
    assert_eq("file read twice -> same triad", t1.datum, t2.datum)
    assert_neq("different files -> different triads", t1.datum, t3.datum)
    print()

    # Display-helper sanity: glyph round-trips bytes correctly.
    print("[display] glyph round-trip")
    sample = compute_triad(b"hello world")
    gl = glyph(sample.datum)
    print(f"      glyph(triad('hello world')) = {gl}")
    print(f"      hex_full                    = {hex_full(sample.datum)}")
    rt_bytes = bytes(ord(c) - 0x2800 for c in gl)
    assert_eq("glyph bytes round-trip", rt_bytes, bytes(sample.datum))
    print()

    print("ALL CHECKS PASSED")
    print()
    print(f"At Q({QUANTUM}), the datum is the full SHA-256 digest of the canonical bytes.")
    print("Triads at this width are byte-compatible with UOR's store:uorAddress (32 bytes).")


if __name__ == "__main__":
    main()
