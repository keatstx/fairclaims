"""Append-only questions log — FAQ-gap research, not legal evidence.

Every concierge call writes one row. Visitor hash is the only
quasi-identifier and rotates weekly; the question is PII-scrubbed
before it reaches this store. Two read methods power the admin
endpoints:

    unmatched(since) — questions where the FAQ retriever found nothing
                       confident. Each row is a candidate FAQ to write.
    digest(days)     — bucketed counts by top FAQ + by unmatched
                       question text, for a weekly review.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import aiosqlite
import structlog

logger = structlog.get_logger()


class QuestionsLogStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS questions_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                asked_at        TEXT    NOT NULL,
                question        TEXT    NOT NULL,
                answer_summary  TEXT    NOT NULL,
                top_faq_id      TEXT,
                top_faq_score   REAL,
                matched         INTEGER NOT NULL,
                visitor_hash    TEXT    NOT NULL,
                page_url        TEXT    NOT NULL DEFAULT '',
                user_agent_kind TEXT    NOT NULL DEFAULT 'desktop'
            )
            """
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_qlog_asked_at ON questions_log(asked_at)"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_qlog_matched ON questions_log(matched)"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_qlog_top_faq ON questions_log(top_faq_id)"
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def append(
        self,
        *,
        question: str,
        answer_summary: str,
        top_faq_id: Optional[str],
        top_faq_score: Optional[float],
        matched: int,
        visitor_hash: str,
        page_url: str,
        user_agent_kind: str,
    ) -> None:
        """Insert one row. Never raises — log + swallow so a logging
        failure can't ever block a user's reply."""
        if self._db is None:
            return
        try:
            now = datetime.now(timezone.utc).isoformat()
            await self._db.execute(
                """
                INSERT INTO questions_log
                    (asked_at, question, answer_summary, top_faq_id,
                     top_faq_score, matched, visitor_hash, page_url,
                     user_agent_kind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    question,
                    answer_summary,
                    top_faq_id,
                    top_faq_score,
                    matched,
                    visitor_hash,
                    page_url,
                    user_agent_kind,
                ),
            )
            await self._db.commit()
        except Exception as exc:  # noqa: BLE001
            await logger.awarning("questions_log_append_failed", error=str(exc))

    async def unmatched(
        self,
        *,
        since: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict]:
        if self._db is None:
            return []
        params: list = []
        clauses = ["matched = 0"]
        if since:
            clauses.append("asked_at >= ?")
            params.append(since)
        where = " AND ".join(clauses)
        params.append(limit)
        async with self._db.execute(
            f"""
            SELECT id, asked_at, question, page_url, user_agent_kind
            FROM questions_log
            WHERE {where}
            ORDER BY asked_at DESC
            LIMIT ?
            """,
            params,
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def digest(self, *, days: int = 7) -> dict:
        if self._db is None:
            return {
                "period_days": days,
                "total": 0,
                "matched": 0,
                "unmatched": 0,
                "top_faqs": [],
                "top_unmatched_questions": [],
            }
        rel = f"-{int(days)} days"

        async def _scalar(sql: str, params=()) -> int:
            async with self._db.execute(sql, params) as cursor:
                row = await cursor.fetchone()
            return int(row[0]) if row else 0

        total = await _scalar(
            "SELECT COUNT(*) FROM questions_log WHERE asked_at >= datetime('now', ?)",
            (rel,),
        )
        matched = await _scalar(
            "SELECT COUNT(*) FROM questions_log WHERE matched = 1 AND asked_at >= datetime('now', ?)",
            (rel,),
        )

        async with self._db.execute(
            """
            SELECT top_faq_id, COUNT(*) AS cnt
            FROM questions_log
            WHERE matched = 1
              AND top_faq_id IS NOT NULL
              AND asked_at >= datetime('now', ?)
            GROUP BY top_faq_id
            ORDER BY cnt DESC
            LIMIT 20
            """,
            (rel,),
        ) as cursor:
            top_faqs = [
                {"faq_id": row["top_faq_id"], "count": int(row["cnt"])}
                for row in await cursor.fetchall()
            ]

        async with self._db.execute(
            """
            SELECT question, COUNT(*) AS cnt
            FROM questions_log
            WHERE matched = 0
              AND asked_at >= datetime('now', ?)
            GROUP BY question
            ORDER BY cnt DESC
            LIMIT 20
            """,
            (rel,),
        ) as cursor:
            top_unmatched = [
                {"question": row["question"], "count": int(row["cnt"])}
                for row in await cursor.fetchall()
            ]

        return {
            "period_days": days,
            "total": total,
            "matched": matched,
            "unmatched": total - matched,
            "top_faqs": top_faqs,
            "top_unmatched_questions": top_unmatched,
        }
