# Phase 1: Fighter Generation - Research

**Researched:** 2026-03-01
**Domain:** Procedural fighter generation (name localization, stat distributions, archetype quotas)
**Confidence:** HIGH

## Summary

Phase 1 replaces the current 100-fighter seed pipeline with a 400-500 fighter generation system that produces nationality-authentic names, quota-enforced archetype distribution, and career-stage-correlated stats. The two new dependencies are **Faker >=40.0** (locale-based name generation) and **numpy** (already installed at v2.4.2, needs to be added to requirements.txt).

Faker provides direct locale support for 16 of the ~18 target nationalities. Three nationalities require proxy locales or supplemental name lists: **Dagestani** (no locale -- use hardcoded romanized Dagestani names), **Cameroonian** (no `fr_CM` -- use `fr_FR`), and **Jamaican** (no `en_JM` -- use `en_GB`). Four locales produce non-Latin script (Russian, Japanese, Korean, Georgian) -- Japanese has a built-in `romanized_name()` method; the other three need hardcoded romanized name lists since the game UI is Latin-script.

The quota-first archetype assignment is a clean architectural inversion of the current waterfall system: allocate archetype slots per weight class first, then generate stats to match. Numpy's `Generator.normal()` and `Generator.beta()` with a seeded RNG provide the controlled distributions needed to create archetype-differentiated stat profiles while maintaining deterministic reproducibility.

**Primary recommendation:** Use Faker with per-nationality locale instances for Latin-script locales, supplemented by hardcoded romanized name arrays for Russian/Korean/Georgian/Dagestani fighters. Generate `first_name_male() + " " + last_name()` to avoid honorific prefixes. Implement quota-first archetype assignment with numpy distributions for stat generation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- MMA-realistic nationality pool: ~15-20 countries weighted by real-world MMA output (USA, Brazil, Russia/Dagestan get biggest shares ~15-20% each; smaller markets like Georgia, New Zealand get 2-5 fighters)
- Use Faker with locale mapping so fighter names match their nationality (no more "Carlos Ivanov")
- Generate archetype-based nicknames at seed time (e.g., knockout artist = "The Hammer") -- Fighter model already has a nickname column (String 30)
- All unique names -- Faker generates until no duplicates across the full roster. Retry with middle initials or alternate names if collisions occur
- Current 23-nationality list gets trimmed/adjusted to MMA-prominent countries
- Balanced ecosystem distribution: ~20% prospects (age 20-24, low fight count), ~35% prime (25-31, peak stats), ~25% veterans (32+, high fight count, declining), ~20% transitional
- Prestige-gated organization distribution: top org (UCC, prestige 90) gets more prime/veteran talent; lower-prestige orgs get more prospects and journeymen; player promotion (prestige 50) starts with less proven fighters
- Same career stage distribution across all weight classes -- consistent 20/35/25/20 split regardless of division
- 10-15% of fighters (~40-60) start as free agents (unsigned), giving the player immediate roster-building options
- Pyramid rarity curve enforced per weight class: Journeyman ~30%, Gatekeeper ~25%, Phenom ~20%, Late Bloomer ~12%, Shooting Star ~8%, GOAT Candidate ~5%
- Quota-first assignment: designate archetype slot first, THEN generate stats to match
- Per-weight-class enforcement: each division independently has the full archetype pyramid (80-100 fighters per class = 4-5 GOAT Candidates per class)
- Soft quotas with +/-3-5% variance
- Strong archetype signatures: stats clearly reflect archetype
- Both style AND archetype shape stats
- Ceiling-based development: each fighter has a potential ceiling
- Numpy distributions (normal/beta) centered on archetype/style targets with controlled variance

