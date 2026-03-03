---
phase: 04-player-origins
verified: 2026-03-02T00:00:00Z
status: human_needed
score: 14/14 automated must-haves verified
re_verification: false
human_verification:
  - test: "Open browser, run `python3 run.py`, visit http://127.0.0.1:5000"
    expected: "Origin selection page appears with 3 cards: The Heir, The Matchmaker, The Comeback. No Easy/Medium/Hard labels visible."
    why_human: "CSS rendering and card layout cannot be verified programmatically — visual confirmation of 3-card row layout, dark theme, hover effects, and selected-state glow required."
  - test: "Click The Matchmaker card, type 'Thunder FC', click Confirm"
    expected: "Card highlights on click, name input slides in, text crawl reveals 2 paragraphs sequentially (first at 0.5s, second at 2.5s) in cinematic second-person voice, Begin button appears ~5.7s after crawl starts."
    why_human: "CSS animation timing (crawl-reveal keyframes with animation-delay) and sequential fade-in feel require live observation. The dual-gate Begin button logic (animation timer + async seed task) cannot be unit-tested."
  - test: "Click Begin after it activates"
    expected: "Redirects to main game dashboard. Sidebar/header shows 'Thunder FC' as the promotion name."
    why_human: "Navigation redirect and promotion name display in dashboard require browser verification."
  - test: "Refresh the page after completing origin selection"
    expected: "Dashboard loads, not origin page. Origin selection never reappears."
    why_human: "Route-switching depends on GameState row presence, which is correct in code but the final user experience (no flash of origin page) needs human confirmation."
---

# Phase 4: Player Origins Verification Report

**Phase Goal:** Player origin selection — 3 archetypes with distinct starting conditions (budget, prestige, roster size), origin page UI, parameterized seed pipeline, narrative intro
**Verified:** 2026-03-02
**Status:** human_needed (all automated checks pass; 4 browser UX items require human)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths — Plan 04-01 (Backend)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `seed_organizations()` accepts origin-specific params with backward-compatible defaults | VERIFIED | Signature: `(session, player_org_name="Player Promotion", player_org_prestige=50.0, player_org_balance=5_000_000.0, origin_type=None)` — seed.py lines 319-325 |
| 2 | 3 origin configs exist with correct budgets ($1.5M/$4M/$8M), prestige (25/40/55), roster targets (6/12/20) | VERIFIED | `ORIGIN_CONFIGS` dict at seed.py lines 241-266: The Heir (8M/55/20), The Matchmaker (4M/40/12), The Comeback (1.5M/25/6) — all match CONTEXT.md spec exactly |
| 3 | `start_new_game()` runs seed pipeline as async task with roster enforcement | VERIFIED | services.py lines 439-494: spawns thread calling `_run_new_game()` which calls `seed_organizations`, `seed_fighters`, `enforce_roster_target`, `enforce_roster_quality`, `fabricate_history` |
| 4 | `has_game_state()` returns True when GameState row exists, False when not | VERIFIED | services.py lines 91-95: `session.get(GameState, 1)` returns bool. Test client on fresh DB returns False (confirmed live) |
| 5 | GameState stores selected `origin_type` as nullable String(50) column | VERIFIED | models.py line 402: `origin_type: Mapped[Optional[str]] = Column(String(50), nullable=True)` |
| 6 | `run.py` starts server without seeding — seeding deferred to origin selection POST | VERIFIED | run.py is 25 lines; grep for `seed_organizations|seed_fighters|fabricate_history` returns 0 matches |
| 7 | `test_cli.py` still works — `seed_organizations()` with no args uses defaults | VERIFIED | `python3 -X utf8 test_cli.py` completes (SEEDING, HISTORY VALIDATION PASSED, IDENTITY VALIDATION PASSED). Pre-existing archetype-record mismatch warnings are unrelated to Phase 4. |

### Observable Truths — Plan 04-02 (Frontend + API)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 8 | GET / on fresh game shows origin.html with 3 selectable cards | VERIFIED | Test client GET / returns 200 with origin.html content (confirmed DOCTYPE, FighterSim title, step-cards section). `/api/origins` returns 3 labels: The Heir, The Matchmaker, The Comeback. |
| 9 | Each card displays name, tagline, budget/prestige/roster stats | VERIFIED | origin.js builds cards from `/api/origins` response (lines 37-103); each card renders label, tagline, budget/prestige/roster_target. No difficulty labels found in origin.html or origin.js. |
| 10 | Confirming name + origin triggers seeding and shows text crawl | VERIFIED | `confirmOrigin()` POSTs to `/api/origin`, on success calls `showTextCrawl()` and `pollSeedTask()` — origin.js lines 147-166 |
| 11 | Text crawl shows 2 paragraphs per origin with sequential CSS fade-in | VERIFIED | `NARRATIVES` object in origin.js contains 2 paragraphs per origin. CSS: `crawl-p1` has `animation-delay: 0.5s`, `crawl-p2` has `animation-delay: 2.5s`, `@keyframes crawlReveal` exists in origin.css |
| 12 | Begin button dual-gated: animation timer AND seed task completion | VERIFIED | `checkBeginReady()` only enables button when `seedComplete && crawlComplete`. `crawlComplete` set by `setTimeout(5700)`, `seedComplete` set by polling `/api/tasks/` — origin.js lines 200-241 |
| 13 | Clicking Begin navigates to main dashboard | VERIFIED | `btn-begin` click handler: `window.location.href = "/"` — origin.js line 239 |
| 14 | GET / after seeding shows index.html — origin page never shown again | VERIFIED | `index()` route in app.py: `if services.has_game_state(): return render_template("index.html")` — app.py lines 28-31 |

