"""Admin endpoints for FAQ-gap research.

Two read-only endpoints behind a bearer-token gate. The token lives
in ``FAIRCLAIMS_ADMIN_TOKEN``; an empty value blocks every request.

These endpoints intentionally do NOT include the visitor_hash or the
answer text — only the question, page, and aggregates. The minimum
that's useful for prioritizing FAQ writes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from fairclaims_concierge.api.dependencies import (
    get_questions_log_store,
    require_admin_token,
)


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])


class UnmatchedRow(BaseModel):
    id: int
    asked_at: str
    question: str
    page_url: str
    user_agent_kind: str


class FAQCount(BaseModel):
    faq_id: str
    count: int


class UnmatchedCount(BaseModel):
    question: str
    count: int


class DigestResponse(BaseModel):
    period_days: int
    total: int
    matched: int
    unmatched: int
    top_faqs: list[FAQCount]
    top_unmatched_questions: list[UnmatchedCount]


@router.get("/questions/unmatched", response_model=list[UnmatchedRow])
async def list_unmatched(
    since: Optional[str] = Query(default=None, description="ISO8601 lower bound on asked_at"),
    limit: int = Query(default=200, ge=1, le=1000),
    store=Depends(get_questions_log_store),
) -> list[UnmatchedRow]:
    if store is None:
        raise HTTPException(status_code=503, detail="questions log not initialized")
    rows = await store.unmatched(since=since, limit=limit)
    return [UnmatchedRow(**row) for row in rows]


@router.get("/questions/digest", response_model=DigestResponse)
async def digest(
    days: int = Query(default=7, ge=1, le=365),
    store=Depends(get_questions_log_store),
) -> DigestResponse:
    if store is None:
        raise HTTPException(status_code=503, detail="questions log not initialized")
    data = await store.digest(days=days)
    return DigestResponse(**data)
