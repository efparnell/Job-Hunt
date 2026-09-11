"""Fetches raw readable text from configured PE/news sources. Reuses
the same low-maintenance whole-page-text approach as career_pages.py —
see that module for the rationale."""

from automation.opportunity_monitor import config
from automation.opportunity_monitor.sources.career_pages import fetch_page_text


def fetch_all_pe_news() -> list[dict]:
    results = []
    for entry in config.PE_NEWS_SOURCES:
        text = fetch_page_text(entry["url"])
        if text:
            results.append({"name": entry["name"], "url": entry["url"], "text": text})
    return results
