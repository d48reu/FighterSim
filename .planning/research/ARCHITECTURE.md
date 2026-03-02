# Architecture Patterns: World-Building Integration

**Domain:** MMA management simulation — world-building layer for pre-generated histories, scaled fighter pools, player scenarios, and fighter identity depth
**Researched:** 2026-03-01
**Confidence:** HIGH (based on direct codebase analysis + domain research)

## Current Architecture Summary

The existing codebase follows a clean layered pattern:

```
Frontend (vanilla JS) --> API Routes (app.py, thin) --> Services (services.py, thick) --> Simulation (simulation/, Flask-free) --> Models (models.py, SQLAlchemy ORM)
```

Key files and their sizes:
- `api/services.py` — 3,698 lines (all business logic)
- `simulation/monthly_sim.py` — 1,765 lines (game advancement)
- `simulation/narrative.py` — 1,538 lines (bios, tags, hype, GOAT)
- `models/models.py` — 648 lines (25 models)
- `simulation/seed.py` — 446 lines (100 fighters, 4 orgs, 15 camps)
- `simulation/fight_engine.py` — 892 lines (tick-based fight sim)

**Critical constraint:** `simulation/` has ZERO Flask dependencies and must stay that way.

## Recommended Architecture for World-Building

The world-building system should be a **pre-game generation pipeline** — a set of modules that run once at new-game creation, producing a fully populated database with fabricated history. It is NOT a runtime system. Once the game starts, the existing monthly_sim.py takes over and the world-building code never runs again.

### Why a Pipeline, Not a Runtime System

The reference game (WMMA) and the Dwarf Fortress approach both use the same pattern: generate the world once, then simulate forward from there. This is the right model because:

1. **Performance** — Generating 400-500 fighters with interconnected histories is expensive. Do it once, not on every month tick.
2. **Consistency** — Pre-generated history must be internally consistent (fighter A beat fighter B at Event X, both records match). This is easier to guarantee in a single pipeline pass.
3. **Determinism** — A seed value produces the same world every time, enabling reproducible testing and "interesting starts."
4. **Separation of concerns** — The monthly_sim already works. World-building fills the database; monthly_sim evolves it.

### Component Boundaries

| Component | Responsibility | Communicates With | New/Modified |
|-----------|---------------|-------------------|--------------|
| `simulation/worldgen/` | Top-level pipeline orchestrator | All worldgen sub-modules, Models | NEW directory |
| `simulation/worldgen/pipeline.py` | Orchestrates full world generation in order | All worldgen modules | NEW |
| `simulation/worldgen/config.py` | World generation parameters (fighter count, org count, history depth, scenario definitions) | pipeline.py | NEW |
| `simulation/worldgen/orgs.py` | Generate organizations with histories, prestige tiers, rivalries | Models (Organization) | NEW |
| `simulation/worldgen/fighters.py` | Generate 400-500 fighters with realistic distributions | Models (Fighter) | NEW (replaces seed.py fighter gen) |
| `simulation/worldgen/history.py` | Fabricate past events, fights, records, title reigns | Models (Event, Fight, Ranking) | NEW |
| `simulation/worldgen/identity.py` | Backstories, personality profiles, behavioral traits, relationships | Models (Fighter), narrative.py | NEW |
| `simulation/worldgen/scenarios.py` | Player origin stories and starting conditions | Models (Organization, GameState) | NEW |
| `simulation/worldgen/validation.py` | Post-generation integrity checks | All Models | NEW |
| `simulation/seed.py` | DEPRECATED — thin wrapper calling pipeline.py for backward compat | worldgen/pipeline.py | MODIFIED |
| `simulation/narrative.py` | Bio generation, tags, hype (runtime) | Models (Fighter, Fight) | MINOR MODS |
| `simulation/monthly_sim.py` | Monthly game advancement (runtime) | Models, fight_engine, narrative | MINOR MODS |
| `models/models.py` | SQLAlchemy ORM models | Database | MODIFIED (new fields) |
| `api/services.py` | API business logic | Models, simulation | MINOR MODS |

### Data Flow

#### New Game Creation Flow

