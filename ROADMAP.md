# FighterSim — Project Roadmap

## Project Overview
Desktop MMA management simulation game. Player manages an MMA promotion — signing fighters, booking events, managing finances, developing talent. Built in Python/Flask/SQLite with a vanilla JS frontend.

**GitHub:** https://github.com/d48reu/FighterSim  
**Stack:** Python 3, Flask, SQLAlchemy, SQLite, HTML/CSS/JS  
**Run:** `python main.py` → http://localhost:5000

---

## Current Status — Completed Features

### Core Simulation Engine
- ✅ Round-by-round fight simulation (30-second ticks, 10 ticks/round)
- ✅ KO/TKO, Submission, Unanimous/Split/Majority Decision methods
- ✅ Realistic method distribution: Sub ~23%, KO ~32%, Dec ~45%
- ✅ Stamina system with cardio-based decay and round recovery
- ✅ Deterministic results via RNG seed

### Fight Engine — Advanced Systems
- ✅ Traits system (12 traits: iron_chin, gas_tank, knockout_artist, fast_hands, etc.)
- ✅ All traits mechanically wired into simulation
- ✅ Knockdown system — probability, hurt state, ref stoppages, double-KD TKO
- ✅ Momentum system (±1.0, decays per tick, affects damage and finish probability)
- ✅ Style matchup system (Striker/Wrestler/Grappler/Well-Rounded affect takedown probability, clinch frequency, ground stickiness)

### Narrative Engine
- ✅ 6 fighter archetypes: Phenom, GOAT Candidate, Gatekeeper, Journeyman, Late Bloomer, Shooting Star
- ✅ Fight result tags: 20+ tags (unstoppable, chin_concerns, giant_killer, redemption, etc.)
- ✅ Context-aware bio generation with career stage gating (prospect/developing/established/veteran/elder)
- ✅ Validation layer catches age-inappropriate language before returning
- ✅ GOAT score tracker
- ✅ Rivalry detection (2+ fights between same pair)
- ✅ Hype and popularity system with monthly decay

### Monthly Simulation
- ✅ sim_month() completes in ~120-170ms regardless of roster size
- ✅ Fighter aging with prime window (pre-prime gains, in-prime fluctuation, post-prime decline)
- ✅ Injury recovery tick-down
- ✅ AI org event generation (~40% chance per org per month)
- ✅ Contract expiry processing with notifications
- ✅ Game clock system (stored current_date, advances by 1 month, starts 2026-01-01)

### Data & Models
- ✅ Fighter, Organization, Event, Fight, Contract, Ranking models
- ✅ Notification model
- ✅ GameState model (persistent game clock)
- ✅ Proper indexes on all frequently queried fields
- ✅ 100 seeded fighters across 5 weight classes with realistic age-gated records

### Player Finances
- ✅ Monthly payroll deduction (salary/12 per fighter)
- ✅ Event revenue credited (gate + PPV)
- ✅ Fighter salary deducted per fight competed
- ✅ Bankruptcy and financial crisis notifications

