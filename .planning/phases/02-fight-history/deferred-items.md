# Deferred Items - Phase 02: Fight History

## Pre-existing: Archetype-record consistency after record reconciliation

**Discovered during:** Plan 02-02, Task 2 (end-to-end validation)
**Scope:** Out-of-scope (pre-existing test checking seed-only invariants, now invalidated by intentional record reconciliation)

**Description:** Step 5e in test_cli.py checks that GOAT_CANDIDATE fighters have 70%+ win rate and SHOOTING_STAR fighters have 60%+ win rate. After `fabricate_history()` reconciles Fighter W/L/D against actual Fight rows, many fighters with few fight slots end up with records that violate these archetype thresholds. This is expected behavior -- the reconciliation (from Plan 02-01) intentionally replaces seed-generated records with actual fight outcomes.

**Recommendation:** Update Step 5e to either (a) skip archetype-record checks after history fabrication, (b) only check fighters with 5+ total fights (small sample sizes produce volatile win rates), or (c) have `fabricate_history()` favor archetype-appropriate outcomes in the matchmaker.
