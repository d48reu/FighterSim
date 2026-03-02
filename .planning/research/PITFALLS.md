# Domain Pitfalls

**Domain:** MMA management simulator -- world-building depth expansion (100 to 400-500 fighters with pre-generated histories, player origin stories, fighter identity systems)
**Researched:** 2026-03-01

## Critical Pitfalls

Mistakes that cause rewrites, broken game feel, or player disengagement at the world-building layer. These are specific to FighterSim's codebase and the domain of MMA management sims.

---

### Pitfall 1: Archetype Distribution Collapse at Scale

**What goes wrong:** The current `_assign_archetype()` function in `seed.py` uses a waterfall of if/elif checks with the final fallback being `Archetype.PHENOM`. At 100 fighters this produces a tolerable distribution. At 500 fighters, simulation shows **69% Phenom, 24.8% Journeyman, 4.6% Gatekeeper, 0.8% GOAT Candidate, 0.8% Shooting Star, and 0% Late Bloomer**. The GOAT Candidate cap (2 per weight class = 10 max) is correct, but Phenom becomes a garbage-bin category for everyone who does not fit the narrow criteria of other archetypes.

**Why it happens:** The archetype conditions were tuned for a 100-fighter seed where the attribute range (40-92 uniform random) and age range (20-37) naturally produce enough variety. At 5x scale, the narrow windows for Late Bloomer (`overall < 62 AND prime_start 29-31`) and Shooting Star (`overall >= 68 AND prime_end <= 29 AND cardio < 60`) capture almost nobody. Meanwhile, any fighter with `wins > losses` who does not match another archetype falls to the Phenom default.

**Consequences:** Fighters all feel the same. The narrative engine generates similar bios, the trait assignment pools cluster around Phenom pools, and the player sees a sea of indistinguishable "Phenoms" -- exactly the problem the world-building milestone is trying to solve.

**Prevention:**
1. Redesign archetype assignment as a **scoring system** rather than a waterfall. Each archetype gets a score based on how well the fighter fits, and the highest-scoring archetype wins (with ties broken by weighted random).
2. Set **target distribution quotas** per weight class (e.g., 15% Phenom, 15% GOAT Candidate, 20% Gatekeeper, 25% Journeyman, 10% Late Bloomer, 15% Shooting Star) and use the scoring system to fill quotas.
3. Widen the attribute/age criteria for underrepresented archetypes at higher fighter counts.
4. Add validation: after seeding, assert that no archetype exceeds 35% of total fighters.

**Detection:** After any seed run, check `SELECT archetype, COUNT(*) FROM fighters GROUP BY archetype`. If any single archetype exceeds 40%, the distribution is broken.

**Phase:** Must be addressed in the very first phase of world-building, before fighter pool expansion. Scaling to 500 fighters without fixing this makes the problem 5x worse.

**Confidence:** HIGH -- verified by simulation against current code.

---

### Pitfall 2: Record-Stats Incoherence ("Paper Champions")

**What goes wrong:** Pre-generated fight records (wins, losses, ko_wins, sub_wins) do not match the fighter's actual attributes. A fighter with 45 striking and 42 grappling should not have a 25-3 record with 18 KO wins. Conversely, an 85-overall fighter should not have a losing record unless they are a Late Bloomer or Journeyman. The current `_gen_record()` function generates records based solely on age, then `_adjust_record_for_archetype()` only adjusts GOAT Candidates and Shooting Stars.

**Why it happens:** When you scale from 100 to 500 fighters and add pre-generated backstories, the mismatch between narrative ("devastating striker from Brazil") and numbers (striking: 47, record: 3-12) becomes glaringly obvious. At 100 fighters, players skim past this. At 500 with deeper identity text, every fighter card invites scrutiny.

**Consequences:** Players lose trust in the simulation. "Why does this guy have a 20-2 record if his stats are garbage?" destroys the feeling that the world is real. This is the number one complaint about procedurally generated rosters in WMMA community forums -- regens that "don't make sense."

