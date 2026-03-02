# Feature Research: World-Building & Fighter Identity

**Domain:** MMA promotion management simulation (world-building milestone)
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH (based on competitor analysis of WMMA5, TEW IX, Football Manager 26, OOTP, MMA Manager)

## Context

FighterSim already has solid mechanical systems (fight engine, monthly sim, contracts, rankings, narrative tags, archetypes, traits). What it lacks is **soul** -- the feeling that the world existed before the player showed up. This research identifies what world-building features create that "lived-in world" feeling in competitor products and maps them to FighterSim's needs.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that every sports management sim with world-building ambitions must have. Missing these and the game feels hollow at startup.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Pre-generated fight records with plausible history** | FM, WMMA5, OOTP all ship with characters who have existing records, stats, and career trajectories. A fighter with 12-3 should feel like he earned those wins. | MEDIUM | FighterSim has age-gated records already but no fight history rows -- records are just numbers with no opponent trail. Need simulated past fights or at minimum retroactive result summaries. |
| **Existing champions at game start** | Every competitor starts with champions crowned in each weight class. WMMA5 has reigning champions across multiple orgs. Players expect to see who holds belts before they start. | LOW | Requires belt system + seed logic to assign champions per weight class per org based on ranking/record. |
| **Established veterans, prospects, and career-stage diversity** | FM's database has 750K+ people with full career histories. WMMA5 has fighters at every career stage (rising, peaking, prime, declining). The roster must feel like a snapshot of a living sport, not a batch generation. | MEDIUM | Current seed generates uniform age distribution (20-37). Need intentional distribution: ~15% prospects (20-23), ~30% rising (24-27), ~30% prime (28-31), ~20% veterans (32-35), ~5% legends (36+). |
| **Roster scaling to ~400-500 fighters** | WMMA5's default world has hundreds of fighters across many orgs. MMA Manager has 940+ AI fighters across 10 promotions. 20 fighters per weight class across 4 orgs is too thin to feel like a real sport. Target: 80-100 per weight class. | HIGH | Current seed is 100 fighters with 80 first names x 80 last names. Scaling 4-5x requires: expanded name pools (150+ each), more nationalities, stat distribution curves that avoid sameness, and org allocation logic that places top talent in top orgs. |
| **Weight class population balance** | All competitors ensure every division has enough fighters to run events and have meaningful rankings. | LOW | Currently random distribution means some classes get 15, others get 25. Need deterministic allocation: equal base + variance. |
| **Distinct fighter identities (not stat blocks)** | WMMA5 differentiates fighters through 50+ attributes, style archetypes, and personality. FM uses personality types ("Ambitious," "Professional," etc.) derived from hidden attributes. Fighters must be recognizable as individuals. | MEDIUM | FighterSim has archetypes + traits + nationality flavor + nicknames. Needs: hometown/city, training background ("came up at Team Alpha Male"), behavioral personality (aggressive negotiator, loyal, drama-prone). |
| **Organization prestige hierarchy with identity** | WMMA5 has GAMMA (UFC equivalent) and ALPHA-1 (PRIDE equivalent) with clear pecking order and distinct identities. Players need to understand the promotion landscape at a glance. | LOW | Already exists structurally (UCC=90, Bellator=70, ONE=75, Player=50). Could use more flavor: org descriptions, event naming conventions, and regional identity. |
| **Free agent pool with meaningful variation** | Players need fighters available to sign who are not all identical. Free agents should include unsigned prospects, released veterans, and fighters between contracts. | LOW | Exists but needs scaling. At 400-500 fighters, some percentage (15-20%) should start unsigned to give the player immediate options. |
| **Nationality-authentic names** | A Japanese fighter named "Chad Williams" breaks immersion instantly. FM's 750K database has culturally-appropriate names for every nation. | MEDIUM | Current name pools are mixed without nationality pairing. Need nationality-keyed name pools so Brazilian fighters get Brazilian names, Russian fighters get Russian names. |

### Differentiators (Competitive Advantage)

