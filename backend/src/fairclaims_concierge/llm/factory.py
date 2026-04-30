"""LLM factory — creates the configured backend.

Two backends in FairClaims: `mock` (canned, always available) and `api`
(Groq via OpenAI-compatible client).

Unlike CEN, FairClaims does NOT wrap the primary in a fallback that
silently returns mock canned text on failure. CEN's mock returns
workflow-relevant generic responses that are acceptable in a navigator
context; in FairClaims they'd be incoherent for residents. Instead:

- Primary (Groq) raises on failure → caught in `_synthesize_with_llm`
  → falls through to rule-based FAQ-verbatim reply with `mode=synthesis`.
- Groq 429 rate-limit responses surface as `httpx.HTTPStatusError`
  through the same path. The widget keeps working under rate limit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from fairclaims_concierge.llm.mock import MockLanguageModel

if TYPE_CHECKING:
    from fairclaims_concierge.config import Settings
    from fairclaims_concierge.llm.base import LanguageModel
    from fairclaims_concierge.llm.openai_compat import OpenAICompatLanguageModel


def create_language_model(
    settings: "Settings",
) -> Union["MockLanguageModel", "OpenAICompatLanguageModel"]:
    """Build the configured LLM backend."""
    if settings.llm_backend == "api":
        from fairclaims_concierge.llm.openai_compat import OpenAICompatLanguageModel

        return OpenAICompatLanguageModel(
            base_url=settings.llm_api_base,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout,
        )
    return MockLanguageModel()