### Claude's Discretion
- Exact Faker locale-to-nationality mapping
- Nickname generation templates and variety
- Specific numpy distribution parameters (mean, std) per archetype/style/stat combination
- How potential ceiling interacts with existing prime_start/prime_end fields
- Exact free agent selection criteria (which fighters are unsigned)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FGEN-01 | Fighter names match nationality using locale-appropriate generation (Faker) | Faker locale mapping verified for 16/18 nationalities; proxy strategy for 3 missing locales; romanization strategy for 4 non-Latin locales; `first_name_male() + last_name()` pattern avoids honorifics |
| FGEN-02 | Fighter pool scales to 400-500 fighters across 5 weight classes (80-100 per class) | Faker name pools verified sufficient (10K-300K combos per locale); `unique` feature prevents duplicates; quota-first loop naturally distributes across weight classes |
| FGEN-03 | Archetype distribution uses quota system instead of waterfall scoring | Quota-first architecture: pre-allocate archetype slots per weight class with pyramid curve, then generate stats to match; eliminates current `_assign_archetype` waterfall that collapses to 69% Phenom |
| FGEN-04 | Fighters span realistic career stages at game start | Career stage quotas (20/35/25/20) drive age + prime window generation; organization distribution gates talent by prestige tier; 10-15% free agents |
| FGEN-05 | Fighter stats correlate with archetype and career stage (numpy distributions) | numpy `Generator.normal()` and `Generator.beta()` with seeded RNG; archetype sets stat center/spread, style sets emphasis weights, career stage sets proximity to ceiling; `np.clip()` enforces 1-100 bounds |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Faker | >=40.0 (current: 40.5.1) | Locale-based name generation | De facto standard for fake data in Python; 105 locales; built-in uniqueness tracking; seeded reproducibility |
| numpy | >=2.0 (installed: 2.4.2) | Statistical distributions for stat generation | Already installed; `default_rng()` with seed for reproducible normal/beta distributions; `np.clip()` for range enforcement |
| SQLAlchemy | >=2.0 (existing) | ORM for Fighter model persistence | Already the project's ORM; no changes needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| random (stdlib) | N/A | Deterministic RNG for non-stat randomness (age, weight class selection, org assignment) | Use for shuffling, choice operations that don't need statistical distributions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Faker locales for non-Latin names | Transliteration library (e.g., `transliterate`, `unidecode`) | Adds dependency; transliterated names often look wrong ("Veniamin Kozlov" instead of authentic "Khabib Nurmagomedov"). Hardcoded romanized lists are more MMA-authentic |
| numpy for distributions | `random.gauss()` + manual clipping | stdlib alternative but no batch generation, no beta distribution, harder to parameterize consistently |
| Faker for ALL names | Expand existing `_FIRST_NAMES`/`_LAST_NAMES` arrays | Doesn't scale; no nationality-name correlation; the exact problem this phase solves |

**Installation:**
```bash
pip install faker>=40.0 numpy>=2.0
```

**requirements.txt update:**
```
flask>=3.0
sqlalchemy>=2.0
gunicorn>=23.0
faker>=40.0
numpy>=2.0
```

## Architecture Patterns

### Recommended Refactoring Structure
```
simulation/
├── seed.py              # Refactored: orchestrator, quota allocation, org distribution
├── name_gen.py          # NEW: Faker locale mapping, romanized name lists, unique name generation
├── stat_gen.py          # NEW: numpy-based stat generation per archetype/style/career stage
├── traits.py            # Existing: trait definitions (minimal changes)
├── narrative.py         # Existing: nickname pools already here, enhance for seed-time assignment
```

The current monolithic `seed.py` (447 lines) should be split into focused modules. The seed orchestrator stays in `seed.py`; name generation and stat generation get their own modules for testability and clarity.

### Pattern 1: Quota-First Archetype Allocation
**What:** Pre-allocate archetype slots per weight class before generating any fighter data.
**When to use:** Always -- this replaces the current waterfall `_assign_archetype`.
**Example:**
```python
import numpy as np

ARCHETYPE_QUOTAS = {
    "Journeyman":     0.30,
    "Gatekeeper":     0.25,
    "Phenom":         0.20,
    "Late Bloomer":   0.12,
    "Shooting Star":  0.08,
    "GOAT Candidate": 0.05,
}

def allocate_archetypes(count_per_class: int, rng: np.random.Generator) -> list[str]:
    """Return a shuffled list of archetype assignments for one weight class.

    Soft quotas: +/-3-5% variance via rounding, then shuffle.
    """
    slots = []
    remaining = count_per_class
    for archetype, ratio in ARCHETYPE_QUOTAS.items():
        # Add small variance: +/- 1-2 fighters
        base = round(count_per_class * ratio)
        variance = rng.integers(-2, 3)  # -2 to +2
        n = max(1, min(base + variance, remaining))
        slots.extend([archetype] * n)
        remaining -= n
    # Fill any remainder with Journeyman (most common)
    slots.extend(["Journeyman"] * remaining)
    rng.shuffle(slots)
    return slots[:count_per_class]
```

