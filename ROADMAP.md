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
- ✅ Fight result tags: 40+ tags (unstoppable, chin_concerns, giant_killer, ko_specialist, highlight_reel, etc.)
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
- ✅ NewsHeadline model (headline ticker)
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
- ✅ **Reality TV show (Ultimate Fighter-style)** — RealityShow, ShowContestant, ShowEpisode models. 8-fighter (4 episodes) or 16-fighter (5 episodes) single-elimination bracket. Seeded by overall rating. Episodes process via sim_month: intro (no fights), quarterfinals, semifinals, finale. $75K/episode production cost. Broadcast deal fee_per_event earned per episode. Completion bonus = show_hype * $500. Winner gets 25% salary discount, runner-up 15%, semifinalists 5%. Bracket visualization in frontend with 3 states (setup/active/completed). Dashboard widget. AI signing guard protects contestants during show and completion month.
  - ✅ **Shenanigans system** — 3-4 slots per episode, 70% trigger each. 5 positive types (viral_training_clip, callout_favorite, mentor_moment, underdog_speech, short_notice_step_up) and 7 negative types (house_fight, out_of_shape, quits_show, breaks_rules, injury_in_training, weight_miss_drama, locker_room_tension). 40/60 positive/negative split. All tags persist on Fighter.narrative_tags. Permanent quitter tag reduces contract acceptance by 15%. Shenanigan cards with animated reveal in episode results.

### Medium Term — Narrative Expansion
- ✅ **Expanded narrative tags (40+)** — 20 new tags added: method-specific (ko_specialist, submission_ace, first_round_finisher, decision_machine, highlight_reel, comeback_victory), career patterns (iron_chin_proven, gatekeeper_confirmed, veteran_presence, clutch_performer, rising_prospect, undefeated, road_warrior, title_contender, dark_horse), loser tags (retirement_watch, glass_cannon, needs_new_camp), fight quality (fight_of_the_night, war_survivor). Tag removal logic: winner loses retirement_watch, loser loses undefeated/rising_prospect on streaks.
- ✅ **Career timeline view** — GET /api/fighters/<id>/timeline returns chronological fight history with running record, opponent info, method, round. Collapsible panel in fighter side panel with green/red W/L borders and gold TITLE badges. Max 300px scroll.
- ✅ **News feed / media ticker** — NewsHeadline model with 8 headline template categories (ko_finish, sub_finish, upset, decision, title_fight, streak, signing, retirement_concern). generate_fight_headline() with priority logic, generate_signing_headline() for OVR>=70. Hooks in all fight sim paths + AI signings. Dashboard widget with category emoji icons, clickable headlines open fighter panel.
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
3. ~~Reality TV show (Ultimate Fighter-style) + shenanigans system~~ ✅
4. ~~Narrative expansion (more tags, career timeline, news ticker)~~ ✅
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
