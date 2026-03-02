# Phase 3: Fighter Identity - Research

**Researched:** 2026-03-02
**Domain:** Jinja2 templated narrative generation from SQLAlchemy fight data
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Layer on top of existing system: keep `generate_fighter_bio()` f-string templates as the "character sketch" paragraph (personality, archetype, traits, nationality flavor)
- Add a NEW Jinja2-powered paragraph that queries actual Fight rows and references specific opponents, methods, and rounds
- Final bio = character sketch + fight-history paragraph (character first, history second)
- Jinja2 templates defined inline in narrative.py as Python string constants (consistent with existing pattern)
- Generated on-the-fly when `get_fighter_bio()` is called -- no new DB columns, always reflects current fight data
- Jinja2 is already installed (used elsewhere in the project)
- Scale with career stage: prospects mention 1 fight (debut or standout win), prime fighters get 2-3 references, veterans get 3-4 key moments
- Specificity level: opponent name + method + round ("knocked out Carlos Silva in the second round") -- not event names, not exact timestamps
- Selective losses referenced: title fight losses, rivalry defeats, and recent skids are fair game. Forgettable early-career losses are skipped
- Rivalry opponents ALWAYS get a dedicated mention when Fighter.rivalry_with is set -- guaranteed payoff for Phase 2's rivalry seeding
- Separate "Career Highlights" section below the bio on the fighter profile -- not woven into bio text
- Curated extraction criteria: title fights (win or loss), KO/sub wins against higher-ranked opponents, upset victories, 3+ win streaks, rivalry fights, debut win
- Capped at 5-6 highlights per fighter regardless of career length
- Mini-narrative format per line (e.g. "Stunned the division with a first-round knockout of Marco Santos at UCC 32")
- New API endpoint needed to serve highlights separately from bio
- Frontend needs a new section in the fighter detail panel
- Moderate variation between archetypes: same sentence structures, different word choices and framing
- Career stage affects narrative STRUCTURE, not just word choice (prospects: forward-looking; prime: present-tense dominance; veterans: retrospective framing)
- Champion overlay: current champions get "defends the crown" language; former champions get "once held the belt" gravitas
- Match existing MMA journalist voice: measured, analytical, specific, never hype

### Claude's Discretion
- Exact Jinja2 template wording and number of template variants per archetype/stage combination
- How highlights are ranked/prioritized when more than 5-6 qualify
- How to handle fighters with very few fights (1-2) -- may produce minimal or no history paragraph
- Query optimization for pulling fight data (single query vs. multiple)
- Highlight sorting order (chronological vs. significance-based)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IDEN-01 | Fighters have composable backstories built from Jinja2 templates that reference actual fight history | Jinja2 `Environment.from_string()` pattern for inline templates; fight query pattern from `get_fighter_timeline()`; career context from `_get_career_context()` for stage/archetype gating; template architecture with archetype x stage matrix |
| IDEN-02 | Career highlights are auto-extracted from fabricated fight history (notable KOs, upsets, streaks) | Fight model has all needed fields (winner_id, method, round_ended, is_title_fight, card_position); extraction criteria mapped to SQL queries; new API endpoint + frontend section pattern established |
</phase_requirements>

## Summary

Phase 3 adds two narrative features on top of the existing bio system: (1) a Jinja2-powered fight-history paragraph appended to the character sketch bio, and (2) a separate career highlights extraction system. Both consume Fight rows created by Phase 2's `fabricate_history()` pipeline.

The technical challenge is moderate. Jinja2 3.1.2 is already installed as a Flask dependency but is not yet imported anywhere in the simulation layer. The `Environment.from_string()` API is the correct tool for inline string templates. The existing `_get_career_context()` function provides the stage/archetype routing needed for template selection. The Fight model already stores all required data fields (opponent IDs, method, round, is_title_fight). The main query pattern exists in `get_fighter_timeline()` and can be adapted.

The content authoring task (writing 20-40 Jinja2 template fragments across archetype/stage combinations) is the largest effort item. The code architecture is straightforward -- the research below documents the exact patterns, queries, and integration points.

