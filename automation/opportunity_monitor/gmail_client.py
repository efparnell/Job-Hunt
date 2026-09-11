"""Reads LinkedIn job-alert emails and sends the daily digest, both
through Evan's Gmail account via the Gmail API. Auth uses a token
generated once locally (see generate_gmail_token.py) and stored as a
GitHub Actions secret — the daily job never does an interactive OAuth
flow.

Both public functions catch every realistic failure from building the
authenticated service (missing/malformed GMAIL_OAUTH_TOKEN, a token
refresh failure) as well as googleapiclient.errors.HttpError from the
API calls themselves, and degrade gracefully rather than crash the
daily unattended run: fetch returns an empty list (treated as "no
LinkedIn alerts today", same as a real empty inbox), send silently
no-ops (the day's log entries still get written even if the
notification email fails — losing one day's digest is much better
than losing the whole run)."""

import base64
import json
import logging
import os
from email.mime.text import MIMEText

from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from automation.opportunity_monitor import config

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# Covers: HttpError (API call failures), KeyError (GMAIL_OAUTH_TOKEN
# env var missing), ValueError (malformed token JSON — json.JSONDecodeError
# is a ValueError subclass), GoogleAuthError (bad/expired/unrefreshable
# credentials). Anything in this tuple means "couldn't do the Gmail
# thing today," never "crash the whole run."
_RECOVERABLE_ERRORS = (HttpError, KeyError, ValueError, GoogleAuthError)

_logger = logging.getLogger(__name__)


def _build_service():
    token_json = os.environ["GMAIL_OAUTH_TOKEN"]
    creds = Credentials.from_authorized_user_info(json.loads(token_json), _SCOPES)
    return build("gmail", "v1", credentials=creds)


def extract_plain_text(payload: dict) -> str:
    """Recursively find the first text/plain part of a Gmail message
    payload and return its decoded body."""
    if payload.get("mimeType") == "text/plain":
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = extract_plain_text(part)
        if result:
            return result
    return ""


def fetch_linkedin_alert_emails(max_results: int = 20) -> list[str]:
    try:
        service = _build_service()
    except _RECOVERABLE_ERRORS as exc:
        _logger.warning(
            "Gmail service unavailable (credential/token problem), treating as no LinkedIn alerts today: %s",
            exc,
        )
        return []

    try:
        query = f"from:{config.LINKEDIN_ALERT_SENDER} newer_than:1d"
        listing = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    except _RECOVERABLE_ERRORS as exc:
        _logger.warning("Gmail list call failed, treating as no LinkedIn alerts today: %s", exc)
        return []

    bodies = []
    for msg_ref in listing.get("messages", []):
        try:
            message = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
            text = extract_plain_text(message["payload"])
        except _RECOVERABLE_ERRORS as exc:
            _logger.warning("Gmail get call failed for message %s, skipping: %s", msg_ref["id"], exc)
            continue
        if text:
            bodies.append(text)
    return bodies


def send_digest_email(subject: str, body_text: str, to_address: str) -> None:
    try:
        service = _build_service()
        message = MIMEText(body_text)
        message["to"] = to_address
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except _RECOVERABLE_ERRORS as exc:
        _logger.warning("Failed to send digest email: %s", exc)