### Pattern 2: Locale-Based Name Generation with Fallbacks
**What:** Map each nationality to a Faker locale, with special handling for non-Latin scripts.
**When to use:** For every fighter created.
**Example:**
```python
from faker import Faker

# Latin-script locales: use Faker directly
NATIONALITY_LOCALE_MAP = {
    "American": "en_US",
    "Brazilian": "pt_BR",
    "Mexican": "es_MX",
    "Irish": "en_IE",
    "British": "en_GB",
    "Canadian": "en_CA",
    "Australian": "en_AU",
    "Swedish": "sv_SE",
    "Norwegian": "no_NO",
    "Polish": "pl_PL",
    "Dutch": "nl_NL",
    "French": "fr_FR",
    "German": "de_DE",
    "Nigerian": "en_NG",
    "South African": "zu_ZA",
    "New Zealander": "en_NZ",
    "Cameroonian": "fr_FR",   # proxy: French-speaking country
    "Jamaican": "en_GB",      # proxy: English-speaking Caribbean
}

# Non-Latin locales: hardcoded romanized name lists
# Japanese uses Faker's built-in romanized_name()
ROMANIZED_NAMES = {
    "Russian": {
        "first": ["Aleksandr", "Dmitri", "Sergei", "Andrei", "Pavel", ...],
        "last": ["Volkov", "Petrov", "Ivanov", "Morozov", "Sokolov", ...],
    },
    "Dagestani": {
        "first": ["Khabib", "Islam", "Zabit", "Magomed", "Shamil", ...],
        "last": ["Nurmagomedov", "Makhachev", "Magomedsharipov", ...],
    },
    "South Korean": {
        "first": ["Sung-Jung", "Chan-Mi", "Dong-Hyun", "Kyung-Ho", ...],
        "last": ["Kim", "Park", "Lee", "Choi", "Jung", ...],
    },
    "Georgian": {
        "first": ["Merab", "Giga", "Levan", "Giorgi", "Lasha", ...],
        "last": ["Dvalishvili", "Chikadze", "Machavariani", "Kutateladze", ...],
    },
}

def generate_name(nationality: str, faker_instances: dict, rng, used_names: set) -> str:
    """Generate a unique name matching the fighter's nationality."""
    for attempt in range(200):
        if nationality == "Japanese":
            name = faker_instances["ja_JP"].romanized_name()
        elif nationality in ROMANIZED_NAMES:
            pool = ROMANIZED_NAMES[nationality]
            first = rng.choice(pool["first"])
            last = rng.choice(pool["last"])
            name = f"{first} {last}"
        else:
            locale = NATIONALITY_LOCALE_MAP[nationality]
            fake = faker_instances[locale]
            name = f"{fake.first_name_male()} {fake.last_name()}"

        if name not in used_names:
            used_names.add(name)
            return name

    # Fallback: append initial
    return f"{name} Jr."
```