Features that would set FighterSim apart from competitors. Not expected, but create memorable moments and replay value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Player origin stories / starting scenarios** | FM26 lets you choose coaching badges, experience level, and personality that affect starting reputation and board expectations. No MMA sim does this well. Selectable backgrounds (e.g., "Former Fighter," "Rich Investor," "Gym Owner," "Reality TV Producer") with different starting budgets, rosters, prestige, and narrative hooks. | MEDIUM | This is FighterSim's biggest narrative differentiator opportunity. WMMA5 does not do this. TEW does not do this. FM does it partially. Full scenario system with 4-6 starting conditions would be unique in the MMA space. |
| **Fighter behavioral personality system** | Beyond combat attributes: how fighters behave in negotiations, interviews, camp. FM has 9 hidden personality attributes (Ambition, Controversy, Loyalty, Professionalism, etc.) that drive emergent narrative. WMMA5 has morale + personality affecting contract demands. A fighter who is "Loyal" stays when offered less; a "Drama Queen" generates headlines but is unreliable. | MEDIUM | Current system has confidence (hidden 0-100) and press conference tone. Needs 3-5 behavioral traits that actually affect game mechanics: contract acceptance, media events, locker room morale, training dedication. |
| **Training lineage / gym origin** | "Came up at AKA" or "Jackson-Wink product." Real MMA fighters are defined partly by where they trained. Assigning fighters to fictional gym lineages creates instant identity and connections between fighters (teammates, gym rivalries). | LOW | Can be done as a string field + seed data. 10-15 fictional gyms with regional/style associations. Lightweight but high narrative impact. |
| **Simulated pre-game fight history (retroactive fight log)** | Rather than just numbers (12-3 record), generate a plausible fight history at seed time: who they beat, how, what round. Players can browse a fighter's career timeline and see they beat "Marcus Johnson by KO in R2" three years ago. Creates deep illusion of a complete world. | HIGH | Most complex differentiator. Need to generate N fight result rows per fighter at seed time, with consistent opponent cross-referencing (if A beat B, B's record shows the loss to A). OOTP does this for its historical mode. |
| **Regional fighter generation by nationality** | Brazilian fighters skew toward grappling, Dagestani toward wrestling -- in stats, not just flavor text. FM's Youth Rating system ties newgen quality to nation. Different regions produce fighters at different rates with different style tendencies. | LOW | Already partially built (NATIONALITY_STYLE_MAP exists in narrative.py). Needs formalization into seed logic so nationality actually biases attribute generation. |
| **Fighter career goals** | MMA Manager has career goals (title shot, big payday, retirement). FM has "Career Plans" visible on player profiles. Fighters who want a title shot get unhappy if not booked for one; fighters motivated by money are easier to sign but demand more. | MEDIUM | Synergizes with behavioral personality. Could be 3-4 goal types: "Title Chaser," "Payday Fighter," "Legacy Builder," "Journeyman Survivor." Affects morale and contract negotiation. |
| **Generational narrative arcs at game start** | Pre-seed the world with 2-3 narrative arcs per weight class: "aging champion everyone wants to dethrone," "undefeated prospect on a collision course," "bitter rivalry between two top-5 fighters." Gives the player immediate storylines to engage with. | MEDIUM | Can be scripted at seed time. Identify top fighters per class, assign rivalry_with, create news headlines for context. High narrative impact for moderate code cost. |
| **Prospect scouting with imperfect information** | WMMA5's scouting accuracy depends on how many fights a fighter has had. FM requires extensive scouting to reveal personality. Showing estimated attribute ranges instead of exact numbers for unscouted fighters adds strategic depth and discovery. | MEDIUM | Requires UI changes (fuzzy stat bars) and a scouting mechanic. Valuable but should be deferred to post-MVP world-building. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem valuable but create problems. Explicitly choosing NOT to build these.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full AI-generated backstory prose for every fighter** | "Give every fighter a unique multi-paragraph backstory using LLM" | External API dependency violates self-contained constraint. 400+ fighters = slow seed time or API cost. Generated prose tends toward generic sameness. Quality control is impossible at scale. | Template-based bios with high variation (already built). Add more template categories and variables (50-100 template fragments) rather than generating freeform text. |
| **Real-world fighter replicas** | "Let me play with real UFC fighters" | Licensing issues. Breaks immersion of the fictional world. Maintenance burden as real rosters change. WMMA5 handles this via community mods, not built-in content. | Strong fictional identities that evoke real archetypes without copying. A Dagestani wrestler with iron_chin evokes Khabib without being Khabib. |
| **Infinite procedural fighter generation** | "Generate new fighters forever so the world never runs out" | Without constraints, procedural generation produces bland sameness. FM's newgen system is widely criticized for producing "grey blobs" that lack personality. Unconstrained generation dilutes roster identity. | Controlled generation: batch new prospects quarterly via monthly_sim (10-15 new debuts per in-game year). Retirement + controlled intake keeps pool stable at 400-500. |
| **Deeply interactive press conferences / dialogue trees** | "Let me choose what to say in press conferences with branching outcomes" | Scope explosion. Dialog tree systems are entire games unto themselves. Returns diminish rapidly after initial novelty. | Current generated press conferences are the right abstraction level. Could add 1-2 choice points ("hype the fight" vs "show respect") but not full branching dialog. |
| **Visual fighter customization editor** | "Let players customize every fighter's appearance" | Scope explosion for a text/stat-driven sim. FighterSim's identity comes from stats, traits, and narrative -- not visual appearance. Development time diverted from simulation depth. | Portrait system (already on roadmap) with pre-generated images assigned by archetype/nationality/age at seed time. Players recognize fighters by name + stats, not appearance. |
| **Full world editor / modding tools** | "Let players create and edit the entire game world" | WMMA5 and TEW ship editors, but they are mature products by established studios. For FighterSim's stage, an editor is premature scope expansion. | Seed data is code-defined and deterministic. Power users can modify seed.py directly. Editor tooling is a post-release consideration. |
| **Championship belt lineage UI** | Belt history display is satisfying but is a UI feature, not a world-building feature | Belt lineage tracking and visualization is its own milestone (already queued in PROJECT.md as "Championship belts as first-class objects"). Building it now conflates two milestones. | Track champion_id per weight class per org (minimal). Full lineage display comes in the belts milestone. |

