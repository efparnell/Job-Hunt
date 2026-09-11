from automation.opportunity_monitor.digest import build_digest_body


def test_build_digest_body_lists_each_alerted_opportunity():
    entries = [
        {"company": "Example Co", "role": "Director of Operations", "score": 88,
         "score_reasoning": "Strong leadership mandate.", "source": "career_page"},
        {"company": "Second Co", "role": "VP Operations", "score": 82,
         "score_reasoning": "Good industry adjacency.", "source": "pe_news"},
    ]
    body = build_digest_body(entries)
    assert "Example Co" in body
    assert "88" in body
    assert "Strong leadership mandate." in body
    assert "Second Co" in body


def test_build_digest_body_on_empty_list():
    assert build_digest_body([]) == "No opportunities scored 80 or above today."


def test_build_digest_body_includes_url_when_present():
    entries = [
        {"company": "Example Co", "role": "Director of Operations", "score": 88,
         "score_reasoning": "Strong leadership mandate.", "source": "career_page",
         "url": "https://example.com/careers/director-of-operations"},
    ]
    body = build_digest_body(entries)
    assert "https://example.com/careers/director-of-operations" in body


def test_build_digest_body_omits_url_line_when_absent_or_none():
    entries = [
        {"company": "LinkedIn Find", "role": "VP Operations", "score": 90,
         "score_reasoning": "Great fit.", "source": "linkedin_email", "url": None},
    ]
    body = build_digest_body(entries)
    # Should not raise, and should not print the literal word "None" as
    # if it were a real URL.
    assert "None" not in body
