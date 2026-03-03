---
phase: 02-fight-history
plan: 03
subsystem: simulation
tags: [fight-history, matchmaker, event-volume, veteran-records, career-realism]

# Dependency graph
requires:
  - phase: 02-fight-history
    plan: 01
    provides: "fabricate_history() module with timeline, matchmaker, narratives"
  - phase: 02-fight-history
    plan: 02
    provides: "Seed pipeline integration and test_cli.py Step 1b validation"
provides:
  - "Veterans show 15-30 fight records backed by real Fight rows (HIST-03 closed)"
  - "Prospects show 1-5 fight records (budget-aware matchmaker)"
  - "222 events with 2146 fights across 5-year history window"
  - "Budget-priority matchmaker: veterans booked first, scan-for-best-opponent pairing"
  - "test_cli.py Step 1b validates career length realism (HIST-03)"
affects: [frontend, api, monthly-sim]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Matchmaker sorts by remaining fight budget descending for veteran priority"
    - "Scan-for-best-opponent pairing replaces adjacent pairing to avoid rematch cap deadlocks"

key-files:
  created: []
  modified:
    - "simulation/history.py"
    - "test_cli.py"

key-decisions:
  - "History window extended from 3 years (2023-2025) to 5 years (2021-2025) for deeper career records"
  - "Event frequency increased from 6-8 weeks to ~2 weeks (10-18 day gaps) per org"
  - "Card size increased from 5-7 to 8-12 fights per event"
  - "Adjacent pairing replaced with scan-for-best-opponent to avoid rematch cap deadlocks with deterministic sort"

patterns-established:
  - "Budget-priority matchmaker: sort available fighters by (-remaining_fights, id) for deterministic veteran-first booking"
  - "Scan-for-best-opponent pairing: for each fighter, scan all remaining opponents instead of only adjacent"

requirements-completed: [HIST-01, HIST-02, HIST-03, HIST-04, HIST-05, HIST-06]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 2 Plan 3: Career Length Realism Summary

**Tuned matchmaker and event volume to produce 222 events with 2146 fights, giving 161 veterans 15-30 fight records and closing the HIST-03 verification gap**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T05:57:52Z
- **Completed:** 2026-03-02T06:02:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Veterans now show 15-30 fight records (avg 19.0) backed by real Fight rows, closing the HIST-03 gap
- Prospects retain 1-5 fight records (avg 2.8) with small budgets consumed quickly
- 161 fighters reach 15+ fights (was 0 before this plan, threshold was 100)
- Max fight count reaches 30 (was 9 before this plan)
- All fighter records (W+L+D) match actual Fight row counts with 0 mismatches
- Determinism preserved: two identical runs produce identical 222 events and 2146 fights

## Task Commits

Each task was committed atomically:

1. **Task 1: Increase event volume and prioritize high-budget fighters in matchmaker** - `1dc4d0e` (feat)
2. **Task 2: Update test_cli.py validation to verify veteran career lengths** - `ad80e40` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `simulation/history.py` - Extended history window to 2021-2025, increased event frequency to ~2 weeks, increased card size to 8-12, replaced adjacent pairing with scan-for-best-opponent, added budget-priority sort
- `test_cli.py` - Added HIST-03 career length realism validation in Step 1b (veteran/prospect counts, max fight count)

## Decisions Made
- **5-year history window (2021-2025):** Doubled from 3 years to provide enough timeline for high-budget fighters to accumulate 25-30 fights across ~120 events per org.
- **~2 week event intervals (10-18 days):** More realistic for major MMA promotions; produces ~360 timeline slots per org vs ~22 at old 6-8 week intervals.
- **8-12 fights per card:** Standard for major MMA promotions; fills more fighter budget per event.
- **Scan-for-best-opponent pairing:** Plan specified budget-priority sort with adjacent pairing, but adjacent pairing created rematch cap deadlocks (same top fighters always adjacent, hit 3-fight max quickly). Replaced with scan-for-next-valid-opponent to maximize fight volume while preserving budget priority and determinism.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjacent pairing deadlocks with deterministic budget sort**
- **Found during:** Task 1 (matchmaker update)
- **Issue:** Plan specified sorting by budget descending with adjacent pairing. This caused the same top fighters to always be adjacent, hitting the 3-fight rematch cap quickly. Result: only 80 veterans reached 15+ fights (need 100+) and many fight slots went unfilled.
- **Fix:** Replaced adjacent pairing (i, i+1 increment) with scan-for-best-opponent: for each fighter a, scan all remaining fighters for first valid opponent not at rematch cap. Preserves budget priority (veterans matched first) while avoiding deadlocks.
- **Files modified:** simulation/history.py
- **Verification:** 161 fighters now reach 15+ fights, max fight count 30, all budgets consumed
- **Committed in:** 1dc4d0e (Task 1 commit)

**2. [Rule 1 - Bug] Event gap tuning needed for sufficient volume**
- **Found during:** Task 1 (parameter tuning)
- **Issue:** Plan specified 14-21 day gaps but this produced only 187 events with 1488 fights (below 200 event threshold). The fight-per-event count dropped due to RNG sequence shift.
- **Fix:** Adjusted gap to 10-18 days, producing 222 events with 2146 fights -- well above all thresholds.
- **Files modified:** simulation/history.py
- **Verification:** 222 events >= 200 threshold, 2146 fights >= 1500 threshold
- **Committed in:** 1dc4d0e (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary to meet HIST-03 requirements. The scan-for-best-opponent pairing is a strictly better algorithm that preserves all plan invariants (budget priority, determinism, rematch cap). No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 02 (Fight History) is fully complete with all HIST requirements met
- Veterans show realistic 15-30 fight records, prospects show 1-5
- All fighter records are backed by real Fight rows with 100% consistency
- History is deterministic and pre-dates 2026
- Ready for Phase 03 (narrative/template expansion) or any downstream phase

## Self-Check: PASSED

- simulation/history.py: FOUND
- test_cli.py: FOUND
- 02-03-SUMMARY.md: FOUND
- Task 1 commit 1dc4d0e: FOUND
- Task 2 commit ad80e40: FOUND

---
*Phase: 02-fight-history*
*Completed: 2026-03-02*
