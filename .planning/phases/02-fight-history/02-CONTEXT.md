# Phase 2: Fight History - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Fabricate 2-3 years of pre-game fight history with real database records (Fight + Event rows), establish champions with title defense lineage, and seed rivalries from repeated matchups. The seed pipeline produces all history at game start; the monthly sim takes over unaware anything was pre-generated.

</domain>

<decisions>
## Implementation Decisions

### Fight narrative depth
- One-line template-based summaries per fight (not multi-sentence, not bare results)
- Method-specific template pools keyed to FightMethod enum (KO/TKO, Submission, Unanimous Decision, Split Decision, Majority Decision)
- Style-aware templates: fighter's FighterStyle (Striker/Grappler/Wrestler/Well-Rounded) influences template selection (e.g. a grappler's KO win reads as "shocking knockout" vs a striker's "trademark power")
- Round mentioned in narrative but not exact time ("finished in the second round" not "won at 2:47 of round 2")
- Title fights get elevated language templates ("captured the crown", "defended the belt for the third time")
- Upset victories flagged in narrative when lower-rated fighter wins (ties into existing giant_killer tag)
- Decision wins get narrative templates too, not just finishes ("outpointed across three rounds", "survived a late scare to win a split decision")
- Early-career fights (prospect's first 1-3 fights) get simpler/shorter narratives ("earned a debut victory") — mirrors how real MMA coverage scales with fight significance

### Champion coronation
- Organic from fabricated history: first champion crowned early in history, title fights happen periodically, current champion is whoever holds the belt at history's end
- Reigning champions should have 2-4 title defenses at game start
- Title changes allowed during history period — some weight classes had 2-3 champions over the history window
- Top 3 AI orgs (UCC, Bellator, One) have formal champions per weight class; player org starts without champions (player earns the right)

### Historical event density
- Each org holds events every 6-8 weeks (~2 events/month total across 4 orgs)
- 5-7 fights per event card (standard MMA card size: main event + co-main + undercard)
- Event naming: sequential numbering only ("UCC 45", "Bellator 78", "One Championship 33") — no thematic names
- Fight results only — no fabricated financial data (gate revenue, PPV buys). Financials start when gameplay begins.

### Rivalry engineering
- Matchmaker intentionally seeds 2-3 rival pairs per weight class (10-15 total rivalries)
- Rematches deliberately booked to trigger update_rivalries() detection (2+ fights between same pair)
- Rivalry fights get special narrative templates referencing previous matchup ("avenged a controversial loss", "settled the score")
- At least one rivalry per weight class involves the champion or former champion (marquee feud at top of division)

### Claude's Discretion
- Exact number of historical events (tuned for performance and fighter record targets)
- Matchmaking algorithm (how fighters are paired within weight classes beyond rivalry seeding)
- Venue names for historical events
- Which specific fighters become champions (determined organically by fabrication logic)
- Template pool size and exact wording
- How title vacancies are handled if a champion "retires" during history

</decisions>

<specifics>
## Specific Ideas

- History should feel like browsing a real MMA promotion's event archive — numbered events, clear results, recognizable patterns
- The timeline API (`get_fighter_timeline()`) already displays Fight+Event rows, so once data exists the display works immediately
- Seed pipeline currently generates W/L/D numbers but no Fight rows — Phase 2 replaces those bare numbers with actual database records that back them up
- Narrative quality scales with fight significance: prospect debut < regular bout < rivalry rematch < title fight

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Fight` model: has all needed fields (fighter_a/b, winner_id, method, round_ended, time_ended, narrative, is_title_fight, card_position, event_id)
- `Event` model: has name, event_date, venue, organization_id, status fields
- `FightMethod` enum: KO_TKO, Submission, Unanimous_Decision, Split_Decision, Majority_Decision — key off these for narrative templates
- `FighterStyle` enum: Striker, Grappler, Wrestler, Well_Rounded — key off these for style-aware narrative templates
- `_gen_record()` in seed.py: career-stage-aware W/L/D generation — history fabrication must produce records matching these ranges
- `update_rivalries()` in narrative.py: sets rivalry_with for pairs with 2+ fights — just needs matchup data to work
- `get_fighter_timeline()` in services.py: reads Fight+Event rows chronologically — no changes needed once data exists
- `rebuild_rankings()` in rankings.py: can be called after history generation to compute initial rankings

### Established Patterns
- Seed pipeline uses deterministic RNG (seed=42) with dual py_rng (stdlib) + np_rng (numpy)
- Fight engine uses FighterStats DTOs decoupled from ORM — history fabrication should NOT use fight engine (too slow, per REQUIREMENTS out-of-scope)
- Events ordered by event_date, fights ordered by card_position within events
- Career stages: prospect (1-5 fights), prime (8-20), veteran (15-30), transitional (10-22)

### Integration Points
- `seed_fighters()` generates fighters first; history generation runs AFTER and creates Fight+Event rows
- Fighter.wins/losses/draws/ko_wins/sub_wins must match actual Fight row counts after fabrication
- Fighter.rivalry_with set by calling update_rivalries() after all history is fabricated
- Rankings rebuilt via rebuild_rankings() per weight class after history
- GameState.current_date = date(2026, 1, 1) — all history events predate this
- 4 orgs exist at seed time: UCC (prestige 90), One (75), Bellator (70), Player (50)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-fight-history*
*Context gathered: 2026-03-02*
