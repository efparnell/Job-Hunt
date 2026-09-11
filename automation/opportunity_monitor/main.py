"""Daily orchestration: fetch every source, hard-filter, score, log
everything that passed filters, and email a digest of the ~80+ ones."""

import logging
from pathlib import Path

from automation.opportunity_monitor import config
from automation.opportunity_monitor.digest import build_digest_body
from automation.opportunity_monitor.filters import passes_hard_filters
from automation.opportunity_monitor.gmail_client import fetch_linkedin_alert_emails, send_digest_email
from automation.opportunity_monitor.log_store import append_entry
from automation.opportunity_monitor.scorer import score_opportunity
from automation.opportunity_monitor.sources.career_pages import fetch_all_career_pages
from automation.opportunity_monitor.sources.pe_news import fetch_all_pe_news

# Cap text handed to the scorer, to bound both API cost and the risk
# of an oversized/noisy page blowing past a reasonable prompt size —
# flagged during Task 6's code review. 8000 chars is comfortably more
# than any real job posting needs while staying well under typical
# context limits even for a noisy full career page.
_MAX_TEXT_CHARS = 8000

_logger = logging.getLogger(__name__)


def _truncate(text: str) -> str:
    return text[:_MAX_TEXT_CHARS]


def _candidates_from_career_pages() -> list[dict]:
    # remote_ok=True here is deliberate, not a placeholder: Task 6's
    # design decision was whole-page text with no per-posting
    # structured parsing, so there's no real per-listing location to
    # geocode. Setting remote_ok=False with a fake "Unknown" location
    # would fail geocoding and fail-close every single career-page
    # candidate (via geocode.py's own fail-closed design), silently
    # making this entire source produce nothing, ever. Geography is
    # instead one of the scorer's six real judgment dimensions (see
    # scorer.py's prompt) — it evaluates whatever location signal
    # actually appears in the page text. Revisit if/when career pages
    # get structured per-posting parsing.
    return [
        {"company": c["name"], "role": "Unknown (see text)", "source": "career_page",
         "text": _truncate(c["text"]), "location_text": "Unknown", "remote_ok": True,
         "url": c["url"]}
        for c in fetch_all_career_pages()
    ]


def _candidates_from_pe_news() -> list[dict]:
    return [
        {"company": c["name"], "role": "Unknown (see text)", "source": "pe_news",
         "text": _truncate(c["text"]), "location_text": "Unknown", "remote_ok": True,
         "url": c["url"]}
        for c in fetch_all_pe_news()
    ]


def _candidates_from_linkedin() -> list[dict]:
    # No URL is available here — fetch_linkedin_alert_emails() returns
    # plain-text email bodies, not structured messages with an
    # extractable posting link. Evan needs to check the actual
    # LinkedIn alert email for the link until email parsing is
    # extended to pull one out.
    return [
        {"company": "Unknown (see LinkedIn alert text)", "role": "Unknown (see text)",
         "source": "linkedin_email", "text": _truncate(body), "location_text": "Unknown", "remote_ok": True,
         "url": None}
        for body in fetch_linkedin_alert_emails()
    ]


def run(log_path: str, digest_to: str) -> None:
    candidates = (
        _candidates_from_career_pages()
        + _candidates_from_pe_news()
        + _candidates_from_linkedin()
    )

    alerted_entries = []
    for candidate in candidates:
        try:
            if not passes_hard_filters(
                candidate["text"], candidate["location_text"], candidate["remote_ok"]
            ):
                continue

            result = score_opportunity(candidate["text"])
            if result is None:
                # scorer.py returns None on API/parse failure — skip this
                # one candidate rather than crash the whole run (it's
                # already logged a warning internally).
                continue

            entry = {
                "company": candidate["company"],
                "role": candidate["role"],
                "source": candidate["source"],
                "url": candidate["url"],
                "score": result["score"],
                "score_reasoning": result["reasoning"],
                "alerted": result["score"] >= config.FIT_SCORE_ALERT_THRESHOLD,
            }
            append_entry(Path(log_path), entry)

            if entry["alerted"]:
                alerted_entries.append(entry)
        except Exception:
            # Every dependency called above already degrades gracefully
            # on its own known failure modes (geocode/filters/scorer all
            # catch their own external-call errors). This is a last-resort
            # guard against something unanticipated (e.g. a malformed
            # candidate dict from a future source) taking down the rest
            # of the run and losing a whole day's digest over one bad
            # candidate — log it and keep going.
            _logger.exception(
                "Unexpected error processing candidate from %s, skipping it: %s",
                candidate.get("source", "unknown source"),
                candidate.get("company", "unknown company"),
            )
            continue

    body = build_digest_body(alerted_entries)
    send_digest_email("Job Hunt Daily Digest", body, digest_to)


if __name__ == "__main__":
    run(log_path="data/opportunity_log.jsonl", digest_to="efparnell@gmail.com")