**Prevention:**
1. Generate records **from** attributes, not independently of them. High-overall fighters get better records; low-overall fighters get worse records. Use overall rating as the primary input to win rate probability.
2. Finish method distribution must correlate with stats: high striking = more KO wins, high grappling = more sub wins.
3. Archetype should influence record shape: Gatekeepers should have roughly .500 records with many fights; Phenoms should have short records with high win rates; Journeymen should have long records with losing records.
4. Add a **coherence validation pass** after generation: for each fighter, check that `overall > 70 implies win_rate > 0.55` and `overall < 55 implies win_rate < 0.50`, with archetype exceptions.

**Detection:** After seeding, query for fighters where `overall >= 75 AND wins < losses` (should only be Late Bloomers) or `overall <= 50 AND wins > losses * 2` (should be zero). Flag any violations.

**Phase:** Must be addressed alongside fighter pool expansion -- they are the same task. You cannot meaningfully scale the roster without fixing this.

**Confidence:** HIGH -- verified by code inspection of `_gen_record()` which uses no attribute inputs.

---

### Pitfall 3: Pre-Generated History Without Corresponding Fight Records

**What goes wrong:** The PROJECT.md specifies "pre-existing records, champions, rivalries, veterans, prospects" -- a lived-in world where the sport existed before the player. But Fight records in the database only exist for fights the simulation has actually run. If a 32-year-old veteran has a 28-6 record at game start, there are 0 Fight rows in the database for those 34 fights. This means: no career timeline, no rivalry detection (which requires 2+ Fight records between the same pair), no quality-of-opposition for rankings, no headline history.

**Why it happens:** The current system stores W-L-D numbers on the Fighter model but these are just integers -- they are not backed by actual Fight objects. The narrative and ranking systems assume Fight rows exist. Adding "history" text without Fight rows creates a Potemkin village: the stories exist but the data systems cannot see them.

**Consequences:**
- Career timeline view shows nothing for pre-game history.
- Rankings quality-of-opposition calculation has no data for pre-game fights, so all fighters start with zero ranking score regardless of record.
- Rivalry detection finds no rivalries at game start even though the world should have established rivalries.
- The "lived-in world" feels hollow the moment the player clicks on any fighter detail view.

**Prevention:**
1. **Generate historical Fight rows** at seed time. For each fighter's pre-game record, create skeleton Fight records with opponents drawn from the same weight class and era. These do not need full tick-by-tick simulation -- they need: winner_id, method, round_ended, and a brief narrative string.
2. Create historical Event rows that these fights belong to (AI org events from "before the game started").
3. Use the historical fights to seed the rankings system so opening rankings reflect the pre-game world.
4. Generate 2-3 established rivalries per weight class by having specific fighter pairs fight 2-3 times in the historical record.
5. **Critical constraint:** Historical fights must not go through the full fight engine (too slow for hundreds of fights at seed time). Use a lightweight result generator that produces statistically appropriate outcomes.

**Detection:** After seeding, query `SELECT COUNT(*) FROM fights` -- if this returns 0 at game start, the lived-in world is fake. Also check `SELECT COUNT(*) FROM fights WHERE fighter_a_id = X OR fighter_b_id = X` for any veteran fighter.

**Phase:** This is the core of the "lived-in world" milestone and should be a dedicated phase. It depends on having the scaled fighter pool and fixed archetype distribution first.

**Confidence:** HIGH -- verified by code inspection. The Ranking module's `rebuild_rankings()` and `update_rivalries()` both query the Fight table, which is empty at game start.

---

### Pitfall 4: Nationality Distribution Unrealism

**What goes wrong:** The current seed uses `rng.choice(_NATIONALITIES)` with a uniform distribution across 23 nationalities. At 500 fighters, this produces approximately equal numbers of American (18), Jamaican (18), and Dagestani (21) fighters. Real MMA is heavily dominated by the United States (~35% of ranked UFC fighters), Brazil (~15%), and Russia (~8%), with other nations contributing smaller shares. A uniform distribution makes the world feel obviously artificial.