**Score:** 14/14 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `models/models.py` | OriginType enum with 3 values | VERIFIED | Lines 85-88: `THE_HEIR`, `THE_MATCHMAKER`, `THE_COMEBACK` as `(str, enum.Enum)` — matches existing pattern |
| `simulation/seed.py` | ORIGIN_CONFIGS dict + parameterized seed_organizations + enforce functions | VERIFIED | ORIGIN_CONFIGS at lines 241-266 (3 entries). `seed_organizations` at line 319 with 4 params. `enforce_roster_target` at line 354. `enforce_roster_quality` at line 391. |
| `api/services.py` | `has_game_state()` + `start_new_game()` + `_run_new_game()` | VERIFIED | `has_game_state` at line 91. `start_new_game` at line 439. `_run_new_game` at line 450. |
| `run.py` | Server starts with empty DB, no seeding | VERIFIED | 25-line file, zero seeding calls. Comment: "seeding deferred to origin selection" |
| `api/app.py` | Route-switching GET /, GET /api/origins, POST /api/origin | VERIFIED | `has_game_state` check at line 29. `/api/origins` at line 45. `/api/origin` POST at line 60. |
| `frontend/templates/origin.html` | Full origin selection page (min 80 lines) | VERIFIED | 56 lines — below the 80-line minimum specified in PLAN. However, the file is structurally complete: 3 steps (cards, name input, text crawl), all wired to JS. Cards are rendered client-side by origin.js, so the HTML shell is intentionally minimal. |
| `frontend/static/css/origin.css` | Dark theme + crawl-reveal keyframe animation | VERIFIED | 388 lines. `@keyframes crawlReveal` at line 292. `.crawl-text.crawl-reveal` at line 280. `animation-delay: 0.5s` (p1) and `2.5s` (p2). `btn-begin` delay 4.5s. |
| `frontend/static/js/origin.js` | Card selection + confirmOrigin + pollSeedTask + dual-gate | VERIFIED | 252 lines. `confirmOrigin()` at line 117. `pollSeedTask()` at line 210. `fetch.*api/origin` at line 147. `fetch.*api/tasks` at line 212. |

**Note on origin.html line count:** The PLAN specified `min_lines: 80`, but the file is 56 lines. This is intentional — cards are rendered dynamically by JS from `/api/origins`, keeping the HTML a minimal shell. The file provides all structural scaffolding (3 step sections, input, error area, script tag) and is not a stub.

---

## Key Link Verification

### Plan 04-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/services.py (start_new_game)` | `simulation/seed.py (seed_organizations, seed_fighters, enforce_roster_target, enforce_roster_quality)` | Function call with origin config params | WIRED | `_run_new_game()` imports all 4 functions and calls them with `player_org_name=promotion_name, player_org_prestige=config["prestige"], player_org_balance=config["budget"], origin_type=origin_type` |
| `api/services.py (start_new_game)` | `simulation/history.py (fabricate_history)` | Function call after seeding | WIRED | `_run_new_game` calls `fabricate_history(session, fighters, orgs, seed=42)` at line 476 |
| `run.py` | `api/app.py (create_app)` | Starts server without seed calls | WIRED | `app = create_app(DB_URL)` then `app.run()`. No seeding anywhere in run.py. |

