"""PII scrubbing — regex implementation only.

CEN ships an optional Presidio (NER-backed) scrubber for production PHI;
FairClaims is a public marketing site that explicitly refuses PHI, so
the regex tier is sufficient. Belt-and-suspenders for SSN, phone, and
email — the three things a stressed visitor is most likely to paste in
without thinking.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

REDACTED = "[REDACTED]"


@runtime_checkable
class PIIScrubber(Protocol):
    def scrub(self, text: str) -> str: ...


class RegexPIIScrubber:
    """Fast regex-based PII redaction for SSN, phone, and email."""

    def scrub(self, text: str) -> str:
        text = _SSN_RE.sub(REDACTED, text)
        text = _PHONE_RE.sub(REDACTED, text)
        text = _EMAIL_RE.sub(REDACTED, text)
        return text


def create_scrubber(backend: str = "regex") -> PIIScrubber:
    # Only regex is supported. The argument is kept for compatibility
    # with config-driven instantiation; an unknown value falls through
    # to regex rather than raising.
    return RegexPIIScrubber()
