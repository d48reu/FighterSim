# Phase 2: Fight History - Research

**Researched:** 2026-03-02
**Domain:** Historical fight data fabrication, deterministic seed pipelines, SQLAlchemy bulk inserts
**Confidence:** HIGH

## Summary

Phase 2 fabricates 2-3 years of pre-game fight history as real database rows (Fight + Event). The entire domain is internal to the existing codebase -- no new libraries, no external APIs, no new models. The challenge is algorithmic: generating ~60-70 events with ~350-400 fights across 3 AI orgs, placing them on a realistic timeline, organically crowning champions through title fight scheduling, seeding rivalries via deliberate rematches, and producing method-specific one-line narratives that scale in quality with fight significance.

The existing codebase provides all necessary building blocks: the Fight/Event ORM models have every field needed, `_gen_record()` already produces career-stage-aware W/L/D targets that the fabrication must match exactly, `update_rivalries()` auto-detects pairs with 2+ fights, `rebuild_rankings()` computes initial rankings, and `get_fighter_timeline()` reads Fight+Event rows chronologically with zero changes needed. The work is a new `fabricate_history()` function in `simulation/seed.py` (or a new `simulation/history.py`) that runs between `seed_fighters()` and the server start, replacing the bare W/L/D numbers with actual Fight rows that back them up.

