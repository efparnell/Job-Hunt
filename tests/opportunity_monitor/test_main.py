from unittest.mock import patch

from automation.opportunity_monitor.main import run


@patch("automation.opportunity_monitor.main.send_digest_email")
@patch("automation.opportunity_monitor.main.append_entry")
@patch("automation.opportunity_monitor.main.score_opportunity")
@patch("automation.opportunity_monitor.main.passes_hard_filters")
@patch("automation.opportunity_monitor.main.fetch_linkedin_alert_emails")
@patch("automation.opportunity_monitor.main.fetch_all_pe_news")
@patch("automation.opportunity_monitor.main.fetch_all_career_pages")
def test_run_scores_filters_logs_and_alerts_only_above_threshold(
    mock_career, mock_pe, mock_linkedin, mock_filters, mock_score, mock_append, mock_send
):
    mock_career.return_value = [{"name": "Career Co", "url": "u1", "text": "Director role text"}]
    mock_pe.return_value = []
    mock_linkedin.return_value = []
    mock_filters.return_value = True
    mock_score.return_value = {"score": 85, "reasoning": "Great fit."}

    run(log_path="unused-because-append_entry-is-mocked", digest_to="efparnell@gmail.com")

    assert mock_append.call_count == 1
    assert mock_send.call_count == 1
    sent_body = mock_send.call_args.args[1]
    assert "Career Co" in sent_body


@patch("automation.opportunity_monitor.main.send_digest_email")
@patch("automation.opportunity_monitor.main.append_entry")
@patch("automation.opportunity_monitor.main.score_opportunity")
@patch("automation.opportunity_monitor.main.passes_hard_filters")
@patch("automation.opportunity_monitor.main.fetch_linkedin_alert_emails")
@patch("automation.opportunity_monitor.main.fetch_all_pe_news")
@patch("automation.opportunity_monitor.main.fetch_all_career_pages")
def test_run_skips_scoring_when_hard_filter_fails(
    mock_career, mock_pe, mock_linkedin, mock_filters, mock_score, mock_append, mock_send
):
    mock_career.return_value = [{"name": "Bad Co", "url": "u1", "text": "PMO-only role"}]
    mock_pe.return_value = []
    mock_linkedin.return_value = []
    mock_filters.return_value = False

    run(log_path="unused-because-append_entry-is-mocked", digest_to="efparnell@gmail.com")

    mock_score.assert_not_called()


@patch("automation.opportunity_monitor.main.send_digest_email")
@patch("automation.opportunity_monitor.main.append_entry")
@patch("automation.opportunity_monitor.main.score_opportunity")
@patch("automation.opportunity_monitor.main.passes_hard_filters")
@patch("automation.opportunity_monitor.main.fetch_linkedin_alert_emails")
@patch("automation.opportunity_monitor.main.fetch_all_pe_news")
@patch("automation.opportunity_monitor.main.fetch_all_career_pages")
def test_run_skips_candidate_when_scoring_fails(
    mock_career, mock_pe, mock_linkedin, mock_filters, mock_score, mock_append, mock_send
):
    mock_career.return_value = [{"name": "Career Co", "url": "u1", "text": "Director role text"}]
    mock_pe.return_value = []
    mock_linkedin.return_value = []
    mock_filters.return_value = True
    mock_score.return_value = None  # scorer.py returns None on API/parse failure

    run(log_path="unused-because-append_entry-is-mocked", digest_to="efparnell@gmail.com")

    mock_append.assert_not_called()
    sent_body = mock_send.call_args.args[1]
    assert "No opportunities scored 80 or above today." == sent_body


@patch("automation.opportunity_monitor.main.send_digest_email")
@patch("automation.opportunity_monitor.main.append_entry")
@patch("automation.opportunity_monitor.main.score_opportunity")
@patch("automation.opportunity_monitor.main.passes_hard_filters")
@patch("automation.opportunity_monitor.main.fetch_linkedin_alert_emails")
@patch("automation.opportunity_monitor.main.fetch_all_pe_news")
@patch("automation.opportunity_monitor.main.fetch_all_career_pages")
def test_run_truncates_oversized_page_text_before_scoring(
    mock_career, mock_pe, mock_linkedin, mock_filters, mock_score, mock_append, mock_send
):
    huge_text = "x" * 50000
    mock_career.return_value = [{"name": "Career Co", "url": "u1", "text": huge_text}]
    mock_pe.return_value = []
    mock_linkedin.return_value = []
    mock_filters.return_value = True
    mock_score.return_value = {"score": 85, "reasoning": "Great fit."}

    run(log_path="unused-because-append_entry-is-mocked", digest_to="efparnell@gmail.com")

    scored_text = mock_score.call_args.args[0]
    assert len(scored_text) <= 8000


