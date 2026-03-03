# Phase 4: Player Origins - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Selectable starting scenarios with narrative intros and mechanical consequences. New games begin with a choice that shapes the player's starting situation and tells them why their promotion exists. The origin selection happens before seeding, and origin parameters feed into the seed pipeline to customize the world. 3 distinct origins with backstory-driven themes.

</domain>

<decisions>
## Implementation Decisions

### Origin scenarios
- 3 backstory-driven origins that also map to implicit difficulty levels:
  1. **The Heir** — Inherited a mid-tier promotion after the founder passed. Prove you belong.
     - Budget: $8M | Prestige: 55 | Roster: 20 fighters
     - Roster quality: 2-3 veterans, mix of prime + prospects ("inherited talent")
  2. **The Matchmaker** — Spent 10 years booking for UCC. Now building your own vision of the sport.
     - Budget: $4M | Prestige: 40 | Roster: 12 fighters
     - Roster quality: Mostly prime fighters, few prospects ("hand-picked roster")
  3. **The Comeback** — Washed-out fighter. Nobody believes in you. Build from nothing.
     - Budget: $1.5M | Prestige: 25 | Roster: 6 fighters
     - Roster quality: All prospects/journeymen ("whoever would sign")
- Player names their own promotion (text input replaces hardcoded "Player Promotion")
- No explicit difficulty labels — let the numbers (budget, prestige, roster) speak for themselves

### Selection experience
- Separate HTML page (e.g., origin.html) — not a view inside the existing SPA
- 3 cards displayed side by side, each showing: origin name, tagline, key stats (budget/prestige/roster size)
- Origin selection happens BEFORE seeding — player picks origin and names promotion, then seed pipeline uses those params
- Flow: origin.html → player selects card → second step for promotion name input → confirm → triggers seed with origin params → redirects to main app
- After selection, origin page is never shown again for that save

### Narrative delivery
- Text crawl: 2 paragraphs per origin (who you are + what's at stake), fading in sequentially with CSS animations
- Shown after origin selection + name input, before gameplay begins (between confirm and dashboard)
- Second-person, cinematic voice — "You stare at the empty arena. This is yours now." — distinct from the measured MMA journalist tone used in fighter bios
- References real game world orgs (UCC, Bellator, One) to ground the story in the world the player will compete in
- "Begin" button at bottom to proceed to dashboard after reading

### Mechanical consequences
- Wide budget spread: $1.5M (Comeback) to $8M (Heir) — The Comeback starts in genuine financial tension
- Prestige gates apply meaningfully:
  - The Heir (55): Tier 1 + Tier 2 training camps unlocked, better fighters willing to sign
  - The Matchmaker (40): Tier 1 unlocked, Tier 2 barely accessible
  - The Comeback (25): Tier 1 only, locked out of Tier 2 camps (require 40), only low-tier fighters interested
- Roster composition differs by quality AND size (not just headcount)
- Origin type stored in database (add to GameState or Organization model) for potential future reference in news headlines, achievements, or UI

### Claude's Discretion
- Exact narrative text for each origin's 2-paragraph intro
- How origin params feed into the existing seed pipeline (modification approach for seed_organizations/seed_fighters)
- Exact CSS animation timing for text crawl
- Origin page HTML/CSS styling (should feel premium/cinematic)
- How promotion name validation works (length limits, character restrictions)
- Database schema choice for storing origin (enum column on GameState vs Organization)

</decisions>

<specifics>
## Specific Ideas

- The Matchmaker's backstory explicitly references leaving UCC — "You spent 10 years booking for UCC..." — creates world continuity
- The Heir's narrative should evoke succession drama — the board wanted to sell, you fought to keep it
- The Comeback should feel scrappy and underdog — "Nobody believes in you" energy
- No difficulty labels or color coding on cards — the fiction shouldn't be broken by gamey UI elements
- Origin selection is a separate page, not woven into the SPA, giving it a distinct cinematic feel before the game "begins"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `seed_organizations()` (seed.py:287): Creates 4 orgs with hardcoded values — needs parameterization for player org's name, prestige, and bank_balance based on origin
- `seed_fighters()` (seed.py): Fighter distribution uses prestige-weighted org assignment — origin's prestige value will naturally affect which fighters the player org attracts
- `Organization` model (models.py:207): Already has `name`, `prestige`, `bank_balance`, `is_player` fields — no new columns needed for base mechanics
- `GameState` model (models.py:388): Has `player_org_id` — could add `origin_type` column here
- Frontend nav + SPA routing (app.js:77): `navigate()` function handles view switching — origin page bypasses this entirely as a separate page

### Established Patterns
- Deterministic seeding with `seed=42` — origin params feed in alongside seed value
- `run.py` flow: delete DB → create app → seed orgs → seed fighters → fabricate history → start server — origin selection must precede this pipeline
- Frontend is vanilla JS with CSS design tokens (Rajdhani + Inter fonts) — origin page should use same font/token system
- Async sim endpoints return task_id — seeding could follow same pattern if it takes time with origin customization

### Integration Points
- `run.py`: Currently hardcodes the full pipeline — needs to accept origin params (origin_type, promotion_name) before seeding
- `seed_organizations()`: Player org creation needs to use origin-specific values instead of hardcoded prestige=50, bank_balance=5M, name="Player Promotion"
- `seed_fighters()`: Org distribution weights (line 269-275) may need origin-aware tuning for roster quality differences
- `GameState`: Add origin_type field for persistence
- New route needed: serve origin.html and handle origin selection API call
- Redirect flow: origin.html → POST origin choice → seed runs → redirect to main app

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-player-origins*
*Context gathered: 2026-03-02*