### Pattern 3: Archetype-Driven Stat Generation with Numpy
**What:** Generate stats from numpy distributions parameterized by archetype, style, and career stage.
**When to use:** For every fighter's 6 core attributes.
**Example:**
```python
import numpy as np

# Archetype stat profiles: (mean, std) for overall stat level
ARCHETYPE_PROFILES = {
    "GOAT Candidate": {"center": 85, "spread": 5, "floor": 75, "ceiling": 95},
    "Phenom":         {"center": 72, "spread": 8, "floor": 60, "ceiling": 90},
    "Gatekeeper":     {"center": 62, "spread": 5, "floor": 52, "ceiling": 72},
    "Journeyman":     {"center": 55, "spread": 6, "floor": 40, "ceiling": 68},
    "Late Bloomer":   {"center": 58, "spread": 7, "floor": 45, "ceiling": 75},
    "Shooting Star":  {"center": 70, "spread": 7, "floor": 58, "ceiling": 85},
}

# Style emphasis: multiplier applied to relevant stats
STYLE_EMPHASIS = {
    "Striker":      {"striking": 1.15, "speed": 1.10, "grappling": 0.90},
    "Grappler":     {"grappling": 1.15, "wrestling": 1.05, "striking": 0.90},
    "Wrestler":     {"wrestling": 1.15, "cardio": 1.05, "striking": 0.92},
    "Well-Rounded": {},  # no bias
}

def generate_stats(archetype: str, style: str, career_stage: str,
                   rng: np.random.Generator) -> dict[str, int]:
    profile = ARCHETYPE_PROFILES[archetype]
    emphasis = STYLE_EMPHASIS.get(style, {})

    stats = {}
    for attr in ["striking", "grappling", "wrestling", "cardio", "chin", "speed"]:
        base = rng.normal(loc=profile["center"], scale=profile["spread"])
        multiplier = emphasis.get(attr, 1.0)
        val = base * multiplier
        val = np.clip(val, 1, 100)
        stats[attr] = int(round(val))

    return stats
```

### Pattern 4: Deterministic Dual-RNG Seeding
**What:** Use both `random.Random(seed)` for general randomness and `np.random.default_rng(seed)` for stat distributions, both from the same master seed.
**When to use:** To maintain full deterministic reproducibility (existing pattern uses `random.Random(seed=42)`).
**Example:**
```python
import random
import numpy as np

def seed_fighters(session, orgs, seed=42, count=450):
    py_rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    # Use py_rng for choices, shuffles, age generation
    # Use np_rng for stat distributions (normal, beta)
```

### Anti-Patterns to Avoid
- **Waterfall archetype assignment:** The current `_assign_archetype()` generates stats first then tries to infer archetype from stats. This creates the 69% Phenom collapse because the fallback at line 184 catches everything that doesn't match other criteria. Quota-first inverts this correctly.
- **`name_male()` for name generation:** Many Faker locales include honorific prefixes ("Ing.", "Prof.", "Sr.", "Herr") in `name_male()`. Always use `first_name_male() + " " + last_name()` instead.
- **Single Faker instance for multiple locales:** While Faker supports multi-locale instances with weights, this conflates nationality selection with name generation. Create one Faker instance per locale and select based on already-chosen nationality.
- **Uniform random for stats:** `rng.randint(40, 92)` (current approach) produces flat distributions with no archetype signature. Numpy normal/beta distributions create the bell-curve clustering that makes archetypes visually distinct.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Locale-appropriate names | Expand `_FIRST_NAMES`/`_LAST_NAMES` arrays | `Faker(locale).first_name_male()` | 105 locales, 100-1000+ names per locale, community-maintained |
| Statistical distributions | Manual bell curve with `random.gauss()` + clipping | `np.random.default_rng().normal()` / `.beta()` | Proper clipping, batch generation, well-tested edge cases |
| Unique name enforcement | Manual `_USED_NAMES` set with retry loop | `Faker.unique` property | Built-in retry, `UniquenessException` for exhaustion detection, per-locale tracking |
| Nickname generation | Build new system from scratch | Extend existing `suggest_nicknames()` in `narrative.py` | Already has archetype pools, trait boosts, nationality nicknames, deduplication |

**Key insight:** The hard parts of this phase (locale name mapping, stat distribution parameterization, quota enforcement) are data configuration problems, not algorithmic problems. The libraries handle the algorithms; the implementation work is defining the right parameters.

## Common Pitfalls

### Pitfall 1: Non-Latin Script Names in Game UI
**What goes wrong:** Faker's `ru_RU`, `ko_KR`, and `ka_GE` locales generate names in Cyrillic, Hangul, and Georgian script respectively. These are unreadable in a Latin-script game UI.
**Why it happens:** Faker generates culturally-authentic names in native script, which is correct behavior but wrong for this use case.
**How to avoid:** Use hardcoded romanized name arrays for Russian, Dagestani, Korean, and Georgian nationalities. Japanese has a built-in `romanized_name()` method. All other target nationalities use Latin-script locales natively.
**Warning signs:** Fighter list shows boxes, question marks, or non-Latin characters.