---

## Feature Dependencies

```
Roster Scaling (400-500 fighters)
    |-- requires --> Expanded Name/Nationality Pools
    |-- requires --> Weight Class Population Balance
    |-- requires --> Org Allocation Logic (top talent in top orgs)
    |-- enables --> Meaningful Rankings (enough depth per class)
    |-- enables --> Free Agent Pool Variation
    |-- enables --> Pre-Generated Fight History (enough opponents)

Nationality-Authentic Names
    |-- requires --> Nationality-Keyed Name Pools
    |-- enhances --> Fighter Backstories (bios reference nationality)
    |-- enhances --> Training Lineage (gym location matches nationality)

Pre-Generated Fight History
    |-- requires --> Roster Scaling (need 40+ per class for cross-referencing)
    |-- requires --> Existing Champions (must know who holds belts)
    |-- enhances --> Fighter Identity (records have context)
    |-- enhances --> Generational Narrative Arcs (history supports storylines)

Existing Champions
    |-- requires --> Minimal Belt System (champion_id per weight class per org)
    |-- requires --> Weight Class Population Balance (enough fighters to crown)

Player Origin Stories
    |-- independent of --> Roster Scaling (works at any fighter count)
    |-- requires --> Org Prestige Hierarchy (starting conditions reference it)
    |-- enhances --> Replay Value

Fighter Behavioral Personality
    |-- enhances --> Contract Negotiations (already exists)
    |-- enhances --> Press Conferences (already exists)
    |-- enhances --> News Headlines (already exists)
    |-- synergizes with --> Fighter Career Goals

Training Lineage / Gym Origin
    |-- independent --> Can be added at any point
    |-- enhances --> Fighter Identity
    |-- enhances --> Regional Fighter Generation

Generational Narrative Arcs
    |-- requires --> Existing Champions
    |-- requires --> Roster Scaling (need enough ranked fighters)
    |-- enhances --> Pre-Generated Fight History (arcs reference history)

Prospect Scouting
    |-- requires --> Fighter Behavioral Personality (something to scout for)
    |-- requires --> UI Changes (fuzzy stat display)
    |-- conflicts with --> Current transparent stat display paradigm
```

