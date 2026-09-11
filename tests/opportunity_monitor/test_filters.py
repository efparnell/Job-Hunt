from automation.opportunity_monitor.filters import has_red_flag, passes_hard_filters


def test_no_red_flag_in_clean_posting():
    text = "Director of Operations overseeing multi-site technical service teams."
    assert has_red_flag(text) is False


def test_detects_red_flag_case_insensitively():
    text = "Must hold an active TOP SECRET security clearance."
    assert has_red_flag(text) is True


def test_detects_red_flag_substring():
    text = "Experience in third-party logistics (3PL) required."
    assert has_red_flag(text) is True


def test_passes_hard_filters_true_for_clean_remote_posting():
    text = "General Manager for a multi-site industrial services company."
    assert passes_hard_filters(text, location_text="Remote", remote_ok=True) is True


def test_passes_hard_filters_false_when_red_flag_present():
    text = "PMO-only leadership role, government contract experience required."
    assert passes_hard_filters(text, location_text="Remote", remote_ok=True) is False
