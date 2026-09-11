# Opportunity Monitoring & Alerting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily, cloud-scheduled job that finds job opportunities from career pages, PE/news sources, and Evan's LinkedIn alert emails, filters out non-starters, scores everything else 0–100 on Evan's real fit criteria using an AI model call, logs every scored opportunity, and emails Evan a digest of anything scoring ~80+.

**Architecture:** A Python package (`automation/opportunity_monitor/`) with one module per concern — sources, hard filters, AI scoring, JSON-lines log storage, and email digest — orchestrated by `main.py`, which a GitHub Actions cron workflow runs once a day. All external calls (HTTP fetch, Gmail API, Anthropic API) are isolated behind thin wrapper functions so the rest of the logic is unit-testable without hitting live services.

**Tech Stack:** Python 3.11+, `requests` + `beautifulsoup4` (page fetching), `google-api-python-client` + `google-auth-oauthlib` (Gmail read/send), `anthropic` (scoring), `geopy` (geocoding for the geography filter), `pytest` (tests), GitHub Actions (scheduler/runtime).

Design doc this plan implements: `automation/2026-09-10-opportunity-monitoring-design.md`.

---

## Task 0: Account & Credential Setup (Evan does this — click-by-click)

No code in this task. Do this before Task 1, since later tasks need these credentials to test against (mocked in unit tests, but you'll want them for the real end-to-end run).

- [ ] **Step 1: Get an Anthropic API key**
  1. Go to console.anthropic.com and sign in (or create an account).
  2. Click **Get API keys** (or the key icon in the left sidebar).
  3. Click **Create Key**, give it a name like `job-hunt-automation`, click **Create Key** again to confirm.
  4. Copy the key shown (starts with `sk-ant-`) — you won't be able to see it again. Paste it somewhere safe for a moment; you'll add it to GitHub in Step 3 below.

- [ ] **Step 2: Create a Google Cloud project and Gmail API credentials**
  1. Go to console.cloud.google.com and sign in with your `efparnell@gmail.com` account.
  2. Click the project dropdown at the top of the page, then click **New Project**.
  3. Name it `job-hunt-automation`, click **Create**. Wait for it to finish, then make sure it's selected in the project dropdown.
  4. In the left sidebar (click the ☰ menu if it's hidden), go to **APIs & Services** → **Library**.
  5. Search for `Gmail API`, click it, click **Enable**.
  6. Go to **APIs & Services** → **OAuth consent screen**.
  7. Choose **External**, click **Create**.
  8. Fill in App name (`Job Hunt Automation`), User support email (your Gmail), Developer contact email (your Gmail). Click **Save and Continue** through the remaining steps (Scopes, Test users — on the Test users step, click **Add Users** and add your own `efparnell@gmail.com`). Click **Save and Continue**, then **Back to Dashboard**.
  9. Go to **APIs & Services** → **Credentials**.
  10. Click **Create Credentials** → **OAuth client ID**.
  11. Application type: **Desktop app**. Name: `job-hunt-automation-cli`. Click **Create**.
  12. A popup shows your Client ID and Client Secret — click **Download JSON**. This file (something like `client_secret_....json`) is needed once, locally, to generate a reusable token (Task 6 explains this).

- [ ] **Step 3: Add secrets to the GitHub repo**
  1. Open a browser and go to `github.com/efparnell/Job-Hunt`.
  2. Click the **Settings** tab (top of the repo page, near Code/Issues/Pull requests).
  3. In the left sidebar, click **Secrets and variables** → **Actions**.
  4. Click **New repository secret**.
  5. Name: `ANTHROPIC_API_KEY`. Value: paste the key from Step 1. Click **Add secret**.
  6. Click **New repository secret** again. You'll add `GMAIL_OAUTH_CLIENT` and `GMAIL_OAUTH_TOKEN` here once Task 6 generates them — skip those two for now, come back after Task 6.

---

## Task 1: Project Scaffolding & Config

**Files:**
- Create: `automation/opportunity_monitor/__init__.py`
- Create: `automation/opportunity_monitor/config.py`
- Create: `automation/requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/opportunity_monitor/__init__.py`
- Test: `tests/opportunity_monitor/test_config.py`

- [ ] **Step 1: Create the package directories and empty `__init__.py` files**

```bash
mkdir -p "automation/opportunity_monitor" "automation/opportunity_monitor/sources" "tests/opportunity_monitor" "tests/fixtures"
touch "automation/opportunity_monitor/__init__.py" "automation/opportunity_monitor/sources/__init__.py" "tests/__init__.py" "tests/opportunity_monitor/__init__.py"
```

- [ ] **Step 2: Write `automation/requirements.txt`**

```
requests==2.32.3
beautifulsoup4==4.12.3
anthropic==0.34.2
google-api-python-client==2.140.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
geopy==2.4.1
pytest==8.3.2
```

- [ ] **Step 3: Write the failing test for config**

`tests/opportunity_monitor/test_config.py`:
```python
from automation.opportunity_monitor import config


def test_edgewater_origin_is_a_lat_lon_pair():
    lat, lon = config.EDGEWATER_ORIGIN
    assert 38.0 < lat < 40.0
    assert -78.0 < lon < -75.0


def test_max_commute_radius_is_positive():
    assert config.MAX_COMMUTE_RADIUS_MILES > 0


def test_red_flag_keywords_is_nonempty_list_of_strings():
    assert len(config.RED_FLAG_KEYWORDS) > 0
    assert all(isinstance(k, str) for k in config.RED_FLAG_KEYWORDS)


def test_target_career_pages_is_a_list():
    assert isinstance(config.TARGET_CAREER_PAGES, list)


def test_fit_score_alert_threshold():
    assert config.FIT_SCORE_ALERT_THRESHOLD == 80
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'automation.opportunity_monitor.config'` (or similar; the module doesn't exist yet)

- [ ] **Step 3: Write `automation/opportunity_monitor/config.py`**

```python
"""Configuration and reference data for the opportunity monitor.

TARGET_CAREER_PAGES and PE_NEWS_SOURCES are intentionally empty below —
Evan needs to fill these in with real URLs before Task 5/6 will find
anything. Don't invent URLs here; wrong ones fail silently or scrape
the wrong page.
"""

# Approximate coordinates for Edgewater, MD — Evan's real origin point
# for the geography filter (Annapolis is a nearby stand-in he uses
# casually, but this is the precise value to filter against).
EDGEWATER_ORIGIN = (38.9351, -76.5372)

# Straight-line-distance proxy for "a 90-minute rush-hour drive."
# This is an approximation (avg. ~30mph effective rush-hour speed over
# 90 minutes) done via geopy's haversine distance, not a real drive-time
# API — upgrade to Google Maps Distance Matrix API later if this proves
# too loose or too tight in practice.
MAX_COMMUTE_RADIUS_MILES = 45

# Fit Score (0-100) threshold at/above which an opportunity triggers an
# alert. Matches Evan's own Priority-A floor from his real tracker.
FIT_SCORE_ALERT_THRESHOLD = 80

# Industry/role auto-reject keywords, matched case-insensitively against
# posting text. Source: Executive Operating Manual chapters 10 & 11.
RED_FLAG_KEYWORDS = [
    "security clearance",
    "top secret",
    "government contract",
    "govcon",
    "third-party logistics",
    "3pl",
    "healthcare administration",
    "accounting practice",
    "hospitality management",
    "residential hvac",
    "residential plumbing",
    "construction project delivery",
    "pmp required",
    "pmo-only",
]

# Fill in with real company career-page URLs before running the career
# page source (Task 5). One dict per company: name + careers URL.
TARGET_CAREER_PAGES: list[dict] = [
    # {"name": "Guardian Restoration Partners", "url": "https://..."},
]

# Fill in with real RSS/news URLs to monitor for PE acquisitions and
# leadership changes before running the PE/news source (Task 5).
PE_NEWS_SOURCES: list[dict] = [
    # {"name": "Example PE Firm News", "url": "https://..."},
]

# Sender address LinkedIn uses for job-alert emails. Confirm this
# matches what's actually in Evan's inbox before Task 6 — LinkedIn has
# changed sending domains before.
LINKEDIN_ALERT_SENDER = "jobalerts-noreply@linkedin.com"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_config.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Install dependencies and commit**

```bash
pip install -r automation/requirements.txt
git add automation/requirements.txt automation/opportunity_monitor/__init__.py automation/opportunity_monitor/config.py automation/opportunity_monitor/sources/__init__.py tests/__init__.py tests/opportunity_monitor/__init__.py tests/opportunity_monitor/test_config.py
git commit -m "$(cat <<'EOF'
feat: scaffold opportunity_monitor package and config

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Geography Filter

**Files:**
- Create: `automation/opportunity_monitor/geocode.py`
- Test: `tests/opportunity_monitor/test_geocode.py`

- [ ] **Step 1: Write the failing test**

`tests/opportunity_monitor/test_geocode.py`:
```python
from unittest.mock import patch
from automation.opportunity_monitor.geocode import within_commute_radius


def test_remote_or_hybrid_always_passes():
    assert within_commute_radius("Anywhere, USA", remote_ok=True) is True


@patch("automation.opportunity_monitor.geocode._geocode")
def test_nearby_location_passes(mock_geocode):
    mock_geocode.return_value = (38.9784, -76.4922)  # Annapolis, MD
    assert within_commute_radius("Annapolis, MD", remote_ok=False) is True


@patch("automation.opportunity_monitor.geocode._geocode")
def test_far_location_fails(mock_geocode):
    mock_geocode.return_value = (34.0522, -118.2437)  # Los Angeles, CA
    assert within_commute_radius("Los Angeles, CA", remote_ok=False) is False


@patch("automation.opportunity_monitor.geocode._geocode")
def test_ungeocodable_location_fails_closed(mock_geocode):
    mock_geocode.return_value = None
    assert within_commute_radius("Nowhere Really", remote_ok=False) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_geocode.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `automation/opportunity_monitor/geocode.py`**

```python
"""Geography hard filter: is a posting's location within Evan's real
commute radius, or remote/hybrid?"""

from geopy.distance import geodesic
from geopy.geocoders import Nominatim

from automation.opportunity_monitor import config

_geolocator = Nominatim(user_agent="job-hunt-automation-efparnell")


def _geocode(location_text: str) -> tuple[float, float] | None:
    """Look up a free-text location string. Returns None if it can't
    be geocoded (e.g. vague text like 'United States; remote')."""
    result = _geolocator.geocode(location_text, timeout=10)
    if result is None:
        return None
    return (result.latitude, result.longitude)


def within_commute_radius(location_text: str, remote_ok: bool) -> bool:
    """True if remote/hybrid, or if the geocoded location falls inside
    MAX_COMMUTE_RADIUS_MILES of Evan's Edgewater, MD origin. Fails
    closed (returns False) if the location can't be geocoded, since an
    unrecognized location shouldn't silently pass the filter."""
    if remote_ok:
        return True
    coords = _geocode(location_text)
    if coords is None:
        return False
    distance = geodesic(config.EDGEWATER_ORIGIN, coords).miles
    return distance <= config.MAX_COMMUTE_RADIUS_MILES
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_geocode.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add automation/opportunity_monitor/geocode.py tests/opportunity_monitor/test_geocode.py
git commit -m "$(cat <<'EOF'
feat: add geography hard filter with commute-radius proxy

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Red-Flag Keyword Filter

**Files:**
- Create: `automation/opportunity_monitor/filters.py`
- Test: `tests/opportunity_monitor/test_filters.py`

- [ ] **Step 1: Write the failing test**

`tests/opportunity_monitor/test_filters.py`:
```python
from automation.opportunity_monitor.filters import has_red_flag, passes_hard_filters


def test_no_red_flag_in_clean_posting():
    text = "Director of Operations overseeing multi-site technical service teams."
    assert has_red_flag(text) is False


def test_detects_red_flag_case_insensitively():
    text = "Must hold an active TOP SECRET security clearance."
    assert has_red_flag(text) is True


def test_detects_red_flag_substring():
    text = "Experience in third-party logistics (3PL) required."
    assert has_red_flag(text) is True


def test_passes_hard_filters_true_for_clean_remote_posting():
    text = "General Manager for a multi-site industrial services company."
    assert passes_hard_filters(text, location_text="Remote", remote_ok=True) is True


def test_passes_hard_filters_false_when_red_flag_present():
    text = "PMO-only leadership role, government contract experience required."
    assert passes_hard_filters(text, location_text="Remote", remote_ok=True) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_filters.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `automation/opportunity_monitor/filters.py`**

```python
"""Hard filters: pass/fail checks applied before any scoring. See
automation/2026-09-10-opportunity-monitoring-design.md section 3."""

from automation.opportunity_monitor import config
from automation.opportunity_monitor.geocode import within_commute_radius


def has_red_flag(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in config.RED_FLAG_KEYWORDS)


def passes_hard_filters(text: str, location_text: str, remote_ok: bool) -> bool:
    """True only if the posting has no red-flag language AND is within
    commute radius or remote/hybrid. Compensation is NOT checked here —
    it's a scored dimension, not a gate (see design doc section 3)."""
    if has_red_flag(text):
        return False
    return within_commute_radius(location_text, remote_ok)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_filters.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add automation/opportunity_monitor/filters.py tests/opportunity_monitor/test_filters.py
git commit -m "$(cat <<'EOF'
feat: add red-flag keyword filter and combined hard-filter check

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Log Store (JSON Lines)

**Files:**
- Create: `automation/opportunity_monitor/log_store.py`
- Test: `tests/opportunity_monitor/test_log_store.py`

- [ ] **Step 1: Write the failing test**

`tests/opportunity_monitor/test_log_store.py`:
```python
import json
from automation.opportunity_monitor.log_store import append_entry, read_all_entries


def test_append_and_read_roundtrip(tmp_path):
    log_path = tmp_path / "opportunity_log.jsonl"
    entry = {
        "company": "Example Co",
        "role": "Director of Operations",
        "source": "career_page",
        "score": 85,
        "score_reasoning": "Strong operating-complexity and leadership-mandate fit.",
        "alerted": True,
    }
    append_entry(log_path, entry)
    entries = read_all_entries(log_path)
    assert len(entries) == 1
    assert entries[0]["company"] == "Example Co"
    assert entries[0]["score"] == 85


def test_append_multiple_entries_stays_one_json_object_per_line(tmp_path):
    log_path = tmp_path / "opportunity_log.jsonl"
    append_entry(log_path, {"company": "A", "score": 60})
    append_entry(log_path, {"company": "B", "score": 90})
    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["company"] == "A"
    assert json.loads(lines[1])["company"] == "B"


def test_read_all_entries_on_missing_file_returns_empty_list(tmp_path):
    log_path = tmp_path / "does_not_exist.jsonl"
    assert read_all_entries(log_path) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_log_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `automation/opportunity_monitor/log_store.py`**

```python
"""Append-only JSON-lines log of every scored opportunity. This is the
Reception-Pattern Log data source (design doc section 5) — never
written into the Excel tracker directly; Evan promotes entries into
that himself."""

import json
from pathlib import Path


def append_entry(log_path: Path, entry: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_all_entries(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    with open(log_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_log_store.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add automation/opportunity_monitor/log_store.py tests/opportunity_monitor/test_log_store.py
git commit -m "$(cat <<'EOF'
feat: add JSON-lines log store for scored opportunities

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: AI-Based Fit Scorer

**Files:**
- Create: `automation/opportunity_monitor/scorer.py`
- Test: `tests/opportunity_monitor/test_scorer.py`

- [ ] **Step 1: Write the failing test**

`tests/opportunity_monitor/test_scorer.py`:
```python
import json
from unittest.mock import MagicMock, patch
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

    assert result["score"] == 88
    assert result["reasoning"] == "Strong fit."


@patch("automation.opportunity_monitor.scorer._client")
def test_score_opportunity_clamps_out_of_range_score(mock_client):
    fake_response = MagicMock()
    fake_response.content = [
        MagicMock(text=json.dumps({"score": 140, "reasoning": "Overclaimed."}))
    ]
    mock_client.messages.create.return_value = fake_response

    result = score_opportunity("Some posting text")

    assert result["score"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_scorer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `automation/opportunity_monitor/scorer.py`**

```python
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


def score_opportunity(posting_text: str) -> dict:
    prompt = build_prompt(posting_text)
    response = _client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    parsed = json.loads(response.content[0].text)
    score = max(0, min(100, int(parsed["score"])))
    return {"score": score, "reasoning": parsed["reasoning"]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_scorer.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add automation/opportunity_monitor/scorer.py tests/opportunity_monitor/test_scorer.py
git commit -m "$(cat <<'EOF'
feat: add AI-based fit scorer calling Claude on Evan's six dimensions

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Career Pages & PE/News Source Fetchers

**Files:**
- Create: `automation/opportunity_monitor/sources/career_pages.py`
- Create: `automation/opportunity_monitor/sources/pe_news.py`
- Create: `tests/fixtures/sample_page.html`
- Test: `tests/opportunity_monitor/test_sources_career_pages.py`

- [ ] **Step 1: Write the fixture**

`tests/fixtures/sample_page.html`:
```html
<html>
<head><title>Careers</title></head>
<body>
  <nav>Home | About | Careers | Contact</nav>
  <h1>Open Positions</h1>
  <div class="job">
    <h2>Director of Operations</h2>
    <p>Location: Elkridge, MD. Oversee multi-site technical service delivery.</p>
  </div>
  <footer>&copy; 2026 Example Co</footer>
</body>
</html>
```

- [ ] **Step 2: Write the failing test**

`tests/opportunity_monitor/test_sources_career_pages.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_sources_career_pages.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write `automation/opportunity_monitor/sources/career_pages.py`**

```python
"""Fetches raw readable text from a company career page. No per-site
structured parsing — the scorer (Task 5) reads the whole page text and
finds anything relevant itself, per the design doc's Tech Stack
decision to keep this low-maintenance."""

import requests
from bs4 import BeautifulSoup

from automation.opportunity_monitor import config


def fetch_page_text(url: str) -> str | None:
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "job-hunt-automation"})
        response.raise_for_status()
    except Exception:
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_sources_career_pages.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Write `automation/opportunity_monitor/sources/pe_news.py`** (same fetch approach, reused)

```python
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
```

- [ ] **Step 7: Commit**

```bash
git add automation/opportunity_monitor/sources/career_pages.py automation/opportunity_monitor/sources/pe_news.py tests/opportunity_monitor/test_sources_career_pages.py tests/fixtures/sample_page.html
git commit -m "$(cat <<'EOF'
feat: add career-page and PE/news text fetchers

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Gmail Client (Read LinkedIn Alerts + Send Digest)

**Files:**
- Create: `automation/opportunity_monitor/gmail_client.py`
- Create: `automation/generate_gmail_token.py` (one-time local script, not part of the daily job)
- Test: `tests/opportunity_monitor/test_gmail_client.py`

- [ ] **Step 1: Write the failing test**

`tests/opportunity_monitor/test_gmail_client.py`:
```python
import base64
from unittest.mock import MagicMock, patch
from automation.opportunity_monitor.gmail_client import extract_plain_text, fetch_linkedin_alert_emails


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_gmail_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `automation/opportunity_monitor/gmail_client.py`**

```python
"""Reads LinkedIn job-alert emails and sends the daily digest, both
through Evan's Gmail account via the Gmail API. Auth uses a token
generated once locally (see generate_gmail_token.py) and stored as a
GitHub Actions secret — the daily job never does an interactive OAuth
flow."""

import base64
import json
import os
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from automation.opportunity_monitor import config

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


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
    service = _build_service()
    query = f"from:{config.LINKEDIN_ALERT_SENDER} newer_than:1d"
    listing = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    bodies = []
    for msg_ref in listing.get("messages", []):
        message = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
        text = extract_plain_text(message["payload"])
        if text:
            bodies.append(text)
    return bodies


def send_digest_email(subject: str, body_text: str, to_address: str) -> None:
    service = _build_service()
    message = MIMEText(body_text)
    message["to"] = to_address
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_gmail_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Write the one-time local token generator**

`automation/generate_gmail_token.py`:
```python
"""Run this ONCE, locally, to produce a reusable OAuth token for the
Gmail API. Not run by the daily GitHub Actions job.

Usage:
    python automation/generate_gmail_token.py path/to/client_secret.json

It opens a browser for you to log into efparnell@gmail.com and
authorize, then prints a JSON blob. Paste that whole blob as the
value of the GMAIL_OAUTH_TOKEN GitHub secret (Task 0, Step 3), and
paste the *client secret file's own contents* as GMAIL_OAUTH_CLIENT.
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

if __name__ == "__main__":
    client_secret_path = sys.argv[1]
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)
    print(creds.to_json())
```

- [ ] **Step 6: Evan runs the token generator and adds the two remaining GitHub secrets**
  1. In a terminal, in the repo folder, run: `python automation/generate_gmail_token.py path\to\your\client_secret_....json` (the file downloaded in Task 0, Step 2.12).
  2. A browser window opens — sign in as `efparnell@gmail.com`, click through the "unverified app" warning (click **Advanced** → **Go to job-hunt-automation (unsafe)** — this is expected for an app only you use), and click **Allow**.
  3. Back in the terminal, a block of JSON text prints out. Copy the whole thing.
  4. Go to `github.com/efparnell/Job-Hunt` → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Name: `GMAIL_OAUTH_TOKEN`. Value: paste the JSON. Click **Add secret**.
  5. Open the `client_secret_....json` file itself in a text editor, copy its entire contents.
  6. **New repository secret** again. Name: `GMAIL_OAUTH_CLIENT`. Value: paste the file contents. Click **Add secret**.

- [ ] **Step 7: Commit**

```bash
git add automation/opportunity_monitor/gmail_client.py automation/generate_gmail_token.py tests/opportunity_monitor/test_gmail_client.py
git commit -m "$(cat <<'EOF'
feat: add Gmail client for reading LinkedIn alerts and sending digest

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Digest Builder

**Files:**
- Create: `automation/opportunity_monitor/digest.py`
- Test: `tests/opportunity_monitor/test_digest.py`

- [ ] **Step 1: Write the failing test**

`tests/opportunity_monitor/test_digest.py`:
```python
from automation.opportunity_monitor.digest import build_digest_body


def test_build_digest_body_lists_each_alerted_opportunity():
    entries = [
        {"company": "Example Co", "role": "Director of Operations", "score": 88,
         "score_reasoning": "Strong leadership mandate.", "source": "career_page"},
        {"company": "Second Co", "role": "VP Operations", "score": 82,
         "score_reasoning": "Good industry adjacency.", "source": "pe_news"},
    ]
    body = build_digest_body(entries)
    assert "Example Co" in body
    assert "88" in body
    assert "Strong leadership mandate." in body
    assert "Second Co" in body


def test_build_digest_body_on_empty_list():
    assert build_digest_body([]) == "No opportunities scored 80 or above today."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_digest.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `automation/opportunity_monitor/digest.py`**

```python
"""Builds the plain-text body of the daily email digest."""


def build_digest_body(alerted_entries: list[dict]) -> str:
    if not alerted_entries:
        return "No opportunities scored 80 or above today."

    lines = []
    for entry in alerted_entries:
        lines.append(
            f"{entry['company']} — {entry['role']} "
            f"(score {entry['score']}, source: {entry['source']})\n"
            f"  {entry['score_reasoning']}\n"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_digest.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add automation/opportunity_monitor/digest.py tests/opportunity_monitor/test_digest.py
git commit -m "$(cat <<'EOF'
feat: add plain-text digest builder

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Orchestrator (`main.py`)

**Files:**
- Create: `automation/opportunity_monitor/main.py`
- Test: `tests/opportunity_monitor/test_main.py`

- [ ] **Step 1: Write the failing test**

`tests/opportunity_monitor/test_main.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/opportunity_monitor/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `automation/opportunity_monitor/main.py`**

```python
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


def _candidates_from_career_pages() -> list[dict]:
    return [
        {"company": c["name"], "role": "Unknown (see text)", "source": "career_page",
         "text": c["text"], "location_text": "Unknown", "remote_ok": False}
        for c in fetch_all_career_pages()
    ]


def _candidates_from_pe_news() -> list[dict]:
    return [
        {"company": c["name"], "role": "Unknown (see text)", "source": "pe_news",
         "text": c["text"], "location_text": "Unknown", "remote_ok": True}
        for c in fetch_all_pe_news()
    ]


def _candidates_from_linkedin() -> list[dict]:
    return [
        {"company": "Unknown (see LinkedIn alert text)", "role": "Unknown (see text)",
         "source": "linkedin_email", "text": body, "location_text": "Unknown", "remote_ok": True}
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/opportunity_monitor/test_main.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: PASS (all tests across all tasks)

- [ ] **Step 6: Commit**

```bash
git add automation/opportunity_monitor/main.py tests/opportunity_monitor/test_main.py
git commit -m "$(cat <<'EOF'
feat: add daily orchestrator tying sources, filters, scorer, log, and digest together

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: GitHub Actions Daily Schedule

**Files:**
- Create: `.github/workflows/opportunity-monitor.yml`

- [ ] **Step 1: Write the workflow file**

`.github/workflows/opportunity-monitor.yml`:
```yaml
name: Opportunity Monitor

on:
  schedule:
    - cron: "0 12 * * *"  # 12:00 UTC daily = 8:00 AM Eastern (adjust for DST as needed)
  workflow_dispatch: {}  # lets Evan trigger it manually from the Actions tab

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r automation/requirements.txt

      - name: Run opportunity monitor
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_OAUTH_TOKEN: ${{ secrets.GMAIL_OAUTH_TOKEN }}
          GMAIL_OAUTH_CLIENT: ${{ secrets.GMAIL_OAUTH_CLIENT }}
        run: python -m automation.opportunity_monitor.main

      - name: Commit updated log
        run: |
          git config user.name "opportunity-monitor-bot"
          git config user.email "actions@github.com"
          git add data/opportunity_log.jsonl
          git diff --staged --quiet || git commit -m "chore: daily opportunity log update"
          git push
```

- [ ] **Step 2: Evan enables Actions write permission for the log commit**
  1. Go to `github.com/efparnell/Job-Hunt` → **Settings** → **Actions** → **General**.
  2. Scroll to **Workflow permissions**.
  3. Select **Read and write permissions**.
  4. Click **Save**.

- [ ] **Step 3: Commit the workflow file**

```bash
git add .github/workflows/opportunity-monitor.yml
git commit -m "$(cat <<'EOF'
feat: schedule daily opportunity monitor via GitHub Actions

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
git push
```

- [ ] **Step 4: Evan fills in real data before the first real run**
  1. Open `automation/opportunity_monitor/config.py`.
  2. Fill in `TARGET_CAREER_PAGES` with real company career-page URLs (start with the watch list in Executive Operating Manual chapter 13).
  3. Fill in `PE_NEWS_SOURCES` with real news/RSS URLs for the PE firms in chapter 12.
  4. Confirm `LINKEDIN_ALERT_SENDER` matches what's actually in your inbox (check a recent LinkedIn alert email's "from" address).
  5. Commit and push those changes.
  6. Go to the **Actions** tab on GitHub, click **Opportunity Monitor** in the left sidebar, click **Run workflow** to trigger a manual test run instead of waiting for the schedule.

---

## Self-Review Notes

- **Spec coverage:** all 8 numbered sections of the design doc map to a task above — sources (Tasks 6, 7), hard filters (Tasks 2, 3), fit score (Task 5), reception-pattern log (Task 4, feeds from the same log), sub-threshold handling and alerting (Tasks 9, 8).
- **Known gap intentionally left open:** the Reception-Pattern Log's "likelihood of positive reception" sub-dimension (design doc section 5) isn't implemented yet — there's not enough real outcome data logged to make it meaningful. Revisit once `data/opportunity_log.jsonl` has enough history; it would plug into `scorer.py`'s prompt as additional context.
- **Type consistency checked:** `entry` dicts built in `main.py` match the keys `digest.py` and `log_store.py` expect (`company`, `role`, `source`, `score`, `score_reasoning`, `alerted`).
