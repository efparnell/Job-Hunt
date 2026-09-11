"""Daily orchestration: fetch every source, hard-filter, score, log
everything that passed filters, and email a digest of the ~80+ ones."""

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


def _truncate(text: str) -> str:
    return text[:_MAX_TEXT_CHARS]


def _candidates_from_career_pages() -> list[dict]:
    return [
        {"company": c["name"], "role": "Unknown (see text)", "source": "career_page",
         "text": _truncate(c["text"]), "location_text": "Unknown", "remote_ok": False}
        for c in fetch_all_career_pages()
    ]


def _candidates_from_pe_news() -> list[dict]:
    return [
        {"company": c["name"], "role": "Unknown (see text)", "source": "pe_news",
         "text": _truncate(c["text"]), "location_text": "Unknown", "remote_ok": True}
        for c in fetch_all_pe_news()
    ]


def _candidates_from_linkedin() -> list[dict]:
    return [
        {"company": "Unknown (see LinkedIn alert text)", "role": "Unknown (see text)",
         "source": "linkedin_email", "text": _truncate(body), "location_text": "Unknown", "remote_ok": True}
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
            "score": result["score"],
            "score_reasoning": result["reasoning"],
            "alerted": result["score"] >= config.FIT_SCORE_ALERT_THRESHOLD,
        }
        append_entry(Path(log_path), entry)

        if entry["alerted"]:
            alerted_entries.append(entry)

    body = build_digest_body(alerted_entries)
    send_digest_email("Job Hunt Daily Digest", body, digest_to)


if __name__ == "__main__":
    run(log_path="data/opportunity_log.jsonl", digest_to="efparnell@gmail.com")
