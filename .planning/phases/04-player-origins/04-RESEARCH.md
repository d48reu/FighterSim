# Phase 4: Player Origins - Research

**Researched:** 2026-03-02
**Domain:** Game startup flow, origin selection UI, seed pipeline parameterization
**Confidence:** HIGH

## Summary

Phase 4 adds a pre-game origin selection screen that determines the player's starting conditions (budget, prestige, roster size/quality) and delivers a narrative intro before gameplay begins. The implementation spans four layers: (1) a new `OriginType` enum and `origin_type` column on `GameState`, (2) parameterization of `seed_organizations()` to accept origin-driven values instead of hardcoded player org defaults, (3) a new `origin.html` page served as a separate route with its own CSS, and (4) a startup flow change so `run.py` launches a web server first, presents the origin page, then seeds on selection rather than seeding at process start.

The existing codebase is well-structured for this change. `seed_organizations()` is a clean 25-line function with hardcoded player org values that can be trivially parameterized. The `_assign_organization()` function already uses prestige-weighted distribution, so different origin prestiges naturally produce different roster compositions. The frontend uses vanilla JS with CSS design tokens (dark theme, Rajdhani + Inter fonts), and the origin page should reuse these tokens for visual consistency while having its own cinematic layout.

**Primary recommendation:** Define origin configs as a Python dict constant, parameterize `seed_organizations()`, create `origin.html` as a standalone page, and restructure `run.py` to defer seeding until after origin selection via a POST endpoint.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 3 backstory-driven origins that also map to implicit difficulty levels:
  1. **The Heir** -- Inherited a mid-tier promotion after the founder passed. Prove you belong.
     - Budget: $8M | Prestige: 55 | Roster: 20 fighters
     - Roster quality: 2-3 veterans, mix of prime + prospects ("inherited talent")
  2. **The Matchmaker** -- Spent 10 years booking for UCC. Now building your own vision of the sport.
     - Budget: $4M | Prestige: 40 | Roster: 12 fighters
     - Roster quality: Mostly prime fighters, few prospects ("hand-picked roster")
  3. **The Comeback** -- Washed-out fighter. Nobody believes in you. Build from nothing.
     - Budget: $1.5M | Prestige: 25 | Roster: 6 fighters
     - Roster quality: All prospects/journeymen ("whoever would sign")