```
Player clicks "New Game" + selects scenario
        |
        v
pipeline.py orchestrates (deterministic seed):
        |
        +--> orgs.py: Generate 6-8 organizations with tiered prestige
        |     |
        |     +--> 1 flagship org (prestige 85-95)
        |     +--> 2 major orgs (prestige 60-80)
        |     +--> 2-3 regional orgs (prestige 30-55)
        |     +--> Player org (from scenario)
        |
        +--> fighters.py: Generate 400-500 fighters
        |     |
        |     +--> Distribution: ~80-100 per weight class
        |     +--> Age curve: realistic pyramid (more 22-28 than 35+)
        |     +--> Skill tiers: elite (5%), contender (15%), solid (40%), fringe (40%)
        |     +--> Contract distribution: top org gets best, trickle down
        |     +--> ~50-70 unattached free agents
        |
        +--> history.py: Fabricate 2-3 years of past events
        |     |
        |     +--> Generate 60-100 past events across all orgs
        |     +--> Simulate or fabricate fight results (records, methods, rounds)
        |     +--> Establish current champions per weight class per org
        |     +--> Create win/loss streaks that justify current rankings
        |     +--> Generate rivalries from rematch pairs
        |     +--> Retire 20-30 fighters (populate Hall of Fame)
        |
        +--> identity.py: Layer personality and identity
        |     |
        |     +--> Assign backstories (training origin, career narrative arc)
        |     +--> Assign behavioral personality (trash talker, humble, enigmatic, etc.)
        |     +--> Create 3-5 "storyline" fighters per weight class (names the player will recognize)
        |     +--> Generate pre-existing news headlines from history
        |
        +--> scenarios.py: Apply player scenario
        |     |
        |     +--> Set player org parameters (budget, prestige, roster)
        |     +--> Seed 3-8 fighters on player roster (depending on scenario)
        |     +--> Set initial rival org relationship
        |     +--> Generate opening narrative text
        |
        +--> validation.py: Integrity checks
              |
              +--> All fighter records match their Fight rows
              +--> All events have valid fight cards
              +--> Rankings are computed and cached
              +--> No orphaned contracts
              +--> Champion exists for each weight class in top orgs
              +--> Method distributions look realistic
```

#### Runtime Flow (unchanged)

```
Player actions --> services.py --> monthly_sim.py --> fight_engine.py
                                                  --> narrative.py
                                                  --> rankings.py
```

The world-building pipeline writes to the database. Everything after that uses the same runtime code that already exists. The monthly_sim does not need to know the world was pre-generated vs manually seeded.

## Model Changes Required

### Fighter Model — New Fields

```python
# Identity depth
backstory: Mapped[Optional[str]] = Column(Text, nullable=True)       # Pre-generated backstory paragraph
personality: Mapped[Optional[str]] = Column(String(30), nullable=True) # behavioral: "trash_talker", "humble", "enigmatic", "stoic", "showman", "professional"
training_origin: Mapped[Optional[str]] = Column(String(100), nullable=True)  # "American Top Team", "Dagestan Wrestling Academy", etc.
hometown: Mapped[Optional[str]] = Column(String(100), nullable=True)  # "Miami, FL", "Makhachkala, Russia"

# Pre-generated history markers
is_champion: Mapped[bool] = Column(Boolean, default=False)            # Current champion in their org
title_defenses: Mapped[int] = Column(Integer, default=0)              # Historical title defense count
career_highlight: Mapped[Optional[str]] = Column(Text, nullable=True) # One-liner best moment
generation_era: Mapped[Optional[str]] = Column(String(20), nullable=True)  # "current", "veteran", "legend" — helps narrative system
```

### New Enum: FighterPersonality

```python
class FighterPersonality(str, enum.Enum):
    TRASH_TALKER = "Trash Talker"
    HUMBLE = "Humble"
    ENIGMATIC = "Enigmatic"
    STOIC = "Stoic"
    SHOWMAN = "Showman"
    PROFESSIONAL = "Professional"
    VOLATILE = "Volatile"
    CEREBRAL = "Cerebral"
```

### Organization Model — New Fields

```python
# World-building fields
founded_year: Mapped[Optional[int]] = Column(Integer, nullable=True)
headquarters: Mapped[Optional[str]] = Column(String(100), nullable=True)
tier: Mapped[Optional[str]] = Column(String(20), nullable=True)  # "flagship", "major", "regional"
total_events_held: Mapped[int] = Column(Integer, default=0)
description: Mapped[Optional[str]] = Column(Text, nullable=True)
```

