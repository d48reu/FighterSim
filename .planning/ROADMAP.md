# Roadmap: FighterSim World-Building

## Overview

FighterSim has strong mechanical systems but the world feels empty at game start -- 100 generic fighters with no history, no champions, no rivalries. This milestone transforms the game's opening into a lived-in world: 400-500 authentically-named fighters spanning career stages, years of pre-generated fight history backed by real database rows, composable backstories that reference actual fights, and selectable player origins that shape the starting experience. The pipeline runs at seed time, writes to the existing schema, and the monthly sim takes over unaware anything was pre-generated.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Fighter Generation** - Overhaul seed to produce 400-500 fighters with authentic names, balanced archetypes, and career-stage-appropriate stats
- [x] **Phase 2: Fight History** - Fabricate 2-3 years of pre-game fight history with real database records, champions, and emergent rivalries
- [x] **Phase 3: Fighter Identity** - Generate composable backstories and career highlights from actual fight history data
- [x] **Phase 4: Player Origins** - Selectable starting scenarios with narrative intros and mechanical consequences
- [ ] **Phase 5: Historical Events UI** - Frontend consumer for historical event browsing API (gap closure)
- [ ] **Phase 6: Tech Debt Cleanup** - Address low-severity tech debt from milestone audit (gap closure)
- [ ] **Phase 7: Origin Roster Rebalance** - Adjust origin starting roster sizes (Comeback 20-40, Matchmaker 60-80, Heir 100-120)
- [ ] **Phase 8: UI Polish** - Column sorting, trait/archetype tooltips, fighter portraits
- [ ] **Phase 9: Narrative Depth** - Varied post-fight recaps and pre-fight press conference flavor
- [ ] **Phase 10: Fighter Camp & Scheduling** - Training camp requirement, wear & tear system, event planning delay
- [ ] **Phase 11: Economics Rebalance** - Rework revenue formulas for deeper financial gameplay

## Phase Details

### Phase 1: Fighter Generation
**Goal**: Players encounter a diverse, believable fighter roster where names match nationalities, archetypes are well-distributed, and fighters span realistic career stages
**Depends on**: Nothing (first phase)
**Requirements**: FGEN-01, FGEN-02, FGEN-03, FGEN-04, FGEN-05
**Success Criteria** (what must be TRUE):
  1. Starting a new game produces 400-500 fighters across 5 weight classes (80-100 per class)
  2. Fighter names visibly match their listed nationality (no "John Smith" from Brazil)
  3. Archetype distribution across the full roster shows no single archetype exceeding 25% (no Phenom collapse)
  4. The fighters list contains a visible mix of prospects (low fight count age 20-24), prime fighters (age 25-31), veterans (age 32+), and declining fighters
  5. Fighter stats correlate with their archetype and career stage (prospects have lower stats with higher ceilings, veterans have developed but declining attributes)
**Plans**: 2 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md -- Foundation modules: name generation (Faker locales + romanized lists) and stat generation (numpy distributions)
- [x] 01-02-PLAN.md -- Seed pipeline refactor: quota-first archetypes, career stages, org distribution, nicknames, full validation

### Phase 2: Fight History
**Goal**: The game world has years of pre-existing fight history that players can browse -- champions defended titles, rivalries formed, veterans accumulated records
**Depends on**: Phase 1
**Requirements**: HIST-01, HIST-02, HIST-03, HIST-04, HIST-05, HIST-06
**Success Criteria** (what must be TRUE):
  1. Every fighter's profile shows a fight record with wins/losses backed by actual Fight rows in the database (not just numbers)
  2. Each weight class has a reigning champion with a visible title defense history
  3. Veterans show 15-25 fight records while prospects show 1-3 fights, matching their career stage
  4. At least some fighter pairs are flagged as rivals (from repeated matchups or contentious finishes in fabricated history)
  5. Historical events with full cards and results are browsable in the events view from day one
**Plans**: 2 plans in 2 waves

Plans:
- [x] 02-01-PLAN.md -- Core fabrication module: narrative templates, outcome resolver, event timeline, matchmaker, champion tracking, and fabricate_history() entry point
- [x] 02-02-PLAN.md -- Pipeline integration: wire into seed/run.py/test_cli.py, add all-org event browsing API, end-to-end validation

### Phase 3: Fighter Identity
**Goal**: Fighters feel like individuals with stories -- their bios reference real fights from their history, and notable career moments are highlighted
**Depends on**: Phase 2
**Requirements**: IDEN-01, IDEN-02
**Success Criteria** (what must be TRUE):
  1. Fighter profile bios read as coherent short narratives that reference specific fights, opponents, and outcomes from their actual database history
  2. Fighter profiles display career highlights (notable KOs, upset victories, winning streaks) auto-extracted from their fabricated fight records
  3. Backstory content varies meaningfully between fighters -- different archetypes and career stages produce noticeably different narrative tones
**Plans**: 2 plans in 2 waves

Plans:
- [x] 03-01-PLAN.md -- Core narrative functions: Jinja2 fight-history paragraph generator and career highlight extractor in narrative.py
- [x] 03-02-PLAN.md -- Full-stack integration: wire into services/API, add highlights endpoint, frontend Career Highlights section, test_cli.py validation

### Phase 4: Player Origins
**Goal**: New games begin with a choice that shapes the player's starting situation and tells them why their promotion exists
**Depends on**: Phase 3
**Requirements**: PLYR-01, PLYR-02, PLYR-03, PLYR-04
**Success Criteria** (what must be TRUE):
  1. Starting a new game presents at least 3 selectable origin scenarios before gameplay begins
  2. Each origin displays a narrative intro explaining the promotion's backstory and why it exists
  3. Selecting different origins produces measurably different starting conditions (budget, roster size, reputation differ)
  4. The chosen origin is reflected in the game state -- a "shoestring startup" origin does not start with the same resources as an "established regional promotion"
