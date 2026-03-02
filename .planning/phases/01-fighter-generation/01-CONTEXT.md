# Phase 1: Fighter Generation - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Overhaul the seed pipeline to produce 400-500 fighters with authentic nationality-matched names, balanced archetypes via quota system, and career-stage-appropriate stats correlated with archetype and style. The existing seed.py is replaced/refactored. Fight history, backstories, and player origins are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Nationality & Name Pool
- MMA-realistic nationality pool: ~15-20 countries weighted by real-world MMA output (USA, Brazil, Russia/Dagestan get biggest shares ~15-20% each; smaller markets like Georgia, New Zealand get 2-5 fighters)
- Use Faker with locale mapping so fighter names match their nationality (no more "Carlos Ivanov")
- Generate archetype-based nicknames at seed time (e.g., knockout artist = "The Hammer") — Fighter model already has a nickname column (String 30)
- Allow shared last names across fighters (realistic — multiple Silvas, Johnsons) but enforce unique full names
- Current 23-nationality list gets trimmed/adjusted to MMA-prominent countries

### Career Stage Mix
- Balanced ecosystem distribution: ~20% prospects (age 20-24, low fight count), ~35% prime (25-31, peak stats), ~25% veterans (32+, high fight count, declining), ~20% transitional
- Prestige-gated organization distribution: top org (UCC, prestige 90) gets more prime/veteran talent; lower-prestige orgs get more prospects and journeymen; player promotion (prestige 50) starts with less proven fighters
- Weight class variation in career demographics: heavier classes (Heavyweight) trend older/more veteran; lighter classes (Flyweight, Lightweight) skew younger — matches real MMA demographics
- 10-15% of fighters (~40-60) start as free agents (unsigned), giving the player immediate roster-building options

### Archetype Rarity
- Pyramid rarity curve enforced per weight class:
  - Common: Journeyman (~30%), Gatekeeper (~25%)
  - Uncommon: Phenom (~20%), Late Bloomer (~12%)
  - Rare: Shooting Star (~8%), GOAT Candidate (~5%)
- Quota-first assignment: designate archetype slot first, THEN generate stats to match (replaces current waterfall scoring that collapses to 69% Phenom)
- Per-weight-class enforcement: each division independently has the full archetype pyramid (80-100 fighters per class = 4-5 GOAT Candidates per class)
- Soft quotas with +/-3-5% variance: one division might have 6% GOAT Candidates, another 4% — organic feel while staying balanced

### Stat Differentiation
- Strong archetype signatures: stats clearly reflect archetype. GOAT Candidates elite across the board (75-95). Phenoms have 1-2 spiky high stats. Journeymen are average everywhere (45-65). You can look at stats and guess the archetype
- Both style AND archetype shape stats: style sets emphasis (Striker = high striking, Grappler = high grappling), archetype sets overall level. A Phenom Striker has spiky-high striking; a Journeyman Striker has moderate striking but it's still their best stat
- Ceiling-based development: each fighter has a potential ceiling. Prospects are far from ceiling (room to grow via training). Prime fighters are near/at ceiling. Veterans are past ceiling (stats declining). Creates a development arc the player can influence
- Numpy distributions (normal/beta) centered on archetype/style targets with controlled variance — produces realistic bell curves instead of uniform random. Adds numpy as a dependency (per FGEN-05)

### Claude's Discretion
- Exact Faker locale-to-nationality mapping
- Nickname generation templates and variety
- Specific numpy distribution parameters (mean, std) per archetype/style/stat combination
- How potential ceiling interacts with existing prime_start/prime_end fields
- Exact free agent selection criteria (which fighters are unsigned)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `simulation/seed.py`: Current seed pipeline (100 fighters) — will be heavily refactored but structure is a starting point
- `simulation/traits.py`: 12 trait definitions with contradiction checking — trait assignment can be enhanced for new archetype quotas
- Fighter model (`models/models.py`): Already has nickname, archetype, narrative_tags, traits, natural_weight, confidence, prime_start/prime_end columns — no schema changes needed for basic generation
- `_assign_traits()`: Weighted pool system per archetype — can be adapted for quota-first approach
- `_gen_record()`: Age-based fight record generation — logic is sound, just needs career-stage-aware tuning

### Established Patterns
- Deterministic seeding with `random.Random(seed)` — maintain for reproducibility
- SQLAlchemy session-based creation with flush/commit pattern
- Archetype enum with 6 values (Phenom, Late Bloomer, Gatekeeper, Journeyman, GOAT Candidate, Shooting Star)
- Weight class enum with 5 values, weight limits and natural weight ranges already defined
- Contract creation tied to fighter creation (fighter → org assignment → contract)

### Integration Points
- `seed_fighters()` called from `run.py` — entry point stays the same, just produces more fighters
- `seed_organizations()` creates 4 orgs (3 AI + 1 player) — unchanged, but fighter distribution across orgs changes
- GameState with `current_date` used for contract expiry calculation
- `monthly_sim.py` takes over after seed — aging, injury, contract systems expect standard Fighter rows

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-fighter-generation*
*Context gathered: 2026-03-01*