### No New Tables Needed

The world-building system generates data for existing tables (Fighter, Organization, Contract, Event, Fight, Ranking, NewsHeadline, Notification). It does NOT need new tables. The history pipeline writes Fight and Event rows that look identical to runtime-generated ones. This is a key design decision: **the fabricated past is indistinguishable from a simulated future** at the data level.

One exception: if title reign tracking is needed later (championship belts as first-class objects), that would be a new model. But per PROJECT.md, that is out of scope for this milestone.

## Patterns to Follow

### Pattern 1: Pipeline Phase Pattern

**What:** Each world-generation step is an independent function that takes a session and config, writes to the database, and returns summary data the next step can use.

**When:** Every worldgen module follows this pattern.

**Example:**

```python
# simulation/worldgen/fighters.py

@dataclass
class FighterGenResult:
    """Summary of fighter generation for downstream phases."""
    fighter_ids: list[int]
    champions: dict[str, int]  # weight_class -> fighter_id
    by_tier: dict[str, list[int]]  # "elite"/"contender"/"solid"/"fringe" -> ids

def generate_fighters(
    session: Session,
    orgs: list[Organization],
    config: WorldGenConfig,
    rng: random.Random,
) -> FighterGenResult:
    """Generate all fighters and assign contracts. Returns summary for history phase."""
    ...
```

**Why:** Each phase can be tested independently. The pipeline is restartable — you can regenerate fighters without regenerating orgs. The result dataclass passes only IDs, not ORM objects, keeping phases loosely coupled.

### Pattern 2: Fabricated History via Record Synthesis (NOT Full Fight Simulation)

**What:** Past fights are fabricated by generating plausible outcomes (winner, method, round) from fighter attributes, NOT by running the full fight engine tick-by-tick.

**When:** Always, for pre-game history generation.

**Example:**

```python
# simulation/worldgen/history.py

def _fabricate_fight_result(
    fighter_a: Fighter,
    fighter_b: Fighter,
    is_title_fight: bool,
    rng: random.Random,
) -> dict:
    """Generate a plausible fight outcome without running the full engine."""
    # Weighted probability based on overall ratings
    a_advantage = (fighter_a.overall - fighter_b.overall) / 100
    a_win_prob = 0.5 + a_advantage * 0.4  # Mild favorite/underdog scaling

    winner = fighter_a if rng.random() < a_win_prob else fighter_b
    loser = fighter_b if winner.id == fighter_a.id else fighter_a

    # Method distribution matching engine targets: Sub ~23%, KO ~32%, Dec ~45%
    method_roll = rng.random()
    if method_roll < 0.23:
        method = "Submission"
    elif method_roll < 0.55:
        method = "KO/TKO"
    else:
        method = rng.choice(["Unanimous Decision", "Split Decision", "Majority Decision"])

    ...
    return {"winner_id": winner.id, "loser_id": loser.id, "method": method, ...}
```

**Why:** Running 600+ full fight simulations (60-100 events x 6-10 fights) through the tick engine at startup would be slow (~30-60 seconds) and produce overly detailed data nobody will read. Fabrication is 100x faster and produces the same observable outcome: a Fight row with winner, method, round, and a narrative sentence. The player never sees the tick-by-tick replay of a fight that happened before the game started.

### Pattern 3: Skill-Tier Distribution Curves

**What:** Fighters are generated in defined tiers with controlled distributions rather than pure random attribute rolls.

**When:** Fighter generation phase.

**Example:**

```python
# simulation/worldgen/config.py

SKILL_TIERS = {
    "elite": {
        "pct": 0.05,  # 5% of fighters
        "attr_range": (78, 95),
        "archetypes": [Archetype.GOAT_CANDIDATE, Archetype.PHENOM],
        "age_range": (24, 32),
    },
    "contender": {
        "pct": 0.15,
        "attr_range": (68, 82),
        "archetypes": [Archetype.PHENOM, Archetype.GOAT_CANDIDATE, Archetype.SHOOTING_STAR],
        "age_range": (22, 34),
    },
    "solid": {
        "pct": 0.40,
        "attr_range": (55, 72),
        "archetypes": [Archetype.GATEKEEPER, Archetype.LATE_BLOOMER, Archetype.PHENOM],
        "age_range": (21, 36),
    },
    "fringe": {
        "pct": 0.40,
        "attr_range": (40, 60),
        "archetypes": [Archetype.JOURNEYMAN, Archetype.GATEKEEPER, Archetype.LATE_BLOOMER],
        "age_range": (20, 37),
    },
}
```