**Primary recommendation:** Use `jinja2.Environment.from_string()` with a module-level Environment instance. Keep templates as Python string constants in narrative.py. Query fight data with a single eager-loaded query per fighter. Route template selection through the existing `_get_career_context()` output.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.2 | Template rendering for fight-history paragraphs and highlight narratives | Already installed (Flask dependency). `from_string()` API is the documented approach for programmatic string templates. Superior to f-strings for conditional blocks and loops within narrative text |
| SQLAlchemy | 2.0+ | Query Fight rows for a fighter's history | Already the ORM in use. Existing query pattern in `get_fighter_timeline()` provides the blueprint |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Flask | 3.0+ | New `/api/fighters/{id}/highlights` endpoint | Already the web framework. Follow existing endpoint pattern from `/api/fighters/{id}/bio` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 `from_string()` | Python f-strings (existing pattern) | f-strings cannot do conditional blocks or loops within the string. Fight-history paragraphs need `{% if %}` and `{% for %}` constructs for variable-length fight references. Jinja2 is the correct upgrade |
| Jinja2 `from_string()` | Jinja2 file-based templates | File templates add filesystem I/O and a template directory. Inline string constants are consistent with narrative.py's existing pattern of storing template text as Python data |
| Single query per fighter | Multiple queries (one per highlight type) | Single query is simpler and faster. All fight data for one fighter fits easily in memory |

**Installation:**
```bash
# No new dependencies needed. Jinja2 is already installed as a Flask dependency.
pip install -r requirements.txt  # Confirms existing stack
```

## Architecture Patterns

### Recommended Changes to Existing Structure
```
simulation/
  narrative.py            # MODIFIED: Add fight-history templates, Jinja2 Environment,
                          #   generate_fight_history_paragraph(), extract_career_highlights()
api/
  services.py             # MODIFIED: Update get_fighter_bio() to append history paragraph,
                          #   add get_fighter_highlights()
  app.py                  # MODIFIED: Add /api/fighters/{id}/highlights endpoint
frontend/
  static/js/app.js        # MODIFIED: Fetch highlights in Promise.all, render new section
  templates/index.html     # MODIFIED: Add Career Highlights section to fighter detail panel
  static/css/style.css     # MODIFIED: Style for highlights list
```

### Pattern 1: Jinja2 Environment with `from_string()`
**What:** Create a module-level `jinja2.Environment()` in narrative.py. Compile templates once using `env.from_string()`. Render with fighter-specific context dicts.
**When to use:** For all fight-history paragraph rendering and highlight mini-narratives.
**Example:**
```python
# Source: https://jinja.palletsprojects.com/en/stable/api — Environment.from_string()
from jinja2 import Environment

_jinja_env = Environment()

# Define templates as Python string constants
_HISTORY_PROSPECT = _jinja_env.from_string(
    "{% if debut_win %}"
    "{{ name }} made a statement in the professional debut, "
    "{{ debut_win.method_text }} {{ debut_win.opponent }} "
    "in the {{ debut_win.round_text }}."
    "{% endif %}"
)

# Render at call time
paragraph = _HISTORY_PROSPECT.render(name=fighter.name, debut_win=debut_data)
```

### Pattern 2: Fight Data Query (single query, structured extraction)
**What:** Query all Fight rows for a fighter in one pass, then extract highlights and history references from the result set in Python.
**When to use:** When `get_fighter_bio()` or `get_fighter_highlights()` is called.
**Example:**
```python
# Adapted from existing get_fighter_timeline() in services.py (line 522)
from sqlalchemy import select, or_

fights = session.execute(
    select(Fight, Event)
    .join(Event, Fight.event_id == Event.id)
    .where(
        or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
        Fight.winner_id.isnot(None),
    )
    .order_by(Event.event_date.asc())
).all()
```