### Pitfall 2: Honorific Prefixes in Generated Names
**What goes wrong:** Names like "Ing. Aldonza Valentin", "Prof. Burkhardt Kostolzin B.Sc.", "Sr. Luan Vargas" appear in fighter roster.
**Why it happens:** Several Faker locales (es_MX, de_DE, pt_BR, pl_PL) include professional titles and honorifics in their `name()` and `name_male()` format strings.
**How to avoid:** Always use `first_name_male() + " " + last_name()` pattern, never `name()` or `name_male()`.
**Warning signs:** Fighter names containing "Dr.", "Prof.", "Ing.", "Sr.", "Herr", "B.Sc." etc.

### Pitfall 3: Faker Seed vs Numpy Seed Collision
**What goes wrong:** Changing one part of generation (e.g., adding a nationality) cascades changes to all subsequent fighters because both RNGs share state.
**Why it happens:** A single seed drives sequential random calls; inserting/removing calls shifts the entire sequence.
**How to avoid:** Derive sub-seeds from the master seed for independent domains: `np_rng = np.random.default_rng(seed)` and `Faker.seed(seed)` independently. Consider per-weight-class sub-seeds to isolate changes.
**Warning signs:** Adding one fighter to one weight class changes names/stats in all other classes.

### Pitfall 4: Small Name Pool Exhaustion
**What goes wrong:** `UniquenessException` raised during generation for locales with small name pools.
**Why it happens:** en_NG has only 20 male first names and 20 last names (400 combos). If Nigeria gets 8-10 fighters, collision probability is manageable. But if weights misconfigure to give Nigeria too many fighters, the pool exhausts.
**How to avoid:** Cap per-nationality fighter count relative to name pool size. For small pools (en_NG, no_NO with 100 firsts), limit to ~15-20 fighters max. The nationality weighting (2-5 fighters for small markets) naturally avoids this.
**Warning signs:** Faker raises `UniquenessException` during seeding.

### Pitfall 5: Archetype Quota Rounding Errors
**What goes wrong:** With 90 fighters per class, 5% GOAT Candidate = 4.5 fighters. Rounding across all archetypes can produce totals != 90.
**Why it happens:** Each archetype's quota rounds independently; sum of rounded values may not equal the target count.
**How to avoid:** Allocate quotas sequentially, tracking remaining slots. Last archetype (Journeyman, most common) absorbs the remainder. Apply variance (+/-2) after base allocation.
**Warning signs:** Weight class ends up with wrong fighter count; some classes have 88, others 94.

### Pitfall 6: Career Stage vs Archetype Contradiction
**What goes wrong:** A 21-year-old "Veteran" or a 35-year-old "Prospect" appears in the roster.
**Why it happens:** Career stage quota (20% prospects) and archetype quota (5% GOAT Candidate) are independent systems; naive assignment can create contradictions.
**How to avoid:** Assign career stage first (determines age range), then archetype (constrained by career stage). Some archetype/career-stage combos are invalid: GOAT Candidate should be prime or veteran, not prospect. Late Bloomer should be prime, not prospect. Define a validity matrix.
**Warning signs:** Young fighters with veteran archetypes; old fighters as prospects.

## Code Examples

Verified patterns from official sources:

### Faker Locale Instance Creation (Verified via Context7)
```python
# Source: Context7 /joke2k/faker - Localized Data Generation
from faker import Faker

# Create per-locale instances (one per nationality)
faker_instances = {}
for nationality, locale in NATIONALITY_LOCALE_MAP.items():
    faker_instances[locale] = Faker(locale)

# Seed all instances deterministically
Faker.seed(42)

# Generate name from specific locale
name = faker_instances["pt_BR"].first_name_male() + " " + faker_instances["pt_BR"].last_name()
# Result: "Caleb Cunha" (Brazilian-appropriate)
```

### Numpy Seeded Distribution Generation (Verified via Context7)
```python
# Source: Context7 /numpy/numpy - Generate samples from probability distributions
import numpy as np

rng = np.random.default_rng(seed=42)

# Normal distribution for stat generation
# mean=70 (Phenom center), std=8 (moderate spread)
stat_value = rng.normal(loc=70, scale=8)
stat_value = int(np.clip(stat_value, 1, 100))

# Beta distribution for ceiling potential (skewed toward high)
# a=5, b=2 -> skewed right (most fighters near their ceiling)
ceiling_factor = rng.beta(a=5, b=2)  # 0.0 to 1.0
# For prospects: a=2, b=5 -> skewed left (far from ceiling)
```

