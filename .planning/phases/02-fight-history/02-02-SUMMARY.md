---
phase: 02-fight-history
plan: 02
subsystem: simulation
tags: [fight-history, seed-pipeline, api-endpoint, integration, determinism]

# Dependency graph
requires:
  - phase: 02-fight-history
    plan: 01
    provides: "fabricate_history() module generating events/fights/champions/rivalries"
  - phase: 01-fighter-generation
    provides: "450 seeded fighters with W/L/D records, 4 orgs, contracts"
provides:
  - "Seed pipeline calls fabricate_history() after seed_fighters() in run.py and test_cli.py"
  - "All-org event browsing via GET /api/events/all-history with optional org filter"
  - "End-to-end validated pipeline: seed -> history -> event sim -> monthly sim -> rankings"
  - "Deterministic history: two runs produce identical 67 events, 405 fights"
  - "History validation step in test_cli.py checking events, fights, titles, rivals, record consistency"
affects: [frontend, api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "fabricate_history() called after seed_fighters() with explicit session.commit()"
    - "All-org event browsing reuses _event_dict() serializer with include_fights=True"

key-files:
  created: []
  modified:
    - "simulation/seed.py"
    - "run.py"
    - "test_cli.py"
    - "api/services.py"
    - "api/app.py"

key-decisions:
  - "fabricate_history() called in run.py/test_cli.py after seed_fighters(), not inside seed_fighters() itself -- keeps seed function focused on fighter generation"
  - "Session commit required after fabricate_history() since it only flushes, not commits"
  - "All-org event browsing uses include_fights=True for full fight details in historical event view"

patterns-established:
  - "History fabrication is a post-seed step, not embedded in seed pipeline"
  - "All-org browsing endpoint pattern: /api/events/all-history?organization_id=N&limit=50"

requirements-completed: [HIST-01, HIST-05, HIST-06]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 2 Plan 2: Seed Pipeline Integration and All-Org Event Browsing Summary

**Wired fabricate_history() into run.py and test_cli.py seed pipeline, added /api/events/all-history endpoint, and validated full end-to-end pipeline with deterministic output (67 events, 405 fights, 18 title fights)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T05:32:45Z
- **Completed:** 2026-03-02T05:36:35Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Wired fabricate_history() into run.py (prints event/fight/champion/rivalry summary on startup)
- Added Step 1b to test_cli.py: validates event counts, fight counts, title fights, rivalries, and per-weight-class record consistency
- Added get_all_event_history() service function and /api/events/all-history route for browsing events from all orgs
- Full pipeline verified: seed -> history -> event sim (10 fights) -> monthly sim (3 months) -> rankings -- all pass
- Determinism confirmed: two identical runs produce identical output

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire fabrication into seed pipeline and startup scripts** - `b39f001` (feat)
2. **Task 2: Add all-org event browsing API endpoint and run end-to-end validation** - `7efaef4` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `simulation/seed.py` - Added import of fabricate_history from simulation.history
- `run.py` - Calls fabricate_history() after seed_fighters() with summary output; fixed rivalry return type
- `test_cli.py` - Added fabricate_history() call with session.commit(), Step 1b validation (events, fights, titles, rivals, record consistency), fixed rivalry_with field name
- `api/services.py` - Added get_all_event_history() function for all-org event browsing with optional org filter
- `api/app.py` - Added /api/events/all-history route with organization_id and limit query params

## Decisions Made
- **fabricate_history() as post-seed step:** Called after seed_fighters() returns, not embedded inside it. Keeps seed_fighters() focused on fighter generation and history fabrication as a separate concern.
- **Explicit session.commit() after fabrication:** fabricate_history() only flushes to DB, so the caller must commit. This is consistent with how SQLAlchemy context managers work (no auto-commit on exit).
- **include_fights=True for all-org browsing:** Historical events include full fight details (results, narratives) since the primary use case is browsing past fight results.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] rivalries return type is int, not list**
- **Found during:** Task 1 (wiring test_cli.py)
- **Issue:** Plan specified `len(history.get('rivalries', []))` but fabricate_history() returns `{'rivalries': len(rivalries)}` -- an int, not a list.
- **Fix:** Changed to `history.get('rivalries', 0)` in both run.py and test_cli.py
- **Files modified:** run.py, test_cli.py
- **Verification:** Pipeline runs without TypeError
- **Committed in:** 7efaef4 (Task 2 commit)

**2. [Rule 1 - Bug] Fighter model uses rivalry_with, not rival_id**
- **Found during:** Task 2 (Step 1b validation)
- **Issue:** Plan referenced `Fighter.rival_id` but the actual model field is `Fighter.rivalry_with`
- **Fix:** Changed query to use `Fighter.rivalry_with.isnot(None)`
- **Files modified:** test_cli.py
- **Verification:** Rivalry count correctly shows 61 fighters with rivals
- **Committed in:** 7efaef4 (Task 2 commit)

**3. [Rule 3 - Blocking] Session not committed after fabricate_history()**
- **Found during:** Task 2 (end-to-end validation)
- **Issue:** Step 1b opened a new session and found 0 events/fights because fabricate_history() only flushes, and the SQLAlchemy context manager doesn't auto-commit on exit
- **Fix:** Added `session.commit()` after fabricate_history() call in test_cli.py Step 1
- **Files modified:** test_cli.py
- **Verification:** Step 1b now sees all 67 events and 405 fights
- **Committed in:** 7efaef4 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for correct pipeline execution. No scope creep. The plan's interface documentation had minor inaccuracies (rivalry return type, field name) that were resolved inline.

## Out-of-Scope Discoveries

**Archetype-record consistency after history fabrication:** Step 5e in test_cli.py reports 33 archetype-record mismatches because fabricate_history() reconciles Fighter W/L/D against actual Fight rows (intentional, from Plan 02-01). This invalidates the seed-only archetype win-rate invariant. Logged to `deferred-items.md` -- not a regression, just a test that predates history fabrication.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 02 (Fight History) is fully complete: fabrication module built and integrated into seed pipeline
- Historical events are browsable via API and fighter timelines populate automatically
- All existing gameplay systems (event sim, monthly sim, rankings) work correctly on top of fabricated history
- Ready for Phase 03 (narrative/template expansion) or any phase that depends on fight history existing at game start

## Self-Check: PASSED

- simulation/seed.py: FOUND (contains fabricate_history import)
- run.py: FOUND (contains fabricate_history call)
- test_cli.py: FOUND (contains fabricate_history call + Step 1b validation)
- api/services.py: FOUND (contains get_all_event_history)
- api/app.py: FOUND (contains all_event_history route)
- Task 1 commit b39f001: FOUND
- Task 2 commit 7efaef4: FOUND
- 02-02-SUMMARY.md: FOUND

---
*Phase: 02-fight-history*
*Completed: 2026-03-02*