**Why it happens:** `rng.choice()` on a flat list gives equal probability to every option. This was invisible at 100 fighters but becomes obviously wrong at 500.

**Consequences:** Players who know anything about MMA will immediately notice that Jamaica has as many fighters as the United States. It breaks immersion before the player even starts playing. It also means the NATIONALITY_STYLE_MAP in `narrative.py` (which maps nationalities to fighting styles) produces an unrealistic style distribution.

**Prevention:**
1. Replace uniform `rng.choice()` with `rng.choices()` using a weighted distribution. Example weights: American 25%, Brazilian 15%, Russian 8%, British 5%, Mexican 5%, Irish 3%, etc.
2. Validate the distribution after seeding: top 3 nationalities should represent at least 40% of fighters.
3. Consider weight-class-specific nationality biases (heavier classes historically have more Eastern European fighters; lighter classes have more Asian and South American fighters).

**Detection:** After seeding, `SELECT nationality, COUNT(*) FROM fighters GROUP BY nationality ORDER BY COUNT(*) DESC`. If the top nationality has fewer than 15% of fighters, the distribution is wrong.

**Phase:** Address alongside fighter pool expansion. Simple fix (change one line) but significant immersion impact.

**Confidence:** HIGH -- verified by simulation against current code.

---

### Pitfall 5: Name Pool Exhaustion and Cultural Incoherence

**What goes wrong:** The current seed has 80 first names and 80 last names, giving 6,400 unique combinations. At 500 fighters the collision retry loop works (only ~20 retries total), but the **cultural incoherence** is worse: the system can produce "Yusuf Eriksson" (Arabic first + Swedish last) or "Bjorn Garcia" (Norse first + Spanish last). At 100 fighters, these occasional oddities are ignorable. At 500 with full backstories, a "Dagestani" fighter named "Patrick O'Brien" is immersion-breaking.

**Why it happens:** First and last names are drawn from independent flat pools with no nationality correlation. The seed assigns nationality independently of name selection.

**Consequences:** Fighters feel procedurally generated rather than like real people. This directly undermines the stated goal: "Fighters are people with backstories, personalities, and reputations -- not procedurally generated stat blocks."

**Prevention:**
1. Create **nationality-keyed name pools**. Each nationality gets its own list of culturally appropriate first and last names.
2. Generate name after nationality assignment, drawing from that nationality's pool.
3. Allow controlled cross-cultural names (e.g., 10% chance of a "diaspora" name for fighters from multicultural countries like the US, Brazil, UK) to add realism without making it the default.
4. Expand name pools to 30+ first and 30+ last names per nationality to avoid repetition within national groups.

**Detection:** Manual review of seed output: scan for names that do not match nationality. Automated: check that fighters sharing a nationality have names drawn from the same cultural pool.

**Phase:** Address during fighter pool expansion. This is a data task (building name pools) that should happen before the scaling code runs.

**Confidence:** HIGH -- verified by code inspection of `_random_name()` which draws from global pools ignoring nationality.

---

## Moderate Pitfalls

### Pitfall 6: Monthly Sim Performance at 5x Scale

**What goes wrong:** The `sim_month()` function iterates over `all_fighters` (line 1642-1644: `select(Fighter).where(Fighter.is_retired == False)`) multiple times per tick. At 100 fighters with the current ~120-170ms timing, scaling to 500 active fighters could push this past the 2-second target, especially considering:
- `_age_fighter()` loops through all fighters
- `_process_retirements()` loops through all fighters again
- `_ai_sign_free_agents()` loads all fighters and builds multiple filtered lists
- `decay_hype()` loads all fighters
- Each AI event simulates 4-8 fights with full fight engine calls

**Prevention:**
1. Profile `sim_month()` at 500 fighters before committing to the architecture. If it exceeds 500ms, optimize hot paths.
2. Consolidate the multiple `select(Fighter).where(is_retired == False)` queries into a single load cached in a local variable.
3. Consider batch updates for aging (single UPDATE statement with CASE) instead of per-fighter ORM operations.
4. The fight engine itself is fast (~2ms per fight); the bottleneck will be ORM overhead from loading/flushing 500 fighter objects.