@patch("automation.opportunity_monitor.main.send_digest_email")
@patch("automation.opportunity_monitor.main.append_entry")
@patch("automation.opportunity_monitor.main.score_opportunity")
@patch("automation.opportunity_monitor.main.passes_hard_filters")
@patch("automation.opportunity_monitor.main.fetch_linkedin_alert_emails")
@patch("automation.opportunity_monitor.main.fetch_all_pe_news")
@patch("automation.opportunity_monitor.main.fetch_all_career_pages")
def test_run_correctly_maps_reasoning_to_score_reasoning_key(
    mock_career, mock_pe, mock_linkedin, mock_filters, mock_score, mock_append, mock_send
):
    mock_career.return_value = [{"name": "Career Co", "url": "u1", "text": "Director role text"}]
    mock_pe.return_value = []
    mock_linkedin.return_value = []
    mock_filters.return_value = True
    mock_score.return_value = {"score": 85, "reasoning": "Great fit."}

    run(log_path="unused-because-append_entry-is-mocked", digest_to="efparnell@gmail.com")

    logged_entry = mock_append.call_args.args[1]
    assert logged_entry["score_reasoning"] == "Great fit."
    assert "reasoning" not in logged_entry


@patch("automation.opportunity_monitor.main.send_digest_email")
@patch("automation.opportunity_monitor.main.append_entry")
@patch("automation.opportunity_monitor.main.score_opportunity")
@patch("automation.opportunity_monitor.main.passes_hard_filters")
@patch("automation.opportunity_monitor.main.fetch_linkedin_alert_emails")
@patch("automation.opportunity_monitor.main.fetch_all_pe_news")
@patch("automation.opportunity_monitor.main.fetch_all_career_pages")
def test_run_threads_url_through_to_logged_entry_and_digest(
    mock_career, mock_pe, mock_linkedin, mock_filters, mock_score, mock_append, mock_send
):
    mock_career.return_value = [
        {"name": "Career Co", "url": "https://example.com/careers/vp-ops", "text": "Director role text"}
    ]
    mock_pe.return_value = []
    mock_linkedin.return_value = []
    mock_filters.return_value = True
    mock_score.return_value = {"score": 85, "reasoning": "Great fit."}

    run(log_path="unused-because-append_entry-is-mocked", digest_to="efparnell@gmail.com")

    logged_entry = mock_append.call_args.args[1]
    assert logged_entry["url"] == "https://example.com/careers/vp-ops"
    sent_body = mock_send.call_args.args[1]
    assert "https://example.com/careers/vp-ops" in sent_body


@patch("automation.opportunity_monitor.main.send_digest_email")
@patch("automation.opportunity_monitor.main.append_entry")
@patch("automation.opportunity_monitor.main.score_opportunity")
@patch("automation.opportunity_monitor.main.passes_hard_filters")
@patch("automation.opportunity_monitor.main.fetch_linkedin_alert_emails")
@patch("automation.opportunity_monitor.main.fetch_all_pe_news")
@patch("automation.opportunity_monitor.main.fetch_all_career_pages")
def test_run_continues_past_one_candidate_raising_an_unexpected_error(
    mock_career, mock_pe, mock_linkedin, mock_filters, mock_score, mock_append, mock_send
):
    mock_career.return_value = [
        {"name": "Broken Co", "url": "u1", "text": "Broken role text"},
        {"name": "Good Co", "url": "u2", "text": "Good role text"},
    ]
    mock_pe.return_value = []
    mock_linkedin.return_value = []
    mock_filters.return_value = True
    # First candidate blows up unexpectedly; second should still process.
    mock_score.side_effect = [RuntimeError("boom"), {"score": 90, "reasoning": "Great fit."}]

    run(log_path="unused-because-append_entry-is-mocked", digest_to="efparnell@gmail.com")

    assert mock_append.call_count == 1
    sent_body = mock_send.call_args.args[1]
    assert "Good Co" in sent_body
