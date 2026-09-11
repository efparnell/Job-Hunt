import json
from unittest.mock import MagicMock, patch

import anthropic

from automation.opportunity_monitor.scorer import build_prompt, score_opportunity


def test_build_prompt_includes_posting_text_and_dimensions():
    prompt = build_prompt("Director of Operations posting text here.")
    assert "Director of Operations posting text here." in prompt
    assert "role scope" in prompt.lower()
    assert "industry adjacency" in prompt.lower()
    assert "operating complexity" in prompt.lower()
    assert "leadership mandate" in prompt.lower()
    assert "geography" in prompt.lower()
    assert "compensation" in prompt.lower()


@patch("automation.opportunity_monitor.scorer._client")
def test_score_opportunity_parses_model_response(mock_client):
    fake_response = MagicMock()
    fake_response.content = [
        MagicMock(text=json.dumps({"score": 88, "reasoning": "Strong fit."}))
    ]
    mock_client.messages.create.return_value = fake_response

    result = score_opportunity("Some posting text")

    assert result == {"score": 88, "reasoning": "Strong fit."}


@patch("automation.opportunity_monitor.scorer._client")
def test_score_opportunity_clamps_out_of_range_score(mock_client):
    fake_response = MagicMock()
    fake_response.content = [
        MagicMock(text=json.dumps({"score": 140, "reasoning": "Overclaimed."}))
    ]
    mock_client.messages.create.return_value = fake_response

    result = score_opportunity("Some posting text")

    assert result["score"] == 100


@patch("automation.opportunity_monitor.scorer._client")
def test_score_opportunity_returns_none_on_api_error(mock_client):
    mock_client.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())

    assert score_opportunity("Some posting text") is None


@patch("automation.opportunity_monitor.scorer._client")
def test_score_opportunity_returns_none_on_malformed_json_response(mock_client):
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="not valid json")]
    mock_client.messages.create.return_value = fake_response

    assert score_opportunity("Some posting text") is None


@patch("automation.opportunity_monitor.scorer._client")
def test_score_opportunity_returns_none_on_missing_keys(mock_client):
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text=json.dumps({"unexpected": "shape"}))]
    mock_client.messages.create.return_value = fake_response

    assert score_opportunity("Some posting text") is None
