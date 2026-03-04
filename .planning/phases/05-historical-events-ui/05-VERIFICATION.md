---
phase: 05-historical-events-ui
verified: 2026-03-03T00:00:00Z
status: human_needed
score: 5/6 must-haves verified
re_verification: false
human_verification:
  - test: "Navigate to Events view and confirm League History section appears below Completed"
    expected: "A 'League History' section with a warm-accented heading, org filter dropdown, event list, and Load More button is visible in the left sidebar below the Completed section"
    why_human: "DOM rendering and visual layout cannot be verified programmatically without a browser"
  - test: "Confirm org filter dropdown is populated with AI org names after Events view loads"
    expected: "Dropdown shows 'All Orgs' plus the 3 AI organization names drawn from the first batch of historical events"
    why_human: "Dynamic dropdown population happens at runtime via JS after API response arrives"
  - test: "Click a historical event and confirm fight card renders with results but no revenue/attendance section"
    expected: "Center column shows event name, venue, date, fight results with method badges and narratives; no Sellout banner, Attendance line, or Revenue Summary block"
    why_human: "Conditional rendering of revenue block (tickets_sold > 0 || gate_revenue > 0) requires live event data to confirm fabricated events have zero values"
  - test: "Confirm player org events do NOT appear in League History"
    expected: "Only AI org events appear in League History list; player org completed events remain only in the Completed section"
    why_human: "Requires running a seeded game and inspecting rendered list items against known player org name"
  - test: "If 25+ historical events exist, confirm Load More button appears and loads the next batch on click"
    expected: "Load More button is visible; clicking it appends the next 25 events to the list without clearing existing entries"
    why_human: "Pagination behavior requires browser interaction and sufficient seed data to trigger the 25-event batch boundary"
---

# Phase 5: Historical Events UI Verification Report

**Phase Goal:** Players can browse pre-generated fight history from the UI, not just the API
**Verified:** 2026-03-03
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Player can see a 'League History' section in the Events view sidebar listing historical events from AI orgs | VERIFIED | `index.html` line 163-172: `<div class="events-section league-history-section">` with `<h3>League History</h3>` placed after Completed section |
| 2 | Player can filter historical events by organization using a dropdown | VERIFIED | `index.html` line 165: `<select id="history-org-filter">` present; `app.js` line 3070: change listener resets offset and calls `loadLeagueHistory()`; org filter URL param appended at line 1174 |
| 3 | Player can click a historical event to see its full fight card and results in the center column | VERIFIED | `app.js` lines 1217-1223: click handler sets `state.selectedEventId` and calls `loadEventCard(state.selectedEventId)`; `loadEventCard()` fetches `/api/events/${eventId}` and renders full card |
| 4 | Player can load more historical events by clicking a 'Load More' button | VERIFIED | `index.html` line 171: `<button id="btn-load-more-history">`; `app.js` line 3074: click listener increments `historyOffset` by `HISTORY_BATCH` and calls `loadLeagueHistory(true)` (append mode); `insertAdjacentHTML('beforeend', html)` used when `append=true` |
| 5 | Historical events do not show revenue/attendance sections (they have zero data) | VERIFIED | `app.js` line 1349: `if (event.tickets_sold > 0 \|\| event.gate_revenue > 0)` guards the entire attendance + revenue block — fabricated events with zero values skip it |
| 6 | Player org events do not appear in League History (they already show in Completed) | VERIFIED | `services.py` `get_all_event_history()`: queries `Organization.is_player == True`, excludes matching org via `Event.organization_id != player_org.id` before fetching |

**Score: 6/6 truths verified programmatically**

