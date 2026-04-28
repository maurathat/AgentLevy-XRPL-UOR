"""Phase 0.2 verification — confirms PRISM is wired up and triads are deterministic.

Run from the repo root with the venv active:

    python scripts/test_prism.py

This script tests three content types (plain string, JSON object, small file)
through the canonical-bytes → SHA-256 → byte-tuple → triad pattern, and
confirms:
  * same input → same triad
  * different inputs → different triads

It does NOT yet enforce the project's canonical form for JSON; that lives in
agentlevy/primitives/canonical.py once Phase 2 starts. For Phase 0 we just want
to prove PRISM works end-to-end.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prism import Q  # noqa: E402  (PRISM is on path via .venv/.../prism_repo.pth)


# 256-bit engine: matches SHA-256 digest width exactly.
ENGINE = Q(31)  # width=32 bytes, bits=256


def triad_of(canonical_bytes: bytes):
    """The integration pattern: canonical bytes → SHA-256 → byte tuple → triad."""
    digest = hashlib.sha256(canonical_bytes).digest()
    return ENGINE.triad(tuple(digest))


def triad_summary(t):
    return {
        "datum_first8": t.datum[:8],
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
    print("PRISM engine:", f"Q(31) width={ENGINE.width} bits={ENGINE.bits}")
    ENGINE.verify()
    print("Q0 algebra verified (PRISM bootstraps Q0 verification on first use).")
    print()

    # --- Content type 1: plain string ---
    print("[1/3] plain string")
    s1 = "hello world"
    s2 = "hello world"
    s3 = "hello world!"
    t1 = triad_of(s1.encode("utf-8"))
    t2 = triad_of(s2.encode("utf-8"))
    t3 = triad_of(s3.encode("utf-8"))
    print(f"      triad(s1) = {triad_summary(t1)}")
    assert_eq("identical strings → identical triads", t1.datum, t2.datum)
    assert_neq("different strings → different triads", t1.datum, t3.datum)
    print()

    # --- Content type 2: JSON object ---
    # NOTE: This uses sort_keys/separators as a STAND-IN for canonical form.
    # The real project canonical form is defined in CANONICAL_FORM.md and
    # implemented in agentlevy/primitives/canonical.py. For Phase 0 we only
    # need to confirm PRISM is deterministic given identical bytes.
    print("[2/3] JSON object (sort_keys+compact as placeholder canonical form)")
    j1 = {"task_id": "abc", "price": 100, "buyer": "alice"}
    j2 = {"price": 100, "buyer": "alice", "task_id": "abc"}  # same content, different key order
    j3 = {"task_id": "abc", "price": 101, "buyer": "alice"}  # one field different
    b1 = json.dumps(j1, sort_keys=True, separators=(",", ":")).encode("utf-8")
    b2 = json.dumps(j2, sort_keys=True, separators=(",", ":")).encode("utf-8")
    b3 = json.dumps(j3, sort_keys=True, separators=(",", ":")).encode("utf-8")
    t1, t2, t3 = triad_of(b1), triad_of(b2), triad_of(b3)
    print(f"      triad(j1) = {triad_summary(t1)}")
    assert_eq("same content / different key order → same triad", t1.datum, t2.datum)
    assert_neq("one field differs → different triad", t1.datum, t3.datum)
    print()

    # --- Content type 3: small file ---
    print("[3/3] small file")
    here = Path(__file__).resolve().parent
    f1 = here / "test_prism.py"      # this file
    f2 = here.parent / "README.md"   # different file
    b1 = f1.read_bytes()
    b1_again = f1.read_bytes()
    b2 = f2.read_bytes()
    t1 = triad_of(b1)
    t2 = triad_of(b1_again)
    t3 = triad_of(b2)
    print(f"      triad(test_prism.py) = {triad_summary(t1)}")
    print(f"      triad(README.md)     = {triad_summary(t3)}")
    assert_eq("file read twice → same triad", t1.datum, t2.datum)
    assert_neq("different files → different triads", t1.datum, t3.datum)
    print()

    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
