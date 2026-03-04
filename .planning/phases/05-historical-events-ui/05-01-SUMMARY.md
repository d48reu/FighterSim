---
phase: 05-historical-events-ui
plan: 01
subsystem: ui
tags: [flask, vanilla-js, css, pagination, events, history]

# Dependency graph
requires:
  - phase: 02-fight-history
    provides: "GET /api/events/all-history endpoint and fabricated event data"
provides:
  - "League History UI section in Events view with org filter and pagination"
  - "Offset pagination on /api/events/all-history endpoint"
  - "Player-org exclusion from historical event listing"
  - "Organization fields (id, name) in event dict responses"
  - "Revenue/attendance hiding for zero-data historical events"
affects: [06-tech-debt-cleanup, 08-ui-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Offset pagination via limit+offset query params on list endpoints"
    - "Dynamic org filter dropdown populated from API response data"
    - "Conditional revenue/attendance rendering based on data presence"

key-files:
  created: []
  modified:
    - api/services.py
    - api/app.py
    - frontend/templates/index.html
    - frontend/static/js/app.js
    - frontend/static/css/style.css
    - ruff.toml

key-decisions:
  - "Offset pagination over cursor pagination -- simpler for browsing historical data with no real-time inserts"
  - "Player-org exclusion via is_player flag query -- keeps League History focused on AI org events only"
  - "Org filter populated from first batch response -- avoids separate /api/organizations endpoint"
  - "Revenue/attendance hidden when tickets_sold and gate_revenue are both zero -- clean UX for fabricated events"

patterns-established:
  - "Offset pagination: limit+offset query params passed through route to service function"
  - "Dynamic filter dropdowns: populate from API response data, reset offset on filter change"
  - "Load More pattern: append mode with hidden button toggled by batch size comparison"

requirements-completed: [HIST-05]

# Metrics
duration: ~10min
completed: 2026-03-03
---

# Phase 5 Plan 01: League History Summary

**Full-stack League History browser with org filter, offset pagination, and revenue hiding for historical events in the Events view sidebar**

## Performance

- **Duration:** ~10 min (across checkpoint-gated execution)
- **Started:** 2026-03-03
- **Completed:** 2026-03-03
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 6

## Accomplishments
- Wired existing /api/events/all-history endpoint to a new League History UI section in the Events view sidebar
- Added offset pagination, player-org exclusion, and organization fields to the event history API
- Built org filter dropdown, paginated event list with Load More, and click-to-view fight cards
- Hidden revenue/attendance sections for historical events (zero data from fabrication)

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend -- Add offset pagination, player-org exclusion, and org fields** - `37a7b19` (feat)
2. **Task 2: Frontend -- League History section with org filter, pagination, and revenue hiding** - `8b3e69b` (feat)
3. **Task 3: Verify League History UI end-to-end** - APPROVED (checkpoint:human-verify, no commit)

## Files Created/Modified
- `api/services.py` - Added organization_id/organization_name to _event_dict(), offset param and player-org exclusion to get_all_event_history()
- `api/app.py` - Added offset query param to /api/events/all-history route
- `frontend/templates/index.html` - Added League History HTML section with org filter dropdown and Load More button
- `frontend/static/js/app.js` - Added loadLeagueHistory() with pagination, org filter wiring, revenue/attendance conditional hiding
- `frontend/static/css/style.css` - Added League History styles (org filter, history list, load-more button, accent color heading)
- `ruff.toml` - Added linting config for code quality

## Decisions Made
- Used offset pagination (limit+offset) over cursor pagination -- simpler for browsing static historical data
- Player-org events excluded via is_player flag query to keep League History focused on AI org history
- Org filter populated from first API batch response to avoid needing a separate organizations endpoint
- Revenue/attendance sections hidden when both tickets_sold and gate_revenue are zero -- clean display for fabricated events

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed full Fighter objects needed for overall computation in enforce_roster_target**
- **Found during:** Task 3 verification (pre-existing bug surfaced during testing)
- **Issue:** enforce_roster_target was using column projection that didn't include enough fields for the Fighter.overall @property
- **Fix:** Changed to use full Fighter objects for overall computation
- **Files modified:** simulation/seed.py
- **Verification:** Fresh seed completes without error
- **Committed in:** `d7ac528`

**2. [Rule 1 - Bug] Added missing session.commit() in fabricate_history**
- **Found during:** Task 3 verification (pre-existing bug surfaced during testing)
- **Issue:** fabricate_history() was not committing its session, causing historical events to not persist
- **Fix:** Added explicit session.commit() call
- **Files modified:** simulation/seed.py
- **Verification:** Historical events appear in database after seeding
- **Committed in:** `354125d`

---

**Total deviations:** 2 auto-fixed (2 bugs, both Rule 1)
**Impact on plan:** Both were pre-existing bugs exposed during end-to-end testing. Essential for historical events to function. No scope creep.

## Issues Encountered
None beyond the pre-existing bugs documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HIST-05 fully satisfied: historical events browsable from UI with org filtering and pagination
- Phase 5 complete (single-plan phase)
- Ready for Phase 6 (Tech Debt Cleanup) or any subsequent phase

## Self-Check: PASSED

All 6 modified files exist on disk. All 4 commit hashes verified in git log. SUMMARY.md created successfully.

---
*Phase: 05-historical-events-ui*
*Completed: 2026-03-03*
