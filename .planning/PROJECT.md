# FighterSim

## What This Is

A desktop MMA promotion management simulator where the player builds an upstart organization within a living, breathing combat sports world. Think WMMA-level depth — fighters with real histories, a sport that existed before you showed up, and the scrappy underdog energy of proving your promotion belongs. Python/Flask/SQLite backend, vanilla JS frontend.

## Core Value

The world feels alive and inhabited. Fighters are people with backstories, personalities, and reputations — not procedurally generated stat blocks. The sport has history. The player is building something real within an existing ecosystem.

## Requirements

### Validated

- ✓ Tick-based fight engine (30s ticks, zones, momentum, knockdowns, traits, style matchups, judge bias) — existing
- ✓ Monthly simulation (aging, injuries, contracts, AI org booking, free agency) — existing
- ✓ Event system (booking, async sim, fight reveal animation, title fights) — existing
- ✓ Contract and roster management (offers, acceptance probability, free agents) — existing
- ✓ Fighter development (15 camps, 3 tiers, prestige-gated) — existing
- ✓ Rankings (dirty flag caching, quality-of-opposition, top 15 per class) — existing
- ✓ TV/broadcast deals (prestige-gated tiers) — existing
- ✓ Venue management (prestige-gated, sellout/turnout mechanics) — existing
- ✓ Rival promotion AI (compete for free agents, poach fighters) — existing
- ✓ Sponsorship system (hype/popularity-based) — existing
- ✓ Reality TV tournament system (brackets, episodes, shenanigans) — existing
- ✓ Narrative system (bios, archetypes, nationalities, nicknames, press conferences) — existing
- ✓ Cornerstone fighters, weight cutting, judging variance — existing
- ✓ Fighter psychology/confidence (hidden 0-100, post-fight shifts) — existing
- ✓ Hall of Fame / GOAT leaderboard with rivalry detection — existing
- ✓ Notification system with unread count — existing
- ✓ Dashboard, fighters table, rankings view, roster, free agents, events, development, HoF — existing

### Active

- [ ] Lived-in world at game start — pre-existing records, champions, rivalries, veterans, prospects
- [ ] Player origin stories — selectable backgrounds with different starting conditions
- [ ] Fighter identity depth — backstories, behavioral personalities, distinguishing traits
- [ ] Fighter pool scaling — expand from 100 to 400-500 fighters with realistic distribution
- [ ] Starting roster depth — new game begins with enough fighters per weight class to feel populated

### Out of Scope

- Fight visualization system — deferred until world-building foundation is solid
- Dual rankings (promotion-specific + cross-promotion) — queued after world-building
- Championship belts as first-class objects (lineage, interim, vacating) — queued after world-building
- Player goals (Dynasty Legacy Score, GOAT Quest, Promotion Tier Ladder) — queued after world-building
- Fighter portraits / pixel art pipeline — deferred
- Sound design — deferred
- Save/load system — deferred
- Tutorial — deferred
- Steam packaging — deferred

## Context

- Feature-rich prototype with 11K lines of production code, 67 API endpoints, 92 simulation functions
- 25 SQLAlchemy models, SQLite database
- Fight engine in simulation/ is fully decoupled from Flask (no dependencies) for future desktop packaging
- All business logic centralized in api/services.py (~3700 lines)
- Current seed: 100 fighters (deterministic seed=42) + 4 orgs across 5 weight classes (~20/class)
- WMMA (World of Mixed Martial Arts) is the quality reference for world-building depth
- The game's mechanical systems are solid — what's missing is soul and narrative immersion
- The beginning of the game doesn't hook the player; fighters blend together, there's no narrative setup

## Constraints

- **Tech stack**: Python 3/Flask/SQLAlchemy/SQLite backend, vanilla JS frontend — no framework changes
- **Decoupling**: simulation/ must have ZERO Flask dependencies
- **Architecture**: All business logic in api/services.py, routes are thin controllers only
- **Time**: Always use game_state.current_date, never date.today()
- **Async**: Simulation endpoints must return task_id, poll via /api/tasks/<id>
- **Rankings**: Only rebuild on dirty flag, never on every request
- **Testing**: Fight engine changes must be validated against method distribution targets (Sub ~23%, KO ~32%, Dec ~45%)
- **Database**: sqlite:///mma_game.db (run.py) or sqlite:///mma_test.db (test_cli.py)
- **Reseeding**: After any model changes, reseed via python run.py

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| World-building before visualization | A lived-in world informs everything else — fight viz, belts, rankings, goals all benefit from a richer foundation | — Pending |
| Player chooses background/scenario | Different starting conditions create replay value and narrative investment | — Pending |
| Scale fighter pool 4-5x | 20 fighters per weight class isn't enough to feel like a real sport | — Pending |
| WMMA as quality reference | Best-in-class for the "living world" feel this game needs | — Pending |

---
*Last updated: 2026-03-01 after initialization*
