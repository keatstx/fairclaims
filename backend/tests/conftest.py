"""Shared test fixtures."""

from __future__ import annotations

import pytest_asyncio

from fairclaims_concierge.core.faq_store import FAQStore


@pytest_asyncio.fixture
async def faq_store():
    """An in-memory FAQ store, fresh per test."""
    store = FAQStore(":memory:")
    await store.initialize()
    yield store
    await store.close()