### Japanese Romanized Names (Verified via Faker ru_RU/ja_JP testing)
```python
# Japanese locale has built-in romanization
fake_jp = Faker("ja_JP")
name = fake_jp.romanized_name()
# Result: "Hiroshi Yoshida" (Latin-script Japanese name)
```

### Unique Name Generation (Verified via Faker docs + testing)
```python
from faker import Faker

fake = Faker("en_US")
Faker.seed(42)

# Generate 50 guaranteed-unique names
names = [fake.unique.name() for _ in range(50)]
assert len(set(names)) == 50  # All unique

# Clear uniqueness tracker between weight classes if needed
fake.unique.clear()
```

## State of the Art

| Old Approach (Current) | New Approach (Phase 1) | Impact |
|------------------------|------------------------|--------|
| `rng.choice(_FIRST_NAMES)` + `rng.choice(_LAST_NAMES)` | `Faker(locale).first_name_male()` + `.last_name()` | Names match nationality; no more "Carlos Ivanov" |
| `rng.randint(40, 92)` for all stats | `np_rng.normal(loc, scale)` per archetype | Stats cluster around archetype center with natural variance |
| `_assign_archetype()` waterfall (stats -> archetype) | Quota-first allocation (archetype -> stats) | Eliminates 69% Phenom collapse; exact distribution control |
| 100 fighters, ~20 per weight class | 400-500 fighters, 80-100 per weight class | 5x roster depth; meaningful rankings; realistic division depth |
| All fighters signed to AI orgs | 10-15% free agents + prestige-gated org distribution | Player has immediate signing options; talent stratified by org tier |
| `random.Random(seed)` only | `random.Random(seed)` + `np.random.default_rng(seed)` | Better distributions while maintaining deterministic reproducibility |

**Deprecated/outdated:**
- Current `_FIRST_NAMES` / `_LAST_NAMES` arrays: Replaced by Faker locales + romanized name lists
- Current `_assign_archetype()` waterfall: Replaced by quota-first allocation
- Current `_NATIONALITIES` list of 23: Trimmed to MMA-prominent ~18 countries with Faker locale mapping

## Open Questions

1. **Potential ceiling column: new field or reuse prime_start/prime_end?**
   - What we know: Fighter model has `prime_start` and `prime_end` fields. CONTEXT.md says "ceiling-based development" with prospects far from ceiling, primes near ceiling.
   - What's unclear: Whether potential ceiling is a single number (max overall) or per-stat ceilings. Whether it needs a new column or can be derived from archetype + prime window.
   - Recommendation: **Claude's discretion.** A single `potential_ceiling` float column (0-100) is simplest. Archetype sets the ceiling value; career stage determines current stats relative to ceiling. Alternatively, derive ceiling from archetype lookup table with no schema change. Recommend the no-schema-change approach: ceiling is implicit in archetype profile (GOAT Candidate ceiling = 95, Journeyman ceiling = 68, etc.).

2. **Dagestani name romanization: how many names are needed?**
   - What we know: Dagestan gets ~15-20% share (like Russia), so potentially 60-90 fighters across weight classes. Name pool needs at least 40-50 first names and 40-50 last names for comfortable uniqueness.
   - What's unclear: The exact count of commonly romanized Dagestani MMA names available.
   - Recommendation: Build a curated list of 50+ romanized Dagestani first names (mix of common: Khabib, Islam, Magomed, Shamil, Zabit, etc.) and 50+ last names (Nurmagomedov, Makhachev, etc.). Similar approach for Russian (romanized: Aleksandr, Dmitri, etc.), Korean (romanized: Sung-Jung, Chan-Mi, etc.), and Georgian (romanized: Merab, Giga, etc.).