- Player names their own promotion (text input replaces hardcoded "Player Promotion")
- No explicit difficulty labels -- let the numbers (budget, prestige, roster) speak for themselves
- Separate HTML page (e.g., origin.html) -- not a view inside the existing SPA
- 3 cards displayed side by side, each showing: origin name, tagline, key stats (budget/prestige/roster size)
- Origin selection happens BEFORE seeding -- player picks origin and names promotion, then seed pipeline uses those params
- Flow: origin.html -> player selects card -> second step for promotion name input -> confirm -> triggers seed with origin params -> redirects to main app
- After selection, origin page is never shown again for that save
- Text crawl: 2 paragraphs per origin (who you are + what's at stake), fading in sequentially with CSS animations
- Shown after origin selection + name input, before gameplay begins (between confirm and dashboard)
- Second-person, cinematic voice -- "You stare at the empty arena. This is yours now." -- distinct from the measured MMA journalist tone used in fighter bios
- References real game world orgs (UCC, Bellator, One) to ground the story
- "Begin" button at bottom to proceed to dashboard after reading
- Wide budget spread: $1.5M (Comeback) to $8M (Heir)
- Prestige gates apply meaningfully (Heir 55 = Tier 1+2 camps, Matchmaker 40 = Tier 1 + barely Tier 2, Comeback 25 = Tier 1 only)
- Roster composition differs by quality AND size
- Origin type stored in database for future reference

### Claude's Discretion
- Exact narrative text for each origin's 2-paragraph intro
- How origin params feed into the existing seed pipeline (modification approach for seed_organizations/seed_fighters)
- Exact CSS animation timing for text crawl
- Origin page HTML/CSS styling (should feel premium/cinematic)
- How promotion name validation works (length limits, character restrictions)
- Database schema choice for storing origin (enum column on GameState vs Organization)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PLYR-01 | Player selects from multiple background origins at game start | Origin page with 3 selectable cards, separate HTML route, card selection JS, POST endpoint for origin choice |
| PLYR-02 | Each origin provides a narrative intro explaining why the promotion exists | Text crawl page with 2 paragraphs per origin, CSS fade-in animations, "Begin" button to proceed |
| PLYR-03 | Origins have mechanical consequences (different starting budget, roster size, reputation) | Origin config dict with budget/prestige/roster params, parameterized seed_organizations(), prestige-weighted fighter distribution |
| PLYR-04 | At least 3 distinct starting scenarios with meaningfully different gameplay | 3 origins with wide parameter spread ($1.5M-$8M budget, 25-55 prestige, 6-20 roster), prestige gates on training camps create cascading gameplay differences |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.0+ | Serve origin.html, handle POST /api/origin | Already in stack, thin controller pattern established |
| SQLAlchemy | 2.0+ | OriginType enum, GameState.origin_type column | Already in stack, all models use this ORM |
| Jinja2 | 3.x | Render origin.html template | Already used for index.html rendering |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vanilla CSS | -- | Origin page styling, text crawl animations | All frontend styling (no CSS frameworks in project) |
| Vanilla JS | -- | Card selection, name input, form submission | All frontend interactivity (no JS frameworks in project) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate origin.html | SPA view in index.html | User explicitly decided on separate page for cinematic feel; separate page is correct |
| Python dict config | JSON/YAML config file | Dict is simpler, co-located with seed code, no file I/O needed |
| CSS animations for text crawl | JS-driven animations | CSS is sufficient for sequential fade-ins with animation-delay; JS would be overengineered |

**Installation:**
```bash
# No new dependencies -- all libraries already installed
```

## Architecture Patterns

### Recommended Project Structure
```
models/models.py         # Add OriginType enum + GameState.origin_type column
simulation/seed.py       # Parameterize seed_organizations() + add ORIGIN_CONFIGS dict
api/app.py               # Add GET /origin + POST /api/origin routes
frontend/
  templates/
    origin.html          # NEW: Origin selection + name input + text crawl page
    index.html           # Unchanged
  static/
    css/
      origin.css         # NEW: Origin page styling (separate from main SPA CSS)
      style.css          # Unchanged
    js/
      origin.js          # NEW: Card selection, name input, API call logic
      app.js             # Unchanged
run.py                   # Restructure: start server WITHOUT seeding, seed on origin POST
```

### Pattern 1: Origin Config as Python Dict
**What:** Define all 3 origins as a constant dict in `seed.py`, keyed by origin type string.
**When to use:** When seed_organizations() needs origin-specific values.
**Why:** Keeps origin data co-located with the seed pipeline. No separate config file to manage. Easy to extend.
```python
# simulation/seed.py
ORIGIN_CONFIGS = {
    "the_heir": {
        "label": "The Heir",
        "tagline": "Inherited a mid-tier promotion. Prove you belong.",
        "budget": 8_000_000,
        "prestige": 55.0,
        "roster_target": 20,
        "roster_quality": "inherited",  # mix of veterans + prime + prospects
    },
    "the_matchmaker": {
        "label": "The Matchmaker",
        "tagline": "10 years booking for UCC. Now building your own vision.",
        "budget": 4_000_000,
        "prestige": 40.0,
        "roster_target": 12,
        "roster_quality": "hand_picked",  # mostly prime, few prospects
    },
    "the_comeback": {
        "label": "The Comeback",
        "tagline": "Washed-out fighter. Nobody believes in you.",
        "budget": 1_500_000,
        "prestige": 25.0,
        "roster_target": 6,
        "roster_quality": "scrappy",  # all prospects/journeymen
    },
}
```

### Pattern 2: Parameterized seed_organizations()
**What:** Add optional parameters to `seed_organizations()` for player org name, prestige, and bank_balance.
**When to use:** Called from the POST /api/origin handler after user selects origin.
**Why:** Minimal change to existing function signature. Falls back to defaults if called without params (preserving test_cli.py compatibility).
```python
def seed_organizations(
    session: Session,
    player_org_name: str = "Player Promotion",
    player_org_prestige: float = 50.0,
    player_org_balance: float = 5_000_000.0,
    origin_type: str | None = None,
) -> list[Organization]:
    orgs = [
        Organization(name="Ultimate Combat Championship", prestige=90.0,
                     bank_balance=50_000_000.0, is_player=False),
        Organization(name="Bellator MMA", prestige=70.0,
                     bank_balance=20_000_000.0, is_player=False),
        Organization(name="One Championship", prestige=75.0,
                     bank_balance=25_000_000.0, is_player=False),
        Organization(name=player_org_name, prestige=player_org_prestige,
                     bank_balance=player_org_balance, is_player=True),
    ]
    # ... rest unchanged ...

    # Store origin type in GameState
    game_state = GameState(
        id=1,
        current_date=date(2026, 1, 1),
        player_org_id=player_org.id if player_org else None,
        origin_type=origin_type,
    )
```

### Pattern 3: Deferred Seeding in run.py
**What:** Start the Flask server with empty DB, serve origin page first, seed after origin POST.
**When to use:** The new startup flow.
**Why:** Origin selection must happen BEFORE seeding because origin params feed into the seed pipeline.
```python
# run.py -- new flow
# 1. Delete old DB
# 2. Create app (creates tables)
# 3. Start server -- serves origin.html at GET /
# 4. User selects origin, names promotion
# 5. POST /api/origin triggers: seed_organizations(params) -> seed_fighters() -> fabricate_history()
# 6. Redirect to main app (index.html served at GET / now that game exists)
```

### Pattern 4: Origin Page Multi-Step Flow (All Client-Side)
**What:** Single origin.html page with JS-managed steps: (1) card selection, (2) name input, (3) text crawl.
**When to use:** The origin selection experience.
**Why:** Avoids multiple page loads. JS shows/hides sections within the same page. Only one server round-trip (the POST to seed).
```
Step 1: Show 3 origin cards -> user clicks one -> card highlights
Step 2: Slide in promotion name input -> user types + confirms
Step 3: POST /api/origin {origin_type, promotion_name}
Step 4: While seeding runs, show text crawl for selected origin
Step 5: When seed completes, show "Begin" button
Step 6: Click "Begin" -> window.location = "/" (now serves index.html)
```

### Pattern 5: Route Switching Based on Game State
**What:** GET / checks if GameState exists. If not, serve origin.html. If yes, serve index.html.
**When to use:** The root route handler.
**Why:** After origin selection, the origin page is never shown again. The check is a single DB query.
```python
@app.route("/")
def index():
    if services.has_game_state():
        return render_template("index.html")
    return render_template("origin.html")
```

### Anti-Patterns to Avoid
- **Seeding before origin selection:** The origin params MUST feed into seed. Never seed with defaults then patch.
- **Modifying index.html for origin flow:** Origin is a separate page with its own cinematic feel. Don't pollute the SPA.
- **Using localStorage for origin state:** Origin type must be in the database for server-side access. Client-side storage is unreliable.
- **Hardcoding roster counts in fighter assignment:** Use the prestige-weighted distribution system that already exists. Different prestige levels naturally attract different fighters. Only adjust the distribution weights or add a roster cap.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS text reveal animation | JS setTimeout chains | CSS `animation-delay` on elements with `opacity: 0 -> 1` and `translateY` | CSS animations are smoother, easier to tune, and don't block the main thread |
| Form validation | Custom regex validators | HTML5 `pattern`, `maxlength`, `required` attributes + small JS for UX polish | Browser-native validation handles edge cases |
| Roster quality composition | New fighter generation logic | Existing `_assign_organization()` prestige weighting + targeted adjustments | The prestige-based distribution already produces different roster quality per org prestige level |
| Loading state during seeding | Custom spinner | CSS `@keyframes` animation on a simple element | Seeding takes 2-5 seconds; a CSS spinner during text crawl covers the wait naturally |

**Key insight:** The existing seed pipeline's prestige-weighted fighter distribution already does most of the work. Different origin prestiges (25/40/55) will naturally produce different roster compositions because `_assign_organization()` sends better fighters to higher-prestige orgs. The main addition needed is a roster size cap to enforce the 6/12/20 targets.

## Common Pitfalls

### Pitfall 1: Roster Size Control
**What goes wrong:** The `_assign_organization()` function distributes fighters probabilistically. With 450 fighters and 4 orgs, the player org might get 80+ fighters instead of the origin's target (6/12/20).
**Why it happens:** Current distribution weights give the player org 10-50% of each career stage bucket. With 450 fighters, that's far more than any origin wants.
**How to avoid:** After running `seed_fighters()`, enforce the roster target by:
  1. Count fighters assigned to player org
  2. If over target, release excess fighters (convert contracts to free agents), prioritizing releasing lower-quality fighters
  3. If under target (unlikely for Heir), keep as-is -- the player can sign free agents
  Alternatively, pass `roster_target` into `seed_fighters()` and cap assignments during the loop.
**Warning signs:** Player org has 50+ fighters on The Comeback origin.

### Pitfall 2: Roster Quality Not Matching Origin Theme
**What goes wrong:** Random distribution gives The Comeback origin a GOAT Candidate or gives The Heir only prospects.
**Why it happens:** `_assign_organization()` is probabilistic. Even with low prestige (25), there's a small chance of getting elite fighters.
**How to avoid:** Add roster quality constraints per origin:
  - **The Heir (inherited):** Allow all career stages. Target 2-3 veterans, rest mixed.
  - **The Matchmaker (hand_picked):** Filter for prime-stage fighters primarily. Few prospects.
  - **The Comeback (scrappy):** Only prospects and journeymen. No GOAT Candidates, no veterans with high overall.
  This can be implemented as a post-seed filter or as an additional constraint in `_assign_organization()`.
**Warning signs:** Test each origin 3-5 times and verify roster quality matches the origin theme.

### Pitfall 3: Seeding Race Condition
**What goes wrong:** User clicks "Begin" before seeding completes, gets empty dashboard.
**Why it happens:** `seed_fighters()` + `fabricate_history()` takes 2-5 seconds. If the text crawl finishes faster, user can proceed too early.
**How to avoid:** Two-gate approach:
  1. POST /api/origin returns a task_id (using existing task polling pattern from `services.py`)
  2. "Begin" button only enables when task completes (poll task status)
  3. Text crawl animation takes ~4-6 seconds, which covers most seeding time naturally
  The existing `pollTask()` function in app.js already implements this pattern for event simulation.
**Warning signs:** "Begin" button appears before seed finishes.

### Pitfall 4: Promotion Name Edge Cases
**What goes wrong:** Empty name, extremely long name, or names with special characters break the UI or DB.
**Why it happens:** No validation on text input.
**How to avoid:** Validate both client-side and server-side:
  - Min length: 2 characters
  - Max length: 50 characters (Organization.name is String(120), but UI layout assumes shorter names)
  - Strip leading/trailing whitespace
  - Allow letters, numbers, spaces, hyphens, apostrophes, periods
  - Reject empty/whitespace-only input
**Warning signs:** Sidebar logo text overflows with long promotion names.

### Pitfall 5: test_cli.py and main.py Breakage
**What goes wrong:** Adding `origin_type` parameter to `seed_organizations()` or changing the GameState model breaks existing test scripts.
**Why it happens:** `test_cli.py` and `main.py` call `seed_organizations()` directly without origin params.
**How to avoid:** Use default parameter values so the function signature is backward-compatible. `origin_type=None` as default. GameState.origin_type should be nullable.
**Warning signs:** `python3 test_cli.py` fails after changes.

## Code Examples

### OriginType Enum and GameState Column
```python
# models/models.py

class OriginType(str, enum.Enum):
    THE_HEIR = "The Heir"
    THE_MATCHMAKER = "The Matchmaker"
    THE_COMEBACK = "The Comeback"

class GameState(Base):
    __tablename__ = "game_state"

    id: Mapped[int] = Column(Integer, primary_key=True)
    current_date: Mapped[date] = Column(Date, nullable=False)
    player_org_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("organizations.id"), nullable=True
    )
    origin_type: Mapped[Optional[str]] = Column(
        Enum(OriginType), nullable=True
    )
```

### Route Switching Based on Game State
```python
# api/app.py

@app.route("/")
def index():
    if services.has_game_state():
        return render_template("index.html")
    return render_template("origin.html")

@app.route("/api/origin", methods=["POST"])
def select_origin():
    data = request.json
    origin_type = data.get("origin_type")
    promotion_name = data.get("promotion_name", "").strip()

    # Validate
    if origin_type not in ORIGIN_CONFIGS:
        return jsonify({"error": "Invalid origin"}), 400
    if not promotion_name or len(promotion_name) < 2 or len(promotion_name) > 50:
        return jsonify({"error": "Name must be 2-50 characters"}), 400

    # Run seeding as async task (existing pattern)
    task_id = services.start_new_game(origin_type, promotion_name)
    return jsonify({"task_id": task_id})
```

### has_game_state() Service Function
```python
# api/services.py

def has_game_state() -> bool:
    """Check if a game has been started (GameState row exists)."""
    with _SessionFactory() as session:
        gs = session.get(GameState, 1)
        return gs is not None
```

### Text Crawl CSS Animation
```css
/* origin.css -- text crawl with sequential fade-in */

.crawl-paragraph {
    opacity: 0;
    transform: translateY(20px);
    animation: crawl-reveal 1.2s var(--ease-out) forwards;
}

.crawl-paragraph:nth-child(1) {
    animation-delay: 0.5s;
}

.crawl-paragraph:nth-child(2) {
    animation-delay: 2.5s;
}

.crawl-begin-btn {
    opacity: 0;
    animation: crawl-reveal 0.8s var(--ease-out) forwards;
    animation-delay: 4.5s;
}

@keyframes crawl-reveal {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

### Origin Card Selection (JS)
```javascript
// origin.js -- card selection and multi-step flow

document.querySelectorAll('.origin-card').forEach(card => {
    card.addEventListener('click', () => {
        // Deselect all, select clicked
        document.querySelectorAll('.origin-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedOrigin = card.dataset.origin;
        // Show step 2: name input
        document.getElementById('step-name').classList.remove('hidden');
    });
});

async function confirmOrigin() {
    const name = document.getElementById('promo-name-input').value.trim();
    if (!name || name.length < 2 || name.length > 50) {
        showError('Promotion name must be 2-50 characters');
        return;
    }

    // POST to server
    const res = await fetch('/api/origin', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ origin_type: selectedOrigin, promotion_name: name })
    });
    const data = await res.json();

    if (data.task_id) {
        // Show text crawl while seeding runs
        showTextCrawl(selectedOrigin);
        // Poll for completion
        pollSeedTask(data.task_id);
    }
}
```

### Roster Size Enforcement Post-Seed
```python
# simulation/seed.py -- after seed_fighters() completes

