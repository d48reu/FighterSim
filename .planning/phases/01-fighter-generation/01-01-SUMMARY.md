---
phase: 01-fighter-generation
plan: 01
subsystem: simulation
tags: [faker, numpy, name-generation, stat-generation, deterministic-rng, tdd]

# Dependency graph
requires: []
provides:
  - "simulation/name_gen.py: Locale-based name generation with romanized fallbacks for 22 nationalities"
  - "simulation/stat_gen.py: Archetype/style/career-stage-driven stat generation with numpy distributions"
  - "requirements.txt: faker>=40.0 and numpy>=2.0 added"
affects: [01-fighter-generation-plan-02, simulation-seed]

# Tech tracking
tech-stack:
  added: [faker>=40.0, numpy>=2.0]
  patterns: [dual-rng-seeding, nfd-ascii-normalization, hardcoded-romanized-fallbacks]

key-files:
  created:
    - simulation/name_gen.py
    - simulation/stat_gen.py
    - tests/test_name_gen.py
    - tests/test_stat_gen.py
    - tests/__init__.py
  modified:
    - requirements.txt

key-decisions:
  - "ASCII normalization via unicodedata NFD + special char table for non-decomposable chars (ø, ł, ß)"
  - "Faker.seed() is global/class-level -- must re-seed before creating new instances for determinism"
  - "Career stage modifiers use uniform range per-stat for natural variance within stage bounds"

patterns-established:
  - "Romanized name fallback: hardcoded arrays for Russian/Dagestani/Korean/Georgian instead of transliteration libraries"
  - "TDD workflow: failing tests committed first, then implementation, verified green"
  - "Dual RNG pattern: stdlib random.Random for choices/shuffles, numpy Generator for statistical distributions"

requirements-completed: [FGEN-01, FGEN-05]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 1 Plan 01: Foundation Modules Summary

**Faker locale-mapped name generation for 22 nationalities with NFD ASCII normalization, plus numpy-driven stat generation parameterized by archetype/style/career stage**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-02T03:55:34Z
- **Completed:** 2026-03-02T04:00:40Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Name generation module covering 18 Latin-script Faker locales + 4 hardcoded romanized name pools (Russian, Dagestani, Korean, Georgian) + Japanese romanized_name()
- Stat generation module with 6 archetype profiles, 4 style emphasis configs, 4 career stage modifiers using numpy normal distributions
- 24 passing tests (12 per module) covering nationality coverage, 500-name uniqueness, Latin-only enforcement, determinism, archetype differentiation, style emphasis, career stage effects, bounds, and bell-curve clustering
- ASCII normalization handles diacritics (NFD decomposition) and special characters (ø, ł, ß) that don't decompose cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Create name generation module** - TDD
   - RED: `2ee7df6` (test: add failing tests for name generation module)
   - GREEN: `dd11edc` (feat: implement name generation module with locale mapping)
2. **Task 2: Create stat generation module** - TDD
   - RED: `0ddf56f` (test: add failing tests for stat generation module)
   - GREEN: `6d775c7` (feat: implement stat generation module with archetype profiles)

## Files Created/Modified
- `simulation/name_gen.py` - Locale-based name generation: NATIONALITY_LOCALE_MAP, ROMANIZED_NAMES, NATIONALITY_WEIGHTS, create_faker_instances(), generate_name(), pick_nationality()
- `simulation/stat_gen.py` - Stat generation: ARCHETYPE_PROFILES, STYLE_EMPHASIS, CAREER_STAGE_MODIFIERS, generate_stats(), compute_overall()
- `tests/test_name_gen.py` - 12 tests for name generation (nationality, uniqueness, Latin-only, determinism)
- `tests/test_stat_gen.py` - 12 tests for stat generation (archetype, style, career stage, bounds, determinism)
- `tests/__init__.py` - Package init for test discovery
- `requirements.txt` - Added faker>=40.0 and numpy>=2.0

## Decisions Made
- **ASCII normalization approach:** Used stdlib `unicodedata.normalize("NFKD")` plus a special character replacement table for characters like Norwegian ø, Polish ł, and German ß that don't decompose via NFD. This avoids adding a transliteration dependency (unidecode).
- **Career stage modifiers as uniform ranges:** Each career stage defines a (low, high) multiplier range. For each stat independently, a factor is sampled uniformly from this range, creating natural per-stat variance within a stage. This makes two prospects of the same archetype feel different while staying within the expected range.
- **Faker determinism pattern:** Faker.seed() is a class-level operation that resets all instances globally. For deterministic name generation, always call create_faker_instances() (which calls Faker.seed()) before generating names. Do not interleave calls across separately-created instance sets.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added ASCII normalization for diacritical characters**
- **Found during:** Task 1 (name generation implementation)
- **Issue:** Faker locales pt_BR, es_MX, sv_SE, no_NO, etc. produce names with accented characters (Otavio, Strom) that fail the Latin-ASCII regex test
- **Fix:** Added _to_ascii() using unicodedata NFD decomposition plus a _SPECIAL_CHARS table for non-decomposable characters (ø->o, ł->l, ß->ss, etc.)
- **Files modified:** simulation/name_gen.py
- **Verification:** test_all_names_latin_script passes with 10 names per nationality, all ASCII
- **Committed in:** dd11edc (part of Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness -- Faker Latin-script locales still produce non-ASCII characters. No scope creep.

## Issues Encountered
- Faker's global seed behavior required adjusting the determinism test to generate all names from one instance set before re-seeding and generating from a second. This is a known Faker characteristic, not a bug.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both foundation modules (name_gen.py, stat_gen.py) are ready for integration into the refactored seed.py in Plan 02
- The dual-RNG pattern (stdlib Random + numpy Generator) is established and documented
- 22 nationalities mapped with verified Latin-ASCII output
- 6 archetype profiles parameterized with differentiated stat distributions

## Self-Check: PASSED

All 6 files verified present. All 4 commits verified in git log. requirements.txt contains both faker>=40.0 and numpy>=2.0.

---
*Phase: 01-fighter-generation*
*Completed: 2026-03-02*