### Pattern 3: Template Selection via Career Context (reuse existing `_get_career_context()`)
**What:** Use the existing career context dict (career_stage, archetype, trajectory, tags) to select which Jinja2 template to render for the fight-history paragraph. Same routing logic as `_select_templates()` but for history templates.
**When to use:** When generating the fight-history paragraph.
**Example:**
```python
ctx = _get_career_context(fighter)

# Route to the right template set
if ctx["career_stage"] == "prospect":
    template = _HISTORY_PROSPECT
elif ctx["career_stage"] in ("developing", "established"):
    template = _HISTORY_TEMPLATES[ctx["archetype"]]  # archetype-specific for prime
else:  # veteran, elder
    template = _HISTORY_VETERAN
```

### Pattern 4: Highlight Extraction with Scoring
**What:** Score each fight against criteria (title fight, KO/sub vs higher-ranked, upset, streak, rivalry, debut), then take top 5-6 by score.
**When to use:** For the career highlights extraction.
**Example:**
```python
def _score_fight_for_highlight(fight_data: dict) -> int:
    """Score a fight for highlight significance. Higher = more notable."""
    score = 0
    if fight_data["is_title_fight"]:
        score += 100  # Title fights always qualify
    if fight_data["is_ko_sub"] and fight_data["opponent_was_higher_ranked"]:
        score += 80
    if fight_data["is_upset"]:
        score += 70
    if fight_data["is_rivalry_fight"]:
        score += 60
    if fight_data["extends_streak_to"] >= 3:
        score += 50
    if fight_data["is_debut"] and fight_data["won"]:
        score += 30
    return score

# Take top 5-6
highlights = sorted(scored_fights, key=lambda x: x["score"], reverse=True)[:6]
```

### Pattern 5: Layered Bio Composition in services.py
**What:** Enhance `get_fighter_bio()` to append the fight-history paragraph after the existing character sketch. The character sketch generation is untouched.
**When to use:** In `get_fighter_bio()` call chain.
**Example:**
```python
def get_fighter_bio(fighter_id: int) -> Optional[str]:
    with _SessionFactory() as session:
        f = session.get(Fighter, fighter_id)
        if not f:
            return None
        # Existing character sketch (UNTOUCHED)
        character_sketch = generate_fighter_bio(f)
        # NEW: fight-history paragraph (needs session for Fight queries)
        history_paragraph = generate_fight_history_paragraph(f, session)
        if history_paragraph:
            return character_sketch + "\n\n" + history_paragraph
        return character_sketch
```

### Anti-Patterns to Avoid
- **Storing generated bios in the database:** Decision is explicit: generate on-the-fly, no new DB columns. Always reflects current fight data including fights that happen after game start.
- **Mixing fight-history references into character sketch templates:** The two paragraphs are separate concerns. Character sketch = personality/archetype. History paragraph = specific fights. Mixing them makes both harder to maintain.
- **Querying fights inside the Jinja2 template:** Templates receive pre-queried data. Database queries happen in Python before rendering. Templates are pure formatting.
- **Using `random.choice()` at render time for template selection:** This was the existing f-string pattern. For Jinja2 templates, pre-compile templates at module load time and select deterministically based on fighter context. Use the `|random` filter only for word-level variation within a template, not for template selection.
- **Loading Jinja2 templates from files:** Decision is explicit: inline Python string constants, consistent with existing pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template rendering with conditionals/loops | Custom string interpolation with nested f-strings | `jinja2.Environment.from_string()` | Jinja2 handles conditional blocks, loops, filters, and escaping. Nested f-strings with conditionals become unreadable and unmaintainable |
| Method name humanization ("KO/TKO" -> "knocked out") | Inline if/elif chains in every template | Jinja2 custom filter or a lookup dict passed as context | Method humanization appears in both bio paragraphs and highlights. Centralize it once |
| Round number to ordinal ("1" -> "first") | Repeated if/else blocks | A small helper function or dict (`{1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}`) | Used in both bio and highlights. Five rounds max in MMA |
| Win streak detection | Re-scanning fight history | Compute during the single fight query pass | The fight query already returns chronological results. Track running streak as you iterate |

**Key insight:** The fight-history paragraph and the highlights system both consume the same underlying fight data query. Compute both from a single pass over the fighter's fight list. Don't query twice.

## Common Pitfalls