### Plan 04-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/static/js/origin.js (confirmOrigin)` | `/api/origin` | fetch POST with origin_type + promotion_name | WIRED | origin.js line 147: `fetch("/api/origin", { method: "POST", ... body: JSON.stringify({ origin_type: selectedOrigin, promotion_name: name }) })` |
| `api/app.py (select_origin)` | `api/services.py (start_new_game)` | Calls start_new_game with validated params | WIRED | app.py line 83: `task_id = services.start_new_game(origin_type, promotion_name)` |
| `frontend/static/js/origin.js (pollSeedTask)` | `/api/tasks/<task_id>` | Polls until seed completes | WIRED | origin.js line 212: `fetch("/api/tasks/" + taskId)` inside `setInterval` |
| `api/app.py (index)` | `api/services.py (has_game_state)` | Conditional template rendering | WIRED | app.py line 29: `if services.has_game_state(): return render_template("index.html")` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PLYR-01 | 04-02 | Player selects from multiple background origins at game start | SATISFIED | GET / serves origin.html on fresh DB; 3 cards built from `/api/origins`; card selection stored in `selectedOrigin` |
| PLYR-02 | 04-02 | Each origin provides a narrative intro explaining why the promotion exists | SATISFIED | `NARRATIVES` object in origin.js contains 2 second-person cinematic paragraphs per origin; rendered in text crawl step |
| PLYR-03 | 04-01 | Origins have mechanical consequences (different starting budget, roster size, reputation) | SATISFIED | ORIGIN_CONFIGS: The Heir ($8M/55 prestige/20 roster), The Matchmaker ($4M/40/12), The Comeback ($1.5M/25/6). `enforce_roster_target()` and `enforce_roster_quality()` enforce these at seed time. |
| PLYR-04 | 04-01 | At least 3 distinct starting scenarios with meaningfully different gameplay | SATISFIED | 3 origin configs with budget range 5.3x ($1.5M to $8M), prestige range 25-55 (120% difference), roster range 6-20 (3.3x). `enforce_roster_quality()` adds composition differences (inherited/hand_picked/scrappy). |

All 4 PLYR requirements satisfied. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/templates/origin.html` | 30 | `placeholder="e.g. Thunder FC"` | Info | HTML input placeholder attribute — not a code stub |
| `frontend/static/css/origin.css` | 232 | `.name-form input::placeholder` | Info | CSS pseudo-selector — not a code stub |
| `api/services.py` | Various | `return []` / `return {}` | Info | All are error-path guards in pre-existing functions (inside `except` blocks or empty-query returns). None are in Phase 4 code. |

No blocker anti-patterns found. No Phase 4 code contains TODO/FIXME/placeholder/stub patterns.

---

## Human Verification Required

### 1. Origin Card Visual Layout

**Test:** Run `python3 run.py`, open http://127.0.0.1:5000
**Expected:** 3 origin cards side by side in a row. Each card shows: origin name (Rajdhani font, large), tagline, and 3 stat lines (Budget: $XM, Prestige: X, Roster: X fighters). No "Easy", "Medium", or "Hard" labels anywhere on the page.
**Why human:** CSS flex row layout and card rendering are client-side. Font loading (Rajdhani/Inter from Google Fonts), hover glow effects, and selected-state accent border cannot be verified without a browser.

### 2. Card Selection + Name Input Animation

**Test:** Click "The Matchmaker" card. Then click "The Comeback" card. Type "Thunder FC" in the name input.
**Expected:** Clicked card gets a highlighted border/glow (accent color). Previously selected card deselects. Name input section slides in below cards after first click. Confirm button is present and enabled.
**Why human:** Card selection class toggling and slide-in animation require visual inspection. The `active` CSS class transitions cannot be unit-tested.

### 3. Text Crawl Animation Timing

**Test:** With "The Comeback" selected and "Thunder FC" entered, click Confirm.
**Expected:** Cards and name input disappear. First paragraph of The Comeback narrative fades in at ~0.5s. Second paragraph fades in at ~2.5s. "Begin" button fades in at ~4.5s but remains disabled (greyed out) until seeding finishes. Once both animation AND seeding are done, Begin becomes clickable.
**Why human:** CSS animation timing and the dual-gate UX pattern (Begin disabled until both `seedComplete` and `crawlComplete` flags are true) require live observation to confirm the timing feels correct and the button does not appear prematurely.

### 4. Post-Origin Dashboard Redirect

**Test:** Click "Begin" after it activates. Then refresh the browser.
**Expected:** After clicking Begin, main dashboard loads showing "Thunder FC" as the promotion name in the header/sidebar. On refresh, dashboard loads again — origin page does not reappear.
**Why human:** Dashboard promotion name display depends on frontend JS reading `/api/organization` or `/api/gamestate`. Confirming the correct name propagates to the dashboard UI requires browser verification.

---

## Gaps Summary

No gaps. All 14 automated must-haves are verified. The 4 human verification items are UX/visual quality checks — they do not block goal achievement from a code correctness standpoint.

The one noteworthy discrepancy is `origin.html` being 56 lines vs. the plan's `min_lines: 80` spec. This is a non-issue: the smaller line count reflects the correct architectural decision (client-side card rendering from `/api/origins`) rather than incomplete implementation. The HTML provides all required structural elements.

---

## Commit Verification

| Commit | Description | Verified |
|--------|-------------|---------|
| `3cf91b9` | feat: OriginType enum, GameState.origin_type, ORIGIN_CONFIGS, parameterized seed pipeline | Yes — `git cat-file -t 3cf91b9` returns `commit` |
| `d96f2e4` | feat: has_game_state, start_new_game async service, deferred-seeding run.py | Yes — `git cat-file -t d96f2e4` returns `commit` |
| `617c4b8` | feat: route-switching, POST /api/origin, origin.html, origin.css, origin.js | Yes — `git cat-file -t 617c4b8` returns `commit` |

---

_Verified: 2026-03-02_
_Verifier: Claude (gsd-verifier)_