### Dependency Notes

- **Roster Scaling requires Expanded Pools:** 100 fighters uses 80 first names x 80 last names. 400-500 fighters with unique names needs 150+ first names, 150+ last names minimum, with nationality-keyed selection to avoid cross-cultural name collisions.
- **Pre-Generated Fight History requires Roster Scaling:** Cross-referencing opponents only works if there are enough fighters in each weight class (40+) to avoid everyone having fought everyone. At 80-100 per class, a fighter with 15 fights has fought maybe 15-20% of the division, which feels realistic.
- **Player Origin Stories are independent:** This can be built at any point and overlaid on any roster size. It modifies starting conditions (org prestige, bank, initial roster), not the fighter database itself.
- **Champions require Minimal Belt System:** Currently belts are implied by is_title_fight on Fight model but there is no champion tracking. Need at minimum a champion_id field per weight class per org, or a lightweight Champion model.
- **Scouting conflicts with current transparency:** Currently all fighter stats are visible to the player. Adding scouting means hiding information, which changes the entire UX paradigm. This is valuable but must be a deliberate design decision, not an afterthought.

---

## MVP Definition

### Launch With (v1 - World-Building Foundation)

These create the "lived-in world" feel with minimum viable scope.

- [ ] **Nationality-authentic names** -- Foundation that makes every other feature more immersive. Nationality-keyed name pools.
- [ ] **Roster scaling to 400-500 fighters** -- Core requirement. Everything else builds on having enough fighters to populate a world.
- [ ] **Weight class population balance** -- Deterministic allocation (80-100 per class, not random).
- [ ] **Career-stage distribution** -- Intentional age/record/archetype distribution across prospects, rising, prime, veteran, and legend tiers.
- [ ] **Existing champions at game start** -- Minimal belt system + seed logic to crown champions per weight class per org.
- [ ] **Training lineage / gym origin** -- String field, 10-15 fictional gyms assigned at seed time. Low effort, high narrative return.

### Add After Validation (v1.x)

Features to add once the expanded roster feels right.

- [ ] **Player origin stories** -- 4-6 selectable starting scenarios with different budgets, prestige, narrative hooks, and mechanical constraints.
- [ ] **Fighter behavioral personality** -- 3-5 personality traits (Loyal, Ambitious, Drama-Prone, Professional, Mercenary) affecting contracts, morale, media events.
- [ ] **Generational narrative arcs** -- 2-3 pre-seeded storylines per weight class (aging champion, undefeated prospect, bitter rivalry) with supporting news headlines.
- [ ] **Regional attribute biasing** -- Nationality actually influences attribute generation in seed logic, not just bio flavor text.

### Future Consideration (v2+)

Features to defer until world-building foundation is proven.

- [ ] **Simulated pre-game fight history** -- Full retroactive fight logs with cross-referenced opponents. Highest complexity feature; needs the foundation first.
- [ ] **Fighter career goals** -- Goal types (Title Chaser, Payday Fighter, Legacy Builder) affecting morale and decisions. Needs behavioral personality system first.
- [ ] **Prospect scouting with imperfect information** -- Requires deliberate UI overhaul and design decisions about information transparency paradigm.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Nationality-authentic names | HIGH | MEDIUM | P1 |
| Roster scaling (400-500) | HIGH | HIGH | P1 |
| Weight class balance | HIGH | LOW | P1 |
| Career-stage distribution | HIGH | MEDIUM | P1 |
| Existing champions | HIGH | LOW | P1 |
| Training lineage / gym origin | MEDIUM | LOW | P1 |
| Player origin stories | HIGH | MEDIUM | P2 |
| Behavioral personality | MEDIUM | MEDIUM | P2 |
| Generational narrative arcs | MEDIUM | MEDIUM | P2 |
| Regional attribute biasing | MEDIUM | LOW | P2 |
| Simulated fight history | HIGH | HIGH | P3 |
| Fighter career goals | MEDIUM | MEDIUM | P3 |
| Prospect scouting | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for world-building milestone launch
- P2: Should have, add in follow-up phase
- P3: Nice to have, future milestone

