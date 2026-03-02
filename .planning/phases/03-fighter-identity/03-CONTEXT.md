# Phase 3: Fighter Identity - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate composable backstories and career highlights from actual fight history data. Fighters feel like individuals with stories — their bios reference real fights, opponents, and outcomes from their database history. Career highlights are auto-extracted and displayed separately. The existing bio system (character sketch) is preserved and layered with new fight-history content.

</domain>

<decisions>
## Implementation Decisions

### Bio composition approach
- Layer on top of existing system: keep `generate_fighter_bio()` f-string templates as the "character sketch" paragraph (personality, archetype, traits, nationality flavor)
- Add a NEW Jinja2-powered paragraph that queries actual Fight rows and references specific opponents, methods, and rounds
- Final bio = character sketch + fight-history paragraph (character first, history second)
- Jinja2 templates defined inline in narrative.py as Python string constants (consistent with existing pattern)
- Generated on-the-fly when `get_fighter_bio()` is called — no new DB columns, always reflects current fight data
- Jinja2 is already installed (used elsewhere in the project)

### Fight reference density
- Scale with career stage: prospects mention 1 fight (debut or standout win), prime fighters get 2-3 references, veterans get 3-4 key moments
- Specificity level: opponent name + method + round ("knocked out Carlos Silva in the second round") — not event names, not exact timestamps
- Selective losses referenced: title fight losses, rivalry defeats, and recent skids are fair game. Forgettable early-career losses are skipped
- Rivalry opponents ALWAYS get a dedicated mention when Fighter.rivalry_with is set — guaranteed payoff for Phase 2's rivalry seeding

### Highlights presentation
- Separate "Career Highlights" section below the bio on the fighter profile — not woven into bio text
- Curated extraction criteria: title fights (win or loss), KO/sub wins against higher-ranked opponents, upset victories, 3+ win streaks, rivalry fights, debut win
- Capped at 5-6 highlights per fighter regardless of career length
- Mini-narrative format per line (e.g. "Stunned the division with a first-round knockout of Marco Santos at UCC 32")
- New API endpoint needed to serve highlights separately from bio
- Frontend needs a new section in the fighter detail panel

### Narrative tone variation
- Moderate variation between archetypes: same sentence structures, different word choices and framing (GOAT Candidate KO = "added to a legacy of dominance"; Journeyman KO = "shocked the division")
- Career stage affects narrative STRUCTURE, not just word choice:
  - Prospects: forward-looking ("the debut win over X showed potential")
  - Prime fighters: present-tense dominance ("is on a tear after finishing Y")
  - Veterans: retrospective framing ("a career defined by the rivalry with Z")
- Champion overlay: current champions get "defends the crown" language; former champions get "once held the belt" gravitas — applied on top of archetype/stage
- Match existing MMA journalist voice: measured, analytical, specific, never hype. Consistent with the character sketch paragraph's tone

### Claude's Discretion
- Exact Jinja2 template wording and number of template variants per archetype/stage combination
- How highlights are ranked/prioritized when more than 5-6 qualify
- How to handle fighters with very few fights (1-2) — may produce minimal or no history paragraph
- Query optimization for pulling fight data (single query vs. multiple)
- Highlight sorting order (chronological vs. significance-based)

</decisions>

<specifics>
## Specific Ideas

- The existing bio voice is excellent — analytical, measured, reads like an MMA journalist who respects the sport. Example: "He reads opponents like he's been in that fight before — because in every important way, he has." The fight-history paragraph should read like the same journalist wrote it
- Narrative quality should scale with fight significance, matching Phase 2's approach: prospect debut < regular bout < rivalry rematch < title fight
- STATE.md flagged that "Template content volume for Phase 3 (50-100 fragments) is a writing task beyond code work" — the moderate variation approach (same structures, different word choices) should keep this manageable

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `generate_fighter_bio()` (narrative.py:1377): Full context-aware bio system — archetype-gated templates, career context calculator, trait sentences, nationality flavor, confidence flavor, validation. ALL preserved as-is
- `_get_career_context()` (narrative.py:1048): Returns career_stage, trajectory, archetype, tags, win_rate, streak — can be reused for fight-history paragraph template selection
- `_select_templates()` (narrative.py:1145): Pattern for context-gated template selection — same approach applies to history templates
- `_validate_bio()` (narrative.py:1352): Bio validation for age/career-inappropriate language — extend for history paragraph
- `Fighter.rivalry_with` field: Set by Phase 2's `update_rivalries()` — query this to guarantee rivalry mentions
- `Fight` model: has fighter_a/b, winner_id, method, round_ended, narrative, is_title_fight, card_position, event_id
- `Event` model: has name, event_date, venue, organization_id
- `get_fighter_bio()` (services.py:431): API wrapper — will need enhancement to also return highlights

### Established Patterns
- Bio generation is stateless: takes Fighter object, returns string. No DB session needed inside (reads from loaded model). Fight-history paragraph will need a session to query Fight rows
- Jinja2 already a dependency (used for narrative templates in Phase 2)
- Frontend fighter detail panel (`frontend/templates/index.html:740-742`) already has bio section with label + content div
- API returns bio via `/api/fighters/{id}/bio` — highlight endpoint would follow same pattern

### Integration Points
- `get_fighter_bio()` in services.py: Add fight-history paragraph generation after existing `generate_fighter_bio()` call
- New API endpoint: `/api/fighters/{id}/highlights` for career highlights list
- Frontend `app.js:268`: Already fetches bio data in `Promise.all` — add highlights fetch there
- Frontend panel: Add new "Career Highlights" section below existing bio section
- `_get_career_context()`: Reuse for both character sketch template selection AND fight-history template selection

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-fighter-identity*
*Context gathered: 2026-03-02*
