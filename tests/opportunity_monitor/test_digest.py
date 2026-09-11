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
