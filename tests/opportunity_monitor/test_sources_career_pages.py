from pathlib import Path
from unittest.mock import MagicMock, patch
from automation.opportunity_monitor.sources.career_pages import fetch_page_text

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_page.html"


@patch("automation.opportunity_monitor.sources.career_pages.requests.get")
def test_fetch_page_text_strips_html_to_readable_text(mock_get):
    mock_response = MagicMock()
    mock_response.text = FIXTURE.read_text()
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    text = fetch_page_text("https://example.com/careers")

    assert "Director of Operations" in text
    assert "Elkridge, MD" in text
    assert "<h1>" not in text


@patch("automation.opportunity_monitor.sources.career_pages.requests.get")
def test_fetch_page_text_returns_none_on_request_failure(mock_get):
    mock_get.side_effect = Exception("network error")
    assert fetch_page_text("https://example.com/careers") is None
