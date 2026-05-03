"""Phase 0.6 verification - confirms Anthropic API connectivity and tool use.

Run from the repo root with the venv active:

    python scripts/test_llm.py

What this does:
  1. Loads ANTHROPIC_API_KEY from .env.
  2. Sends a plain "hello world" message to confirm connectivity, key
     validity, and SDK version compatibility.
  3. Sends a tool-use call that mirrors the shape of Phase 2.4 compliance-
     agent KYC extraction: synthetic corporate description in -> structured
     beneficial-ownership record out. Confirms structured output works.

Notes:
  - The model is set to claude-sonnet-4-5; this is the demo's intended model.
    If your account doesn't have access, swap to claude-3-5-sonnet-latest or
    claude-haiku-4-5 below.
  - This is a CONNECTIVITY test, not a production client. The real LLM
    client lives at agentlevy/llm/client.py (Phase 2.4) and adds caching,
    canonicalization, and the schema-validation layer per CANONICAL_FORM.md.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the repo root importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402


MODEL = "claude-sonnet-4-5"

EXTRACT_TOOL = {
    "name": "record_beneficial_ownership",
    "description": (
        "Record a structured beneficial-ownership extraction from a "
        "corporate-records description. Used by the compliance agent to "
        "produce the input to sanctions screening."
    ),
    "input_schema": {
        "type": "object",
        "required": ["company_name", "jurisdiction", "beneficial_owners"],
        "properties": {
            "company_name": {"type": "string"},
            "jurisdiction": {
                "type": "string",
                "description": "Country or US state of incorporation.",
            },
            "beneficial_owners": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "ownership_percent"],
                    "properties": {
                        "name": {"type": "string"},
                        "ownership_percent": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        "additionalProperties": False,
    },
}

SYNTHETIC_DOC = (
    "Acme Holdings LLC is a Delaware-incorporated holding company. "
    "Per its 2025 ownership disclosure, beneficial owners are John Doe "
    "(60% equity stake) and Jane Smith (40% equity stake). No other "
    "owners hold a stake exceeding the 25% reporting threshold."
)


def load_key() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    # override=True so the .env file beats any shell-level empty default.
    # Some launchers (including the Claude Code CLI session) export an empty
    # ANTHROPIC_API_KEY for safety; the project's .env should win locally.
    load_dotenv(repo_root / ".env", override=True)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is empty or missing in .env")
    if not key.startswith("sk-ant-"):
        print(
            "[warn] ANTHROPIC_API_KEY does not start with 'sk-ant-'. "
            "Continuing anyway."
        )
    return key


def hello_world(client: anthropic.Anthropic) -> None:
    print("[1/2] basic connectivity check")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=50,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: 'hello agentlevy' (lowercase, no punctuation).",
            }
        ],
    )
    text_blocks = [b.text for b in resp.content if b.type == "text"]
    text = "".join(text_blocks).strip()
    print(f"      model:       {resp.model}")
    print(f"      stop_reason: {resp.stop_reason}")
    print(f"      tokens:      in={resp.usage.input_tokens} out={resp.usage.output_tokens}")
    print(f"      reply:       {text!r}")
    if "hello agentlevy" not in text.lower():
        print("[FAIL] reply did not contain expected phrase.")
        raise SystemExit(1)
    print("      [PASS] connectivity OK")
    print()


def tool_use(client: anthropic.Anthropic) -> None:
    print("[2/2] tool use (structured output)")
    print(f"      input doc: {SYNTHETIC_DOC[:80]}...")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_beneficial_ownership"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract beneficial ownership from the following corporate "
                    "description and call the record_beneficial_ownership tool "
                    "with the structured result.\n\n"
                    f"{SYNTHETIC_DOC}"
                ),
            }
        ],
    )
    print(f"      stop_reason: {resp.stop_reason}")
    print(f"      tokens:      in={resp.usage.input_tokens} out={resp.usage.output_tokens}")

    tool_blocks = [b for b in resp.content if b.type == "tool_use"]
    if not tool_blocks:
        print("[FAIL] model did not produce a tool_use block.")
        print(f"       full response.content: {resp.content}")
        raise SystemExit(1)

    tool = tool_blocks[0]
    print(f"      tool_name:   {tool.name}")
    print(f"      tool_input:  {json.dumps(tool.input, indent=10)[:400]}")

    # Light schema sanity check
    inp = tool.input
    required = ("company_name", "jurisdiction", "beneficial_owners")
    missing = [k for k in required if k not in inp]
    if missing:
        print(f"[FAIL] tool input missing required keys: {missing}")
        raise SystemExit(1)
    if not isinstance(inp["beneficial_owners"], list) or not inp["beneficial_owners"]:
        print("[FAIL] beneficial_owners is empty or not a list.")
        raise SystemExit(1)

    total_pct = sum(o.get("ownership_percent", 0) for o in inp["beneficial_owners"])
    print(f"      sum of ownership_percent: {total_pct}")
    if not (95 <= total_pct <= 105):
        print(
            f"[warn] sum of ownership_percent = {total_pct} (not ~100). "
            "Not a hard fail; flagged for review."
        )
    print("      [PASS] tool use OK")
    print()


def main() -> None:
    key = load_key()
    print(f"Anthropic SDK: {anthropic.__version__}")
    print(f"Model:         {MODEL}")
    print(f"Key:           sk-ant-...{key[-6:]}")
    print()

    client = anthropic.Anthropic(api_key=key)

    try:
        hello_world(client)
        tool_use(client)
    except anthropic.APIError as exc:
        print(f"[FAIL] Anthropic API error: {exc}")
        raise SystemExit(1)

    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
