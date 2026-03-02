# Roadmap: FighterSim World-Building

## Overview

FighterSim has strong mechanical systems but the world feels empty at game start -- 100 generic fighters with no history, no champions, no rivalries. This milestone transforms the game's opening into a lived-in world: 400-500 authentically-named fighters spanning career stages, years of pre-generated fight history backed by real database rows, composable backstories that reference actual fights, and selectable player origins that shape the starting experience. The pipeline runs at seed time, writes to the existing schema, and the monthly sim takes over unaware anything was pre-generated.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Fighter Generation** - Overhaul seed to produce 400-500 fighters with authentic names, balanced archetypes, and career-stage-appropriate stats
- [ ] **Phase 2: Fight History** - Fabricate 2-3 years of pre-game fight history with real database records, champions, and emergent rivalries
- [ ] **Phase 3: Fighter Identity** - Generate composable backstories and career highlights from actual fight history data
- [ ] **Phase 4: Player Origins** - Selectable starting scenarios with narrative intros and mechanical consequences

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
- [ ] 01-01-PLAN.md -- Foundation modules: name generation (Faker locales + romanized lists) and stat generation (numpy distributions)
- [ ] 01-02-PLAN.md -- Seed pipeline refactor: quota-first archetypes, career stages, org distribution, nicknames, full validation

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
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Fighter Identity
**Goal**: Fighters feel like individuals with stories -- their bios reference real fights from their history, and notable career moments are highlighted
**Depends on**: Phase 2
**Requirements**: IDEN-01, IDEN-02
**Success Criteria** (what must be TRUE):
  1. Fighter profile bios read as coherent short narratives that reference specific fights, opponents, and outcomes from their actual database history
  2. Fighter profiles display career highlights (notable KOs, upset victories, winning streaks) auto-extracted from their fabricated fight records
  3. Backstory content varies meaningfully between fighters -- different archetypes and career stages produce noticeably different narrative tones
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: Player Origins
**Goal**: New games begin with a choice that shapes the player's starting situation and tells them why their promotion exists
**Depends on**: Phase 3
**Requirements**: PLYR-01, PLYR-02, PLYR-03, PLYR-04
**Success Criteria** (what must be TRUE):
  1. Starting a new game presents at least 3 selectable origin scenarios before gameplay begins
  2. Each origin displays a narrative intro explaining the promotion's backstory and why it exists
  3. Selecting different origins produces measurably different starting conditions (budget, roster size, reputation differ)
  4. The chosen origin is reflected in the game state -- a "shoestring startup" origin does not start with the same resources as an "established regional promotion"
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Fighter Generation | 1/2 | In Progress | - |
| 2. Fight History | 0/0 | Not started | - |
| 3. Fighter Identity | 0/0 | Not started | - |
| 4. Player Origins | 0/0 | Not started | - |
