# FighterSim Roadmap Backlog

> GitHub issue creation is currently blocked by token permissions (`Resource not accessible by personal access token`), so this file is the canonical issue-ready backlog for now.

## Current Product Thesis

FighterSim is no longer missing core systems. The job now is to turn the existing simulation into a clear, compelling management game where the player can:
- identify value
- build profitable and prestigious cards
- shape roster identity over time
- compete against rival organizations in a living ecosystem

The next roadmap should prioritize decision quality and game loop strength over raw feature count.

---

## Priority Order

1. Recommendation labels for contracts and roster decisions
2. Booking recommendation engine in event builder
3. Expiring contracts and roster decision center
4. Scouting / prospect discovery board
5. Fighter morale, loyalty, and negotiation depth
6. Rival org strategy and bidding wars
7. Media, rivalry, and popularity loops
8. Title-picture and divisional politics improvements

---

## Backlog Items

### 1. Recommendation labels for contracts and roster decisions
Priority: P0
Suggested issue title: `Roadmap: add recommendation labels for contracts and roster decisions`

Goal:
Turn visible market data into immediate player guidance.

Scope:
- Add labels such as:
  - Buy Now
  - Fair Price
  - Overpay Risk
  - Sell Soon
  - High-Leverage Renewal
  - Low-Interest Asset
- Surface them in:
  - Free Agents
  - Roster
  - Expiring Contracts
  - Show contestant signing list
- Back labels with deterministic logic from current `market_context` and `offer_evaluation`.

Acceptance criteria:
- Recommendation labels appear anywhere the player signs, renews, or evaluates fighter value.
- API returns a normalized recommendation field.
- Frontend shows labels consistently and colorfully.
- Tests cover recommendation generation and rendering.

Why now:
This is the fastest path from “visible data” to “playable decisions.”

---

### 2. Booking recommendation engine in event builder
Priority: P0
Suggested issue title: `Roadmap: add matchmaking recommendations to the event builder`

Goal:
Help the player build better cards faster.

Scope:
- Add recommended matchups using current roster + available free agents where relevant.
- Suggest:
  - best main event
  - best co-main
  - best prospect development fight
  - best “safe money” fight
- Show reasons:
  - booking value
  - competitiveness
  - star power
  - prospect risk
  - projected profit / prestige contribution

Acceptance criteria:
- Event screen exposes a recommendation section or smart autofill actions.
- At least the top 3 matchup suggestions are shown with reasons.
- Player can click a recommendation to add the matchup directly.
- Tests cover ranking/scoring behavior for recommendations.

Why now:
Booking should become the center of the management loop.

---

### 3. Expiring contracts and roster decision center
Priority: P0
Suggested issue title: `Roadmap: build an expiring contracts and roster decision center`

Goal:
Create a clear “what do I do now?” contract-management surface.

Scope:
- Add a dedicated dashboard or panel for:
  - contracts expiring soon
  - bad contracts
  - roster surplus by division
  - divisions needing reinforcements
  - salary efficiency / value-over-cost readouts
- Add recommendation actions:
  - Renew
  - Wait
  - Release
  - Replace

Acceptance criteria:
- Player can review all near-term contract problems in one place.
- Contract rows include value context and recommendation labels.
- Roster pressure / imbalance is shown per weight class.
- Tests cover contract-center data derivation.

Why now:
This creates a real retention / churn game instead of passive roster ownership.

---

### 4. Scouting and prospect discovery board
Priority: P1
Suggested issue title: `Roadmap: add scouting and prospect discovery systems`

Goal:
Make acquisition more interesting than browsing a static list.

Scope:
- Add scouting board with discovered prospects.
- Add scout-quality / uncertainty mechanics.
- Surface “heard about this guy” leads and prospect pipelines.
- Optionally add region, archetype, and upside-based scouting categories.

Acceptance criteria:
- Player can discover fighters not immediately obvious from current lists.
- Some prospect information is uncertain until scouted further.
- Scouting produces a repeatable monthly pipeline of leads.
- Tests cover discovery generation and uncertainty formatting.

Why now:
This makes the market into gameplay rather than spreadsheet sorting.

---

### 5. Fighter morale, loyalty, and negotiation depth
Priority: P1
Suggested issue title: `Roadmap: add morale loyalty and negotiation preferences`

Goal:
Make negotiations multi-dimensional instead of pure math.

Scope:
- Add preferences like:
  - wants money
  - wants activity
  - wants contenders only
  - values prestige
  - prefers loyalty / hates lowball offers
- Add morale and org relationship effects.
- Add consequences from inactivity, repeated low offers, or broken expectations.

Acceptance criteria:
- Contract acceptance depends on more than salary + prestige.
- Fighter profile surfaces key negotiation preferences.
- Repeated bad management changes future negotiations.
- Tests cover preference-driven acceptance changes.

Why now:
This is how the roster becomes a cast of personalities instead of pure assets.

---

### 6. Rival organization strategy and bidding wars
Priority: P1
Suggested issue title: `Roadmap: add rival org identities and bidding wars`

Goal:
Make the world push back on the player.

Scope:
- Give AI orgs identifiable strategies:
  - prospect hunters
  - prestige-chasers
  - budget opportunists
  - division snipers
- Add bidding wars and targeted poaching.
- Add rivalry pressure around key divisions and stars.

Acceptance criteria:
- AI org behavior differs meaningfully by strategy.
- Contested fighters can trigger bidding competition.
- Player sees why rival orgs are dangerous in specific divisions.
- Tests cover org strategy outputs and bidding behavior.

Why now:
A static world kills long campaigns.

---

### 7. Media, rivalry, and popularity machine
Priority: P2
Suggested issue title: `Roadmap: deepen media narratives rivalries and star-building`

Goal:
Let publicity and storylines materially shape value.

Scope:
- Make media arcs influence popularity, hype, and booking power.
- Expand rivalry effects on event value and fighter demand.
- Add villain / fan-favorite / cult-hero / can’t-miss prospect style identities.

Acceptance criteria:
- Narrative arcs produce measurable business consequences.
- Rivalries materially affect event projections and fighter value.
- UI makes those narratives legible.

Why later:
High upside, but decision clarity and loop structure should come first.

---

### 8. Title picture and divisional politics
Priority: P2
Suggested issue title: `Roadmap: improve title-picture logic and divisional politics`

Goal:
Make rankings and championships matter more.

Scope:
- Better contender logic
- title eliminators
- inactivity pressure on champs
- fan backlash for weak title booking
- division heat/cold indicators

Acceptance criteria:
- Rankings have clearer gameplay consequences.
- Title fights are harder to abuse.
- Division quality and health are visible.

Why later:
Important, but less urgent than roster, booking, and acquisition loops.

---

## Suggested Milestone Packaging

### Milestone A: Decision Clarity
- Recommendation labels
- Expiring contracts / roster decision center
- Booking recommendations

### Milestone B: Talent Pipeline
- Scouting board
- Prospect surfacing
- Negotiation depth

### Milestone C: Living World
- Rival org strategy
- bidding wars
- media / rivalry machine
- divisional politics

---

## Immediate Next Build Recommendation

If we continue right now, do this next:
1. Recommendation labels for contracts and roster decisions
2. Expiring contracts / roster decision center
3. Booking recommendation engine

That is the shortest path to making FighterSim feel like a real game instead of a broad simulation sandbox.
