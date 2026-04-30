"""Visitor hashing for analytics dedup — not for re-identification.

The hash combines a server-side salt + a weekly-rotating epoch index +
the visitor's IP + their user-agent string. Properties:

- Within a week, the same visitor produces a stable hash → analytics
  can dedup "unique askers" without storing PII.
- Across weeks, the same visitor produces a *different* hash → no
  long-term tracking of any individual.
- The salt is server-side only, so the hash can't be precomputed
  externally to deanonymize a visitor.

The output is truncated to 32 hex chars (128 bits) — plenty for
collision resistance at FairClaims' traffic levels and shorter to
inspect in the questions_log table.
"""

from __future__ import annotations

import hashlib
import time

_WEEK_SECONDS = 7 * 24 * 60 * 60


def compute_visitor_hash(*, ip: str, user_agent: str, salt: str) -> str:
    week = int(time.time() // _WEEK_SECONDS)
    raw = f"{salt}|{week}|{ip}|{user_agent}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def user_agent_kind(ua: str) -> str:
    """Bucket the UA into desktop / mobile / bot for a low-cardinality
    column. We deliberately discard the raw UA — keeping it would let
    a determined operator try to triangulate identity over time."""
    ua = (ua or "").lower()
    if "bot" in ua or "crawler" in ua or "spider" in ua:
        return "bot"
    if "mobile" in ua or "iphone" in ua or "android" in ua:
        return "mobile"
    return "desktop"
