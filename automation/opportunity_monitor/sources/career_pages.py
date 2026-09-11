"""Fetches raw readable text from a company career page. No per-site
structured parsing — the scorer (Task 5) reads the whole page text and
finds anything relevant itself, per the design doc's Tech Stack
decision to keep this low-maintenance."""

import logging

import requests
from bs4 import BeautifulSoup

from automation.opportunity_monitor import config

_logger = logging.getLogger(__name__)


def fetch_page_text(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "job-hunt-automation"})
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # Logged so a blocked scraper (403, DNS failure, site redesign)
        # is visible in the run log instead of being indistinguishable
        # from "fetched fine, nothing new on the page today."
        _logger.warning("Failed to fetch %s, skipping this source: %s", url, exc)
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def fetch_all_career_pages() -> list[dict]:
    """Returns a list of {"name", "url", "text"} for every configured
    target company whose page fetched successfully."""
    results = []
    for entry in config.TARGET_CAREER_PAGES:
        text = fetch_page_text(entry["url"])
        if text:
            results.append({"name": entry["name"], "url": entry["url"], "text": text})
    return results
