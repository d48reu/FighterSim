---
phase: 04-player-origins
plan: 01
subsystem: database, simulation
tags: [sqlalchemy, enum, seed-pipeline, origin-system, async-task]

# Dependency graph
requires:
  - phase: 03-fighter-identity
    provides: narrative system, fighter bios, seed pipeline
provides:
  - OriginType enum with 3 player starting conditions
  - ORIGIN_CONFIGS dict with budget/prestige/roster parameters per origin
  - Parameterized seed_organizations() with backward-compatible defaults
  - enforce_roster_target() and enforce_roster_quality() roster shaping functions
  - has_game_state() service function
  - start_new_game() async service for origin-driven game creation
  - Deferred-seeding run.py (server starts with empty DB)
affects: [04-02 (API endpoints + frontend for origin selection)]

# Tech tracking
tech-stack:
  added: []
  patterns: [origin-driven seed pipeline, deferred seeding startup, roster enforcement functions]

key-files:
  created: []
  modified:
    - models/models.py
    - simulation/seed.py
    - api/services.py
    - run.py

key-decisions:
  - "OriginType stored as String(50) not SQLAlchemy Enum for SQLite compatibility"
  - "enforce_roster_quality uses age vs prime_start for prospect detection (not a separate career_stage column)"
  - "run.py defers all seeding to origin selection POST endpoint (Plan 04-02)"

patterns-established:
  - "Origin config dict pattern: keyed by OriginType.value string, contains label/tagline/budget/prestige/roster_target/roster_quality"
  - "Roster enforcement pipeline: enforce_roster_target (size) then enforce_roster_quality (composition) as post-seed steps"

requirements-completed: [PLYR-03, PLYR-04]

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 04 Plan 01: Player Origins Backend Summary

**OriginType enum with 3 origin configs ($1.5M/$4M/$8M budgets), parameterized seed pipeline with roster enforcement, async start_new_game service, deferred-seeding run.py**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T01:35:40Z
- **Completed:** 2026-03-03T01:38:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- OriginType enum (THE_HEIR, THE_MATCHMAKER, THE_COMEBACK) with meaningful gameplay differences: budget ($1.5M to $8M), prestige (25 to 55), roster size (6 to 20)
- Parameterized seed_organizations() maintains full backward compatibility -- test_cli.py passes unchanged
- Async start_new_game() service runs complete seed pipeline (organizations + fighters + roster enforcement + history fabrication) with origin parameters
- run.py restructured for deferred seeding -- server starts with empty DB, ready for origin selection UI

## Task Commits

Each task was committed atomically:

1. **Task 1: Add OriginType enum, GameState.origin_type column, and ORIGIN_CONFIGS dict with parameterized seed_organizations** - `3cf91b9` (feat)
2. **Task 2: Add has_game_state and start_new_game services, restructure run.py for deferred seeding** - `d96f2e4` (feat)

## Files Created/Modified
- `models/models.py` - Added OriginType enum (3 values) and GameState.origin_type nullable String(50) column
- `simulation/seed.py` - Added ORIGIN_CONFIGS dict, parameterized seed_organizations(), enforce_roster_target(), enforce_roster_quality()
- `api/services.py` - Added has_game_state(), start_new_game(), _run_new_game() async task pair
- `run.py` - Restructured to start server without seeding (deferred to origin selection)

## Decisions Made
- Used String(50) for GameState.origin_type instead of SQLAlchemy Enum to keep SQLite compatibility simple -- OriginType enum validates in Python code, not at DB level
- Prospect detection in enforce_roster_quality uses `fighter.age < fighter.prime_start` since there is no explicit career_stage column stored on Fighter
- enforce_roster_quality for "scrappy" origin releases fighters with overall > 75 OR GOAT_CANDIDATE archetype to ensure The Comeback starts with underdog-tier talent

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend foundation complete for origin-driven game creation
- Plan 04-02 can now build API endpoints (POST /api/origin) and frontend origin selection screen
- has_game_state() enables frontend routing: show origin screen when False, show dashboard when True

## Self-Check: PASSED

All files found. All commits verified (3cf91b9, d96f2e4).

---
*Phase: 04-player-origins*
*Completed: 2026-03-03*
