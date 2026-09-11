import base64
from unittest.mock import MagicMock, patch

from googleapiclient.errors import HttpError

from automation.opportunity_monitor.gmail_client import (
    extract_plain_text,
    fetch_linkedin_alert_emails,
    send_digest_email,
)


def test_extract_plain_text_from_multipart_payload():
    plain_body = "Hi Evan, new job alert: Director of Operations at Example Co."
    encoded = base64.urlsafe_b64encode(plain_body.encode()).decode()
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": encoded}},
            {"mimeType": "text/html", "body": {"data": "PGh0bWw+aWdub3JlPC9odG1sPg=="}},
        ],
    }
    assert extract_plain_text(payload) == plain_body


@patch("automation.opportunity_monitor.gmail_client._build_service")
def test_fetch_linkedin_alert_emails_returns_parsed_bodies(mock_build_service):
    plain_body = "New alert: VP Operations role."
    encoded = base64.urlsafe_b64encode(plain_body.encode()).decode()

    mock_service = MagicMock()
    mock_build_service.return_value = mock_service
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg1"}]
    }
    mock_service.users().messages().get().execute.return_value = {
        "id": "msg1",
        "payload": {"mimeType": "text/plain", "body": {"data": encoded}},
    }

    emails = fetch_linkedin_alert_emails(max_results=5)

    assert len(emails) == 1
    assert emails[0] == plain_body


def _http_error():
    resp = MagicMock()
    resp.status = 500
    return HttpError(resp=resp, content=b'{"error": "boom"}')


@patch("automation.opportunity_monitor.gmail_client._build_service")
def test_fetch_linkedin_alert_emails_returns_empty_list_on_api_error(mock_build_service):
    mock_build_service.side_effect = _http_error()
    assert fetch_linkedin_alert_emails() == []


@patch("automation.opportunity_monitor.gmail_client._build_service")
def test_fetch_linkedin_alert_emails_returns_empty_list_when_list_call_fails(mock_build_service):
    mock_service = MagicMock()
    mock_build_service.return_value = mock_service
    mock_service.users().messages().list().execute.side_effect = _http_error()
    assert fetch_linkedin_alert_emails() == []


@patch("automation.opportunity_monitor.gmail_client._build_service")
def test_send_digest_email_swallows_api_error(mock_build_service):
    mock_service = MagicMock()
    mock_build_service.return_value = mock_service
    mock_service.users().messages().send().execute.side_effect = _http_error()

    # Should not raise — the daily job must not crash just because the
    # notification email failed to send.
    send_digest_email("subject", "body", "efparnell@gmail.com")


@patch("automation.opportunity_monitor.gmail_client._build_service")
def test_send_digest_email_calls_gmail_send_on_success(mock_build_service):
    mock_service = MagicMock()
    mock_build_service.return_value = mock_service

    send_digest_email("subject", "body text", "efparnell@gmail.com")

    mock_service.users().messages().send.assert_called()
