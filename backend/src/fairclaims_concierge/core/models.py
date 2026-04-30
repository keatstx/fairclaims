"""Pydantic models for the FairClaims concierge.

Subset lifted from CEN — only the FAQ + concierge surface. Session,
Project, AOPDefinition, ChatMessage, Artifact, SuggestedInput, etc. are
not lifted (no workflows, no chat persistence, no input forms).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class FAQ(BaseModel):
    """One Q+A pair in the concierge knowledge base.

    `module_name` is repurposed in FairClaims as a pillar tag
    (`charity_care`, `medical_debt`, etc.) — the FAQ store treats it as
    an opaque scope filter, so the same field carries different meaning
    across projects without code changes.
    """

    id: str
    module_name: Optional[str] = None
    project_id: Optional[str] = None
    question: str
    answer: str
    source_filename: str = ""
    owner_id: Optional[str] = None
    created_at: str = ""


class FAQCreate(BaseModel):
    question: str
    answer: str
    module_name: Optional[str] = None
    project_id: Optional[str] = None
    source_filename: str = ""


class ConciergeQuery(BaseModel):
    question: str
    page_url: Optional[str] = None  # which page the resident was on


class ConciergeCitation(BaseModel):
    """One grounding source used to answer a question."""

    faq_id: Optional[str] = None
    kind: str = "faq"  # faq (only kind in FairClaims; CEN also has workflow/sop/case_context)
    question: str = ""
    score: float = 0.0


class ConciergeResponse(BaseModel):
    answer: str
    mode: str  # "synthesis" | "llm_synthesis" | "guardrail" | "no_match"
    citations: List[ConciergeCitation] = Field(default_factory=list)
