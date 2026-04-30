"""Dependency injection for FastAPI routes.

Module-level globals + ``init_dependencies(...)`` setter is intentional
— FastAPI's ``Depends`` on a function lets routes pull from a single
shared instance without weaving them through every signature.

CEN ships a much wider surface here (sessions, projects, audit, sop,
storage, event bus, engines, chat, current_user). FairClaims trims to
just the four things the public concierge route needs:

    settings
    faq_store
    llm
    questions_log_store    (added in Phase 4)
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Header, HTTPException

from fairclaims_concierge.config import Settings
from fairclaims_concierge.core.faq_store import FAQStore


# Module-level state. Set once in app.py lifespan via init_dependencies.
_settings: Optional[Settings] = None
_faq_store: Optional[FAQStore] = None
_llm: Optional[object] = None
# questions_log_store wired in Phase 4 — declared here so the accessor
# exists from day one and routes can import it ahead of the wiring.
_questions_log_store: Optional[object] = None


def init_dependencies(
    *,
    settings: Settings,
    faq_store: FAQStore,
    llm: Optional[object] = None,
    questions_log_store: Optional[object] = None,
) -> None:
    global _settings, _faq_store, _llm, _questions_log_store
    _settings = settings
    _faq_store = faq_store
    _llm = llm
    _questions_log_store = questions_log_store


def get_settings() -> Settings:
    if _settings is None:
        raise RuntimeError("Settings not initialized — call init_dependencies first")
    return _settings


def get_faq_store() -> FAQStore:
    if _faq_store is None:
        raise RuntimeError("FAQ store not initialized — call init_dependencies first")
    return _faq_store


def get_llm() -> Optional[object]:
    return _llm


def get_questions_log_store() -> Optional[object]:
    return _questions_log_store


def require_admin_token(authorization: Optional[str] = Header(default=None)) -> None:
    """Bearer-token gate for /admin/* endpoints.

    Empty ``FAIRCLAIMS_ADMIN_TOKEN`` blocks every admin request — never
    auto-disables. Constant-time comparison so we don't leak the
    token's length to a timing attacker.
    """
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(status_code=401, detail="admin endpoints disabled")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    presented = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(presented, settings.admin_token):
        raise HTTPException(status_code=401, detail="invalid token")
