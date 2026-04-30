"""Import an FAQ library Markdown file into the FAQ store.

Lifted from CEN with two adaptations:
1. Use-case → pillar tag mapping is FairClaims-specific.
2. ``seed_default_faqs_if_empty`` reads ``backend/seed/fairclaims_resident_faqs.md``.

Format (compatible with the FairClaims_Resident_FAQ_Master.md library):

    # USE CASE 1: CHARITY CARE
    ## STAGE 1: AWARENESS

    **Q1: I got a huge hospital bill — is there really free help?**
    **A (Short):** …
    **A (Full):** …
    **Sources:**
    - [Title](https://…)

The ``_USE_CASE_HEADER`` regex is case-insensitive, so both CEN's
``# Use Case 1: Charity Care`` and FairClaims' ``# USE CASE 1: CHARITY
CARE (Q1–Q20)`` parse cleanly without code changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from fairclaims_concierge.core.faq_store import FAQStore


# Use-case heading -> pillar tag. Anything not in this map imports as
# a globally-scoped FAQ (module_name=NULL). The FAQ store treats
# `module_name` as an opaque scope filter — same column, different
# meaning across CEN and FairClaims.
_USE_CASE_TO_MODULE: dict[str, str] = {
    "charity care": "charity_care",
    "medical debt": "medical_debt",
    "prior authorization": "prior_authorization",
    "workplace injury": "workplace_injury",
    "workplace injuries": "workplace_injury",
    "toxic exposure": "toxic_exposure",
}


_USE_CASE_HEADER = re.compile(r"^#\s+Use\s+Case\s+\d+\s*:\s*(?P<name>.+?)\s*$", re.IGNORECASE)
_QUESTION_LINE = re.compile(r"^\*\*Q\d+\s*:\s*(?P<q>.+?)\*\*\s*$")
_SHORT_ANSWER = re.compile(r"^\*\*A\s*\(Short\)\s*:\*\*\s*(?P<a>.*)$", re.IGNORECASE)
_FULL_ANSWER = re.compile(r"^\*\*A\s*\(Full\)\s*:\*\*\s*(?P<a>.*)$", re.IGNORECASE)
_SIMPLE_ANSWER = re.compile(r"^\*\*A\s*:\*\*\s*(?P<a>.*)$", re.IGNORECASE)
_SOURCES_HEADER = re.compile(r"^\*\*Sources?\s*:\*\*\s*$", re.IGNORECASE)


@dataclass
class ParsedFAQ:
    question: str
    answer: str
    use_case: str
    module_name: Optional[str]


def parse_faq_markdown(text: str) -> list[ParsedFAQ]:
    """Walk the markdown line-by-line and emit one ParsedFAQ per Q block."""
    lines = text.splitlines()
    current_use_case = ""
    current_module: Optional[str] = None

    out: list[ParsedFAQ] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        m = _USE_CASE_HEADER.match(line)
        if m:
            current_use_case = m.group("name").strip()
            current_module = _module_for_use_case(current_use_case)
            i += 1
            continue

        q_match = _QUESTION_LINE.match(line)
        if not q_match:
            i += 1
            continue

        question = q_match.group("q").strip()
        i += 1

        short_answer = ""
        full_answer = ""
        sources_lines: list[str] = []

        while i < len(lines):
            ln = lines[i]
            if _USE_CASE_HEADER.match(ln) or _QUESTION_LINE.match(ln):
                break

            sa = _SHORT_ANSWER.match(ln)
            fa = _FULL_ANSWER.match(ln)
            simple = _SIMPLE_ANSWER.match(ln)

            if sa:
                short_answer = _continuation_text(lines, i, sa.group("a"))
                i = _skip_continuation(lines, i)
                continue
            if fa:
                full_answer = _continuation_text(lines, i, fa.group("a"))
                i = _skip_continuation(lines, i)
                continue
            if simple and not short_answer and not full_answer:
                full_answer = _continuation_text(lines, i, simple.group("a"))
                i = _skip_continuation(lines, i)
                continue
            if _SOURCES_HEADER.match(ln):
                i += 1
                while i < len(lines):
                    sn = lines[i]
                    if _USE_CASE_HEADER.match(sn) or _QUESTION_LINE.match(sn):
                        break
                    if sn.strip().startswith(("-", "*", "•")):
                        sources_lines.append(sn.strip())
                    elif sn.strip().startswith("**"):
                        break
                    i += 1
                continue
            i += 1

        body = _stitch_answer(short_answer, full_answer, sources_lines)
        if question and body:
            out.append(
                ParsedFAQ(
                    question=question,
                    answer=body,
                    use_case=current_use_case,
                    module_name=current_module,
                )
            )

    return out


def _continuation_text(lines: list[str], start: int, first_value: str) -> str:
    parts: list[str] = [first_value.strip()]
    j = start + 1
    while j < len(lines):
        nxt = lines[j]
        stripped = nxt.strip()
        if not stripped:
            break
        if (
            _USE_CASE_HEADER.match(nxt)
            or _QUESTION_LINE.match(nxt)
            or _SHORT_ANSWER.match(nxt)
            or _FULL_ANSWER.match(nxt)
            or _SIMPLE_ANSWER.match(nxt)
            or _SOURCES_HEADER.match(nxt)
            or stripped.startswith("**")
            or stripped.startswith("---")
            or stripped.startswith("***")
            or stripped.startswith("# ")
        ):
            break
        parts.append(stripped)
        j += 1
    return " ".join(p for p in parts if p).strip()


def _skip_continuation(lines: list[str], start: int) -> int:
    j = start + 1
    while j < len(lines):
        nxt = lines[j]
        stripped = nxt.strip()
        if not stripped:
            break
        if (
            _USE_CASE_HEADER.match(nxt)
            or _QUESTION_LINE.match(nxt)
            or _SHORT_ANSWER.match(nxt)
            or _FULL_ANSWER.match(nxt)
            or _SIMPLE_ANSWER.match(nxt)
            or _SOURCES_HEADER.match(nxt)
            or stripped.startswith("**")
            or stripped.startswith("---")
            or stripped.startswith("***")
            or stripped.startswith("# ")
        ):
            break
        j += 1
    return j


def _stitch_answer(
    short_answer: str, full_answer: str, sources: Iterable[str]
) -> str:
    parts: list[str] = []
    if short_answer:
        parts.append(short_answer)
    if full_answer and full_answer != short_answer:
        if short_answer:
            parts.append("")
        parts.append(full_answer)
    sources_list = [s for s in sources if s.strip()]
    if sources_list:
        parts.append("")
        parts.append("Sources:")
        parts.extend(sources_list)
    return "\n".join(parts).strip()


def _module_for_use_case(use_case: str) -> Optional[str]:
    needle = use_case.lower()
    for key, module in _USE_CASE_TO_MODULE.items():
        if key in needle:
            return module
    return None


async def import_faqs(
    *,
    text: str,
    faq_store: FAQStore,
    source_filename: str = "",
    owner_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> int:
    """Parse the markdown library and write each entry to the FAQ store.
    Returns the count of FAQs imported."""
    parsed = parse_faq_markdown(text)
    for entry in parsed:
        await faq_store.create(
            question=entry.question,
            answer=entry.answer,
            module_name=entry.module_name,
            project_id=project_id,
            source_filename=source_filename,
            owner_id=owner_id,
        )
    return len(parsed)


async def seed_default_faqs_if_empty(faq_store: FAQStore) -> int:
    """Auto-seed the bundled FairClaims resident FAQ library on first startup.

    Idempotent: only seeds when the FAQ table is empty. To rev FAQs in
    production, drop a new ``backend/seed/fairclaims_resident_faqs.md``
    and redeploy — the table is wiped on first deploy when the persistent
    disk is fresh, or operated on manually otherwise.
    """
    from pathlib import Path

    existing = await faq_store.list_all()
    if existing:
        return 0

    seed_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "seed"
        / "fairclaims_resident_faqs.md"
    )
    if not seed_path.exists():
        return 0

    text = seed_path.read_text(encoding="utf-8")
    return await import_faqs(
        text=text,
        faq_store=faq_store,
        source_filename="fairclaims_resident_faqs.md (bundled seed)",
        owner_id=None,
    )