**Detection:** Add timing instrumentation to `sim_month()` in the test suite. Run `test_cli.py` with 500 fighters and check the 3-month sim timing.

**Phase:** Validate early (during or immediately after pool expansion) but optimize only if measured performance is a problem. Do not prematurely optimize.

**Confidence:** MEDIUM -- the current code is designed for 100 fighters, and the ROADMAP already notes "sim_month() completes in ~120-170ms regardless of roster size" but this was never tested at 500.

---

### Pitfall 7: "Wall of Text" Backstory Fatigue

**What goes wrong:** Adding deep backstories to 500 fighters creates a paradox: depth requires text, but 500 multi-paragraph backstories are too much content. Players do not read 500 bios. The effort of generating rich backstories is wasted if the player only cares about 20-30 fighters at a time. Worse, if backstory templates are not varied enough, players notice repetition within the first 10 fighters they click on.

**Why it happens:** WMMA-style games solve this by having backstories emerge from simulated history rather than pre-written text. FighterSim's `narrative.py` already uses template-based bios, but the template pool needs to be dramatically larger at 500 fighters. The ROADMAP's "Lessons Learned" section already notes: "Bio templates need 3+ variants per category or repetition becomes obvious immediately."

**Consequences:** Players either skip all backstories (wasted development effort) or read enough to spot patterns and feel the procedural seams. Neither outcome achieves the goal of fighters feeling like "real people."

**Prevention:**
1. **Layered disclosure**: Short one-line "hook" visible in fighter lists; full bio only on click/expand. Invest quality in hooks, not length in bios.
2. **Template multiplication through combination**: Instead of 5 full-bio templates, use modular components (origin sentence + training sentence + career sentence + personality sentence) with 10+ variants each. 10x10x10x10 = 10,000 unique combinations from 40 templates.
3. **Prioritize distinctiveness over depth**: A fighter's one memorable trait (e.g., "Missed weight 3 times," "Never been knocked down," "Former rugby player") is worth more than 3 paragraphs of generic backstory.
4. **Let history speak**: The pre-generated fight records (Pitfall 3) ARE the backstory. A career timeline showing 8 first-round KOs is more evocative than a paragraph saying "known for his devastating power."

**Detection:** Have 3 people click through 20 random fighters and note which ones "feel the same." If more than 30% feel samey, templates need more variety.

**Phase:** Parallel with fighter identity depth. Do not try to write 500 unique bios -- invest in the modular template system instead.

**Confidence:** HIGH -- validated by the project's own Lessons Learned and by procedural generation literature (Tanya X. Short: "worry about samey, boring blandness, not chaos").

---

### Pitfall 8: Player Origin Stories That Do Not Affect Gameplay

**What goes wrong:** The PROJECT.md lists "selectable backgrounds with different starting conditions" as an active requirement. The common mistake is making origin stories purely cosmetic -- a paragraph of flavor text at game start that changes nothing mechanical. Players quickly learn that the choice does not matter and the replay value promised by multiple origins is fake.

**Why it happens:** It is easier to write flavor text than to design divergent starting conditions that are meaningfully different without being unfairly balanced. Changing starting budget is trivial; changing starting roster, reputation, and AI behavior requires deeper system integration.

**Consequences:** Players feel deceived. "Choose your background" followed by identical gameplay is worse than no choice at all because it sets expectations and then fails to meet them.

**Prevention:**
1. Each origin must change at least 3 mechanical dimensions: starting budget, starting prestige, starting roster size/quality, AI org relationships, and/or first-month events.
2. Example origins with real mechanical teeth:
   - **Regional promoter**: Low budget ($1M), low prestige (30), 8 cheap fighters, but no rival attention early.
   - **TV executive's pet project**: Medium budget ($5M), medium prestige (50), broadcast deal locked in, but must meet event pace or lose everything.
   - **Former champion turned promoter**: Low budget ($2M), high starting prestige (65), one elite fighter on roster, but high salary obligations.
