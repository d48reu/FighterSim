# Requirements: FighterSim World-Building

**Defined:** 2026-03-01
**Core Value:** The world feels alive and inhabited — fighters are people with backstories, personalities, and reputations, not procedurally generated stat blocks.

## v1 Requirements

Requirements for the world-building milestone. Each maps to roadmap phases.

### Fighter Generation

- [x] **FGEN-01**: Fighter names match their nationality using locale-appropriate generation (Faker)
- [x] **FGEN-02**: Fighter pool scales to 400-500 fighters across 5 weight classes (80-100 per class)
- [x] **FGEN-03**: Archetype distribution uses quota system instead of waterfall scoring (no more 69% Phenom collapse)
- [x] **FGEN-04**: Fighters span realistic career stages at game start (prospects, prime, veterans, declining)
- [x] **FGEN-05**: Fighter stats correlate with archetype and career stage (numpy distributions, not uniform random)

### Pre-Generated History

- [x] **HIST-01**: Fighters have pre-existing fight records backed by real Fight rows in the database
- [x] **HIST-02**: Each weight class has an established champion at game start
- [x] **HIST-03**: Career lengths vary realistically (veterans 15-25 fights, prospects 1-3)
- [x] **HIST-04**: Pre-existing rivalries emerge from fabricated fight history
- [x] **HIST-05**: Historical events with results are browsable from day one
- [x] **HIST-06**: Career timelines are populated from fabricated history

### Fighter Identity

- [x] **IDEN-01**: Fighters have composable backstories built from Jinja2 templates that reference actual fight history
- [x] **IDEN-02**: Career highlights are auto-extracted from fabricated fight history (notable KOs, upsets, streaks)

### Player Experience

- [x] **PLYR-01**: Player selects from multiple background origins at game start
- [x] **PLYR-02**: Each origin provides a narrative intro explaining why the promotion exists
- [x] **PLYR-03**: Origins have mechanical consequences (different starting budget, roster size, reputation)
- [x] **PLYR-04**: At least 3 distinct starting scenarios with meaningfully different gameplay

### Origin Tuning

- [ ] **ORIG-01**: Origin roster sizes rebalanced — Comeback 20-40, Matchmaker 60-80, Heir 100-120 fighters

### UI Polish

- [ ] **UIPOL-01**: Column sorting on all table screens (fighters, events, rankings, etc.)
- [ ] **UIPOL-02**: Hover tooltips on traits and archetypes explaining what they mean
- [ ] **UIPOL-03**: Fighter portraits displayed on fighter cards and profiles

### Narrative

- [ ] **NARR-01**: Varied post-fight recap templates — no repeated text within the same event
- [ ] **NARR-02**: Pre-fight press conference narrative flavor text

### Fighter Scheduling

- [ ] **SCHED-01**: Training camp requirement — fighters need X weeks before a booked fight
- [ ] **SCHED-02**: Wear & tear / fatigue accumulation and recovery system
- [ ] **SCHED-03**: Minimum time delay between booking an event and event day

### Economics

- [ ] **ECON-01**: Rebalanced PPV, gate, and broadcast revenue formulas
- [ ] **ECON-02**: Financial model transparency — player can see how revenue is calculated

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Fighter Identity (Extended)

- **IDEN-03**: Behavioral personality traits (3-5 types) affecting mechanics (contracts, morale, media)
- **IDEN-04**: Personality types visible on fighter cards (trash talker, humble warrior, head case)

### Fighter Generation (Extended)

- **FGEN-06**: Training lineage / gym origins (10-15 fictional gyms assigned at seed time)
- **FGEN-07**: Regional attribute biasing (Brazilian fighters trend toward grappling, etc.)

### Visualization

- **VIZ-01**: Tug-of-war momentum bars during fight playback
- **VIZ-02**: Round-by-round tabbed fight breakdowns
- **VIZ-03**: Animation speed modes (Cinematic / Normal / Quick)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dual rankings (promotion + cross-promotion) | Separate milestone — depends on world-building foundation |
| Championship belts as first-class objects | Separate milestone — belt lineage requires populated history first |
| Player goals (Dynasty Score, GOAT Quest, Tier Ladder) | Separate milestone — goals need rich world to measure against |
| Fighter portraits / pixel art | Deferred — visual layer, not world-building |
| Sound design | Deferred — future milestone |
| Save/load system | Deferred — future milestone |
| Tutorial | Deferred — future milestone |
| Steam packaging | Deferred — future milestone |
| LLM-generated content | Violates self-contained constraint (no external API keys) |
| Full fight engine replay for history | Too slow (~100x slower than fabrication for identical observable data) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FGEN-01 | Phase 1: Fighter Generation | Complete |
| FGEN-02 | Phase 1: Fighter Generation | Complete |
| FGEN-03 | Phase 1: Fighter Generation | Complete |
| FGEN-04 | Phase 1: Fighter Generation | Complete |
| FGEN-05 | Phase 1: Fighter Generation | Complete |
| HIST-01 | Phase 2: Fight History | Complete |
| HIST-02 | Phase 2: Fight History | Complete |
| HIST-03 | Phase 2: Fight History | Complete |
| HIST-04 | Phase 2: Fight History | Complete |
| HIST-05 | Phase 2: Fight History + Phase 5: Historical Events UI | Complete |
| HIST-06 | Phase 2: Fight History | Complete |
| IDEN-01 | Phase 3: Fighter Identity | Complete |
| IDEN-02 | Phase 3: Fighter Identity | Complete |
| PLYR-01 | Phase 4: Player Origins | Complete |
| PLYR-02 | Phase 4: Player Origins | Complete |
| PLYR-03 | Phase 4: Player Origins | Complete |
| PLYR-04 | Phase 4: Player Origins | Complete |

| ORIG-01 | Phase 7: Origin Roster Rebalance | Pending |
| UIPOL-01 | Phase 8: UI Polish | Pending |
| UIPOL-02 | Phase 8: UI Polish | Pending |
| UIPOL-03 | Phase 8: UI Polish | Pending |
| NARR-01 | Phase 9: Narrative Depth | Pending |
| NARR-02 | Phase 9: Narrative Depth | Pending |
| SCHED-01 | Phase 10: Fighter Camp & Scheduling | Pending |
| SCHED-02 | Phase 10: Fighter Camp & Scheduling | Pending |
| SCHED-03 | Phase 10: Fighter Camp & Scheduling | Pending |
| ECON-01 | Phase 11: Economics Rebalance | Pending |
| ECON-02 | Phase 11: Economics Rebalance | Pending |

**Coverage:**
- v1 requirements: 17 total — 17/17 satisfied
- v1.1 requirements: 11 total — 0/11 satisfied
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-03 after gap closure phase creation*
