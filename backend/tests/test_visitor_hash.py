"""Visitor hash properties — stable within a week, drifts across weeks."""

from __future__ import annotations

from unittest.mock import patch

from fairclaims_concierge.visitor_hash import compute_visitor_hash, user_agent_kind


def test_same_inputs_yield_same_hash_within_week():
    h1 = compute_visitor_hash(ip="203.0.113.7", user_agent="Mozilla/5.0", salt="s")
    h2 = compute_visitor_hash(ip="203.0.113.7", user_agent="Mozilla/5.0", salt="s")
    assert h1 == h2


def test_different_ip_different_hash():
    h1 = compute_visitor_hash(ip="203.0.113.7", user_agent="UA", salt="s")
    h2 = compute_visitor_hash(ip="203.0.113.8", user_agent="UA", salt="s")
    assert h1 != h2


def test_different_salt_different_hash():
    h1 = compute_visitor_hash(ip="203.0.113.7", user_agent="UA", salt="s1")
    h2 = compute_visitor_hash(ip="203.0.113.7", user_agent="UA", salt="s2")
    assert h1 != h2


def test_hash_drifts_across_weeks():
    """Same inputs in different weeks → different hashes (no cross-week tracking)."""
    with patch("fairclaims_concierge.visitor_hash.time.time", return_value=1700000000):
        h1 = compute_visitor_hash(ip="203.0.113.7", user_agent="UA", salt="s")
    with patch("fairclaims_concierge.visitor_hash.time.time", return_value=1700000000 + 14 * 24 * 3600):
        h2 = compute_visitor_hash(ip="203.0.113.7", user_agent="UA", salt="s")
    assert h1 != h2


def test_hash_is_32_hex_chars():
    h = compute_visitor_hash(ip="1.1.1.1", user_agent="UA", salt="s")
    assert len(h) == 32
    int(h, 16)  # raises if not hex


def test_user_agent_kind_buckets():
    assert user_agent_kind("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)") == "mobile"
    assert user_agent_kind("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)") == "desktop"
    assert user_agent_kind("Googlebot/2.1") == "bot"
    assert user_agent_kind("") == "desktop"
