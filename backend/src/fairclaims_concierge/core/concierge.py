"""Concierge service — FAQ-grounded synthesis with guardrail + fallback.

Pipeline per request:

    user question (PII-scrubbed by caller)
       │
       ├─► hard guardrail (medical / legal / financial)  ─► fixed refusal
       │
       ▼
    retrieve top-K FAQs from the FAQ store (TF-IDF + cosine)
       │
       ▼
    synthesis layer
       • LLM (Groq via openai_compat):  grounded-prompt synthesis
       • fallback (mock or LLM error):  rule-based first-paragraph reply
       │
       ▼
    response { answer, mode, citations }   +   fused chunks (for logging)

CEN fuses three retrieval sources (FAQs, current workflow node, case
context). FairClaims is FAQ-only — no workflows, no case, no history.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from fairclaims_concierge.core.concierge_prompt import build_context_block, render_prompt
from fairclaims_concierge.core.faq_store import FAQStore
from fairclaims_concierge.core.models import ConciergeCitation, ConciergeResponse


# ── Guardrails (deterministic, fire even when no LLM) ────────────────


_OUT_OF_SCOPE_KEYWORDS = {
    "diagnose",
    "diagnosis",
    "prescribe",
    "prescription",
    "lawsuit",
    "sue ",
    "attorney",
    "settlement",
    "should i pay",
    "should i sign",
    "is this legal",
    "is this fraud",
    "what dose",
    "what medication",
}

_OUT_OF_SCOPE_REPLY = (
    "I'm going to stop short of that one — that's a question for a real "
    "lawyer, doctor, or financial counselor. I can explain how programs "
    "like charity care or appeals work in general, but I can't give "
    "advice for your specific case. The best next step is the Get "
    "Started page — a FairClaims advocate will reach out, and it costs "
    "you nothing."
)

_NO_MATCH_REPLY = (
    "I don't have a clean answer for that yet. Try rephrasing it, or "
    "visit the Get Started page — a FairClaims advocate can talk it "
    "through with you. (Your question is logged so we can add it to "
    "the FAQ.)"
)


def _is_out_of_scope(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _OUT_OF_SCOPE_KEYWORDS)


# ── Retrieval ────────────────────────────────────────────────────────


@dataclass
class RetrievedChunk:
    """One grounding chunk produced by the FAQ retriever."""

    text: str
    score: float
    citation: ConciergeCitation


async def _retrieve_faqs(
    *,
    question: str,
    faq_store: FAQStore,
    top_k: int = 3,
) -> List[RetrievedChunk]:
    matches = await faq_store.search(question, top_k=top_k)
    out: List[RetrievedChunk] = []
    for faq, score in matches:
        out.append(
            RetrievedChunk(
                text=faq.answer,
                score=float(score),
                citation=ConciergeCitation(
                    faq_id=faq.id,
                    kind="faq",
                    question=faq.question,
                    score=round(float(score), 3),
                ),
            )
        )
    return out


# ── Synthesis ────────────────────────────────────────────────────────


async def _synthesize_with_llm(
    *,
    llm,
    question: str,
    chunks: List[RetrievedChunk],
) -> Optional[str]:
    """LLM-grounded conversational reply.

    Returns None when the LLM isn't configured, the backend is mock, or
    the call fails — caller falls back to the rule-based path. Groq
    429s land here as ``httpx.HTTPStatusError`` and flow through the
    same fallback (the FallbackLanguageModel wrapper catches them
    upstream, but defense in depth is cheap).
    """
    if llm is None:
        return None
    backend = getattr(llm, "backend_name", "")
    if "mock" in backend.lower():
        return None
    chunks_text = [c.text for c in chunks]
    context_block = build_context_block(chunks_text=chunks_text)
    prompt = render_prompt(context_block=context_block, question=question)
    try:
        return (await llm.generate(prompt, max_tokens=320)).strip()
    except Exception:  # noqa: BLE001
        return None


def _synthesize_rule_based(chunks: List[RetrievedChunk]) -> str:
    """Rule-based fallback when no LLM is configured (or LLM failed).

    Returns the first paragraph of the top-scored FAQ verbatim. Not
    chatty, but grounded — the resident sees something useful even
    without an LLM round-trip.
    """
    if not chunks:
        return _NO_MATCH_REPLY
    return _first_paragraph(chunks[0].text)


def _first_paragraph(text: str) -> str:
    for para in text.split("\n\n"):
        s = para.strip()
        if s:
            return s
    return text.strip()


# ── Public entry point ──────────────────────────────────────────────


async def answer_question(
    question: str,
    *,
    faq_store: FAQStore,
    llm: Optional[object] = None,
) -> Tuple[ConciergeResponse, List[RetrievedChunk]]:
    """Answer a resident's question.

    Returns ``(response, fused_chunks)`` so the caller can log the top
    match (faq_id, score) without re-querying. The caller is
    responsible for PII-scrubbing the question before invoking.
    """
    # 1) Hard guardrail.
    if _is_out_of_scope(question):
        return (
            ConciergeResponse(answer=_OUT_OF_SCOPE_REPLY, mode="guardrail"),
            [],
        )

    # 2) Retrieve top-K FAQs.
    chunks = await _retrieve_faqs(question=question, faq_store=faq_store)

    # 3) No match → fixed reply with no citations. Logged as unmatched
    # so it surfaces in the FAQ-gap report.
    if not chunks:
        return (
            ConciergeResponse(answer=_NO_MATCH_REPLY, mode="no_match"),
            [],
        )

    # 4) Try LLM synthesis. Fall back to rule-based on any failure.
    citations = [c.citation for c in chunks]
    answer = await _synthesize_with_llm(llm=llm, question=question, chunks=chunks)
    if answer:
        mode = "llm_synthesis"
    else:
        answer = _synthesize_rule_based(chunks)
        mode = "synthesis"

    return (
        ConciergeResponse(answer=answer, mode=mode, citations=citations),
        chunks,
    )