**Why:** Pure random (current seed.py approach: `rng.randint(40, 92)` for all attributes) produces a flat distribution where everyone clusters around 66. Real sports have a steep talent pyramid — a few elite fighters everyone knows, a larger group of contenders, and a big base of journeymen. This tier system guarantees the world feels differentiated from the start.

### Pattern 4: Backward-Compatible seed.py Wrapper

**What:** The existing `seed.py` becomes a thin wrapper that calls the worldgen pipeline with default parameters.

**When:** To avoid breaking `python run.py` and `python test_cli.py`.

**Example:**

```python
# simulation/seed.py (modified)

from simulation.worldgen.pipeline import generate_world, WorldGenConfig

def seed_organizations(session):
    """Legacy wrapper — delegates to worldgen pipeline."""
    config = WorldGenConfig(
        fighter_count=100,  # Keep 100 for backward compat / fast tests
        history_depth_months=0,  # No fabricated history for quick tests
        scenario="default",
    )
    return generate_world(session, config).organizations

def seed_fighters(session, orgs, seed=42, count=100):
    """Legacy wrapper — full worldgen only when count >= 400."""
    if count >= 400:
        config = WorldGenConfig(fighter_count=count, seed=seed)
        return generate_world(session, config).fighters
    else:
        # Original fast path for tests
        return _legacy_seed_fighters(session, orgs, seed, count)
```

**Why:** The test suite (`test_cli.py`) needs to seed 100 fighters fast. Full worldgen with history fabrication is only needed for "New Game." This pattern gives both paths without code duplication.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Generating History at Runtime

**What:** Running the history fabrication pipeline during monthly_sim or on-demand.
**Why bad:** Breaks the existing 120-170ms sim_month performance target. Creates inconsistent state if history generation is interrupted.
**Instead:** Generate all history once during new-game creation. The monthly_sim only advances the world forward from the generated state.

### Anti-Pattern 2: Full Fight Engine for Past Fights

**What:** Running `simulate_fight()` through the tick engine for every fabricated historical fight.
**Why bad:** 600+ fight simulations would take 30-60 seconds. The tick-by-tick data (knockdowns per round, momentum swings) is never surfaced for past fights. It wastes computation producing data nobody reads.
**Instead:** Use the lightweight fabrication function that produces statistically similar outcomes (matching the ~23%/32%/45% method distribution) in a single random call per fight.

### Anti-Pattern 3: Storing Backstories in JSON Blobs

**What:** Packing all identity data (backstory, personality, training origin, hometown, career highlight) into a single JSON Text column.
**Why bad:** Cannot query by personality type. Cannot index on training origin. Makes the Fighter model's already-complex _fighter_dict() even worse.
**Instead:** Use dedicated columns for structured data (personality, training_origin, hometown). Use Text columns only for freeform narrative (backstory, career_highlight).

### Anti-Pattern 4: Coupling Scenario Logic to Fighter Generation

**What:** Having `fighters.py` know about player scenarios (e.g., "if player is underdog, generate worse fighters for their roster").
**Why bad:** Scenarios and fighter generation are orthogonal concerns. Fighter gen should produce a realistic world; scenario selection should then carve out a starting position within it.
**Instead:** `fighters.py` generates the full pool. `scenarios.py` runs after, assigning specific fighters to the player roster and adjusting starting conditions.

### Anti-Pattern 5: Breaking the Flat File Structure

**What:** Creating deep nested module hierarchies like `simulation/worldgen/fighters/generators/base.py`.
**Why bad:** The codebase uses flat files (one file per concern). Adding 3+ levels of nesting creates import complexity and fights the established pattern.
**Instead:** Keep `simulation/worldgen/` as a single-level directory with one file per pipeline phase. If a file exceeds 500 lines, split by concern, not by abstraction layer.

