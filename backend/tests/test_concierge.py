"""End-to-end concierge: guardrail, no-match, FAQ-grounded reply."""

from __future__ import annotations

import pytest

from fairclaims_concierge.core.concierge import answer_question
from fairclaims_concierge.llm.mock import MockLanguageModel


@pytest.mark.asyncio
async def test_guardrail_fires_on_legal_questions(faq_store):
    response, chunks = await answer_question(
        "should I sue this hospital?", faq_store=faq_store
    )
    assert response.mode == "guardrail"
    assert "Get Started" in response.answer
    assert chunks == []


@pytest.mark.asyncio
async def test_no_match_when_faq_store_empty(faq_store):
    response, chunks = await answer_question(
        "What is charity care?", faq_store=faq_store
    )
    assert response.mode == "no_match"
    assert chunks == []


@pytest.mark.asyncio
async def test_synthesis_returns_grounded_answer(faq_store):
    await faq_store.create(
        question="What is charity care?",
        answer="Charity care is free or reduced-cost hospital care for low-income patients.",
        module_name="charity_care",
    )
    await faq_store.create(
        question="Who qualifies for charity care?",
        answer="Families at or below 200% of the Federal Poverty Level qualify in Illinois.",
        module_name="charity_care",
    )
    response, chunks = await answer_question(
        "what is charity care", faq_store=faq_store, llm=MockLanguageModel()
    )
    # Mock LLM is intentionally skipped by the synthesizer — falls
    # through to rule-based which returns the top FAQ first paragraph.
    assert response.mode == "synthesis"
    assert "Charity care" in response.answer
    assert len(response.citations) >= 1
    assert response.citations[0].kind == "faq"
    assert chunks


@pytest.mark.asyncio
async def test_response_includes_citations_with_scores(faq_store):
    await faq_store.create(
        question="How do I appeal a denial?",
        answer="File an internal appeal with your insurer within 180 days.",
    )
    response, _ = await answer_question(
        "how do I appeal", faq_store=faq_store
    )
    assert response.mode == "synthesis"
    assert response.citations
    assert response.citations[0].score > 0
    assert response.citations[0].faq_id
