"""Regex PII scrubber covers SSN, phone, email."""

from fairclaims_concierge.privacy.pii_scrubber import REDACTED, RegexPIIScrubber


def test_scrubs_ssn():
    s = RegexPIIScrubber()
    assert s.scrub("My SSN is 123-45-6789, please help") == f"My SSN is {REDACTED}, please help"


def test_scrubs_phone_dashes():
    s = RegexPIIScrubber()
    assert REDACTED in s.scrub("Call me at 312-555-0142")


def test_scrubs_phone_parens():
    s = RegexPIIScrubber()
    assert REDACTED in s.scrub("My number is (312) 555-0142")


def test_scrubs_email():
    s = RegexPIIScrubber()
    assert s.scrub("write me at jane.doe@example.com today") == f"write me at {REDACTED} today"


def test_leaves_clean_text_alone():
    s = RegexPIIScrubber()
    text = "I got a hospital bill I cannot pay. What can FairClaims do?"
    assert s.scrub(text) == text


def test_scrubs_multiple_kinds():
    s = RegexPIIScrubber()
    out = s.scrub("Email me at jane@example.com or call 312-555-0142, my SSN is 123-45-6789.")
    assert out.count(REDACTED) == 3