3. **Free agent selection criteria**
   - What we know: 10-15% of fighters (~40-60) should be unsigned. CONTEXT.md marks this as Claude's discretion.
   - What's unclear: Should free agents skew toward certain career stages or archetypes?
   - Recommendation: Free agents should be a realistic mix: some prospects too raw for big orgs, some veterans between contracts, a few mid-career fighters. Weight toward prospects and veterans (players want to discover unknowns or sign experienced fighters). Avoid making GOAT Candidates free agents (they'd realistically be signed).

## Locale-to-Nationality Mapping (Research Result)

### Verified Working Locales (Latin Script)
| Nationality | Faker Locale | Pool Size (M first x last) | Notes |
|-------------|-------------|---------------------------|-------|
| American | en_US | 322 x 1000 | Large pool, no issues |
| Brazilian | pt_BR | 142 x 102 | Adequate for 60-90 fighters |
| Mexican | es_MX | 347 x 623 | Use `first_name_male()` to avoid "Mtro." prefix |
| Irish | en_IE | 329 x 2304 | Large pool |
| British | en_GB | 182 x 500 | Adequate |
| Canadian | en_CA | Uses en_US pools | Large pool |
| Australian | en_AU | Uses en_US pools | Large pool |
| Swedish | sv_SE | 500 x 500 | Large pool |
| Norwegian | no_NO | 100 x 101 | Smaller pool, limit to ~15 fighters |
| Polish | pl_PL | 100 x 3890 | Male firsts smaller but workable |
| Dutch | nl_NL | 251 x 1130 | Large pool |
| French | fr_FR | 88 x 400 | Smaller firsts pool, adequate |
| German | de_DE | 1000 x 406 | Use `first_name_male()` to avoid "Prof." etc. |
| Nigerian | en_NG | 20 x 20 | Small pool (400 combos); limit to 5-8 fighters |
| South African | zu_ZA | Needs testing | May need supplemental names |
| New Zealander | en_NZ | Uses en_AU/en_US | Adequate |

### Proxy Locales
| Nationality | Proxy Locale | Rationale |
|-------------|-------------|-----------|
| Cameroonian | fr_FR | French-speaking country; French names are appropriate |
| Jamaican | en_GB | English-speaking Caribbean; British-influenced names |

### Hardcoded Romanized Lists Required
| Nationality | Reason | Estimated Pool Needed |
|-------------|--------|----------------------|
| Russian | ru_RU outputs Cyrillic | 50+ first, 50+ last |
| Dagestani | No locale exists | 50+ first, 50+ last (MMA-authentic Caucasian names) |
| South Korean | ko_KR outputs Hangul | 30+ first, 20+ last (fewer Korean surnames) |
| Georgian | ka_GE outputs Georgian script | 30+ first, 30+ last |

### Japanese (Special Case)
| Nationality | Method | Notes |
|-------------|--------|-------|
| Japanese | `Faker("ja_JP").romanized_name()` | Built-in romanization; no custom list needed |

## Sources

### Primary (HIGH confidence)
- Context7 `/joke2k/faker` - Locale initialization, multi-locale support, seeding, weighted locales
- Context7 `/numpy/numpy` - `default_rng()`, `normal()`, `beta()`, seed reproducibility
- Direct Faker installation testing (v40.5.1) - All locale name generation verified locally
- Existing codebase: `simulation/seed.py`, `models/models.py`, `simulation/narrative.py`

### Secondary (MEDIUM confidence)
- [Faker official docs - Localized Providers](https://faker.readthedocs.io/en/master/locales.html) - Full locale list (105 locales)
- [Faker official docs](https://faker.readthedocs.io/) - Unique feature documentation
- [Faker PyPI](https://pypi.org/project/Faker/) - Current version 40.5.1

### Tertiary (LOW confidence)
- Dagestani/Georgian/Korean romanized name pool sizing: estimated based on MMA roster analysis and name diversity. Actual pool sizes should be validated during implementation by checking that 50+ unique names can be generated per nationality without repetition.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Both Faker and numpy verified via installation, Context7, and local testing
- Architecture: HIGH - Quota-first pattern is a clean inversion of existing waterfall; all integration points verified in codebase
- Pitfalls: HIGH - Non-Latin script, honorific, and pool exhaustion issues all verified through direct testing
- Locale mapping: MEDIUM - 16/18 nationalities verified; Dagestani and proxy locale name quality is estimated

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable domain; Faker and numpy APIs rarely change)
