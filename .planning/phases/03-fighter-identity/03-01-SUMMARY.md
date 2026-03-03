---
phase: 03-fighter-identity
plan: 01
subsystem: narrative
tags: [jinja2, sqlalchemy, fight-history, career-highlights, templates]

# Dependency graph
requires:
  - phase: 02-fight-history
    provides: "Fabricated Fight + Event rows with methods, rounds, title fights, rivalries"
provides:
  - "generate_fight_history_paragraph(fighter, session) -- Jinja2-powered paragraph referencing actual fights"
  - "extract_career_highlights(fighter, session) -- scored highlight extraction capped at 6"
  - "_query_fighter_fights() -- single-pass fight data query with batch opponent names"
  - "_detect_champion_status() -- Ranking-based champion/former-champion detection"
  - "54 compiled Jinja2 templates across archetype x stage matrix"
affects: [03-fighter-identity plan 02, api integration, frontend fighter detail]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Jinja2 Environment.from_string() for inline narrative templates"
    - "Module-level compiled template pattern (54 templates at import time)"
    - "Deterministic template selection via random.Random(fighter.id)"
    - "Batch opponent name fetching to avoid N+1 queries"

key-files:
  created:
    - "test_fight_history_narrative.py"
  modified:
    - "simulation/narrative.py"

key-decisions:
  - "Fighter.overall is a @property, batch queries use full Fighter objects instead of column projection"
  - "54 templates total: 3 prospect + 18 prime + 18 veteran + 4 overlays + 3 minimal + 8 highlight templates"
  - "Key fight selection uses composite scoring (title > rivalry > KO/sub > upset > recency)"

patterns-established:
  - "Jinja2 from_string() with module-level Environment for narrative templates in simulation/"
  - "Single-query fight data extraction shared between paragraph and highlight generation"
  - "Champion status detection via Ranking table (rank 1 = current) with title-fight-win fallback (former)"

requirements-completed: [IDEN-01, IDEN-02]

# Metrics
duration: 7min
completed: 2026-03-02
---

# Phase 3 Plan 01: Fight-History Narrative Summary

**Jinja2 fight-history paragraph generator with 54 archetype/stage templates and scored career highlight extractor referencing actual Fight rows**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-02T23:58:53Z
- **Completed:** 2026-03-03T00:06:03Z
- **Tasks:** 2
- **Files modified:** 1 (simulation/narrative.py) + 1 test file created

## Accomplishments
- Built `generate_fight_history_paragraph()` that produces archetype-aware, stage-gated prose referencing specific opponents, methods, and rounds from actual Fight rows
- Built `extract_career_highlights()` that scores fights and returns top 6 highlights with mini-narrative text
- 54 compiled Jinja2 templates covering prospect/prime/veteran stages x 6 archetypes, plus champion and rivalry overlays
- Validated against 50 seeded fighters across all career stages with zero errors
- TDD test suite with 15 tests covering all edge cases (zero fights, debut, veteran, rivalry with/without shared fights, champion/former champion, archetype variation, stage variation)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests** - `21b0dfb` (test)
2. **Task 1 (GREEN): Implement fight-history paragraph and career highlights** - `c8a83bc` (feat)

Task 2 validation passed without requiring code changes (seeded DB validation confirmed correctness).

## Files Created/Modified
- `simulation/narrative.py` - Added 934 lines: Jinja2 Environment, 54 compiled templates, helper functions (_humanize_method, _ordinal_round, _query_fighter_fights, _detect_champion_status, _score_fight_for_highlight, _select_key_fights), generate_fight_history_paragraph(), extract_career_highlights()
- `test_fight_history_narrative.py` - 15 TDD tests for all narrative and highlight functionality

## Decisions Made
- Used full Fighter object fetch instead of column projection for batch opponent queries because Fighter.overall is a @property (not a DB column)
- 54 total templates exceeds the ~25-30 estimate in the plan -- additional templates for highlight mini-narratives and minimal/debut cases
- Key fight selection for paragraph references uses composite scoring rather than simple recency, ensuring title fights and rivalry bouts always surface

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Fighter.overall property in batch query**
- **Found during:** Task 1 (GREEN phase, first test run)
- **Issue:** `select(Fighter.id, Fighter.name, Fighter.overall)` fails because `overall` is a @property, not a mapped column
- **Fix:** Changed to `select(Fighter).where(...)` and computed overall from the loaded objects
- **Files modified:** simulation/narrative.py
- **Verification:** All 15 tests pass
- **Committed in:** c8a83bc (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix for SQLAlchemy compatibility. No scope creep.

## Issues Encountered
- `seed_fighters()` and `fabricate_history()` signatures changed from earlier phases (now require `orgs` and `fighters` parameters). Task 2 validation script updated to match current API.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Fight-history paragraph and career highlights are ready for API integration (Plan 02)
- services.py `get_fighter_bio()` can append history paragraph via `generate_fight_history_paragraph(fighter, session)`
- New `/api/fighters/{id}/highlights` endpoint can call `extract_career_highlights(fighter, session)`
- Frontend fighter detail panel can add Career Highlights section

## Self-Check: PASSED

- FOUND: test_fight_history_narrative.py
- FOUND: simulation/narrative.py
- FOUND: 03-01-SUMMARY.md
- FOUND: 21b0dfb (test commit)
- FOUND: c8a83bc (feat commit)
- FOUND: All functions importable

---
*Phase: 03-fighter-identity*
*Completed: 2026-03-02*
