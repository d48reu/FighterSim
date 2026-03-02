# Research Summary: FighterSim World-Building Milestone

**Domain:** Procedural world generation / character identity systems for MMA management simulation
**Researched:** 2026-03-01
**Overall confidence:** HIGH

## Executive Summary

FighterSim has solid mechanical systems (fight engine, monthly sim, rankings, contracts, events) but the world feels empty at game start -- 100 generic fighters with no queryable fight history, no champions, no rivalries, and names that don't match nationalities. The world-building milestone transforms this into a lived-in world with 400-500 fighters, pre-generated fight histories backed by real database records, nationality-authentic names, composable backstories, fighter personality types, and selectable player origin stories.

The stack recommendation is intentionally minimal: **one new pip dependency (Faker >=40.0)** plus leveraging two libraries already installed (Jinja2 as Flask dependency, numpy). Everything else uses Python stdlib and the existing fight engine. This restraint is deliberate -- the project's self-contained constraint (no external API keys) and the simulation/ decoupling constraint (no Flask dependencies) eliminate most external options. The remaining choices (Faker over hardcoded name lists, Jinja2 over Markov chains, numpy distributions over uniform random) are each well-supported by evidence.

The architecture is a seed-time generation pipeline: generate fighters, simulate history, post-process for champions/rivalries, generate backstories, apply player origin. This pipeline runs once at new-game creation and writes to the existing database schema (with minor model extensions). The existing monthly_sim.py takes over from there, unaware the world was pre-generated. This pattern is validated by WMMA5 (the genre reference) and Dwarf Fortress-style world generation.

The critical pitfalls are all about coherence at scale. At 100 fighters, inconsistencies are ignorable. At 500, they break immersion: archetype distribution collapses to 69% Phenom, records don't match stats, names don't match nationalities, backstories contradict traits. Every pitfall has a concrete prevention strategy documented with validation queries.

## Key Findings

**Stack:** One new dependency (Faker >=40.0 for nationality-authentic names), plus Jinja2 (already installed) for composable backstory templates and numpy (already installed) for archetype-aware stat distributions. No LLMs, no Markov chains, no heavy frameworks.

**Architecture:** Seed-time generation pipeline in a new `simulation/worldgen/` directory with 6-8 modules. Each pipeline phase writes to the database and passes summary data downstream. History is fabricated via lightweight result generation (not full fight engine), keeping seed time under 10 seconds.

**Critical pitfall:** Archetype distribution collapse at scale -- the current `_assign_archetype()` produces 69% Phenom at 500 fighters. Must be redesigned as a scoring/quota system before any pool expansion.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Foundation: Fighter Generation Overhaul** - Fix archetype distribution, integrate Faker for names, add numpy stat distributions, expand to 400-500 fighters
   - Addresses: Nationality-authentic names, enough fighters per weight class, career stage diversity, archetype-aware stats
   - Avoids: Archetype collapse (Pitfall 1), name-nationality incoherence (Pitfall 5), nationality distribution unrealism (Pitfall 4)

2. **History: Pre-Generated Fight Records** - Build the history fabrication pipeline that creates Events and Fights for 2-3 years of pre-game history
   - Addresses: Pre-existing fight records with real opponents, champion history, rivalry emergence, veteran/legend fighters
   - Avoids: Empty Fight table (Pitfall 3), record-stats incoherence (Pitfall 2)

3. **Identity: Fighter Backstories and Personality** - Jinja2 composable template system for backstories, personality type assignment, career highlights
   - Addresses: Fighter backstories/bios, fighter personality system, prospect scouting context
   - Avoids: Wall of text fatigue (Pitfall 7), backstory-trait contradictions (Pitfall 12)

4. **Player Experience: Origin Stories** - Selectable starting scenarios with mechanical consequences
   - Addresses: Player origin stories
   - Avoids: Cosmetic-only origins (Pitfall 8)

**Phase ordering rationale:**
- Foundation first because every subsequent phase depends on having a well-distributed fighter pool with authentic names and coherent stats.
- History second because backstories reference fight history (you can't narrate "a devastating knockout in their third fight" without that fight existing).
- Identity third because it consumes both fighter data and history data to produce coherent narratives.
- Player experience last because origin stories place the player into the already-built world.

**Research flags for phases:**
- Phase 2 (History): Key architectural decision needed -- the ARCHITECTURE.md recommends lightweight fight fabrication while STACK.md proposes reusing the full fight engine. Fabrication is ~100x faster and sufficient (players never replay pre-game fights tick-by-tick). Recommend fabrication with method distributions matching the fight engine's targets (Sub ~23%, KO ~32%, Dec ~45%). This should be validated against actual fight engine output during implementation.
- Phase 3 (Identity): Template authoring is a content task, not a code task. Budget time for writing 50-100 template fragments, not just the Jinja2 integration code.
- Phase 1 (Foundation): Needs performance validation at 500 fighters for the monthly_sim -- current ~120-170ms timing was never tested at 5x scale.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Faker confirmed on PyPI (v40.5.1), all locales verified. Jinja2 and numpy confirmed installed locally. Alternatives researched and rejected with evidence. |
| Features | HIGH | Feature list directly from PROJECT.md active requirements, cross-referenced with WMMA5 as genre reference. |
| Architecture | HIGH | Pipeline pattern validated by codebase analysis and genre references. Component boundaries follow existing simulation/ patterns. One open decision (fabrication vs full engine for history). |
| Pitfalls | HIGH | All critical pitfalls verified by code inspection or simulation. Prevention strategies are concrete and testable. |

## Gaps to Address

- **History fabrication vs full fight engine:** The two research files disagree on this. Resolution: use fabrication (ARCHITECTURE.md recommendation) because the full engine produces tick-level data nobody reads for pre-game fights. Validate method distributions match during implementation.
- **Monthly sim performance at 500 fighters:** Flagged as Pitfall 6 but not benchmarked. Profile early, optimize only if measured performance exceeds 500ms.
- **Fighter replenishment system:** The monthly_sim needs to generate new prospects to replace retired fighters. This is a known gap not yet designed -- will need phase-specific research.
- **Faker locale gaps:** No dedicated locales for Dagestani, Cameroonian, or Jamaican fighters. Proxy locales identified (Russian, French, American) with curated name overrides for Dagestani specifically. Needs validation during implementation.
- **Template content volume:** The modular backstory system needs 50-100 template fragments. This is a writing/content task that may require its own time budget beyond code implementation.

---
*Research summary for: FighterSim world-building milestone*
*Researched: 2026-03-01*