---

## Competitor Feature Analysis

| Feature | WMMA5 | TEW IX (CornellVerse) | Football Manager 26 | MMA Manager | FighterSim Approach |
|---------|-------|----------------------|---------------------|-------------|---------------------|
| **Pre-built world** | Default database with orgs, fighters, history | CornellVerse has decades of fictional history, 60+ promotions, named characters | 750K+ real people with full career data | 940+ AI fighters across 10 promotions | Fictional world with 400-500 fighters, 4-5 orgs, seeded history |
| **Fighter personality** | Morale + personality affecting contract demands | Relationships + personality affecting storylines | 9 hidden personality attributes (1-20 scale) producing labels like "Ambitious" | Greed, happiness, bad habits, career goals | Start with 3-5 behavioral traits (Loyal, Ambitious, Drama-prone, Professional, Mercenary) |
| **Career stages** | Rising, peaking, prime, declining | Workers have career arcs | Youth, developing, peak, declining | Aging + retirement | Formalize into 5 stages: Prospect, Rising, Prime, Veteran, Legend |
| **Manager origin** | Choose org to manage, no backstory | Choose promotion to book | Choose badges, experience, personality, coaching style | Start from scratch | Selectable origin stories with mechanical differences -- novel for MMA sims |
| **Champion system** | Full belt system with history | Championship tracking per promotion | League tables, cups, titles | Titles across promotions | Minimal belt system: champion_id per weight class per org |
| **Roster scale** | Hundreds of fighters | Thousands of workers | 750K+ database (load 120-150K) | 940+ fighters | 400-500 fighters (right-sized for indie scope) |
| **Scouting** | Accuracy depends on fighter's fight count | Scout workers before hiring | Full scouting system with reports | Basic fighter viewing | Defer -- start with transparency, add scouting later |
| **Newgen/intake** | Auto-fills talent gaps when shortage | Workers debut regularly | Annual youth intake per club, personality inherited from Head of Youth Development | Continuous procedural generation | Controlled: 10-15 new prospects per in-game year via monthly_sim |
| **World editor** | Detailed editor included | Robust modding via community | Pre-Game Editor (free tool) | No editing | Not building an editor. Seed data is code-defined. |
| **Name authenticity** | Not detailed in sources | Pre-written character names | Real-world database with authentic names | Procedural with nationality variance | Nationality-keyed name pools (Brazilian names for Brazilians, etc.) |

---

## Key Insights from Research

1. **The CornellVerse is the gold standard for fictional sports worlds.** TEW IX ships with a fictional universe that has decades of pre-written history, named characters with backstories, and interconnected promotion hierarchies. This level of handcrafted detail is what creates the "lived-in" feeling. FighterSim should aim for a similar feel but at smaller scale -- 400-500 fighters with enough seed-time narrative to feel real.

2. **Football Manager's personality system is the gold standard for hidden attributes driving emergent narrative.** Nine personality attributes, each rated 1-20, combine to produce personality labels ("Ambitious," "Professional," "Temperamental") that players learn to read and value over time. The Head of Youth Development's personality even influences newgen personalities. FighterSim should adopt a simplified version: 3-5 behavioral traits that affect mechanics, not just flavor text.

