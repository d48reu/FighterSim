# Requirements: FighterSim World-Building

**Defined:** 2026-03-01
**Core Value:** The world feels alive and inhabited — fighters are people with backstories, personalities, and reputations, not procedurally generated stat blocks.

## v1 Requirements

Requirements for the world-building milestone. Each maps to roadmap phases.

### Fighter Generation

- [ ] **FGEN-01**: Fighter names match their nationality using locale-appropriate generation (Faker)
- [ ] **FGEN-02**: Fighter pool scales to 400-500 fighters across 5 weight classes (80-100 per class)
- [ ] **FGEN-03**: Archetype distribution uses quota system instead of waterfall scoring (no more 69% Phenom collapse)
- [ ] **FGEN-04**: Fighters span realistic career stages at game start (prospects, prime, veterans, declining)
- [ ] **FGEN-05**: Fighter stats correlate with archetype and career stage (numpy distributions, not uniform random)

### Pre-Generated History

- [ ] **HIST-01**: Fighters have pre-existing fight records backed by real Fight rows in the database
- [ ] **HIST-02**: Each weight class has an established champion at game start
- [ ] **HIST-03**: Career lengths vary realistically (veterans 15-25 fights, prospects 1-3)
- [ ] **HIST-04**: Pre-existing rivalries emerge from fabricated fight history
- [ ] **HIST-05**: Historical events with results are browsable from day one
- [ ] **HIST-06**: Career timelines are populated from fabricated history

### Fighter Identity

- [ ] **IDEN-01**: Fighters have composable backstories built from Jinja2 templates that reference actual fight history
- [ ] **IDEN-02**: Career highlights are auto-extracted from fabricated fight history (notable KOs, upsets, streaks)

### Player Experience

- [ ] **PLYR-01**: Player selects from multiple background origins at game start
- [ ] **PLYR-02**: Each origin provides a narrative intro explaining why the promotion exists
- [ ] **PLYR-03**: Origins have mechanical consequences (different starting budget, roster size, reputation)
- [ ] **PLYR-04**: At least 3 distinct starting scenarios with meaningfully different gameplay

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
| FGEN-01 | Phase 1: Fighter Generation | Pending |
| FGEN-02 | Phase 1: Fighter Generation | Pending |
| FGEN-03 | Phase 1: Fighter Generation | Pending |
| FGEN-04 | Phase 1: Fighter Generation | Pending |
| FGEN-05 | Phase 1: Fighter Generation | Pending |
| HIST-01 | Phase 2: Fight History | Pending |
| HIST-02 | Phase 2: Fight History | Pending |
| HIST-03 | Phase 2: Fight History | Pending |
| HIST-04 | Phase 2: Fight History | Pending |
| HIST-05 | Phase 2: Fight History | Pending |
| HIST-06 | Phase 2: Fight History | Pending |
| IDEN-01 | Phase 3: Fighter Identity | Pending |
| IDEN-02 | Phase 3: Fighter Identity | Pending |
| PLYR-01 | Phase 4: Player Origins | Pending |
| PLYR-02 | Phase 4: Player Origins | Pending |
| PLYR-03 | Phase 4: Player Origins | Pending |
| PLYR-04 | Phase 4: Player Origins | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 after roadmap creation*