def enforce_roster_target(session: Session, player_org_id: int, target: int) -> None:
    """Release excess fighters from player org to hit roster target."""
    contracts = session.execute(
        select(Contract)
        .where(Contract.organization_id == player_org_id,
               Contract.status == ContractStatus.ACTIVE)
        .join(Fighter)
        .order_by(Fighter.striking + Fighter.grappling + Fighter.wrestling)  # weakest first
    ).scalars().all()

    if len(contracts) <= target:
        return

    # Release excess, starting with lowest-rated fighters
    for contract in contracts[target:]:
        session.delete(contract)
    session.flush()
```

### Narrative Text (Discretion Area)
```python
# simulation/seed.py or separate origins.py

ORIGIN_NARRATIVES = {
    "the_heir": [
        "The call came on a Tuesday. Gerald Rawlings -- your mentor, your father's best friend, the man who built Apex Fighting from a warehouse show into a regional powerhouse -- was gone. Heart attack at 63. The board wanted to sell. The networks wanted to renegotiate. Everyone had an opinion about what happens next.",
        "You stare at the empty arena. Eighteen thousand seats, a cage that's hosted legends, and a legacy that doesn't belong to you yet. The Rawlings name opened doors. Yours will have to keep them open. You have the roster, you have the budget, but respect? That's earned fight by fight."
    ],
    "the_matchmaker": [
        "Ten years. Ten years of building fight cards for UCC, turning unknowns into contenders, engineering the kind of matchups that make crowds forget to breathe. You made their champions. You filled their arenas. And when you asked for a seat at the table, they laughed.",
        "So you walked. Took your rolodex, your eye for talent, and every lesson learned from a decade inside the machine. Your promotion doesn't have the budget or the broadcast deal. What it has is you -- the person who knows exactly which fights the world wants to see. Now you just need to prove it's not the logo on the cage that matters. It's who's booking the fights."
    ],
    "the_comeback": [
        "They remember your last fight. Everybody does. Third-round stoppage, flat on the canvas, the referee waving it off while the crowd went quiet. That was three years ago. The gym closed. The sponsors vanished. Your name became a punchline on MMA forums -- 'pulled a you-know-who.'",
        "But fighters don't quit. You scraped together every dollar, called in every favor, and signed six hungry kids who remind you of yourself -- back when you still believed you could be somebody. The warehouse smells like sweat and ambition. The budget wouldn't cover one UCC undercard. Nobody in the industry gives you six months. Good. You've been counted out before."
    ],
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded player org in seed.py | Parameterized seed with origin selection | This phase | Player org values driven by origin choice |
| run.py seeds immediately on start | Server starts, presents origin page, seeds on selection | This phase | Origin selection must precede world generation |
| Single startup flow (run.py) | Conditional routing: origin.html or index.html based on DB state | This phase | Supports both fresh games and resuming existing saves |

**Deprecated/outdated:**
- `"Player Promotion"` hardcoded name in seed.py: Will be replaced by user-chosen promotion name
- Direct seeding in run.py: Will be replaced by API-triggered seeding after origin selection

## Open Questions

1. **Roster quality composition enforcement**
   - What we know: Different origins need different roster quality profiles (veterans for Heir, prime for Matchmaker, prospects for Comeback). The prestige-weighted distribution partially handles this.
   - What's unclear: Whether the existing distribution weights produce close-enough roster compositions at prestige levels 25/40/55, or whether explicit post-seed filtering is needed.
   - Recommendation: Test the existing distribution at each prestige level first. If compositions don't match origin themes, add a post-seed filter that releases/reassigns fighters. This is LOW risk since the enforcement function is simple.

2. **run.py vs main.py startup divergence**
   - What we know: `run.py` deletes DB and reseeds (fresh start). `main.py` uses existing DB. Both need to work with the new origin flow.
   - What's unclear: Whether `main.py` should also check for origin page display, or if it always assumes an existing game.
   - Recommendation: Both `run.py` and `main.py` should use the same `create_app()` with route-switching logic. `run.py` deletes DB first (ensuring origin page shows). `main.py` serves existing DB (origin page never shows). The route-switching pattern handles both cases.

3. **Seeding time during text crawl**
   - What we know: Seeding 450 fighters + fabricating history takes 2-5 seconds. Text crawl animation is ~4-6 seconds.
   - What's unclear: Whether seeding consistently finishes within the text crawl duration.
   - Recommendation: Use the existing task polling pattern. The "Begin" button only appears after both (a) the text crawl animation finishes AND (b) the seed task completes. If seed finishes first, button appears on animation end. If animation finishes first, show a subtle loading indicator until seed completes.

## Sources

### Primary (HIGH confidence)
- `/home/d48reu/FighterSim/simulation/seed.py` -- Full seed pipeline reviewed: seed_organizations (line 287-312), seed_fighters (line 464-649), _assign_organization (line 237-280)
- `/home/d48reu/FighterSim/models/models.py` -- All 25 models reviewed. GameState (line 388-395), Organization (line 207-228), existing enum patterns (9 enums using str+enum.Enum)
- `/home/d48reu/FighterSim/api/app.py` -- Flask route patterns, template/static paths, create_app factory
- `/home/d48reu/FighterSim/api/services.py` -- get_gamestate(), get_player_org(), init_db(), task polling pattern
- `/home/d48reu/FighterSim/run.py` -- Current startup flow: delete DB -> create_app -> seed -> server
- `/home/d48reu/FighterSim/frontend/static/css/style.css` -- Design tokens (lines 14-104), animation patterns (@keyframes fadeIn, arena-enter, crawl patterns)
- `/home/d48reu/FighterSim/frontend/static/js/app.js` -- Navigation system, pollTask(), API helper
- `/home/d48reu/FighterSim/frontend/templates/index.html` -- Full SPA template structure, sidebar nav, font imports

### Secondary (MEDIUM confidence)
- CSS animation-delay patterns for sequential reveals: Standard CSS3 feature, well-supported in all modern browsers

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- No new dependencies, all patterns already exist in codebase
- Architecture: HIGH -- Seed pipeline is well-understood, parameterization is straightforward, route-switching is a common Flask pattern
- Pitfalls: HIGH -- Identified from direct code analysis of seed.py distribution logic and run.py startup flow

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable -- no external dependencies or fast-moving libraries)
