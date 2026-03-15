# FighterSim Current State

Last updated: 2026-03-14
Repo state at write time: clean after push

## What FighterSim is now

FighterSim is no longer just a loose bundle of simulation systems.
It now has a coherent management-game spine with:
- roster acquisition decisions
- roster retention pressure
- event booking guidance
- scouting/discovery guidance
- rival-org pressure
- title politics
- campaign goals
- dashboard-level decision support

Core management loop:
1. Review dashboard pressure
2. Sign / renew / release fighters
3. Book events or reality-show moves
4. Advance month
5. React to financial, prestige, roster, and world-state consequences

---

## Major shipped systems

### 1. Fight / world simulation backbone
Already present and functioning:
- fight engine
- monthly sim
- aging / injuries / retirements
- AI org events
- rankings
- narratives / history

### 2. Market and contract layer
Shipped:
- market-signal pricing
- contract acceptance probabilities
- sponsorship term adjustments
- market context surfaced in API and UI

Player-facing value:
- asking salary now has context
- not every free agent is equal
- the game explains why a fighter is hot, overpriced, cold, or worth pursuing

### 3. Recommendation labels
Shipped across key decision surfaces:
- Buy Now
- Fair Price
- Overpay Risk
- Sell Soon
- High-Leverage Renewal
- Replaceable
- Core Asset
- Low-Interest Asset

### 4. Roster decision center
Shipped:
- renewal pressure
- sell / replace candidates
- buy targets
- division outlook

This is the current "what should I do now?" management hub.

### 5. Event booking recommendations
Shipped:
- best main event
- best co-main
- best prospect fight
- best safe-money fight

Integrated into the event builder UI.

### 6. Scouting board
Shipped:
- featured prospects
- under the radar
- ready now
- division targets

### 7. Scouting fog-of-war
Shipped:
- scout confidence
- estimated overall range
- upside label
- fog note

This gives scouting uncertainty instead of full certainty.

### 8. Negotiation preferences / morale
Shipped as derived systems:
- money priority
- activity priority
- spotlight priority
- prestige priority
- loyalty label
- morale label

Shown in fighter panel and offer evaluation.

### 9. Relationship memory
Shipped as persistent relationship state:
- lowball history
- rejected offers
- successful signings
- successful renewals
- releases
- trust label / summary

This means negotiations now remember prior treatment.

### 10. Rival org identities and bidding pressure
Shipped:
- Prestige Hunter
- Talent Factory
- Star Chaser
- Division Sniper

Also shipped:
- contested target surfacing
- bidding pressure in negotiations

### 11. Title picture / contender politics
Shipped in rankings view:
- champion
- contenders
- title eliminator
- division heat
- politics notes

### 12. Champion inactivity enforcement
Shipped:
- overdue champions cannot be casually booked in non-title fights
- the next relevant booking must be a title defense

### 13. Media storyline escalation
Shipped dashboard storyline layer:
- rivalry storylines
- title-picture heat storylines
- prospect buzz storylines
- poaching watch storylines

### 14. Campaign objectives / owner goals
Shipped origin-based objective layer:
- The Heir goals
- The Matchmaker goals
- The Comeback goals
- sandbox fallback goals

Displayed on dashboard with progress bars.

### 15. Smart assistant actions
Shipped dashboard guidance layer:
- best signing
- best renewal
- best booking
- biggest risk this month

This is the current top-level action prioritizer.

---

## Current strengths

FighterSim is strongest right now at:
- free-agent market timing
- roster retention / churn decisions
- event booking support
- scouting and prospect surfacing
- dashboard-level strategic clarity

The game is now opinionated about:
- what is a good signing
- what is a bad contract
- what is a strong fight card
- what divisions need attention
- what the player should care about this month

---

## Current weaknesses / next frontier

The highest-leverage unfinished areas are:

1. Deeper media/business payoff
- media should affect more than dashboard flavor
- storylines should feed harder into demand and long-tail star value

2. Long-run relationship consequences
- current relationship memory is good, but still mostly negotiation-facing
- it can eventually affect inactivity tolerance, re-sign willingness after release, rivalry heat, etc.

3. Campaign structure / difficulty escalation
- owner goals exist
- but longer campaign arcs, milestone rewards, and fail states are still light

4. Smart assistant execution
- current assistant can advise
- next step is one-click action execution from those recommendations

5. Advanced title politics
- current title pressure exists
- future improvements could include interim titles, title-vacancy flow, harder contender rules, and fan backlash

---

## Recommended next build order

If continuing from here, the strongest next sequence is:

1. Smart assistant execution
- one-click best signing / best renewal / best booking

2. Deeper media-business coupling
- storylines materially changing booking value, hype pressure, and demand

3. Extended relationship consequences
- more memory effects beyond acceptance math

4. Advanced title-politics systems
- interim belts, mandatory contender handling, vacancy logic

---

## Recent major commits

Most important recent commits in order:
- 670a930 fix: resolve double-unavailable reality show finales
- 2d0b129 feat: add fighter market signal pricing
- addb88a feat: expose fighter market context in offers
- 5c9007a feat: show market context in fighter panels
- 8ad0326 feat: add market summaries to roster and show lists
- 21c9716 feat: add interactive market sorting filters
- a5bd820 docs: add FighterSim roadmap backlog
- 30420ee feat: add contract recommendation labels
- 72d7435 feat: add roster decision center
- 3813f20 feat: add event booking recommendations
- 727ec1a feat: add scouting board
- 1c93456 feat: add negotiation preferences and morale
- 283001c feat: add rival org identities and bidding pressure
- 631e3ea feat: add title picture and contender politics
- 4c96f84 feat: add scouting uncertainty to board
- 1822dd5 feat: add strategic AI org behaviors
- 24c2cd6 feat: add owner campaign objectives
- 816ce9e feat: add smart assistant actions
- e6d723d feat: add relationship memory for negotiations
- 99d2461 feat: add media storyline escalation
- 316e9c5 feat: enforce overdue champion title defenses

---

## Bottom line

FighterSim is now a real management game foundation.
The project has enough structure that new work should focus less on random system addition and more on:
- sharper consequences
- better synthesis
- faster actionability
- stronger long-term campaign pressure
