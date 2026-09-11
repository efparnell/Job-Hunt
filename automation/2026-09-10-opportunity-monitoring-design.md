# Opportunity Monitoring & Alerting — Design
## Job Hunt Automation

**Status:** Approved, tech stack settled 2026-09-11, ready for implementation plan
**Scope:** Job-hunt automation only. This document does not cover consulting/GTM work (out of scope for this project entirely — see project memory) or the scheduling/calendar/booking-link subsystem (deliberately deferred, not designed here). Email integration is now partially in scope — see Tech Stack below — limited to reading LinkedIn alert emails and sending the digest; anything broader (e.g. outbound correspondence, scheduling emails) is still deferred.

## Tech Stack (settled 2026-09-11)

- **Language:** Python.
- **Runtime:** Cloud — a scheduled GitHub Actions workflow in this repo (`efparnell/Job-Hunt`, private), not a local machine, so it runs whether or not Evan's PC is on.
- **Data storage:** A separate, simple log file in the repo (not the Excel tracker) — the automation never writes into `Tracker\Executive Job Dashboard.xlsm` directly. Evan reviews the digest and manually copies anything he wants formally tracked into the Excel tracker himself. Exact file format (CSV vs. JSON) is an implementation-plan-level decision, not a design-level one.
- **Alerting:** Email only for the MVP, sent from Evan's existing Gmail account (efparnell@gmail.com). SMS (originally scoped in section 7) is deferred to a later pass — Evan would need to set up a paid SMS provider (Twilio is the standard choice) himself first, similar to how he set up the GitHub repo.
- **LinkedIn coverage:** Not scraped directly (against LinkedIn's ToS and technically fragile). Instead, Evan already receives LinkedIn's own job-alert emails; the system reads those out of his Gmail (read access, same account as sending) and parses them as a source. This replaces "LinkedIn Jobs search" as originally listed in section 2.
- **Standing manual fallback, independent of this system:** any time Evan spots something himself (a LinkedIn alert, a posting from a friend, etc.), he can just paste it to Claude directly for on-the-spot fit scoring — no need to wait for the automated pipeline.
- **Scoring mechanism:** an AI model call (Claude API), not hand-coded rules. The job passes posting text plus Evan's scoring criteria/lessons-learned context and gets back a 0–100 score with reasoning. Needs an Anthropic API key as a GitHub Actions secret; cost is small (roughly cents/day at this volume).
- **Career-page monitoring approach:** no per-site structured parsers. Each career page's raw text is fetched and handed to the scoring step to find and evaluate anything that looks like a new relevant opening — low-maintenance, no custom code per company website, at the cost of being less precise about exactly what's new since the last scan.

---

## 1. Purpose

Automate the mechanical work of finding and triaging job opportunities so Evan spends his time evaluating and deciding, not searching. The system finds, filters, scores, and surfaces opportunities; Evan does 100% of the judgment on what to actually pursue.

---

## 2. Sources

**Phase 1 (all three included together, per Evan 2026-09-11 — LinkedIn-via-email turned out to be no harder than the others, so no reason to hold it back):**
- Target company career pages (the watch list in Executive Operating Manual, chapter 13, plus PE-backed peers as the list grows)
- PE acquisition & leadership-change news (new acquisitions/executive transitions at PE-backed companies — historically a leading indicator per Evan's own notes, roles often emerge 6–18 months post-acquisition)
- **LinkedIn job-alert emails, read via Gmail** — Evan already has LinkedIn saved-search alerts emailing him; the system reads and parses those out of his Gmail inbox rather than scraping LinkedIn directly (see Tech Stack). Evan may want to tune/broaden his LinkedIn saved-search filters so these alert emails cast a wide enough net — worth a quick pass together once this is built.

**Deferred (later phase):**
- Executive recruiter postings/boards (industrial & technical services search firms) — not yet designed in detail.
- Direct LinkedIn Jobs scraping — dropped from scope entirely in favor of the email-based approach above; not planned.

Extensible: new sources can be added as they're identified; this list is not exhaustive by design.

**Resolved:** the earlier open item about a static LinkedIn data export is superseded by the live email-based approach above — the export isn't needed for this subsystem.

---

## 3. Hard Filters (pass/fail, applied before any scoring)

**Revised 2026-09-11** after reviewing Evan's real tracker (`Tracker\Executive Job Dashboard.xlsm` — see job-search-tracker memory): compensation is **not** a hard filter in practice. Carter Machinery's posted range (85–115k) was below his stated floor, but he pursued it anyway — "their high end was near enough to my low end" plus strong overall fit. So compensation moves to a scored dimension (section 4) instead of a gate.

Auto-reject, no scoring, no logging needed beyond a simple discard count:

- **Geography:** farther than a 90-minute rush-hour drive from Edgewater, MD, AND not remote/hybrid.
- **Industry/role red flags** (per Executive Operating Manual, chapters 10 & 11): GovCon/clearance required, pure logistics/3PL, healthcare administration, accounting-firm operations, hospitality, residential HVAC/plumbing, construction project delivery, PMO/PMP-heavy roles.

Rationale: these are non-negotiable constraints, not matters of degree — scoring them would waste effort. This mirrors Evan's own "protect time, pass quickly" lesson.

**Implementation note (2026-09-11, final review of the Phase 1 build):** in the actual `main.py` orchestrator, the geography gate above is currently a no-op for all three live sources — none of them extract a real per-listing location (career pages and PE/news are whole-page text with no structured parsing, per this doc's own Tech Stack decision; LinkedIn alert emails aren't parsed for location either), so every candidate is passed through as `remote_ok=True` rather than gated. See `main.py`'s `_candidates_from_career_pages()` comment for the full reasoning: gating on a fake "Unknown" location would fail-closed and silently zero out that entire source forever, which is worse than the alternative. Geography is, in practice, scored by the AI model (section 4) using whatever location signal appears in the text — not hard-gated — until/unless structured per-listing location extraction is added. The red-flag keyword check is the only hard filter with real teeth today.

---

## 4. Fit Score (0–100)

**Revised 2026-09-11 to match Evan's own real, already-in-use system** (found in the tracker's Instructions sheet), rather than the 0–10 scale this section originally proposed by mistake (that 0–10 scale is a document-quality framework of Evan's, unrelated to opportunity fit — see job-search-approach memory).

Applies to every opportunity that survives the hard filters. Six dimensions, per Evan's own Instructions sheet:

- **Role scope**
- **Industry adjacency**
- **Operating complexity**
- **Leadership mandate**
- **Geography** (degree of convenience, now that the hard filter already passed)
- **Compensation** (degree above/below his real floor — a scored input, not a gate; a strong enough score on the other dimensions can outweigh a below-floor range, as it did for Carter Machinery)

Plus one new dimension proposed for the automated version, not yet in his manual spreadsheet practice — confirm with Evan before building it in:
- **Likelihood of positive reception** (see section 5 — pulled from the Reception-Pattern Log; can move the score up or down based on empirical response patterns for similar companies/specialties, given the real headwind of changing industries at 40)

**Priority bands, per his real data:** Priority A ≈ 86–96, Priority B ≈ 74–82, Priority C ≈ 60–68. **~80+ is the practical "strong fit" floor** — the threshold that triggers an alert (section 6), matching Priority A's definition ("strong fit plus a credible access path or urgent strategic reason to engage").

**Open item:** exact relative weighting across these dimensions isn't documented anywhere — Evan scores these by judgment, not a spreadsheet formula. Recommend starting with business-problem-adjacent dimensions (role scope, industry adjacency, leadership mandate) weighted heaviest, consistent with chapter 11's Lessons 1 & 2 that these are the most predictive, then calibrating against his real scored history in the tracker once there's enough data to compare.

---

## 5. Reception-Pattern Log

A running record, seeded from Evan's own application history (Executive Operating Manual Appendix D, Appendix C, and the real tracker — see job-search-tracker memory) and updated as new outcomes occur, tracking which company types/specialties/sizes actually engage positively (interview, response) versus go dark.

This exists because Evan named directly that changing industries at 40 is a real headwind — objectively strong-fit companies may still not respond, and he wants that tracked empirically rather than assumed away. Early on, with little data, the "likelihood of positive reception" sub-score in section 4 defaults to neutral; it sharpens as outcomes accumulate. This log doubles as the "lessons learned about who's actually interested in me" artifact Evan asked for.

---

## 6. Sub-Threshold Handling

Every opportunity that clears the hard filters (section 3) — regardless of its 0–100 score — gets logged with its score and reasoning, feeding the Reception-Pattern Log. Nothing that clears the filters is discarded outright.

Only opportunities scoring **~80 or above** (Priority-A territory) trigger an alert (section 7). Everything else sits in the log for later review or pattern analysis, but doesn't interrupt Evan's day.

---

## 7. Alerting

- **Email (Phase 1):** a digest containing full detail (score + reasoning) for every ~80+ opportunity found, sent from Evan's Gmail.
- **SMS (deferred):** exactly one text per day, sent only if the day's count of ~80+ opportunities is greater than zero, never one text per opportunity — build this once Evan has a Twilio (or equivalent) account set up.

---

## 8. Explicitly Out of Scope (for this spec)

- A fresh-session kickoff file for a coding-focused session (flag when relevant — not yet needed)
- Scheduling/calendar/booking-link coordination (separate subsystem, not yet designed)
- Email integration beyond reading LinkedIn alert emails and sending the digest (see Tech Stack) — anything broader (outbound correspondence, scheduling emails) is a separate subsystem, not yet designed
- Any consulting/go-to-market/monetization work (out of scope for the Job Hunt project entirely, per Evan's 2026-09-10 scope decision)

---

## Open Questions

1. Relative weighting of the section 4 fit-score dimensions.
2. How exactly compensation should be scored relative to the $120k-after-tax real floor — e.g. a smooth degrade below floor vs. a step function — now that it's confirmed to be a scored dimension rather than a gate (needs a rough pre-tax gross-up assumption either way).
3. Exact log file format (CSV vs. JSON) and schema for the Reception-Pattern Log / per-opportunity score log — implementation-plan-level decision.
4. Exactly which target-company career pages and PE/news sources to start with, and their URLs/feed formats — needed before Phase 1 can be coded, likely resolved during plan-writing or Task 1 of implementation.
