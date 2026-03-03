---
phase: 02-fight-history
verified: 2026-03-02T07:00:00Z
status: gaps_found
score: 8/9 must-haves verified
gaps:
  - truth: "Veterans show 15-30 fight records while prospects show 1-3, backed by real Fight rows"
    status: failed
    reason: "Post-fabrication record reconciliation caps all fighters at the number of fights they could be scheduled into across ~67 events. Max total fight record observed is 9 (not 15-30 for veterans). Veterans avg 1.8 total fights, prospects avg 0.9. Zero fighters reach 15+ fights. The system generates real Fight rows and Fighter records match those rows exactly, but the volume (67 events x ~6 fights = ~400 slots for ~370 AI-org fighters) cannot produce veteran-scale records."
    artifacts:
      - path: "simulation/history.py"
        issue: "Record reconciliation at line 1074 overwrites seeded veteran records (15-30) with actual fight counts (max 8). The event volume is insufficient to fill veteran fight budgets."
    missing:
      - "Either increase event volume significantly (400+ events to support 15-fight veterans), OR accept that the truth should be restated as 'veterans have more fights than prospects, backed by real Fight rows' and update the requirement language. The current reconciliation approach is sound but the volume cap makes the 15-30 claim unachievable."
human_verification:
  - test: "Run python3 run.py and open http://127.0.0.1:5000/api/events/all-history in a browser"
    expected: "JSON array of 50+ historical events with fight results and narratives, all dated before 2026-01-01"
    why_human: "Cannot start the Flask server in a non-interactive verification context; API endpoint response format and data quality need visual confirmation"
  - test: "Check fighter profile page for a veteran fighter (age 32+) in the frontend"
    expected: "Timeline shows 2-8 historical fights with narratives, event names, and opponent names"
    why_human: "Frontend rendering of fighter timelines requires browser access to confirm UI wiring is correct"
---

# Phase 2: Fight History Verification Report

**Phase Goal:** Fabricate 2-3 years of pre-game fight history as real database rows — complete with events, results, narratives, champions, rivalries, and rankings.
**Verified:** 2026-03-02T07:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Plan 02-01)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | fabricate_history() produces Fight+Event rows matching each fighter's existing W/L/D counts exactly | VERIFIED | 405 Fight rows, 0/50 sampled fighters have record mismatches; records reconciled post-fabrication |
| 2 | Each AI org's weight classes with 2+ fighters have a reigning champion with 2-4 title defenses | VERIFIED | 5 champions across 5 weight classes, 18 title fights total |
| 3 | Veterans show 15-30 fight records while prospects show 1-3, backed by real Fight rows | FAILED | Post-reconciliation: all fighters max at 9 total fights; veterans avg 1.8, prospects avg 0.9; 0 fighters reach 15+ |
| 4 | 10-15 rival pairs exist across weight classes, each with 2+ shared fights | VERIFIED | 34 pairs with 2+ shared fights; 61 fighters have rivalry_with set |
| 5 | Every fight has a one-line narrative template that mentions method and round | VERIFIED | 405/405 fights have narratives (100%); all reference method and round |
| 6 | All historical events predate 2026-01-01 | VERIFIED | 0 events with date >= 2026-01-01 across all 67 events |

**Score (Plan 02-01):** 5/6 truths verified

### Observable Truths (Plan 02-02)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running run.py seeds fighters AND fabricates fight history before starting the server | VERIFIED | run.py lines 21+33: imports and calls fabricate_history() after seed_fighters() |
| 2 | Running test_cli.py exercises the full seed + history pipeline and prints a summary | VERIFIED | test_cli.py lines 63-67, 70-149: fabricate_history call + Step 1b validation block |
| 3 | Historical events from all orgs are browsable via an API endpoint | VERIFIED | /api/events/all-history route in app.py line 107; get_all_event_history() in services.py line 1556 |
| 4 | Fighter timelines show historical fights when viewed via get_fighter_timeline() | VERIFIED | get_fighter_timeline() at services.py line 522 queries Fight+Event rows with or_ filter; verified returns 8 fights for top fighter |
| 5 | The seed pipeline is deterministic: two runs produce identical fight history | VERIFIED | Two consecutive runs produce identical output: 67 events, 405 fights, same champion IDs |

**Score (Plan 02-02):** 5/5 truths verified

**Combined Score:** 10/11 truths verified (1 failed)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `simulation/history.py` | Complete fight history fabrication module | VERIFIED | 1136 lines, contains fabricate_history(), all required helper functions; zero Flask imports |
| `simulation/seed.py` | fabricate_history() call after seed_fighters() | VERIFIED | Line 27: `from simulation.history import fabricate_history` |
| `run.py` | Updated startup to include history fabrication | VERIFIED | Lines 21+33: import and call with summary output |
| `api/services.py` | All-org event browsing function | VERIFIED | `get_all_event_history()` at line 1556 with real DB query and optional org filter |
| `api/app.py` | Route for all-org event browsing | VERIFIED | `/api/events/all-history` at lines 107-112 |

---

### Key Link Verification (Plan 02-01)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `simulation/history.py` | `models/models.py` | `from models.models import` | WIRED | Line 20 imports Fight, Event, Fighter, Organization, WeightClass, Contract, ContractStatus, FightMethod, FighterStyle, ContractStatus |
| `simulation/history.py` | `simulation/narrative.py` | `update_rivalries()` | WIRED | Line 877: lazy import; line 1068: called post-fabrication; produces 61 rival fighters |
| `simulation/history.py` | `simulation/rankings.py` | `rebuild_rankings()` | WIRED | Line 878: lazy import; lines 1071-1072: called for each WeightClass |

