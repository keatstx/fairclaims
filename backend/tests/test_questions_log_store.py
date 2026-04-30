"""Questions log: append, unmatched, digest."""

from __future__ import annotations

import pytest
import pytest_asyncio

from fairclaims_concierge.core.questions_log_store import QuestionsLogStore


@pytest_asyncio.fixture
async def log_store():
    store = QuestionsLogStore(":memory:")
    await store.initialize()
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_append_and_unmatched(log_store):
    await log_store.append(
        question="what is xyz?",
        answer_summary="no idea",
        top_faq_id=None,
        top_faq_score=None,
        matched=0,
        visitor_hash="hash1",
        page_url="/",
        user_agent_kind="desktop",
    )
    await log_store.append(
        question="what is charity care?",
        answer_summary="answered",
        top_faq_id="faq-1",
        top_faq_score=0.7,
        matched=1,
        visitor_hash="hash2",
        page_url="/pages/charity-care.html",
        user_agent_kind="mobile",
    )
    rows = await log_store.unmatched()
    assert len(rows) == 1
    assert rows[0]["question"] == "what is xyz?"
    assert rows[0]["page_url"] == "/"


@pytest.mark.asyncio
async def test_digest(log_store):
    for _ in range(3):
        await log_store.append(
            question="charity care?",
            answer_summary="ok",
            top_faq_id="faq-charity",
            top_faq_score=0.8,
            matched=1,
            visitor_hash="h",
            page_url="/",
            user_agent_kind="desktop",
        )
    await log_store.append(
        question="how do I file appeals on a Tuesday?",
        answer_summary="dunno",
        top_faq_id=None,
        top_faq_score=None,
        matched=0,
        visitor_hash="h",
        page_url="/pages/medical-debt.html",
        user_agent_kind="mobile",
    )
    d = await log_store.digest(days=7)
    assert d["total"] == 4
    assert d["matched"] == 3
    assert d["unmatched"] == 1
    top = {f["faq_id"]: f["count"] for f in d["top_faqs"]}
    assert top["faq-charity"] == 3
    assert d["top_unmatched_questions"][0]["question"] == "how do I file appeals on a Tuesday?"


@pytest.mark.asyncio
async def test_append_never_raises_on_bad_state(log_store):
    """Even after close, append should not raise — the rule is "never block the user."""
    await log_store.close()
    # Should silently no-op rather than crash.
    await log_store.append(
        question="q",
        answer_summary="a",
        top_faq_id=None,
        top_faq_score=None,
        matched=0,
        visitor_hash="h",
        page_url="/",
        user_agent_kind="desktop",
    )
