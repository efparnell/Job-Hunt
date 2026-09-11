# Opportunity Monitoring & Alerting — Design
## Job Hunt Automation

**Status:** Draft, approved by Evan 2026-09-10, concept-level (no tech stack chosen yet)
**Scope:** Job-hunt automation only. This document does not cover consulting/GTM work (out of scope for this project entirely — see project memory) or the scheduling/calendar/booking-link and email subsystems (deliberately deferred sub-projects, not designed here).

---

## 1. Purpose

Automate the mechanical work of finding and triaging job opportunities so Evan spends his time evaluating and deciding, not searching. The system finds, filters, scores, and surfaces opportunities; Evan does 100% of the judgment on what to actually pursue.

---

## 2. Sources

- Target company career pages (the watch list in Executive Operating Manual, chapter 13, plus PE-backed peers as the list grows)
- LinkedIn Jobs search (standing queries against target titles/industries/geography)
- Executive recruiter postings/boards (industrial & technical services search firms)
- PE acquisition & leadership-change news (new acquisitions/executive transitions at PE-backed companies — historically a leading indicator per Evan's own notes, roles often emerge 6–18 months post-acquisition)
- Extensible: new sources can be added as they're identified; this list is not exhaustive by design.

**Open item:** Evan can provide a LinkedIn data export file. A personal export (saved/applied jobs, connections, messages) is static, not a live feed, so it's assumed this seeds the **Reception-Pattern Log** (section 5) with his real application history rather than serving as a live daily-scan source. Confirm this assumption, and what the export actually contains, before implementation.

---

## 3. Hard Filters (pass/fail, applied before any scoring)

Auto-reject, no scoring, no logging needed beyond a simple discard count:

- **Geography:** farther than a 90-minute rush-hour drive from Edgewater, MD, AND not remote/hybrid.
- **Compensation:** disclosed comp with no realistic path to Evan's real floor — $120k/year after-tax, roughly gross-estimated to a pre-tax equivalent (exact gross-up formula is an implementation detail, not a design decision); may flex somewhat for unusually strong benefits.
- **Industry/role red flags** (per Executive Operating Manual, chapters 10 & 11): GovCon/clearance required, pure logistics/3PL, healthcare administration, accounting-firm operations, hospitality, residential HVAC/plumbing, construction project delivery, PMO/PMP-heavy roles.

Rationale: these are non-negotiable constraints, not matters of degree — scoring them would waste effort. This mirrors Evan's own "protect time, pass quickly" lesson.

---

## 4. Fit Score (0–10)

Applies to every opportunity that survives the hard filters. Scale, philosophy, and anti-inflation discipline borrowed from Evan's "AI Evaluation Framework — 0–10 Scoring Criteria" doc (8 = uncommon/excellent, every score needs evidence, avoid inflation) — but the **dimensions being scored are opportunity-fit dimensions**, not that document's document-quality dimensions:

- **Business-problem alignment** (green/red-flag language from chapter 10 — heaviest weight; chapters 11's Lessons 1 & 2 establish this as the most predictive single factor)
- **Industry/strategic fit** (match to target industries — see job-search-targets)
- **Organizational maturity / transformation opportunity** (multi-site, founder-led or PE-backed, growth-stage)
- **Leadership scope** (real P&L/organizational authority vs. a narrow functional role)
- **PE alignment** (bonus signal, not required)
- **Compensation strength** (degree above the real floor, now that the hard filter already passed)
- **Geographic convenience** (exact commute/remote quality, now that the hard filter already passed)
- **Likelihood of positive reception** (see section 5 — pulled from the Reception-Pattern Log; can move the score up or down based on empirical response patterns for similar companies/specialties)

**8.0 is the floor** for "strong fit" — the threshold that triggers an alert (section 6).

**Open item:** relative weighting across these dimensions is not yet fixed. Recommend starting with business-problem alignment weighted roughly double the others, then adjusting once real scored data exists to compare against actual outcomes.

---

## 5. Reception-Pattern Log

A running record, seeded from Evan's own application history (Executive Operating Manual Appendix D, Appendix C, and the LinkedIn export per section 2) and updated as new outcomes occur, tracking which company types/specialties/sizes actually engage positively (interview, response) versus go dark.

This exists because Evan named directly that changing industries at 40 is a real headwind — objectively strong-fit companies may still not respond, and he wants that tracked empirically rather than assumed away. Early on, with little data, the "likelihood of positive reception" sub-score in section 4 defaults to neutral; it sharpens as outcomes accumulate. This log doubles as the "lessons learned about who's actually interested in me" artifact Evan asked for.

---

## 6. Sub-Threshold Handling

Every opportunity that clears the hard filters (section 3) — regardless of its 0–10 score — gets logged with its score and reasoning, feeding the Reception-Pattern Log. Nothing that clears the filters is discarded outright.

Only opportunities scoring **8.0 or above** trigger an alert (section 7). Everything else sits in the log for later review or pattern analysis, but doesn't interrupt Evan's day.

---

## 7. Alerting

- **Email:** a digest containing full detail (score + reasoning) for every 8.0+ opportunity found.
- **SMS:** exactly one text per day, sent only if the day's count of 8.0+ opportunities is greater than zero. Never one text per opportunity.

---

## 8. Explicitly Out of Scope (for this spec)

- Tech stack / implementation tooling (to be discussed separately, once design work in this project reaches that point — Evan asked to be flagged when we get there)
- A fresh-session kickoff file for a coding-focused session (same — flag when relevant)
- Scheduling/calendar/booking-link coordination (separate subsystem, not yet designed)
- Email integration beyond serving as the alert channel above (separate subsystem, not yet designed)
- Any consulting/go-to-market/monetization work (out of scope for the Job Hunt project entirely, per Evan's 2026-09-10 scope decision)

---

## Open Questions

1. What exactly is in the LinkedIn export file, and does it change how sections 2 or 5 should work?
2. Relative weighting of the section 4 fit-score dimensions.
3. Exact pre-tax comp threshold to use as a proxy for the $120k-after-tax real floor (needs a rough tax-bracket assumption).
4. Where/how the Reception-Pattern Log and per-opportunity score log should live (a file format decision — deferred to the tech-stack conversation).
