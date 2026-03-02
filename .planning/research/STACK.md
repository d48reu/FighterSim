# Stack Research

**Domain:** Procedural world generation / character backstory systems for MMA management simulation
**Researched:** 2026-03-01
**Confidence:** HIGH

## Context

FighterSim is an existing Python/Flask/SQLAlchemy/SQLite MMA management simulator with 11K lines of production code, 100 fighters across 5 weight classes, and a working narrative engine (`simulation/narrative.py`) that uses hardcoded Python dicts and `str.format()` for bio generation. The world-building milestone needs to scale to 400-500 fighters with pre-generated fight histories, rich backstories, player origin stories, and personality systems -- all without introducing external API dependencies or breaking the simulation/ decoupling constraint.

**Constraint:** The simulation/ directory must have ZERO Flask dependencies. All new generation code belongs in simulation/.

## Recommended Stack

### Core Technologies (Already In Place -- Do Not Change)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python 3 | 3.10+ | Runtime | Already in use; `random.choices()` with weights is the core procedural tool |
| Flask | >=3.0 | Web framework | Already in use; thin controller layer only |
| SQLAlchemy | >=2.0 | ORM / bulk operations | Already in use; provides bulk insert via Core for 400-500 fighter seeding |
| SQLite | 3 | Database | Already in use; 500 fighters with history is well within SQLite's comfort zone |

### New Dependencies for World-Building

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Faker | >=40.0 | Nationality-authentic name generation | 80+ locales including pt_BR, ru_RU, ja_JP, ko_KR, ka_GE, sv_SE, no_NO, es_MX, fr_FR, en_IE, en_AU, en_NZ, pl_PL, de_DE, nl_NL, ha_NG, zu_ZA. Maps directly to the 23 nationalities in seed.py. Deterministic with `.seed()`. Production-stable (v40.5.1, actively maintained, requires Python >=3.10). | HIGH |

### Already Available (No pip install needed)

| Technology | Version | Purpose | Why Relevant |
|------------|---------|---------|--------------|
| Jinja2 | 3.1.2 | Template-based backstory generation | Already installed as Flask dependency. Superior to `str.format()` for complex backstory templates with conditionals, loops, and filters. No new dependency. |
| numpy | 2.4.2 | Weighted distributions for attribute generation at scale | Already installed. `numpy.random.Generator` with explicit seed gives reproducible attribute curves (e.g., bell curves for fighter stats by archetype). Better than `random.gauss()` for batch generation of 400-500 fighters. |
| random (stdlib) | builtin | Seeded RNG for all procedural generation | Already the core RNG in seed.py and fight_engine.py. `random.Random(seed)` instances provide deterministic, reproducible generation. |
| json (stdlib) | builtin | Storing structured backstory data, fight history metadata | Already used for narrative_tags and traits in the Fighter model. |

## Installation

```bash
# Single new dependency
pip install "Faker>=40.0"
```

Add to requirements.txt:
```
faker>=40.0
```

That is the only new package. Everything else is already available.

## Architecture Decisions

### 1. Name Generation: Faker (not hardcoded lists)

**Current state:** seed.py has 80 first names and 80 last names in flat Python lists, generating via `rng.choice()`. Nationality is assigned independently of name, so a "Japanese" fighter might be named "Chad Williams."

**Recommendation:** Use Faker with locale-specific providers to generate nationality-authentic names. Map each of the 23 in-game nationalities to a Faker locale:

```python
NATIONALITY_TO_LOCALE = {
    "American": "en_US",
    "Brazilian": "pt_BR",
    "Mexican": "es_MX",
    "Russian": "ru_RU",
    "Irish": "en_IE",
    "British": "en_GB",
    "Canadian": "en_CA",
    "Australian": "en_AU",
    "Swedish": "sv_SE",
    "Norwegian": "no_NO",
    "Japanese": "ja_JP",
    "South Korean": "ko_KR",
    "Georgian": "ka_GE",
    "Dagestani": "ru_RU",  # No Dagestani locale; Russian names are culturally close
    "Polish": "pl_PL",
    "Dutch": "nl_NL",
    "French": "fr_FR",
    "German": "de_DE",
    "Nigerian": "en_NG",   # or ha_NG for Hausa names
    "Cameroonian": "fr_FR", # Francophone Cameroon; no dedicated locale
    "South African": "zu_ZA",
    "New Zealander": "en_NZ",
    "Jamaican": "en_US",   # No Jamaican locale; closest culturally
}
```