**Plans**: 2 plans in 2 waves

Plans:
- [x] 04-01-PLAN.md -- Backend foundation: OriginType enum, ORIGIN_CONFIGS, parameterized seed pipeline, async start_new_game service, deferred-seeding run.py
- [x] 04-02-PLAN.md -- Frontend origin page + API routes: route-switching, POST /api/origin, origin.html with cards + name input + text crawl, human verification

### Phase 5: Historical Events UI
**Goal**: Players can browse pre-generated fight history from the UI, not just the API
**Depends on**: Phase 2
**Requirements**: HIST-05 (strengthens existing API-level satisfaction with UI access)
**Gap Closure:** Closes integration gap (GET /api/events/all-history has no frontend consumer) and flow gap (Historical Event Browsing breaks at frontend)
**Success Criteria** (what must be TRUE):
  1. A UI view exists that displays historical events with their fight cards and results
  2. The view is reachable from the main navigation or events section
  3. Historical events load from GET /api/events/all-history and render correctly
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Tech Debt Cleanup
**Goal**: Address low-severity tech debt items identified during milestone audit
**Depends on**: Nothing (independent cleanup)
**Requirements**: None (tech debt, not feature requirements)
**Gap Closure:** Closes tech debt from v1.0 audit
**Success Criteria** (what must be TRUE):
  1. Dead imports removed from simulation/seed.py (fabricate_history line 27, compute_overall line 25)
  2. 02-VERIFICATION.md updated to reflect HIST-03 closure by Plan 02-03
  3. Career stage vocabulary documented or unified between seed.py and narrative.py
  4. ROADMAP.md progress table accurately reflects all phase statuses
  5. test_cli.py Step 5e archetype-record consistency check reviewed and resolved or documented
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

### Phase 7: Origin Roster Rebalance
**Goal**: Origin starting rosters feel appropriately scaled — Comeback is a scrappy underdog, Matchmaker has moderate depth, Heir inherits a stacked roster
**Depends on**: Phase 4
**Requirements**: ORIG-01
**Success Criteria** (what must be TRUE):
  1. Comeback origin seeds 20-40 fighters
  2. Matchmaker origin seeds 60-80 fighters
  3. Heir origin seeds 100-120 fighters
  4. Fighter distribution across weight classes remains balanced within each origin
**Plans**: TBD

Plans:
- [ ] 07-01: TBD

### Phase 8: UI Polish
**Goal**: The game interface feels polished — tables are sortable, unfamiliar terms are explained on hover, and fighters have visual identity
**Depends on**: Nothing (independent)
**Requirements**: UIPOL-01, UIPOL-02, UIPOL-03
**Success Criteria** (what must be TRUE):
  1. All table/column screens support click-to-sort on column headers
  2. Hovering over trait names (e.g., "Iron Chin") and archetype names (e.g., "Phenom", "Pressure Fighter") shows a tooltip explaining what they mean
  3. Fighter cards/profiles display a portrait image
**Plans**: TBD

Plans:
- [ ] 08-01: TBD

### Phase 9: Narrative Depth
**Goal**: Fight narratives feel varied and the pre-fight experience builds anticipation
**Depends on**: Nothing (independent)
**Requirements**: NARR-01, NARR-02
**Success Criteria** (what must be TRUE):
  1. Post-fight recap text uses varied templates — no identical recap appearing more than once per event card
  2. Pre-fight press conferences display narrative flavor text for upcoming matchups
**Plans**: TBD

Plans:
- [ ] 09-01: TBD

### Phase 10: Fighter Camp & Scheduling
**Goal**: Fights require preparation — fighters need training camp time, accumulate wear and tear, and events can't be created and run on the same day
**Depends on**: Nothing (independent)
**Requirements**: SCHED-01, SCHED-02, SCHED-03
**Success Criteria** (what must be TRUE):
  1. Fighters require a minimum training camp period (X weeks) before being eligible for a booked fight
  2. Fighters accumulate fatigue/damage from fights that requires recovery time
  3. Events have a minimum planning delay between creation date and event date
  4. UI reflects fighter availability status (in camp, recovering, available)
**Plans**: TBD

Plans:
- [ ] 10-01: TBD

### Phase 11: Economics Rebalance
**Goal**: The financial model feels deeper and more meaningful — revenue sources are rebalanced and the player understands how money flows
**Depends on**: Nothing (independent)
**Requirements**: ECON-01, ECON-02
**Success Criteria** (what must be TRUE):
  1. PPV, gate, and broadcast revenue formulas are rebalanced for realistic feel
  2. Financial breakdown is visible to the player (how revenue was calculated)
  3. Economic decisions feel consequential — booking choices meaningfully affect the bottom line
**Plans**: TBD

Plans:
- [ ] 11-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Fighter Generation | 2/2 | Complete | 2026-03-02 |
| 2. Fight History | 3/3 | Complete | 2026-03-02 |
| 3. Fighter Identity | 2/2 | Complete | 2026-03-02 |
| 4. Player Origins | 2/2 | Complete | 2026-03-03 |
| 5. Historical Events UI | 0/0 | Not started | - |
| 6. Tech Debt Cleanup | 0/0 | Not started | - |
| 7. Origin Roster Rebalance | 0/0 | Not started | - |
| 8. UI Polish | 0/0 | Not started | - |
| 9. Narrative Depth | 0/0 | Not started | - |
| 10. Fighter Camp & Scheduling | 0/0 | Not started | - |
| 11. Economics Rebalance | 0/0 | Not started | - |
