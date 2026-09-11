"""Hard filters: pass/fail checks applied before any scoring. See
automation/2026-09-10-opportunity-monitoring-design.md section 3."""

from automation.opportunity_monitor import config
from automation.opportunity_monitor.geocode import within_commute_radius


def has_red_flag(text: str | None) -> bool:
    """Missing/empty posting text (a plausible real-world scrape
    failure) is treated as having no red flag to check, not a crash —
    the caller (passes_hard_filters, or a source fetcher upstream) is
    responsible for deciding what to do with unusable text."""
    if not text:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in config.RED_FLAG_KEYWORDS)


def passes_hard_filters(text: str, location_text: str, remote_ok: bool) -> bool:
    """True only if the posting has no red-flag language AND is within
    commute radius or remote/hybrid. Compensation is NOT checked here —
    it's a scored dimension, not a gate (see design doc section 3)."""
    if has_red_flag(text):
        return False
    return within_commute_radius(location_text, remote_ok)