### Contract System
- ✅ Free agents view with asking salary calculation
- ✅ Offer panel with acceptance probability (salary factor + prestige factor)
- ✅ Rejection reasons (low offer, low prestige, can't afford)
- ✅ Roster view with active contracts
- ✅ Release fighter
- ✅ Contract renewal with loyalty bonus
- ✅ Expiring contracts widget on dashboard

### Event Booking
- ✅ Three-panel layout (event list / card builder / fighter pool)
- ✅ Create event with venue and game date
- ✅ Fighter pool filtered by weight class, available fighters only
- ✅ Add/remove fights from card
- ✅ Revenue projection (updates live as fights added)
- ✅ Async simulation with task polling
- ✅ Fight reveal animation (sequential, typewriter narrative, skip on click)
- ✅ Title fight support
- ✅ Event history view

### Fighter Development
- ✅ TrainingCamp and FighterDevelopment models
- ✅ 15 training camps across 3 tiers (prestige-gated)
- ✅ Focus areas: Striking, Grappling, Wrestling, Cardio, Balanced
- ✅ Attribute gains based on tier, focus, age, prime window, consistency bonus
- ✅ Diminishing returns above 85 overall
- ✅ Natural decay for untrained fighters past prime
- ✅ Development projection table (3/6/12 month forecast)
- ✅ Development notifications (milestones, decline warnings)
- ✅ Monthly cost deducted from bank balance

### Rankings
- ✅ Cached rankings with dirty flag
- ✅ Quality-of-opposition weighting
- ✅ Per weight class, top 15

### Frontend
- ✅ Dashboard with finances, expiring contracts, recent results, upcoming events
- ✅ Fighters table (filterable, sortable)
- ✅ Rankings view
- ✅ Roster with stat bars and fighter panel
- ✅ Free Agents with offer flow
- ✅ Events (booking, results, history)
- ✅ Development tab
- ✅ Hall of Fame (GOAT leaderboard + rivalries)
- ✅ Notification bell with unread count

---

## Lessons Learned

### Architecture Decisions That Paid Off
- **Flask-independent fight engine** — zero web framework imports in simulation code. Made testing trivial and would make a future desktop packaging (PyInstaller/Electron) much cleaner.
- **Async task pattern for simulation** — returning task_id immediately and polling avoids blocking the UI for long simulations. Right call from day one.
- **Narrative as a separate module** — `narrative.py` completely decoupled from fight logic means you can iterate on bios and tags without touching simulation.
- **Dirty flag on rankings** — only rebuild when fights happen, not on every request. Simple optimization that matters at scale.

### Bugs That Cost Time
- **Game clock using date.today()** — contracts never expired through normal gameplay. Fixed by adding GameState model with stored current_date. Always use game time, never real time.
- **Submission rate 100%** — takedown probability was too high, ground stickiness made fights stay on mat, submission attempt rate too aggressive. Required careful tuning of 8 parameters simultaneously.
- **Fighter records too high for age** — seed data generating 20-year-olds with 15 fights. Fixed with age-gated max_fights lookup table.
- **Event simulator pulling from all orgs** — player event was using fighters from AI rosters. Always filter by organization_id.
- **Aging bug** — fighters aging 1 year per month instead of per year. Fixed by gating age increment behind 1/12 probability roll.
- **Archetype assignment too loose** — 21-year-olds getting Gatekeeper + Veteran IQ. Fixed with hard age gates on both archetype and trait assignment.

### Bio System Lessons
- Template-based bios need a **decision tree with hard gates**, not a flat lookup. Age, fight count, trajectory, and archetype must all be checked before selecting language.
- Always **validate before returning** — a fallback generic bio is better than a contradiction ("youth and skill" for a 39-year-old).
- Pluralization must be handled explicitly — never interpolate numbers without a helper function.
- Bio templates need **3+ variants per category** or repetition becomes obvious immediately.

### Fight Engine Lessons
- Tune submission rate, KO rate, and decision rate together — they're interconnected. Changing one moves all three.
- Traits need to be **mechanically meaningful**, not just cosmetic badges. Players will notice if iron_chin doesn't actually change KO thresholds.
- Style matchup modifiers should be **conservative** — small adjustments (±0.05-0.10) have large compounding effects over 10 ticks × 3-5 rounds.

---

## Remaining Roadmap

### Near Term — Personality Layer
- ✅ **Nationality system** — NATIONALITY_STYLE_MAP, NATIONALITY_NICKNAMES, NATIONALITY_TONE dicts added. _nationality_flavor() wired into generate_fighter_bio(). (622be82)
- ✅ **Nickname system** — Fighter.nickname field, suggest_nicknames() with weighted pools by archetype/trait/nationality. GET/POST API endpoints. Inline edit with suggestion chips in frontend. (8b82988)
- ✅ **Press conference system** — Fight.press_conference + Event.has_press_conference model fields. generate_press_conference() with tone profiles, 5-7 exchanges, hype/PPV boost. Animated sequential reveal in frontend. (5215c7b)
- ✅ **Cornerstone Fighters system** — Fighter.is_cornerstone field, max 3 per org, +5 hype and +2 prestige on wins, auto-removal on 3 consecutive losses, enhanced press conferences (7 exchanges), gold crown badges, dashboard widget. (a3ce6e9)

### Near Term — Simulation Depth
- ✅ **Weight cutting** — natural_weight/fighting_weight fields on Fighter. Cut severity (easy/moderate/severe/extreme) applies stamina/chin penalties in fight engine. Missed weight probability with 20% purse fines. Cut severity badges in fighter pool UI. (a74f338)
- ✅ **Judging variance** — 5 named judge profiles (Garcia, Tanaka, O'Brien, Petrov, Williams) with striking/grappling/aggression/damage biases. Per-judge 10-point must scoring. Scorecard table shown in fight results UI. (a74f338)
- ✅ **Fighter psychology / confidence** — hidden confidence field (0-100, default 70). Post-fight shifts: KO win +12, KO loss -18. Fight engine modifiers for high/low confidence. Monthly decay toward 70. sky_high_confidence and shell_shocked narrative tags. Bio flavor and press conference tone affected. (0450529)

### Medium Term — Business Layer
- ✅ **TV/streaming deals** — broadcast contracts requiring minimum card quality and event frequency. Revenue multiplier on successful events. Prestige-gated tiers (Regional/National/Premium). (f733e9f)
- ✅ **Venue management** — prestige-gated venues, capacity shown in dropdown, Major Arena requires 65 prestige, Stadium requires 80. Sellout bonus and poor turnout prestige hit. (f733e9f)
- ✅ **Rival promotion AI** — AI orgs compete for free agents, poach your fighters, respond to your prestige growth. Designated rival org tracked on dashboard. (23cc23a)
- ✅ **Sponsorship system** — per-fighter sponsorships across 4 tiers (Local Brand to Global Sponsor). Hype/popularity gated, cornerstone bonuses, monthly stipend payments, compliance checks. Dashboard widget + roster fighter panel integration. (sponsorship-system)
- ⏳ **Reality TV show (Ultimate Fighter-style)** — player produces a tournament show with 8 or 16 free agent prospects. Runs over several simulated months with a bracket. Each episode tick: fighters gain small attribute improvements, hype builds for the show and fighters, narrative moments generate. Winner gets automatic contract offer, runners-up available at discount. Show costs money to produce but generates monthly hype and prestige. Satisfies broadcast deal event requirements.
  - **Shenanigans system** — each episode tick, fighters have a chance to trigger positive or negative random events. Good: steps up on short notice (hype spike, fan favorite tag), goes viral for training clip (popularity bump), calls out tournament favorite (rivalry created). Bad: house fight (suspended one episode), shows up out of shape (stamina penalty), quits the show (eliminated + permanent quitter tag on their career), breaks house rules (fine + hype hit). Events feed into existing narrative and tag system — tags follow fighters into their future careers. Player decisions: sign the talented quitter? Cut the troublemaker who keeps winning?

### Medium Term — Narrative Expansion
- ⏳ **More narrative tag variety** — currently ~20 tags, need 40+. Specific finish types (spinning heel kick KO, rear naked choke, etc.), comeback stories, retirement hints.
- ⏳ **Career timeline view** — fight-by-fight tag history on fighter profile showing narrative arc.
- ⏳ **News feed / media ticker** — simulated headlines on dashboard based on recent fight results, contract signings, rivalries.
- ⏳ **Retirement system** — fighters decline past a threshold and retire. Legacy score. Retired legends as coaching staff boosting camp effectiveness.

### Polish & Visual
- ⏳ **Fighter portraits** — library of ~80-100 generated portraits assigned by archetype/age at seed time. Midjourney with --cref for consistency.
- ⏳ **Design sprint** — full visual overhaul. Committed typography system, color palette per weight class, motion design, component library (Arena UI). Reference: Hades, Football Manager newer UI.
- ⏳ **Fight visualization upgrade** — round-by-round momentum bars, damage tracking display during event simulation.
- ⏳ **Sound design** — ambient crowd noise, fight bell, notification sounds, finish sounds.

### Release Prep
- ⏳ **Save/load system** — multiple save slots, autosave before month advance.
- ⏳ **Settings** — difficulty (starting budget, AI aggression, fighter development rate), display options.
- ⏳ **Tutorial / onboarding** — guided first event flow for new players.
- ⏳ **Steam Early Access prep** — PyInstaller packaging, Steam store page, trailer, pricing ($24.99).

---

## Feature Priority Order (Current)
1. ~~Rival promotion AI~~ ✅
2. ~~Sponsorship system~~ ✅
3. Reality TV show (Ultimate Fighter-style) + shenanigans system
4. Narrative expansion (more tags, career timeline, news ticker)
5. Retirement system
6. Fighter portraits
7. **Design sprint** ← full visual overhaul before public release
8. Fight visualization upgrade
9. Sound design
10. Save/load
11. Steam prep

---

## Technical Notes
- Always use `game_state.current_date` — never `date.today()`
- Fight engine has zero Flask dependencies — keep it that way
- All business logic in `api/services.py` — routes only call service functions
- Simulation endpoints must be async (return task_id, poll `/api/tasks/<id>`)
- Trait contradictions defined in `simulation/traits.py` — check before assigning
- Bio validation in `narrative.py` must pass before returning any generated text
- Rankings only rebuild when dirty flag is set — never on every request
- Drop and reseed DB after any model changes: `python -c "from simulation.seed import *; ..."`
