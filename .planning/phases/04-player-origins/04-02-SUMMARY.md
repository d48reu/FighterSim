---
phase: 04-player-origins
plan: 02
subsystem: frontend, api
tags: [flask-routes, vanilla-js, css-animations, origin-selection, text-crawl, async-polling]

# Dependency graph
requires:
  - phase: 04-player-origins
    plan: 01
    provides: OriginType enum, ORIGIN_CONFIGS, has_game_state(), start_new_game(), deferred-seeding run.py
provides:
  - Route-switching GET / (origin.html vs index.html based on GameState)
  - GET /api/origins endpoint serving origin configs to frontend
  - POST /api/origin endpoint triggering async seed with validation
  - origin.html standalone page with 3-card selection, name input, cinematic text crawl
  - origin.css with CSS animation keyframes (crawl-reveal) and dark theme styling
  - origin.js with card interaction, fetch POST, seed polling, dual-gated Begin button
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [route-switching via has_game_state(), dual-gate pattern (animation + async task), CSS crawl-reveal keyframes, standalone HTML page outside SPA]

key-files:
  created:
    - frontend/templates/origin.html
    - frontend/static/css/origin.css
    - frontend/static/js/origin.js
  modified:
    - api/app.py

key-decisions:
  - "Origin configs served via GET /api/origins so frontend never hardcodes origin data"
  - "Text crawl narratives stored client-side in origin.js (no server round-trip for static prose)"
  - "Dual-gate Begin button: both seed task completion AND animation timer must fire before enabling"

patterns-established:
  - "Route-switching pattern: GET / checks has_game_state() to serve origin vs dashboard"
  - "Standalone page pattern: origin.html is independent of SPA, with its own CSS/JS"
  - "Dual-gate UX pattern: combine async completion + animation timer before enabling next action"

requirements-completed: [PLYR-01, PLYR-02]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 04 Plan 02: Origin Selection Frontend Summary

**Cinematic origin selection page with 3 cards (Heir/Matchmaker/Comeback), promotion naming, second-person text crawl with CSS fade-in, and dual-gated Begin flow**

## Performance

- **Duration:** 5 min (includes human verification checkpoint)
- **Started:** 2026-03-03T01:39:00Z
- **Completed:** 2026-03-03T02:11:00Z
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 4

## Accomplishments
- Route-switching at GET / serves origin.html on fresh DB and index.html after game creation -- origin page never reappears
- 3 selectable origin cards (The Heir, The Matchmaker, The Comeback) with budget/prestige/roster stats, no difficulty labels
- Promotion name input with HTML5 validation (2-50 chars) and pattern enforcement
- Cinematic second-person text crawl with CSS crawl-reveal animations (sequential fade-in at 0.5s, 2.5s delays)
- Dual-gated Begin button: requires both seed task completion (async polling) AND animation timer to enable

## Task Commits

Each task was committed atomically:

1. **Task 1: Add route-switching, POST /api/origin endpoint, origin.html, origin.css, origin.js** - `617c4b8` (feat)
2. **Task 2: Verify origin selection flow end-to-end in browser** - human-verify checkpoint, user approved

## Files Created/Modified
- `api/app.py` - Added route-switching at GET / (has_game_state check), GET /api/origins, POST /api/origin with validation
- `frontend/templates/origin.html` - Standalone origin selection page with 3-step flow (cards, name input, text crawl)
- `frontend/static/css/origin.css` - Dark theme styling, card hover/selected states, crawl-reveal keyframes, responsive layout
- `frontend/static/js/origin.js` - Card selection, confirmOrigin(), showTextCrawl(), pollSeedTask(), dual-gate Begin button logic

## Decisions Made
- Origin configs delivered via dedicated GET /api/origins endpoint rather than embedding in HTML template -- keeps frontend decoupled from server-side rendering
- Narrative text crawl content stored as JS objects in origin.js -- static prose doesn't need server round-trips
- Begin button uses dual-gate pattern (seedComplete flag + setTimeout matching animation duration) to prevent premature navigation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 (Player Origins) is fully complete -- both backend (04-01) and frontend (04-02) plans delivered
- New games now start with cinematic origin selection before gameplay
- All 4 PLYR requirements satisfied (PLYR-01 through PLYR-04)
- Ready to proceed to Phase 5 (Historical Events UI) or Phase 6 (Tech Debt Cleanup)

## Self-Check: PASSED

All files found. Commit verified (617c4b8).

---
*Phase: 04-player-origins*
*Completed: 2026-03-03*
