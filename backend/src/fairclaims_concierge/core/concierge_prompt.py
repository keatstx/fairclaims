"""Prompt assembly for the LLM-backed concierge.

Loads ``backend/prompts/concierge.md`` once, builds a context block from
the retrieved FAQ chunks, and renders the final prompt.

FairClaims has no workflow / case / chat history to fold in, so the
context block is FAQ-only — much simpler than CEN's three-source fuse.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List


_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "prompts"
    / "concierge.md"
)


@lru_cache(maxsize=1)
def _load_template() -> str:
    """Load the prompt template once. lru_cache so repeat callers
    don't re-read the file."""
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Defensive: ship a minimal fallback if the template file is
        # missing (e.g., partial deploy). Prevents 500s.
        return (
            "You are the FairClaims Assistant. Speak warmly, briefly, "
            "at an 8th-grade reading level. Ground every answer in the "
            "context below.\n\n{context_block}\n\nQuestion: {question}\n\n"
            "Reply:"
        )


def build_context_block(*, chunks_text: List[str]) -> str:
    """Compose the {context_block} the prompt expects.

    Returns a numbered list of FAQ chunks, or empty string when no
    chunks matched. The LLM still gets the question without grounding
    in that case, but the prompt instructs it to refer the resident to
    Get Started rather than synthesize from thin air.
    """
    if not chunks_text:
        return ""
    chunk_lines = [f"  [{i + 1}] {c}" for i, c in enumerate(chunks_text)]
    return "## FAQs and references\n" + "\n\n".join(chunk_lines)


def render_prompt(*, context_block: str, question: str) -> str:
    template = _load_template()
    return template.format(context_block=context_block, question=question)