3. **Roster scale matters more than individual depth.** MMA Manager ships with 940 fighters and basic personality (greed, happiness, goals). WMMA5 has hundreds with deep attributes. The pattern is clear: you need enough fighters that the world feels populated, even if individual backstories are thin. 400-500 with moderate depth beats 100 with deep backstories every time.

4. **Nobody in the MMA sim space does player origin stories well.** This is FighterSim's clearest opportunity for differentiation. FM26's manager creation is the closest analog (choose badges, experience, personality), and it only appeared in its current form recently. An MMA sim with selectable starting scenarios would be novel in the genre.

5. **Champions at game start are non-negotiable.** Every competitor has this. FighterSim's current seed creates 100 fighters with no champions, no belts, no title history. This is the single biggest gap for the "lived-in world" feeling. Fix this first.

6. **Controlled generation beats infinite generation.** FM's newgen system is widely criticized for producing "grey blobs" that lack personality. MMA Manager's 940 procedural fighters are functional but forgettable. The key insight from WMMA5 and TEW: auto-fill gaps when needed, but cap total population and ensure quality over quantity. Target 400-500 and maintain that level through retirement + controlled intake.

7. **Training lineage is low-cost, high-impact.** Real MMA conversation constantly references gyms ("AKA product," "Jackson-Wink fighter"). Adding a gym_origin string field and 10-15 fictional gyms at seed time is perhaps the best effort-to-immersion ratio feature on this list.

---

## Sources

- [Grey Dog Software - WMMA5 Official Page](https://greydogsoftware.com/title/world-of-mixed-martial-arts-5/) -- MEDIUM confidence (official but limited feature detail)
- [WMMA5 Player's Handbook](https://hansmellman.github.io/wmma5-players-handbook/) -- HIGH confidence (community-maintained detailed reference covering attributes, morale, personality, career cycles, regional systems)
- [WMMA5 Style Archetypes Analysis](https://fuldapocalypsefiction.com/2022/04/09/wmma5-style-archetypes/) -- MEDIUM confidence (detailed community analysis of fighter differentiation)
- [WMMA5 Review - Pure Evil MMA](https://pureevilmma.wordpress.com/2020/05/08/world-of-mixed-martial-arts-5-game-review/) -- MEDIUM confidence (detailed user review)
- [TEW IX Official Page](https://greydogsoftware.com/title/total-extreme-wrestling-ix-2/) -- MEDIUM confidence (official, CornellVerse/TEWverse details)
- [CornellVerse Wiki](https://en.wikipedia.org/wiki/Extreme_Warfare) -- MEDIUM confidence (Wikipedia, cross-referenced)
- [FM26 Manager Creation - Official](https://www.footballmanager.com/the-dugout/creating-your-manager-fm26) -- HIGH confidence (official Sports Interactive documentation)
- [FM26 Personality Guide - FM Scout](https://www.fmscout.com/a-guide-to-player-personalities-football-manager.html) -- HIGH confidence (well-sourced community guide, verified against multiple sources)
- [FM Youth Intake Guide - Passion4FM](https://www.passion4fm.com/youth-intake-guide-how-clubs-produce-newgens/) -- MEDIUM confidence (community guide corroborated by official FM documentation)
- [OOTP Fictional League Wizard - Official Manual](https://manuals.ootpdevelopments.com/index.php?man=ootp16&page=fictional_wizard) -- HIGH confidence (official OOTP manual)
- [MMA Manager Features - GM Games](https://gmgames.org/section/mma-manager-and-ufc-simulator-games/) -- MEDIUM confidence (aggregator, feature list verified)
- [Indie Dev Guide to Fictional Sports Worlds - Wayline](https://www.wayline.io/blog/indie-devs-guide-parallel-dimension-sports-sims-without-real-world-licenses) -- LOW confidence (single source, general advice, useful for design philosophy)
- [FM Database Size - Passion4FM](https://www.passion4fm.com/how-to-set-up-your-database-size-in-football-manager/) -- HIGH confidence (well-documented, 750K+ figure widely cited)

---
*Feature research for: FighterSim World-Building Milestone*
*Researched: 2026-03-01*