3. Validate that each origin produces a distinguishable first 6 months of gameplay through test runs.

**Detection:** Play the first 6 months with each origin. If you make the same decisions in the same order, the origins are not differentiated enough.

**Phase:** This should be a separate phase after the core world-building (fighter pool, histories, identities) because origins depend on having a rich world to place the player into.

**Confidence:** MEDIUM -- based on design analysis and sports management sim community patterns. No codebase evidence for or against.

---

### Pitfall 9: services.py Growing Past Maintainability

**What goes wrong:** `api/services.py` is already 3,700 lines of business logic. Adding world-building features (historical fight generation, backstory generation, origin story setup, expanded seed logic, identity systems) could push it past 5,000 lines. At that point, finding and modifying code becomes a significant development drag. The file already handles contracts, events, fights, rankings, development, sponsorships, reality shows, and more.

**Why it happens:** The architectural decision to centralize all business logic in one file was practical at smaller scale. The constraint "All business logic in api/services.py" from CLAUDE.md is becoming a liability.

**Consequences:** Merge conflicts in a single-developer project are not an issue, but cognitive load is. When one function change in services.py can break 15 other functions due to shared state, development slows dramatically.

**Prevention:**
1. World-building code should live in `simulation/` modules, not in services.py. The existing pattern (fight_engine.py, monthly_sim.py, narrative.py, seed.py, traits.py) is the right home.
2. New modules to create: `simulation/history.py` (historical fight generation), `simulation/identity.py` (fighter backstory/personality systems), `simulation/origins.py` (player origin story logic).
3. services.py should only **call** these modules, not contain the implementation. This follows the existing pattern where services.py calls `simulate_fight()` from fight_engine.py rather than containing fight logic.
4. Update the constraint to: "services.py orchestrates; simulation/ modules implement."

**Detection:** Track `wc -l api/services.py` after each milestone. If it grows by more than 300 lines during world-building, logic that belongs in simulation/ leaked into services.

**Phase:** Establish the module structure at the start of world-building, before writing any new feature code. Create the empty files with docstrings as the first commit.

**Confidence:** HIGH -- verified by line count (3,698) and the existing modular pattern in simulation/.

---

## Minor Pitfalls

### Pitfall 10: Deterministic Seed Brittleness

**What goes wrong:** The current seed uses `random.Random(42)` for deterministic generation. Any change to the generation order (adding a new field, changing an if/else branch, inserting a new `rng.randint()` call) changes the entire downstream sequence. Fighter #50 gets completely different attributes because fighter #49's generation consumed one extra random call. This makes iterative development painful -- every tweak requires visually re-validating the entire 500-fighter output.

**Prevention:**
1. Use **per-fighter sub-seeds**: `fighter_rng = random.Random(main_seed + fighter_index)` so that changes to one fighter's generation do not cascade to others.
2. Alternatively, use a two-pass approach: first pass generates all fighter IDs and basic attributes with the main RNG; second pass adds detailed attributes with per-fighter RNGs seeded by fighter ID.
3. Accept that some determinism will be lost during active development and only lock down the final seed for release.

**Detection:** Change one attribute range and diff the full seed output. If more than 10% of fighters change, the seed is too fragile.

**Phase:** Address early, during the seed refactor for pool expansion. Retrofitting per-fighter seeds later is much harder.

**Confidence:** HIGH -- verified by code inspection of seed.py's single-RNG architecture.

---

### Pitfall 11: Weight Class Population Imbalance

**What goes wrong:** At 500 fighters with `rng.choice(weight_classes)`, each of the 5 weight classes gets ~100 fighters. But the game needs different populations per class to feel realistic -- Heavyweight historically has fewer fighters, Lightweight and Welterweight are the most stacked divisions. Additionally, with retirement removing fighters over time, unpopulated classes can become barren if not replenished.

**Prevention:**
1. Use weighted distribution for weight classes: Lightweight 25%, Welterweight 25%, Middleweight 20%, Heavyweight 15%, Flyweight 15%.
2. Build a fighter replenishment system into monthly_sim (new prospects enter free agency periodically) to replace retired fighters.
3. Validate minimum viable population per weight class at game start (at least 60 per class for matchmaking to work across 4 orgs).