All 6 truths have structural and code-level confirmation. 5 items additionally require human browser verification for runtime behavior confirmation (see Human Verification section).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services.py` | `get_all_event_history` with offset param, player-org exclusion, org fields in `_event_dict` | VERIFIED | Function signature: `organization_id=None, limit=50, offset=0`. Player-org exclusion via `is_player == True` query. `_event_dict` returns `organization_id` and `organization_name` fields. Query chain: `.order_by(...).offset(offset).limit(limit)` |
| `api/app.py` | offset query param on `/api/events/all-history` route | VERIFIED | Line 166: `offset = request.args.get("offset", 0, type=int)`. Line 169: passed as `offset=offset` to service call |
| `frontend/templates/index.html` | League History HTML section with org filter dropdown and Load More button | VERIFIED | Lines 163-172: complete `league-history-section` div with `h3`, `select#history-org-filter`, `div#events-history-list`, `button#btn-load-more-history` (initially `hidden`) |
| `frontend/static/js/app.js` | `loadLeagueHistory` function with pagination and org filter | VERIFIED | Lines 1170-1225: full implementation — API call with limit/offset/org params, empty-state handling, HTML rendering with org name in meta, append vs. replace mode, Load More toggle, org dropdown population on first load, click handlers calling `loadEventCard` |
| `frontend/static/css/style.css` | Styling for League History section, org filter, load-more button | VERIFIED | Lines 3298-3319: `.history-org-filter`, `.history-list`, `.load-more-btn`, `.league-history-section h3` — all four rules present with design token usage and fallbacks |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/static/js/app.js` | `/api/events/all-history` | `api()` fetch in `loadLeagueHistory()` | WIRED | Line 1173: `` let url = `/api/events/all-history?limit=${HISTORY_BATCH}&offset=${historyOffset}`; `` then `await api(url)` at line 1175 |
| `frontend/static/js/app.js` | `loadEventCard()` | click handler on history event list items | WIRED | Lines 1217-1223: `el.querySelectorAll('.event-list-item').forEach(...)` attaches click listener setting `state.selectedEventId` then calling `loadEventCard(state.selectedEventId)` |
| `api/services.py` | Organization model | player-org exclusion query and org name in `_event_dict` | WIRED | `get_all_event_history` queries `Organization.is_player == True`; `_event_dict` accesses `event.organization.name` via SQLAlchemy relationship |
| `loadLeagueHistory` | `loadEventsView` | Added to Promise.all call | WIRED | Line 1117: `await Promise.all([loadScheduledEvents(), loadCompletedEvents(), loadLeagueHistory(), loadBookableFighters()])` |
| `history-org-filter` change | `loadLeagueHistory()` | DOM event listener | WIRED | Line 3070-3073: change listener resets `historyOffset = 0` and calls `loadLeagueHistory()` |
| `btn-load-more-history` click | `loadLeagueHistory(true)` | DOM event listener | WIRED | Line 3074-3077: click listener increments `historyOffset += HISTORY_BATCH` and calls `loadLeagueHistory(true)` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HIST-05 | 05-01-PLAN.md | Historical events with results are browsable from day one | SATISFIED | Full-stack implementation: backend offset pagination + player-org exclusion + org fields; frontend League History section with org filter, pagination, fight card rendering, and revenue hiding. Commits `37a7b19` (backend) and `8b3e69b` (frontend) verified in git log. |

**Orphaned requirements check:** REQUIREMENTS.md maps HIST-05 to "Phase 2: Fight History + Phase 5: Historical Events UI". Phase 5 claims only HIST-05. No orphaned requirements.

### Anti-Patterns Found

None detected. Scan of all 5 modified files (api/services.py, api/app.py, frontend/templates/index.html, frontend/static/js/app.js, frontend/static/css/style.css) found:
- No TODO/FIXME/HACK/PLACEHOLDER comments in history-related code
- No stub returns (`return null`, `return {}`, `return []`) in history functions
- No empty JS handlers — all event listeners perform real actions
- Revenue/attendance conditional is substantive (not a placeholder guard)

### Human Verification Required

#### 1. League History Section Visual Rendering

**Test:** Start a fresh game with `python3 run.py`, select any origin, navigate to Events view
**Expected:** A "League History" section with warm-accented heading appears below "Completed" in the left sidebar, showing a dropdown and event list
**Why human:** DOM layout and CSS visual rendering require a browser

#### 2. Org Filter Dropdown Population

**Test:** In the Events view, inspect the org filter dropdown after page load
**Expected:** Dropdown shows "All Orgs" plus the names of the 3 AI organizations (seeded names)
**Why human:** Dynamic population from API response data happens at runtime; org names are database-generated

#### 3. Fight Card Rendering Without Revenue (Historical Events)

**Test:** Click any event in the League History list
**Expected:** Center column shows fight results with method badges and narratives; no Sellout banner, no Attendance line, no Revenue Summary block
**Why human:** Requires confirming fabricated events have `tickets_sold=0` and `gate_revenue=0` in the live database, and that the conditional renders correctly at runtime

#### 4. Player Org Exclusion Confirmed

**Test:** Note the player org name shown in the top navigation; confirm it does not appear as an org in League History
**Expected:** Player org events absent from League History; same events appear in Completed section
**Why human:** Requires cross-referencing rendered list items against known player org name in a live session

#### 5. Load More Pagination

**Test:** If League History shows a "Load More" button, click it
**Expected:** Next batch of 25 events appends below existing items without clearing the list; button disappears when all events are loaded
**Why human:** Requires sufficient seed data (25+ fabricated events per org) and browser interaction

### Gaps Summary

No gaps. All 6 observable truths are structurally verified. All 5 required artifacts exist, are substantive (not stubs), and are wired. All 6 key links are confirmed. HIST-05 is fully satisfied. The 5 human verification items are confirmatory, not blocking — they validate runtime behavior of code that is correctly structured.

---

_Verified: 2026-03-03_
_Verifier: Claude (gsd-verifier)_
