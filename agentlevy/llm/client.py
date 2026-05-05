"""LLM client — Anthropic SDK wrapper with structured-output validation + cache.

Exposes a single ``LLMClient`` class. Agents (Phase 2.5) instantiate it
once and call ``.complete_structured()`` to get a Pydantic-validated
response with ``LLMCache`` automatically wrapping the call (live or
cache mode per .env).

Why one wrapper instead of using anthropic.Anthropic directly
-------------------------------------------------------------

* **Structured output is the only thing agents need.** Free-form text
  is harder to act on and harder to audit. Forcing every LLM call to
  return a Pydantic-validatable JSON object via tool use means parse
  failures surface at the boundary, not deep in agent code.

* **Cache discipline is invisible at the agent layer.** Agents call
  ``complete_structured()``; whether it hits the API or replays a
  fixture is an .env flag. Demos run on cache mode for determinism.

* **Cost + safety guardrails live here.** Default model, default
  max_tokens, default temperature, and abort-on-unexpected-tool-call
  policy are all enforced once instead of scattered.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Type, TypeVar

from anthropic import Anthropic
from pydantic import BaseModel, ValidationError

from agentlevy.llm.cache import CacheMiss, LLMCache


T = TypeVar("T", bound=BaseModel)


# Project default model. Override per-call if needed.
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.0  # Determinism wins for KYC; agents can opt in to >0.


class LLMClient:
    """Anthropic SDK wrapper with structured output + fixture cache.

    Parameters
    ----------
    api_key
        Anthropic API key. Defaults to the ``ANTHROPIC_API_KEY`` env var.
    model
        Model ID. Defaults to ``claude-sonnet-4-5``.
    cache
        Optional pre-built ``LLMCache``. If None, builds a default one
        using ``LLM_CACHE_MODE`` env var.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        cache: Optional[LLMCache] = None,
    ) -> None:
        self.model = model
        self.cache = cache or LLMCache()
        # Lazy-init the API client only when needed (cache-mode runs
        # never need an API key).
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._anthropic: Optional[Anthropic] = None

    @property
    def anthropic(self) -> Anthropic:
        """Lazy Anthropic client. Raises if API key missing AND we need it."""
        if self._anthropic is None:
            if not self._api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set. Either populate .env or "
                    "use LLM_CACHE_MODE=cache (with pre-recorded fixtures)."
                )
            self._anthropic = Anthropic(api_key=self._api_key)
        return self._anthropic

    # ------------------------------------------------------------------
    # Structured-output completion
    # ------------------------------------------------------------------

    def complete_structured(
        self,
        *,
        system: str,
        user: str,
        schema: Type[T],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> T:
        """Call the LLM and parse the response as the given Pydantic schema.

        Builds a request envelope, hashes it for the cache, then either
        replays from fixture (cache mode) or hits the API (live mode,
        recording the response after).

        Parameters
        ----------
        system
            System prompt — agent role + behavior contract.
        user
            User message — task-specific input.
        schema
            Pydantic model class. The LLM is forced to call a tool whose
            input schema matches this model; the tool input is
            ``schema.model_validate(...)``ed before return.
        """
        # Build the canonical request envelope. This becomes the cache key.
        request = {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "tool": {
                "name": _tool_name_for(schema),
                "input_schema": schema.model_json_schema(),
            },
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if self.cache.mode == "cache":
            response = self.cache.get(request)  # raises CacheMiss
        else:
            response = self._call_api(request)
            self.cache.put(request, response)

        # Extract the tool input and validate it as the requested schema.
        try:
            tool_input = response["tool_input"]
        except (KeyError, TypeError) as e:
            raise RuntimeError(
                f"Cached/live response missing 'tool_input' key: {response!r}"
            ) from e
        return schema.model_validate(tool_input)

    # ------------------------------------------------------------------
    # Live API call (pulled out so cache mode can avoid SDK init)
    # ------------------------------------------------------------------

    def _call_api(self, request: dict) -> dict:
        """Make the actual Anthropic API call, return a shape ready for cache.

        Returned dict has the form ``{"tool_input": {...}, "raw": {...}}``
        — ``tool_input`` is what the agent layer cares about; ``raw`` is
        the full SDK response for audit/debug.
        """
        response = self.anthropic.messages.create(
            model=request["model"],
            system=request["system"],
            messages=request["messages"],
            max_tokens=request["max_tokens"],
            temperature=request["temperature"],
            tool_choice={"type": "tool", "name": request["tool"]["name"]},
            tools=[{
                "name": request["tool"]["name"],
                "description": (
                    "Emit the structured result for this task. Required."
                ),
                "input_schema": request["tool"]["input_schema"],
            }],
        )

        # Find the tool_use block. tool_choice="tool" forces exactly one.
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                return {
                    "tool_input": block.input,
                    "raw": response.model_dump(mode="json"),
                }
        raise RuntimeError(
            f"LLM returned no tool_use block; response: {response.content!r}"
        )


def _tool_name_for(schema: Type[BaseModel]) -> str:
    """Convert e.g. ``BeneficialOwnershipExtraction`` to ``emit_beneficial_ownership_extraction``."""
    import re
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", schema.__name__).lower()
    return f"emit_{snake}"
