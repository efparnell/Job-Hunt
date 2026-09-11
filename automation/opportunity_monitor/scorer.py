"""AI-based fit scoring: calls Claude to score a posting 0-100 against
Evan's real six dimensions (design doc section 4)."""

import json
import os

import anthropic

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

_SCORING_INSTRUCTIONS = """
You are screening a job posting for Evan Parnell, an operations
executive (COO / Director / VP Operations / General Manager profile)
targeting industrial services, environmental services, commercial
HVAC, building automation, equipment dealers/distributors, laboratory
& technical services, and PE-backed service businesses.

Score the posting below from 0-100 using these six weighted
dimensions: role scope, industry adjacency, operating complexity,
leadership mandate, geography, and compensation. Weight role scope,
industry adjacency, and leadership mandate most heavily — Evan's own
market experience shows these predict fit best. Compensation should
degrade the score if well below a real floor of roughly $120k/year
after-tax, but should not zero it out on its own if other dimensions
are strong.

Respond with ONLY a JSON object: {"score": <int 0-100>, "reasoning":
"<one to three sentences citing which dimensions drove the score>"}

Posting:
"""


def build_prompt(posting_text: str) -> str:
    return _SCORING_INSTRUCTIONS + posting_text


def score_opportunity(posting_text: str) -> dict | None:
    """Returns {"score": int, "reasoning": str}, or None if scoring
    failed — an API error, timeout, or a response that doesn't parse
    into the expected shape. This is called once per candidate in the
    daily unattended pipeline, so a failure must degrade to "skip this
    one candidate" (None) rather than crash the whole run, matching
    the hardening pattern established in geocode.py and filters.py."""
    prompt = build_prompt(posting_text)

    try:
        response = _client.messages.create(
            model="claude-sonnet-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError:
        return None

    try:
        parsed = json.loads(response.content[0].text)
        score = max(0, min(100, int(parsed["score"])))
        reasoning = str(parsed["reasoning"])
    except (json.JSONDecodeError, KeyError, ValueError, IndexError, TypeError):
        return None

    return {"score": score, "reasoning": reasoning}