**Primary recommendation:** Build a single `fabricate_history()` function that generates a chronological event timeline, uses a fast stats-based fight outcome resolver (NOT the tick-based fight engine), writes Fight+Event rows matching each fighter's existing record exactly, and calls `update_rivalries()` + `rebuild_rankings()` at the end.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- One-line template-based summaries per fight (not multi-sentence, not bare results)
- Method-specific template pools keyed to FightMethod enum (KO/TKO, Submission, Unanimous Decision, Split Decision, Majority Decision)
- Style-aware templates: fighter's FighterStyle (Striker/Grappler/Wrestler/Well-Rounded) influences template selection (e.g. a grappler's KO win reads as "shocking knockout" vs a striker's "trademark power")
- Round mentioned in narrative but not exact time ("finished in the second round" not "won at 2:47 of round 2")
- Title fights get elevated language templates ("captured the crown", "defended the belt for the third time")
- Upset victories flagged in narrative when lower-rated fighter wins (ties into existing giant_killer tag)
- Decision wins get narrative templates too, not just finishes ("outpointed across three rounds", "survived a late scare to win a split decision")
- Early-career fights (prospect's first 1-3 fights) get simpler/shorter narratives ("earned a debut victory") -- mirrors how real MMA coverage scales with fight significance
- Organic champion coronation from fabricated history: first champion crowned early in history, title fights happen periodically, current champion is whoever holds the belt at history's end
- Reigning champions should have 2-4 title defenses at game start
- Title changes allowed during history period -- some weight classes had 2-3 champions over the history window
- Top 3 AI orgs (UCC, Bellator, One) have formal champions per weight class; player org starts without champions
- Each org holds events every 6-8 weeks (~2 events/month total across 4 orgs)
- 5-7 fights per event card (standard MMA card size: main event + co-main + undercard)
- Event naming: sequential numbering only ("UCC 45", "Bellator 78", "One Championship 33") -- no thematic names
- Fight results only -- no fabricated financial data (gate revenue, PPV buys). Financials start when gameplay begins.
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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HIST-01 | Fighters have pre-existing fight records backed by real Fight rows in the database | Core fabrication function: generate Fight+Event rows matching `_gen_record()` W/L/D targets. Pattern: reverse-engineer target records into concrete fight outcomes. |
| HIST-02 | Each weight class has an established champion at game start | Champion coronation system: track current champ per weight class per org, schedule title fights periodically, crown first champ early in timeline. No new DB fields needed -- champion = highest-ranked fighter with title defense Fight rows. |
| HIST-03 | Career lengths vary realistically (veterans 15-25 fights, prospects 1-3) | Already produced by `_gen_record()` in seed.py. Fabrication must generate exactly the right number of Fight rows to match these existing W/L/D counts. |
| HIST-04 | Pre-existing rivalries emerge from fabricated fight history | Matchmaker seeds 2-3 rival pairs per weight class by deliberately booking rematches. Then call `update_rivalries()` which auto-detects pairs with 2+ fights and sets `rivalry_with`. |
| HIST-05 | Historical events with results are browsable from day one | Events created with sequential naming ("UCC 1", "UCC 2", ...), EventStatus.COMPLETED, fights with full results. Existing `get_event()` and `_event_dict()` already serialize these. Need to add/modify an endpoint for all-org event browsing (current `get_event_history()` is player-org-only). |
| HIST-06 | Career timelines are populated from fabricated history | `get_fighter_timeline()` already reads Fight+Event rows chronologically. Once Fight rows exist with valid event_id references, timelines populate automatically. Zero code changes needed in the timeline function. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0+ (already installed) | ORM for bulk Fight+Event inserts | Already the project's ORM |
| Python stdlib random | 3.x | Deterministic RNG for fight outcomes | Matches existing `py_rng` pattern in seed.py |
| numpy | (already installed) | Not needed for this phase | History fabrication is pure Python logic |

### Supporting
No new libraries needed. This phase is entirely internal codebase work.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fast stats-based outcome resolver | Full fight engine (`simulate_fight()`) | REQUIREMENTS.md explicitly excludes full engine replay: "~100x slower than fabrication for identical observable data". A stats-weighted coin flip per fight is sufficient. |
| In-memory batch then bulk insert | One-by-one `session.add()` + `session.flush()` per fight | Batch approach is faster for ~350-400 fights, but the existing seed pipeline uses per-entity flush. Either works at this scale; batch is cleaner. |

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Code Structure
```
simulation/
├── seed.py             # Existing -- add fabricate_history() call after seed_fighters()
├── history.py          # NEW -- all fabrication logic isolated in one module
│   ├── fabricate_history()         # Main entry point
│   ├── _build_event_timeline()    # Generate event dates + org assignments
│   ├── _matchmake_card()          # Pair fighters for one event (rivalry-aware)
│   ├── _resolve_fight_outcome()   # Fast winner/method/round determination
│   ├── _generate_narrative()      # Template-based one-line fight summary
│   └── _track_champions()         # Crown/defend/change champions per weight class
├── narrative.py        # Existing -- update_rivalries() called post-fabrication
├── rankings.py         # Existing -- rebuild_rankings() called post-fabrication
└── fight_engine.py     # UNTOUCHED -- not used for history fabrication
```

### Pattern 1: Record-Driven Fabrication (Top-Down Scheduling)
**What:** Instead of simulating fights and accumulating records, work backwards from the target records. Each fighter already has W/L/D counts from `_gen_record()`. The fabrication allocates those wins and losses to concrete fights across the timeline.
**When to use:** When target statistics exist before the events that produce them.
**Example:**
```python
# Pseudocode: allocate fighter's record to fight slots
def _allocate_fights(fighter, events_timeline, py_rng):
    """Distribute fighter's W/L/D across events on the timeline."""
    total_fights = fighter.wins + fighter.losses + fighter.draws
    # Pick `total_fights` event slots where this fighter's weight class appears
    # For each slot, mark whether this is a W, L, or D for this fighter
    outcomes = (['W'] * fighter.wins + ['L'] * fighter.losses + ['D'] * fighter.draws)
    py_rng.shuffle(outcomes)
    return outcomes
```

### Pattern 2: Chronological Event Generation with Running State
**What:** Generate events in chronological order, maintaining a running state of who has fought recently, who the current champion is, and which rivalry rematches are due. This produces naturally ordered data.
**When to use:** When fabricated data must form a coherent narrative arc (champions defended, rivalries built over time).
**Example:**
```python
# Pseudocode: chronological generation
def fabricate_history(session, fighters, orgs, py_rng):
    champion = {}  # {(org_id, weight_class): fighter_id}
    fight_count = defaultdict(int)  # {fighter_id: fights_so_far}
    matchup_history = defaultdict(int)  # {(id_a, id_b): count}

    for event_date, org in event_timeline:
        event = Event(name=f"{org.name} {next_event_num[org.id]}", ...)
        roster = get_available_fighters(org, fight_count, fighters)
        card = _matchmake_card(roster, champion, matchup_history, py_rng)
        for fight_spec in card:
            outcome = _resolve_fight_outcome(fight_spec, py_rng)
            session.add(Fight(...))
            fight_count[winner_id] += 1
            fight_count[loser_id] += 1
```

### Pattern 3: Two-Pass Approach (Recommended)
**What:** Pass 1 builds the event timeline and pairs fighters. Pass 2 resolves outcomes and ensures records match targets. This separates scheduling concerns from outcome concerns.
**When to use:** When you need to guarantee record totals match pre-existing values.
**Why recommended:** The core challenge is that `_gen_record()` already set W/L/D on each fighter. Fabrication must produce exactly those numbers. A two-pass approach lets you first figure out WHO fights WHOM and WHEN, then resolve outcomes to hit targets.

### Anti-Patterns to Avoid
- **Using the fight engine for history:** The tick-based `simulate_fight()` is ~100x slower and produces unpredictable records. History fabrication needs deterministic, target-matching outcomes.
- **Generating financial data for historical events:** Decision says "fight results only -- no fabricated financial data." Set gate_revenue=0, ppv_buys=0, broadcast_revenue=0 on historical events.
- **Modifying Fighter.wins/losses/draws during fabrication:** These values are already correct from `_gen_record()`. The fabrication must produce Fight rows that MATCH these existing counts, not overwrite them.
- **Creating champions as a post-hoc assignment:** Champions should emerge organically from the fabricated fight timeline via title fight scheduling, not be retroactively assigned after the fact.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rivalry detection | Custom rivalry finder | `update_rivalries()` in narrative.py | Already detects pairs with 2+ fights, handles legendary_rivalry tag for 3+. Just need to create the fight data. |
| Rankings computation | Custom ranking after history | `rebuild_rankings()` in rankings.py | Already computes scores from fighter stats and records. Call once per weight class after fabrication. |
| Fighter timeline display | Custom timeline builder | `get_fighter_timeline()` in services.py | Already joins Fight+Event and produces chronological results. Zero changes needed. |
| Event detail serialization | Custom event formatter | `_event_dict()` in services.py | Already serializes events with fight results. Works for historical events. |
| Narrative tag application | Custom post-history tagger | `apply_fight_tags()` in narrative.py | Consider calling for historically significant fights (title fights, upsets) to seed initial tags. |

**Key insight:** The display and query infrastructure already exists. Phase 2 is purely a data generation task -- once Fight+Event rows exist with correct foreign keys, everything downstream works automatically.

## Common Pitfalls

### Pitfall 1: Record Mismatch After Fabrication
**What goes wrong:** Fighter.wins/losses/draws don't match the actual count of Fight rows where they won/lost/drew.
**Why it happens:** `_gen_record()` sets W/L/D during seed_fighters(). If fabrication generates a different number of wins than the stored count, the data is inconsistent.
**How to avoid:** Either (a) treat the existing W/L/D as targets and ensure fabrication produces exactly that many fight outcomes, OR (b) zero out the W/L/D before fabrication and recompute from actual Fight rows after. Option (a) is cleaner because it preserves the archetype adjustments from `_adjust_record_for_archetype()`.
**Warning signs:** `fighter.wins != len([f for f in fights where f.winner_id == fighter.id])`

### Pitfall 2: Fighter Appearing in Two Fights on Same Event
**What goes wrong:** A fighter is paired twice on the same card.
**Why it happens:** Matchmaking doesn't track which fighters are already booked on the current event.
**How to avoid:** Maintain a `booked_this_event: set[int]` during card construction and skip fighters already in it.

### Pitfall 3: Fighter Exceeding Their Target Fight Count
**What goes wrong:** A veteran with 20 target fights gets booked into 25 fights because the matchmaker keeps selecting them.
**Why it happens:** No budget tracking per fighter across the timeline.
**How to avoid:** Maintain a `remaining_fights: dict[int, int]` counter initialized from each fighter's total record (wins + losses + draws). Decrement on each booking. Exclude fighters with remaining_fights == 0 from the matchmaker pool.

### Pitfall 4: Determinism Breakage
**What goes wrong:** Re-running `run.py` produces different fight histories.
**Why it happens:** RNG state diverges if the order of operations changes or a non-deterministic data structure (e.g., dict iteration before Python 3.7) is used.
**How to avoid:** Use the existing dual-RNG pattern (py_rng = random.Random(seed)). Pass `py_rng` to every function. Never call `random.random()` directly. Sort any collections by a stable key (fighter.id) before iterating.

### Pitfall 5: Champion of an Org Without Fighters in That Weight Class
**What goes wrong:** Trying to crown a Flyweight champion for an org that has no Flyweight fighters.
**Why it happens:** Not all orgs have fighters in every weight class. The seed pipeline distributes fighters unevenly.
**How to avoid:** Before scheduling title fights, check that the org has at least 2 fighters in the weight class. Only crown champions for org/weight-class combinations that have sufficient roster depth.

### Pitfall 6: Historical Events Post-Dating Game Start
**What goes wrong:** Some fabricated events have dates >= 2026-01-01 (the GameState.current_date), confusing the monthly sim.
**Why it happens:** Timeline generation doesn't respect the game start boundary.
**How to avoid:** All historical event dates must be strictly before date(2026, 1, 1). Use a history window of ~2023-01-01 to 2025-12-15 (leaving a 2-week gap).

### Pitfall 7: Bulk Insert Performance
**What goes wrong:** Fabrication takes >10 seconds, slowing down `run.py` startup.
**Why it happens:** Individual `session.add()` + `session.flush()` for 350+ Fight rows creates excessive DB round-trips.
**How to avoid:** Batch adds: use `session.add_all([list_of_fights])` then one `session.flush()` per event. For ~70 events with ~6 fights each, this is ~70 flushes instead of ~420.

## Code Examples

### Fast Fight Outcome Resolver
```python
def _resolve_fight_outcome(
    fighter_a: Fighter,
    fighter_b: Fighter,
    winner_id: int,
    py_rng: random.Random,
) -> dict:
    """Determine method, round for a fabricated fight given a predetermined winner."""
    winner = fighter_a if winner_id == fighter_a.id else fighter_b
    loser = fighter_b if winner_id == fighter_a.id else fighter_a

    # Method distribution weighted by winner's style and stats
    style = winner.style.value if hasattr(winner.style, 'value') else str(winner.style)
    if style == "Striker":
        method_weights = {"KO/TKO": 45, "Submission": 10, "Unanimous Decision": 25,
                          "Split Decision": 12, "Majority Decision": 8}
    elif style == "Grappler":
        method_weights = {"KO/TKO": 10, "Submission": 45, "Unanimous Decision": 25,
                          "Split Decision": 12, "Majority Decision": 8}
    elif style == "Wrestler":
        method_weights = {"KO/TKO": 15, "Submission": 15, "Unanimous Decision": 40,
                          "Split Decision": 18, "Majority Decision": 12}
    else:  # Well-Rounded
        method_weights = {"KO/TKO": 25, "Submission": 20, "Unanimous Decision": 30,
                          "Split Decision": 15, "Majority Decision": 10}

    method = py_rng.choices(
        list(method_weights.keys()),
        weights=list(method_weights.values()),
        k=1
    )[0]

    # Round ended
    if method in ("KO/TKO", "Submission"):
        round_ended = py_rng.choices([1, 2, 3], weights=[35, 40, 25], k=1)[0]
    else:
        round_ended = 3  # decisions always go the distance

    return {
        "winner_id": winner_id,
        "method": method,
        "round_ended": round_ended,
    }
```

### Narrative Template Structure
```python
# Template pools keyed by (method, context)
# context: "title", "rivalry", "upset", "prospect_debut", "standard"

HISTORY_NARRATIVE_TEMPLATES = {
    ("KO/TKO", "title"): [
        "{winner} captured the {division} crown with a devastating knockout in the {round_word} round.",
        "{winner} defended the belt for the {defense_ordinal} time, stopping {loser} in the {round_word} round.",
    ],
    ("KO/TKO", "rivalry"): [
        "{winner} settled the score with a thunderous knockout of {loser} in the {round_word} round.",
        "{winner} avenged a previous loss, finishing {loser} emphatically in round {round}.",
    ],
    ("KO/TKO", "upset"): [
        "In a shocking upset, {winner} stunned {loser} with a knockout in the {round_word} round.",
    ],
    ("KO/TKO", "prospect_debut"): [
        "{winner} earned a debut victory with a stoppage in the {round_word} round.",
    ],
    ("KO/TKO", "standard"): [
        "{winner} put {loser} away in the {round_word} round.",
        "{winner} finished {loser} with strikes in round {round}.",
    ],
    # ... similar pools for Submission, Unanimous Decision, Split Decision, Majority Decision
}

# Style-aware modifiers applied after template selection
STYLE_NARRATIVE_MODIFIERS = {
    ("Grappler", "KO/TKO"): "A shocking knockout from the grappler. ",
    ("Striker", "Submission"): "An unexpected submission from the striker. ",
    # Only apply when fighter wins outside their primary style
}
```

### Champion Tracking State Machine
```python
def _track_champions(event_fights, champion_state, py_rng):
    """Update champion state based on title fight results.

    champion_state: dict[(org_id, WeightClass), {
        'champion_id': int,
        'defense_count': int,
        'reign_start_event_id': int,
    }]
    """
    for fight in event_fights:
        if not fight.is_title_fight:
            continue
        key = (fight.event.organization_id, fight.weight_class)
        current = champion_state.get(key)

        if current is None:
            # First title fight -- winner becomes inaugural champion
            champion_state[key] = {
                'champion_id': fight.winner_id,
                'defense_count': 0,
                'reign_start_event_id': fight.event_id,
            }
        elif fight.winner_id == current['champion_id']:
            # Successful defense
            current['defense_count'] += 1
        else:
            # Title change
            champion_state[key] = {
                'champion_id': fight.winner_id,
                'defense_count': 0,
                'reign_start_event_id': fight.event_id,
            }
```

### Event Timeline Generation
```python
def _build_event_timeline(
    orgs: list[Organization],
    start_date: date,
    end_date: date,
    py_rng: random.Random,
) -> list[tuple[date, Organization]]:
    """Generate chronological event schedule for all orgs.

    Each org gets an event every 6-8 weeks. Player org excluded.
    Returns list of (event_date, org) tuples sorted by date.
    """
    ai_orgs = [o for o in orgs if not o.is_player]
    timeline = []
    event_counters = {org.id: 0 for org in ai_orgs}

    for org in ai_orgs:
        current = start_date + timedelta(days=py_rng.randint(0, 14))
        while current < end_date:
            timeline.append((current, org))
            event_counters[org.id] += 1
            gap_days = py_rng.randint(42, 56)  # 6-8 weeks
            current += timedelta(days=gap_days)

    timeline.sort(key=lambda t: t[0])
    return timeline
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare W/L/D numbers on Fighter | Actual Fight+Event rows backing up records | Phase 2 (this phase) | Enables timelines, event browsing, rivalry detection |
| No champion tracking | Champion emerges from fabricated title fight history | Phase 2 (this phase) | Each weight class has a reigning champion at game start |
| Random event naming | Sequential org-numbered events ("UCC 1", "UCC 2") | Phase 2 (this phase) | More realistic event archive |
| Player-org-only event history endpoint | All-org event browsing | Phase 2 (this phase) | Historical events visible from day one |

**Deprecated/outdated:**
- `_gen_record()` will still run during `seed_fighters()` to set initial W/L/D targets, but these numbers are now VERIFIED against actual Fight row counts post-fabrication.

## Open Questions

1. **Where to store "current champion" per weight class per org**
   - What we know: No DB field currently exists for champion tracking. The Fight model has `is_title_fight` boolean. Rankings exist but rank != champion.
   - What's unclear: Should we add a `champion_id` column to a table, or derive it at runtime from most-recent title fight win?
   - Recommendation: Use a lightweight approach -- derive champion from the most recent title fight win per org per weight class at runtime. This avoids a schema migration and keeps the data self-consistent. Alternatively, a small `Champion` table or a column on `Organization` could work but is likely overkill for now. **Claude's discretion per CONTEXT.md.**

2. **Event browsing endpoint scope**
   - What we know: `get_event_history()` currently filters to player org only. Historical events span 3 AI orgs.
   - What's unclear: Should we modify `get_event_history()` to accept an optional org filter, or create a new endpoint?
   - Recommendation: Add an optional `organization_id` parameter to `get_event_history()` (or a new `get_all_event_history()` function), and add a corresponding route. This keeps backward compatibility.

3. **Fighter record reconstruction strategy**
   - What we know: `_gen_record()` produces target W/L/D. Fabrication must match these exactly.
   - What's unclear: Do we zero-out W/L/D before fabrication and recompute, or treat existing values as targets and validate?
   - Recommendation: Treat as targets. After fabrication, run a validation pass that asserts `fighter.wins == count(fights where winner_id == fighter.id)` for every fighter. If any mismatch, fix in the validation pass. This is safer than zeroing and recomputing because it preserves `_adjust_record_for_archetype()` guarantees.

4. **How to handle fighters with 0 total fights**
   - What we know: `_gen_record()` can theoretically return 0 total fights (unlikely but possible if career_stage bounds produce it).
   - What's unclear: Should every fighter have at least 1 historical fight?
   - Recommendation: Leave 0-fight fighters as-is. They represent unsigned newcomers about to debut. The fabrication simply skips them.

## Sources

### Primary (HIGH confidence)
- `/home/d48reu/FighterSim/models/models.py` - Fight, Event, Fighter, Organization ORM models -- all fields verified
- `/home/d48reu/FighterSim/simulation/seed.py` - `_gen_record()`, `seed_fighters()` pipeline, deterministic RNG pattern
- `/home/d48reu/FighterSim/simulation/narrative.py` - `update_rivalries()` implementation (pairs with 2+ fights)
- `/home/d48reu/FighterSim/simulation/rankings.py` - `rebuild_rankings()` implementation
- `/home/d48reu/FighterSim/api/services.py` - `get_fighter_timeline()`, `get_event_history()`, `_event_dict()`, VENUES
- `/home/d48reu/FighterSim/simulation/fight_engine.py` - `FightResult` dataclass, `_NARRATIVE_TEMPLATES`, `_build_narrative()`
- `/home/d48reu/FighterSim/simulation/monthly_sim.py` - `_generate_ai_event()` pattern for event+fight creation
- `/home/d48reu/FighterSim/.planning/REQUIREMENTS.md` - HIST-01 through HIST-06, out-of-scope items

### Secondary (MEDIUM confidence)
- Existing `_generate_ai_event()` in monthly_sim.py serves as a reference for how events and fights are created during gameplay -- the history fabrication should produce structurally identical rows.

### Tertiary (LOW confidence)
- None. All findings based on direct code inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new libraries; all tools are existing codebase components verified by reading source
- Architecture: HIGH - Two-pass fabrication is a well-understood pattern; all integration points verified in code
- Pitfalls: HIGH - Identified from direct analysis of existing data model constraints and seed pipeline behavior

**Research date:** 2026-03-02
**Valid until:** Indefinite (internal codebase analysis, no external dependency versioning concerns)
