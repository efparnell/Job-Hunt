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