## Scalability Considerations

| Concern | At 100 fighters (tests) | At 500 fighters (game) | At 1000+ fighters (future) |
|---------|------------------------|------------------------|---------------------------|
| Seed time | <1 second (no history) | 3-8 seconds (with history) | 10-20 seconds (acceptable for new game) |
| DB size | ~200 KB | ~2-5 MB | ~10 MB |
| Monthly sim | 120-170ms (current) | 300-500ms (needs profiling) | May need batch queries |
| Rankings rebuild | Instant | <100ms per class | May need score caching |
| Memory during gen | Negligible | ~50 MB peak | ~100 MB peak |

**Key performance note:** The monthly_sim currently queries all fighters. At 500 fighters, the `_age_fighter` loop, contract processing, and AI event generation will run 5x longer. This is likely still under the 2-second target, but should be profiled during implementation. If needed, batch SQLAlchemy queries (select all fighters at once, process in memory, flush once) rather than per-fighter queries.

**Bulk insert optimization:** For the worldgen pipeline, use `session.add_all()` with a final `session.commit()` rather than `session.add()` + `session.flush()` per fighter. At 500 fighters this saves significant time. For history fabrication (600+ Fight rows), consider `session.bulk_insert_mappings(Fight, fight_dicts)` for a 10-15x speedup over individual ORM inserts.

## Suggested Build Order

The components have clear dependencies. Build in this order:

```
Phase 1: Foundation
  worldgen/config.py       (no dependencies)
  worldgen/orgs.py         (depends on: config, models)
  worldgen/fighters.py     (depends on: config, models, orgs output)
  worldgen/validation.py   (depends on: models)
  Model changes            (new Fighter/Org fields)

Phase 2: History
  worldgen/history.py      (depends on: fighters output, models)
  Modify seed.py           (thin wrapper for backward compat)

Phase 3: Identity
  worldgen/identity.py     (depends on: fighters, history outputs, narrative.py patterns)
  Modify narrative.py      (consume new personality/backstory fields)

Phase 4: Player Experience
  worldgen/scenarios.py    (depends on: all prior phases)
  worldgen/pipeline.py     (orchestrates all phases)
  API/frontend changes     (scenario selection UI, new-game flow)
```

**Dependency graph:**

```
config.py ----+
              |
orgs.py ------+--> fighters.py --+--> history.py --+--> identity.py --+--> scenarios.py --> pipeline.py
              |                  |                 |                  |
models.py ----+                  |                 |                  |
                                 |                 |                  |
validation.py -------------------+-----------------+------------------+
```

**Build order rationale:**
- Config and orgs first because everything depends on organization structure.
- Fighters before history because you need fighter IDs to create Fight rows.
- History before identity because backstories reference a fighter's past fights and achievements.
- Identity before scenarios because scenarios select from the identity-enriched fighter pool.
- Pipeline last because it orchestrates all phases and needs them complete.

## Sources

- Direct codebase analysis — all 8 source files read and analyzed (HIGH confidence)
- [WMMA5 — Grey Dog Software](https://greydogsoftware.com/title/world-of-mixed-martial-arts-5/) — reference game features (MEDIUM confidence)
- [WMMA5 Review — GM Games](https://gmgames.org/world-of-mixed-martial-arts-wmma5/review/) — world-building depth reference (MEDIUM confidence)
- [Dwarf Fortress World Generation — Wiki](https://dwarffortresswiki.org/index.php/World_generation) — history simulation pattern reference (MEDIUM confidence)
- [ZenGM Architecture — GitHub](https://github.com/zengm-games/zengm) — client-worker sports sim architecture (LOW confidence, different tech stack)
- [SQLAlchemy Bulk Inserts — Official Docs](https://docs.sqlalchemy.org/en/20/_modules/examples/performance/bulk_inserts.html) — performance optimization for seeding (HIGH confidence)
- [SQLAlchemy Bulk Insert Discussion](https://github.com/sqlalchemy/sqlalchemy/discussions/10537) — 500-record seeding performance patterns (MEDIUM confidence)
- [PC Gamer — Wrestling Sims](https://www.pcgamer.com/for-20-years-these-obscure-wrestling-sims-have-been-taking-players-behind-the-scenes/) — genre history and patterns (LOW confidence)
