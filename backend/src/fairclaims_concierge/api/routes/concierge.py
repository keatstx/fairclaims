"""Public concierge endpoint — POST /concierge/ask.

Single endpoint. No auth. No case scoping. PII-scrubs the question
before retrieval per the rule that the scrubber runs at every external
boundary. Question logging hooks land in Phase 4 — this Phase 3 pass
just gets the round-trip working end-to-end.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from fairclaims_concierge.api.dependencies import (
    get_faq_store,
    get_llm,
    get_questions_log_store,
    get_settings,
)
from fairclaims_concierge.config import Settings
from fairclaims_concierge.core.concierge import answer_question
from fairclaims_concierge.core.faq_store import FAQStore
from fairclaims_concierge.core.models import ConciergeQuery, ConciergeResponse
from fairclaims_concierge.privacy.pii_scrubber import create_scrubber


_scrubber = create_scrubber("regex")


router = APIRouter(tags=["concierge"])


@router.post("/concierge/ask", response_model=ConciergeResponse)
async def ask_concierge(
    body: ConciergeQuery,
    request: Request,
    faq_store: FAQStore = Depends(get_faq_store),
    settings: Settings = Depends(get_settings),
    llm=Depends(get_llm),
    questions_log_store=Depends(get_questions_log_store),
) -> ConciergeResponse:
    """Answer a resident's question against the FAQ library.

    Returns a guardrail refusal for medical/legal/financial questions,
    a no-match reply with no citations when nothing in the FAQ store
    matches, or a synthesized reply (LLM if configured, FAQ-verbatim
    fallback otherwise) with citations.
    """
    if not settings.concierge_enabled:
        raise HTTPException(
            status_code=503,
            detail="concierge disabled",
        )

    scrubbed = _scrubber.scrub(body.question)

    response, chunks = await answer_question(
        scrubbed,
        faq_store=faq_store,
        llm=llm,
    )

    # Phase 4 wires the questions_log here. For Phase 3 the dependency
    # is None and we skip silently. The hook is in place so Phase 4 is
    # purely additive in this file.
    if questions_log_store is not None:
        try:
            await _log_question(
                questions_log_store=questions_log_store,
                request=request,
                settings=settings,
                question=scrubbed,
                page_url=body.page_url or "",
                response=response,
                chunks=chunks,
            )
        except Exception:  # noqa: BLE001
            # Logging never blocks the user's reply.
            pass

    return response


async def _log_question(
    *,
    questions_log_store,
    request: Request,
    settings: Settings,
    question: str,
    page_url: str,
    response: ConciergeResponse,
    chunks,
) -> None:
    """Append a row to the questions_log. Wired in Phase 4."""
    from fairclaims_concierge.visitor_hash import compute_visitor_hash, user_agent_kind

    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else ""
    visitor_hash = compute_visitor_hash(
        ip=ip, user_agent=ua, salt=settings.visitor_hash_salt
    )

    matched = response.mode in {"llm_synthesis", "synthesis"} and bool(response.citations)
    top = response.citations[0] if response.citations else None

    await questions_log_store.append(
        question=question,
        answer_summary=response.answer[:200],
        top_faq_id=(top.faq_id if top else None),
        top_faq_score=(top.score if top else None),
        matched=1 if matched else 0,
        visitor_hash=visitor_hash,
        page_url=page_url,
        user_agent_kind=user_agent_kind(ua),
    )