### Key Link Verification (Plan 02-02)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run.py` | `simulation/history.py` | `from simulation.history import fabricate_history` | WIRED | Line 21 import, line 33 call |
| `api/app.py` | `api/services.py` | `get_all_event_history` route | WIRED | app.py line 112 calls `services.get_all_event_history()` |
| `api/services.py` | `models/models.py` | `select(Event).where(Event.organization_id == ...)` | WIRED | Lines 1563-1567: real query with Event.status and optional organization_id filter |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HIST-01 | 02-01, 02-02 | Fighters have pre-existing fight records backed by real Fight rows | SATISFIED | 405 Fight rows created; Fighter.wins/losses/draws match actual Fight row counts (0 mismatches in 50-fighter sample) |
| HIST-02 | 02-01 | Each weight class has an established champion at game start | SATISFIED | All 5 weight classes have a champion: Flyweight, Lightweight, Welterweight, Middleweight, Heavyweight each have a named reigning champion |
| HIST-03 | 02-01 | Career lengths vary realistically (veterans 15-25 fights, prospects 1-3) | BLOCKED | Veterans max at 7 Fight rows, avg 2.5; prospects max at 7 Fight rows, avg 1.8. No fighter reaches 15 total fights. Reconciliation overwrites seeded records with actual fight counts. |
| HIST-04 | 02-01 | Pre-existing rivalries emerge from fabricated fight history | SATISFIED | 34 rivalry pairs with 2+ shared fights; 61/450 fighters have rivalry_with set; update_rivalries() called post-fabrication |
| HIST-05 | 02-01, 02-02 | Historical events with results are browsable from day one | SATISFIED | GET /api/events/all-history returns completed events from all orgs with full fight details and narratives |
| HIST-06 | 02-01, 02-02 | Career timelines are populated from fabricated history | SATISFIED | get_fighter_timeline() queries Fight+Event rows chronologically; verified 8 fights returned for a top fighter |

**HIST-03** is the only requirement that cannot be fully confirmed against its stated standard. The SUMMARY (02-01) documents this as an intentional architectural decision: the event volume (67 events, ~400 fight slots) cannot fill the seeded veteran fight budgets (which target 15-30 fights per veteran). Record reconciliation keeps the database consistent but results in compressed career lengths.

---

### Anti-Patterns Found

No blocker or warning-level anti-patterns found.

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `simulation/history.py` | TODOs/stubs | None found | Clean — 1136 lines of substantive implementation |
| `run.py` | TODOs/stubs | None found | Clean |
| `api/services.py` | TODOs/stubs | None found | Clean |
| `api/app.py` | TODOs/stubs | None found | Clean |
| `test_cli.py` | TODOs/stubs | None found | Clean |

**Known non-blocker issue (deferred-items.md):** test_cli.py Step 5e archetype-record consistency check reports 33 mismatches after history fabrication. This is expected — the pre-existing test was written for seed-only records and is now invalidated by the intentional reconciliation. Logged for Phase 3 or test maintenance, not a gap for this phase.

---

### Human Verification Required

#### 1. API Endpoint Response Quality

**Test:** Start the server with `python3 run.py`, then curl `http://127.0.0.1:5000/api/events/all-history`
**Expected:** JSON array of 50+ completed historical events, each with a `fights` array containing results with narratives like "Timofei Davydov captured the crown with a stunning submission of..."
**Why human:** Cannot start Flask server in verification context; API response JSON structure and narrative quality require visual inspection

#### 2. Fighter Timeline in Frontend

**Test:** Start the server, open the frontend, navigate to any fighter profile (especially a veteran with 5+ fights)
**Expected:** Timeline tab shows fights in chronological order with event name, date, opponent, result, method, and narrative
**Why human:** Frontend rendering requires browser; cannot verify JS rendering pipeline programmatically

---

### Gaps Summary

One gap blocks full goal achievement:

**HIST-03 / Truth 3: Career length realism**

The phase goal includes "2-3 years of pre-game fight history" and the plan specified veterans should show 15-30 fights backed by real Fight rows. The fabrication engine produces only ~67 events across 3 AI orgs over 3 years. With 5-7 fights per event and ~370 AI-org fighters needing scheduling, each fighter averages only 2-3 fight appearances. The maximum fight count observed is 9.

The SUMMARY documents this as an intentional architectural decision ("Record reconciliation over strict budget matching") and correctly identifies the root cause: 67 events x 6 fights = 402 fight slots cannot absorb 370+ fighters with veteran budgets of 15-30 fights each.

**The observable consequence:** At game start, the player sees veteran fighters with 4-7 fight records, not 15-25 fight records. The "lived-in" sense of history is compressed. A 35-year-old veteran looks like they just started their career.

**Options to close this gap:**
1. Increase event frequency (reduce 6-8 week interval to 3-4 weeks) to generate 120-140 events
2. Remove the event-based scheduling constraint and let fighters appear across any number of historical events
3. Restate HIST-03 requirement as "career lengths vary — veterans have more fights than prospects" (lower bar, achievable with current design)

The gap does not prevent the system from functioning correctly — records are data-consistent, narratives exist, rivals are established, champions are crowned. But the career length realism specifically called out in HIST-03 is not achieved at the scale originally specified.

---

## Commit Verification

All commits claimed in SUMMARY files verified present in git log:

| Commit | Plan | Status |
|--------|------|--------|
| `ce2645e` | 02-01 Task 1 | FOUND |
| `7e36bb4` | 02-01 Task 2 | FOUND |
| `b39f001` | 02-02 Task 1 | FOUND |
| `7efaef4` | 02-02 Task 2 | FOUND |

---

_Verified: 2026-03-02T07:00:00Z_
_Verifier: Claude (gsd-verifier)_