### Pitfall 1: Session Scope for Fight Queries
**What goes wrong:** `generate_fighter_bio()` currently takes a Fighter object with no session. Fight-history paragraph needs to query Fight rows, which requires an active session.
**Why it happens:** The existing bio function was designed as stateless (reads from loaded Fighter model attributes). Fight-history breaks that contract.
**How to avoid:** The integration point is in `get_fighter_bio()` in services.py (line 431), which already has a session context (`with _SessionFactory() as session`). Pass the session to the new `generate_fight_history_paragraph()` function. Keep `generate_fighter_bio()` signature unchanged.
**Warning signs:** `DetachedInstanceError` when trying to access relationships on a Fighter loaded in a different session.

### Pitfall 2: N+1 Query for Opponent Names
**What goes wrong:** For each fight, looking up the opponent name with a separate `session.get(Fighter, opponent_id)` query. With 15-25 fights per veteran, this is 15-25 extra queries.
**Why it happens:** The existing `get_fighter_timeline()` does exactly this (line 546: `opponent = session.get(Fighter, opponent_id)`).
**How to avoid:** Pre-load all opponent names in a single query. Collect opponent IDs from the fight list, then batch-fetch: `session.execute(select(Fighter.id, Fighter.name).where(Fighter.id.in_(opponent_ids)))`.
**Warning signs:** Slow bio loading on fighters with many fights.

### Pitfall 3: Empty Fight History for New-Game Fighters
**What goes wrong:** Fighters signed after game start (free agents, reality show graduates) have zero Fight rows. The fight-history paragraph must gracefully return empty string.
**Why it happens:** Only pre-seed fighters have fabricated history. Post-seed fighters build history through gameplay.
**How to avoid:** Check fight count before attempting template rendering. Return `""` (empty string) for fighters with 0-1 completed fights. The character sketch paragraph handles these fighters already.
**Warning signs:** Blank or broken paragraphs appearing in fighter bios.

### Pitfall 4: Rivalry Mention When Rival Has No Shared Fights
**What goes wrong:** `Fighter.rivalry_with` may be set by reality show shenanigans (monthly_sim.py line 579-582) even when the pair has never actually fought. The bio paragraph references a rivalry fight that doesn't exist.
**Why it happens:** Two code paths set `rivalry_with`: `update_rivalries()` (requires 2+ actual fights) and reality show shenanigans (sets rivalry without fights).
**How to avoid:** When checking for rivalry mentions, verify that shared fights actually exist in the Fight table before referencing specific bouts. If rivalry_with is set but no shared fights exist, mention the rivalry itself without citing a specific fight.
**Warning signs:** Bio paragraph references "the rivalry fight" that never happened.

### Pitfall 5: Template Content Volume Underestimation
**What goes wrong:** STATE.md flags this: "Template content volume for Phase 3 (50-100 fragments) is a writing task beyond code work." Writing too few template variants makes all bios sound the same.
**Why it happens:** Focus on code architecture, underinvestment in template diversity.
**How to avoid:** The moderate variation approach (CONTEXT.md decision) reduces scope: same sentence structures, different word choices per archetype. Target 3-4 templates per archetype x career-stage combination, with word-level variation via Jinja2 `|random` filter. This yields ~20-30 templates total, not 50-100.
**Warning signs:** Reading 5 fighter bios from the same archetype and they all sound identical.

### Pitfall 6: Highlight Event Name Reference
**What goes wrong:** CONTEXT.md highlight format includes event names ("Stunned the division with a first-round knockout of Marco Santos at UCC 32"). If the event name is not joined in the query, it requires an extra query.
**Why it happens:** Fight model has `event_id` but not the event name directly.
**How to avoid:** The fight query already joins Event (pattern from `get_fighter_timeline()`). Include `event.name` in the extracted data so highlights can reference it.
**Warning signs:** Highlights missing event context, or extra queries per highlight.

## Code Examples

Verified patterns from the existing codebase:

### Fight Query Pattern (from services.py:530)
```python
# Source: /home/d48reu/FighterSim/api/services.py line 530
fights = session.execute(
    select(Fight, Event)
    .join(Event, Fight.event_id == Event.id)
    .where(
        or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
        Fight.winner_id.isnot(None),
    )
    .order_by(Event.event_date.asc(), Fight.id.asc())
).all()
```

### Career Context Reuse (from narrative.py:1048)
```python
# Source: /home/d48reu/FighterSim/simulation/narrative.py line 1048
ctx = _get_career_context(fighter)
# Returns: career_fights, career_stage, trajectory, displayed_archetype,
#          archetype, significant_tag, streak, win_rate, past_prime, tags
```

### Existing Bio Generation (from narrative.py:1377)
```python
# Source: /home/d48reu/FighterSim/simulation/narrative.py line 1377
def generate_fighter_bio(fighter: Fighter) -> str:
    ctx = _get_career_context(fighter)
    templates = _select_templates(fighter, ctx)
    template = random.choice(templates)
    bio = template.format(**fmt)
    # ... validation, nationality, traits, confidence ...
    return bio
```

### API Endpoint Pattern (from app.py:238)
```python
# Source: /home/d48reu/FighterSim/api/app.py line 238
@app.route("/api/fighters/<int:fighter_id>/bio")
def fighter_bio(fighter_id: int):
    bio = services.get_fighter_bio(fighter_id)
    if bio is None:
        return jsonify({"error": "Fighter not found"}), 404
    return jsonify({"bio": bio})
```

### Frontend Fetch Pattern (from app.js:268)
```javascript
// Source: /home/d48reu/FighterSim/frontend/static/js/app.js line 268
const [fighter, bioData, tagsData] = await Promise.all([
    api(`/api/fighters/${fighterId}`),
    api(`/api/fighters/${fighterId}/bio`),
    api(`/api/fighters/${fighterId}/tags`),
]);
// Add highlights fetch to this Promise.all array
```

### Frontend Panel Structure (from index.html:740)
```html
<!-- Source: /home/d48reu/FighterSim/frontend/templates/index.html line 740 -->
<div class="panel-bio-section">
    <div class="panel-bio-label">Fighter Profile</div>
    <div id="panel-bio" class="panel-bio">&mdash;</div>
</div>
<!-- Career Highlights section would be inserted after this -->
```

### Jinja2 from_string() API (from Context7 / official docs)
```python
# Source: https://jinja.palletsprojects.com/en/stable/api — Environment.from_string()
from jinja2 import Environment

env = Environment()
template = env.from_string("Hello {{ name }}! {% if wins > 10 %}Veteran.{% endif %}")
result = template.render(name="Silva", wins=15)
# Result: "Hello Silva! Veteran."
```

