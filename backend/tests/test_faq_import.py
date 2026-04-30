"""Parse the bundled FairClaims_Resident_FAQ_Master seed file."""

from __future__ import annotations

from pathlib import Path

import pytest

from fairclaims_concierge.core.faq_import import (
    import_faqs,
    parse_faq_markdown,
    seed_default_faqs_if_empty,
)


SEED_PATH = (
    Path(__file__).resolve().parent.parent
    / "seed"
    / "fairclaims_resident_faqs.md"
)


def test_seed_file_exists():
    assert SEED_PATH.exists(), f"seed missing at {SEED_PATH}"


def test_parser_extracts_at_least_50_entries():
    text = SEED_PATH.read_text(encoding="utf-8")
    parsed = parse_faq_markdown(text)
    assert len(parsed) >= 50, f"only parsed {len(parsed)} entries"


def test_parser_assigns_pillar_tags():
    text = SEED_PATH.read_text(encoding="utf-8")
    parsed = parse_faq_markdown(text)
    pillars = {p.module_name for p in parsed if p.module_name}
    # Resident library covers at least these two top-of-file pillars.
    assert "charity_care" in pillars
    assert "medical_debt" in pillars


def test_parser_includes_sources_in_answer_body():
    text = SEED_PATH.read_text(encoding="utf-8")
    parsed = parse_faq_markdown(text)
    has_sources = sum(1 for p in parsed if "Sources:" in p.answer)
    assert has_sources >= len(parsed) * 0.5, "expected at least half of FAQs to carry sources"


@pytest.mark.asyncio
async def test_import_into_faq_store(faq_store):
    text = SEED_PATH.read_text(encoding="utf-8")
    n = await import_faqs(text=text, faq_store=faq_store, source_filename="seed.md")
    assert n >= 50
    listed = await faq_store.list_all()
    assert len(listed) == n


@pytest.mark.asyncio
async def test_seed_helper_idempotent(faq_store):
    """Second call seeds nothing — no duplicates."""
    n1 = await seed_default_faqs_if_empty(faq_store)
    assert n1 >= 50
    n2 = await seed_default_faqs_if_empty(faq_store)
    assert n2 == 0
    assert len(await faq_store.list_all()) == n1