**Detection:** After seeding, check `SELECT weight_class, COUNT(*) FROM fighters GROUP BY weight_class`. Also run a 12-month sim and verify no class drops below 40 active fighters.

**Phase:** Fighter pool expansion phase.

**Confidence:** MEDIUM -- distribution issue verified by code, but replenishment system is speculative.

---

### Pitfall 12: Backstory-Trait Contradictions

**What goes wrong:** A fighter gets the backstory "Known for devastating knockout power, this striker terrorizes opponents on the feet" but has the trait `submission_magnet` and stats of striking: 45, grappling: 80. The identity system and the trait/stat system tell different stories.

**Prevention:**
1. Generate backstory **after** traits and stats are finalized, using them as inputs.
2. The modular template system (Pitfall 7) should include conditional gates: striking-focused backstory components only fire if `striking >= 65`.
3. Run a consistency check: for each fighter, verify that backstory keywords align with top-2 stats and assigned traits.

**Detection:** Automated: parse generated backstory text for keywords ("striker," "knockout," "grappler," "submission") and compare against actual top stat. Flag mismatches.

**Phase:** During fighter identity depth work, after stats and traits are finalized.

**Confidence:** HIGH -- the project's own Lessons Learned documents this exact class of bug (age-inappropriate language in bios, archetype-record contradictions).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Fighter pool expansion (100 to 500) | Archetype collapse (Pitfall 1), name-nationality incoherence (Pitfall 5), nationality distribution (Pitfall 4), record-stats incoherence (Pitfall 2) | Fix archetype scoring, build nationality-keyed name pools, add weighted distributions, generate records from attributes. Validate all distributions after every seed run. |
| Pre-generated histories | Empty Fight table at game start (Pitfall 3), performance at scale (Pitfall 6) | Build lightweight historical fight generator in simulation/history.py. Profile seed timing at 500 fighters with 5,000+ historical fights. |
| Fighter identity depth | Wall of text fatigue (Pitfall 7), backstory-trait contradictions (Pitfall 12) | Modular template system with conditional gates. Short hooks over long bios. Let fight records be the primary narrative. |
| Player origin stories | Cosmetic-only origins (Pitfall 8) | Each origin must change 3+ mechanical dimensions. Test by playing 6 months with each. |
| All phases | services.py bloat (Pitfall 9), RNG brittleness (Pitfall 10), weight class imbalance (Pitfall 11) | Establish module structure early. Use per-fighter sub-seeds. Validate distributions continuously. |

## Sources

- [ZenGM: So You Want to Write a Sports Sim Game](https://zengm.com/blog/2019/07/so-you-want-to-write-a-sports-sim-game/) -- iterative development advice for sports sims
- [Gamasutra/Game Developer: Devs Weigh In on Procedural Generation](https://www.gamedeveloper.com/design/devs-weigh-in-on-the-best-ways-to-use-but-not-abuse-procedural-generation) -- Tanya X. Short on "samey blandness" vs chaos in procedural generation
- [WMMA5 Community Discussions](https://forum.greydogsoftware.com/topic/44604-wmma5-small-questions-thread/) -- fighter regen quality complaints, distribution issues
- [Football Manager Player Personalities](https://fminside.net/guides/basic-guides/30-personalities-in-football-manager) -- how FM handles 40 personality types; "Balanced" as the most common but least interesting
- [Grey Dog Software: WMMA5](https://greydogsoftware.com/title/world-of-mixed-martial-arts-5/) -- reference implementation for MMA management world-building
- [SQLAlchemy 2.0 Sessions Documentation](https://docs.sqlalchemy.org/en/20/faq/sessions.html) -- flush/commit performance strategies for bulk operations
- FighterSim codebase: direct code inspection of seed.py, monthly_sim.py, narrative.py, models.py, traits.py (HIGH confidence -- primary evidence source)