### Jinja2 Random Filter (from Context7 / official docs)
```python
# Source: https://jinja.palletsprojects.com/en/stable/templates — random filter
# Use for word-level variation within a single template
template_str = "{{ name }} {{ ['destroyed', 'finished', 'stopped']|random }} {{ opponent }}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| f-string templates with `str.format()` | Jinja2 `from_string()` for complex narrative | Phase 3 introduces this | f-strings stay for character sketch (simple variable substitution). Jinja2 adds conditionals and loops needed for variable-length fight references |
| Stateless bio generation (no DB queries) | Session-aware history paragraph (queries Fight rows) | Phase 3 introduces this | `generate_fighter_bio()` remains stateless. New `generate_fight_history_paragraph()` takes a session. Integration happens in services.py |
| Bio = single paragraph | Bio = character sketch + fight-history paragraph | Phase 3 introduces this | Two-paragraph structure separated by newline. Each paragraph maintained independently |

**Deprecated/outdated:**
- Nothing in the existing stack is deprecated. Jinja2 3.1.2 is current and stable. SQLAlchemy 2.0+ query patterns are current.

## Open Questions

1. **How to detect "current champion" at query time**
   - What we know: Champions are tracked during `fabricate_history()` via in-memory `champion_state` dict, and during gameplay via the rankings system (rank 1). There is no explicit `is_champion` column on Fighter.
   - What's unclear: Whether the champion overlay language ("defends the crown") should check rankings (rank 1 = champion) or scan title fight history (most recent title fight winner in the weight class).
   - Recommendation: Check `Ranking` table for rank 1 in the fighter's weight class. This is the runtime source of truth and works for both fabricated history and live gameplay. Fall back to "former champion" language if the fighter has any title fight wins but is not currently rank 1.

2. **Highlight sorting: chronological vs. significance**
   - What we know: User left this to Claude's discretion. Both approaches have merit.
   - Recommendation: Significance-based (highest score first). Fighters with long careers would have their best moments buried at the end in chronological order. The highlight section is a "greatest hits" list, not a timeline -- the Career Timeline section already provides chronological ordering.

3. **Fighters with 1-2 fights: minimal or no history paragraph**
   - What we know: User acknowledges this may produce minimal content. The character sketch already handles prospects well.
   - Recommendation: 0 completed fights = no history paragraph. 1 fight = single-sentence debut reference only if it was a win. 2 fights = short paragraph. 3+ fights = full template rendering.

## Architectural Recommendations (Claude's Discretion Items)

### Template Variant Count
Recommend 3 templates per archetype (6 archetypes) x 3 broad career stages (prospect, prime, veteran) = up to 54 slots, but with heavy reuse:
- **Prospect stage:** 3 templates shared across all archetypes (prospects don't have enough history to differentiate)
- **Prime stage:** 3 templates per archetype = 18 templates
- **Veteran stage:** 3 templates per archetype = 18 templates
- **Champion overlay:** 2 sentence fragments (current champion, former champion) applied on top
- **Rivalry insert:** 2 sentence fragments injected when rivalry_with is set
- **Total:** ~25-30 distinct template strings + 4 overlay fragments

### Query Optimization
Single query approach:
1. Query all Fight + Event rows for the fighter (joined) in chronological order
2. Batch-fetch all opponent Fighter names in one IN() query
3. Process the result list once: compute running streak, detect title fights, identify rivalry fights, score for highlights
4. Pass structured data dicts to both the history paragraph template and the highlights extractor

### Highlight Prioritization (when > 6 qualify)
Score-based priority with tiebreaker by recency:
1. Title fight win (score: 100)
2. Title fight loss (score: 90)
3. KO/Sub finish of higher-ranked opponent (score: 80)
4. Upset victory (won despite lower overall) (score: 70)
5. Rivalry fight (score: 60)
6. Extends win streak to 3+ (score: 50)
7. Debut win (score: 30)

Tiebreaker: more recent fight wins. Cap at 6 highlights.

## Sources

### Primary (HIGH confidence)
- Jinja2 official docs via Context7 (`/websites/jinja_palletsprojects_en_stable`) -- `Environment.from_string()`, template conditionals/loops, `|random` filter
- Codebase inspection: `narrative.py` (1442 lines) -- existing bio generation, `_get_career_context()`, `_select_templates()`, `_validate_bio()`
- Codebase inspection: `services.py` line 431 -- `get_fighter_bio()`, line 522 -- `get_fighter_timeline()` fight query pattern
- Codebase inspection: `models/models.py` -- Fighter model (rivalry_with, archetype, age, wins/losses), Fight model (winner_id, method, round_ended, is_title_fight, fighter_a_id, fighter_b_id), Event model (name, event_date)
- Codebase inspection: `app.py` line 238 -- `/api/fighters/{id}/bio` endpoint pattern
- Codebase inspection: `frontend/static/js/app.js` line 268 -- Promise.all fetch pattern, line 348 -- bio rendering
- Codebase inspection: `frontend/templates/index.html` line 740 -- bio section HTML structure
- `pip show jinja2` -- confirmed version 3.1.2 installed locally

### Secondary (MEDIUM confidence)
- None needed. All findings verified against installed code and Context7 docs.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Jinja2 3.1.2 confirmed installed, API verified via Context7, no new dependencies
- Architecture: HIGH -- All integration points verified in existing codebase with exact line numbers
- Pitfalls: HIGH -- Session scope, N+1 query, and rivalry edge cases identified from actual code inspection

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable domain, no fast-moving dependencies)