**Why Faker over expanding the hardcoded lists:** Scaling to 400-500 fighters with 23 nationalities means you need ~2000+ unique name combinations that sound authentic. Maintaining that as hardcoded lists is a data management nightmare. Faker's locale providers already have hundreds of culturally appropriate names per locale. Deterministic seeding (`Faker.seed_instance(42)`) maintains reproducibility.

**Gaps:** No dedicated locales for Dagestani, Cameroonian, or Jamaican. Use closest cultural proxy (Russian, French, American respectively) and supplement with a small curated override list for common Dagestani names (Khabib-style: Magomed, Makhachev, Nurmagomedov, etc.).

**Confidence:** HIGH -- Faker v40.5.1 confirmed on PyPI, all critical locales verified in official docs.

### 2. Backstory Text Generation: Jinja2 Templates (not Markov chains, not LLMs)

**Current state:** narrative.py uses `str.format()` with hardcoded template strings in Python dicts, selected via `random.choice()`. Works fine for 100 fighters but produces repetitive output at 400-500.

**Recommendation:** Migrate backstory generation to Jinja2 templates stored as Python strings (not files). Jinja2 provides:
- **Conditionals:** `{% if archetype == 'Phenom' %}` for archetype-specific backstory branches
- **Filters:** `{{ age | ordinal }}`, custom filters for narrative variation
- **Macros:** Reusable narrative blocks (training background, career arc, personality reveal)
- **Choice extension:** Custom Jinja2 extension for `{% choice %}` blocks that pick random alternatives

This is a natural evolution of the existing `str.format()` pattern, not a rewrite. The templates stay in Python code (in the simulation/ module), maintaining the zero-Flask-dependency constraint.

**Why not Markov chains (markovify):** Markov chains generate plausible-sounding gibberish. Fighter backstories need to be factually consistent with the fighter's stats, archetype, nationality, and record. A 12-0 Phenom should not get a backstory about "struggling through adversity." Template-based generation with conditionals guarantees coherent output. Markovify (v0.9.4) is also tested only up to Python 3.10 and has not been updated recently.

**Why not Tracery (pytracery):** Tracery is elegant for short procedural text (tweets, one-liners) but pytracery has not been meaningfully updated since ~2016, has open PRs and issues, and uses Travis CI (defunct). For the complexity needed here (multi-paragraph backstories with stat-aware conditionals), Jinja2 is more powerful, better maintained, and already installed.

**Why not LLM generation:** The project constraint is "no external API keys needed -- fully self-contained simulation." LLM-generated backstories would require either an API key or a local model, both of which violate the self-contained constraint and add significant complexity.

**Confidence:** HIGH -- Jinja2 3.1.x is a Flask dependency, confirmed installed, well-documented for programmatic text templating.

### 3. Fight History Simulation: Reuse Existing Fight Engine (not a new system)

**Current state:** The fight engine (`simulation/fight_engine.py`) simulates 30-second tick fights with full results. Seed currently generates win/loss records via `_gen_record()` but no actual Fight objects (no opponents, no methods, no events).

**Recommendation:** Use the existing fight engine to simulate pre-game-start history. During seed:
1. Create historical events for each AI org (monthly, going back 3-5 years)
2. Book fighters into those events using the existing matchmaking logic
3. Run the existing fight engine for each bout (fast -- no UI, no Flask)
4. Store results as real Fight and Event records in the database

This produces a consistent, queryable fight history where every fighter's record is backed by actual simulated bouts with real opponents, methods, and rounds. The fight engine is already Flask-free, so this works entirely within simulation/.

**Performance consideration:** Simulating ~2000-3000 historical fights during seed (5 years of monthly events across 4 orgs). The fight engine runs in-memory with no I/O per tick. Estimated seed time: 10-30 seconds for the full history simulation, well within acceptable "fresh start" time.

**Why not just generate fake records:** A fighter with a 15-3 record but no queryable fight history breaks immersion the moment a player looks at their profile. Pre-simulated history means every win and loss has an opponent, a method, a round, and an event -- the world existed before the player arrived.

**Confidence:** HIGH -- this is reusing existing, tested code in a new context. No new dependencies.

### 4. Attribute Generation at Scale: numpy.random.Generator (not random.gauss)

**Current state:** seed.py generates all fighter attributes as uniform random: `rng.randint(40, 92)`. This produces a flat distribution where every fighter is roughly the same quality.

**Recommendation:** Use `numpy.random.Generator` (already installed as numpy 2.4.2) for archetype-aware attribute distributions:
- **GOAT Candidates:** High mean, low variance (consistently elite)
- **Phenoms:** High mean, medium variance (talented but raw)
- **Gatekeepers:** Medium mean, low variance (solid but limited ceiling)
- **Journeymen:** Low-medium mean, high variance (wild inconsistency)

```python
rng = numpy.random.default_rng(seed=42)
# Example: GOAT Candidate striking
striking = int(rng.normal(loc=82, scale=5).clip(60, 98))
```

numpy's Generator API (introduced in numpy 1.17) provides:
- Explicit seeding for reproducibility
- Normal, beta, and triangular distributions for realistic attribute curves
- Vectorized generation (generate all 500 fighters' stats in one call)
- Better statistical properties than stdlib random

**Why numpy over stdlib random:** For 400-500 fighters, you want statistically meaningful distributions, not just random integers. numpy lets you define archetype-specific distribution curves that produce a realistic talent pyramid (few elites, many average, some busts). The stdlib `random.gauss()` works for individual calls but numpy is already installed and provides batch generation + clipping in one line.

**Confidence:** HIGH -- numpy 2.4.2 confirmed installed, Generator API is stable since numpy 1.17.

### 5. Data Storage: Existing SQLAlchemy Models + Minor Extensions

**Current state:** Fighter model has `narrative_tags` (JSON text), `traits` (JSON text), and basic career fields. No dedicated backstory storage.

**Recommendation:** Add a small number of fields to the Fighter model and potentially one new model:
- `Fighter.backstory` (Text) -- generated backstory paragraph
- `Fighter.personality_type` (String) -- behavioral personality tag
- `Fighter.origin_city` (String) -- city/region of origin (for flavor)
- `Fighter.gym_name` (String) -- training gym name (for narrative coherence)
- New model: `PlayerOrigin` -- stores selectable player background/scenario data

Use `session.bulk_insert_mappings()` or `session.execute(insert(Fighter), data_list)` for efficient bulk seeding of 400-500 fighters. SQLAlchemy Core insert is ~40x faster than individual ORM `session.add()` calls for bulk operations.

**Confidence:** HIGH -- straightforward SQLAlchemy model extension, well-documented patterns.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Name generation | Faker (locale-aware) | Expanded hardcoded lists | Scaling to 400-500 unique nationality-authentic names from hardcoded lists is a maintenance burden; Faker has thousands of names per locale built-in |
| Name generation | Faker | Pynames | Pynames focuses on fantasy/RPG races, not real-world nationalities. Only supports English and Russian. Much smaller library with less community support |
| Backstory text | Jinja2 templates | Markovify (Markov chains) | Markov chains can't guarantee factual consistency with fighter stats. A 15-0 Phenom might get a "comeback from losses" backstory. Templates with conditionals guarantee coherence |
| Backstory text | Jinja2 templates | Tracery (pytracery) | Unmaintained since ~2016, no Python 3.10+ testing, limited to short-form text. Jinja2 handles multi-paragraph conditionals natively |
| Backstory text | Jinja2 templates | LLM API (Claude, GPT) | Violates "no external API keys" constraint. Adds network dependency to a self-contained simulation |
| Fight history | Reuse fight engine | Generate fake W-L records only | Fake records with no queryable opponents/methods break immersion. Real simulated history creates a consistent world |
| Stat distribution | numpy distributions | stdlib random.randint | Uniform distribution produces unrealistic talent pool. numpy gives bell curves, archetype-specific distributions, and batch generation |
| Stat distribution | numpy distributions | scipy.stats | scipy is a heavy dependency (100MB+) for functionality numpy already provides. Don't add it |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Any LLM API for generation | Violates self-contained constraint; adds API key dependency, network dependency, cost, and latency to seed process | Jinja2 templates with conditional logic |
| Tracery / pytracery | Unmaintained since ~2016; no modern Python testing; too limited for multi-paragraph backstories | Jinja2 (already installed) |
| Markovify for backstories | Cannot guarantee factual consistency with fighter data; generates plausible nonsense, not coherent narratives | Jinja2 templates with stat-aware conditionals |
| scipy.stats | 100MB+ dependency for distributions numpy already handles | numpy.random.Generator |
| Pandas for data manipulation | Heavy dependency; not needed for this use case; SQLAlchemy + Python dicts are sufficient | SQLAlchemy Core bulk operations |
| External name databases (CSV/JSON files) | Adds file I/O complexity and maintenance burden; Faker's locale providers are better curated | Faker locale providers |
| Procedural generation frameworks (Wave Function Collapse, etc.) | Designed for spatial/grid generation (maps, dungeons), not character/narrative generation | Python stdlib + Faker + Jinja2 |

## Stack Patterns by Variant

**If generating a fresh world (run.py):**
- Use Faker with deterministic seed for all names
- Use numpy.random.Generator for stat distributions
- Run fight engine in batch mode for 3-5 years of history
- Use Jinja2 to generate all backstories in one pass after stats are set
- Bulk insert via SQLAlchemy Core

**If adding fighters to existing world (monthly_sim.py newgen):**
- Same Faker + numpy + Jinja2 pipeline but for individual fighters
- Fight history comes from ongoing simulation, not pre-generation
- Backstory references existing world state (champions, events)

**If player selects origin story (new game setup):**
- PlayerOrigin model stores scenario data
- Scenario affects starting org stats (prestige, bank, roster size)
- No additional library needed -- pure data/logic

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Faker >=40.0 | Python >=3.10 | Faker 40.x dropped Python 3.9 support |
| Jinja2 3.1.x | Flask >=3.0 | Already a Flask dependency; no version conflict possible |
| numpy 2.4.x | Python >=3.10 | Already installed; numpy 2.x has breaking changes from 1.x but since it's already working, no issue |
| SQLAlchemy >=2.0 | SQLite 3.x | Already in use; bulk insert methods work with SQLite |

## Sources

- [Faker PyPI](https://pypi.org/project/Faker/) -- version 40.5.1 confirmed, Python >=3.10, production-stable (HIGH confidence)
- [Faker locales documentation](https://faker.readthedocs.io/en/master/locales.html) -- all critical locales verified (HIGH confidence)
- [Faker person provider docs](https://faker.readthedocs.io/en/master/providers/faker.providers.person.html) -- 18 name generation methods confirmed (HIGH confidence)
- [markovify GitHub](https://github.com/jsvine/markovify) -- v0.9.4, tested Python 3.7-3.10 only (MEDIUM confidence on Python 3.12+ compat)
- [pytracery GitHub](https://github.com/aparrish/pytracery) -- last meaningful update ~2016, unmaintained (HIGH confidence it should be avoided)
- [Jinja2 template docs](https://jinja.palletsprojects.com/en/stable/templates/) -- 3.1.x, confirmed installed as Flask dependency (HIGH confidence)
- [numpy.random.Generator docs](https://numpy.org/doc/stable/reference/random/generated/numpy.random.choice.html) -- 2.4.x confirmed installed (HIGH confidence)
- [SQLAlchemy bulk insert docs](https://docs.sqlalchemy.org/en/20/_modules/examples/performance/bulk_inserts.html) -- Core insert ~40x faster than ORM for bulk ops (HIGH confidence)
- [WMMA5 Grey Dog Software](https://greydogsoftware.com/title/world-of-mixed-martial-arts-5/) -- reference for world-building depth (MEDIUM confidence, design reference only)
- [ZenGM blog on sports sims](https://zengm.com/blog/2019/07/so-you-want-to-write-a-sports-sim-game/) -- general sports sim design advice (MEDIUM confidence)

---
*Stack research for: FighterSim world-building milestone*
*Researched: 2026-03-01*
