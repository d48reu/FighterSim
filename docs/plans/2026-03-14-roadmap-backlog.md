# FighterSim Roadmap Backlog

> GitHub issue creation is currently blocked by token permissions (`Resource not accessible by personal access token`), so this file is the canonical issue-ready backlog for now.

## Current Product Thesis

FighterSim is now a real management game foundation, not just a simulation sandbox.
The game can already guide the player through:
- signing talent
- retaining or cutting talent
- booking events
- scouting future talent
- handling rival pressure
- reading title-politics pressure
- pursuing campaign goals

The roadmap should now prioritize consequence density, actionability, and long-term campaign texture over adding more disconnected systems.

---

## Status Snapshot

Completed major systems:
- Recommendation labels for contracts and roster decisions
- Booking recommendation engine in event builder
- Expiring contracts and roster decision center
- Scouting board
- Scouting uncertainty / fog-of-war
- Fighter morale, loyalty, negotiation preferences
- Persistent relationship memory for negotiations
- Rival org identities and bidding pressure
- Title-picture and divisional politics surfaces
- Champion inactivity title-defense enforcement
- Media / storyline escalation widget
- Campaign objectives / owner goals
- Smart assistant actions on dashboard
- Stronger AI org strategic behavior

This means the original Milestones A-C are largely shipped in MVP form.

---

## New Priority Order

1. Smart assistant execution layer
2. Deeper media-business coupling
3. Expanded relationship consequences beyond negotiation
4. Advanced title-politics systems
5. Campaign structure and difficulty escalation
6. Deeper AI org strategic behavior
7. Premium scouting / intel systems
8. Presentation and UX unification

---

## Next Backlog Items

### 1. Smart assistant execution layer
Priority: P0
Suggested issue title: `Roadmap: add one-click execution for smart assistant actions`

Goal:
Turn the dashboard assistant from advisor into operator.

Scope:
- Add one-click actions where safe and obvious:
  - Sign this fighter
  - Renew this fighter
  - Open booking recommendation in event builder
  - Jump to the risk item that needs attention
- Every assistant card should support direct action or deep-link navigation.
- Use existing recommendation outputs rather than inventing new logic.

Acceptance criteria:
- Dashboard assistant cards expose direct actions.
- Sign / renew actions prefill existing UI and reduce clicks.
- Booking action opens the relevant matchup context in the event flow.
- Tests cover assistant action metadata and UI rendering.

Why now:
The game already knows what the best move is. The next win is making the move fast.

---

### 2. Deeper media-business coupling
Priority: P1
Suggested issue title: `Roadmap: make media storylines materially affect business outcomes`

Goal:
Make storylines change economics and roster value, not just dashboard flavor.

Scope:
- Media arcs should feed into:
  - booking demand
  - popularity drift
  - hype persistence
  - sponsorship attractiveness
  - rivalry intensity
- Add stronger categories like:
  - breakout buzz
  - falling stock
  - revenge angle
  - champion under pressure
  - poaching war

Acceptance criteria:
- Storylines influence at least one projection or negotiation-facing system.
- News and media widgets become mechanically relevant.
- Tests cover storyline-to-business propagation.

Why now:
The storyline layer exists. Now it should matter.

---

### 3. Expanded relationship consequences beyond negotiation
Priority: P1
Suggested issue title: `Roadmap: extend relationship memory into roster and career consequences`

Goal:
Make relationship memory affect more than immediate acceptance math.

Scope:
- Use relationship memory to influence:
  - willingness to renew after inactivity
  - tolerance for lower pay after good treatment
  - trust decay after releases or repeated lowballs
  - headline/storyline language
  - loyalty pressure for cornerstone-type fighters
- Add clearer long-term trust trajectories.

Acceptance criteria:
- Relationship memory visibly changes more than offer acceptance.
- Fighter profile makes trust state legible.
- Repeat management style produces meaningfully different outcomes over time.
- Tests cover longer-lived relationship effects.

Why now:
Persistent memory is shipped. The next step is deeper consequence.

---

### 4. Advanced title-politics systems
Priority: P1
Suggested issue title: `Roadmap: deepen title-politics with vacancy and interim flows`

Goal:
Push title management from “good surface” to “real sports-politics system.”

Scope:
- Interim title logic
- Vacancy logic when champs are absent too long
- contender queue pressure
- stronger backlash for bad title booking
- clearer ranking consequences around eliminators and defenses

Acceptance criteria:
- Inactive champion pressure can escalate beyond a single booking block.
- Title scenes produce different branches: defense, interim, vacancy, eliminator.
- Rankings and title state stay coherent.
- Tests cover title-state transitions.

Why now:
Current title enforcement is good, but still MVP-level.

---

### 5. Campaign structure and difficulty escalation
Priority: P1
Suggested issue title: `Roadmap: deepen campaign structure and difficulty progression`

Goal:
Turn owner goals into a fuller campaign arc.

Scope:
- Mid-game and late-game objectives
- milestone rewards or consequences
- origin-specific escalation
- possible fail states / recovery paths
- difficulty pressure tied to org growth

Acceptance criteria:
- Objectives evolve over time instead of remaining static.
- Campaign pressure scales with the player’s progress.
- Different origins diverge more strongly in playstyle.

Why now:
The game has goals; it now needs progression structure.

---

### 6. Deeper AI org strategic behavior
Priority: P2
Suggested issue title: `Roadmap: deepen AI org strategy in booking and roster construction`

Goal:
Make AI organizations feel like durable competitors with distinct habits.

Scope:
- More aggressive identity expression in:
  - roster composition
  - title focus
  - event quality profile
  - signing thresholds
  - division concentration
- More visible consequences in rival intel.

Acceptance criteria:
- AI org behavior diverges more clearly by identity over long campaigns.
- Rival dashboard intel explains real future threats.
- Tests cover org strategy effects across multiple systems.

Why later:
The base identity system exists and is useful already.

---

### 7. Premium scouting / intel systems
Priority: P2
Suggested issue title: `Roadmap: deepen scouting with tiers, reveal progression, and intel quality`

Goal:
Turn scouting into a progression system, not just a board.

Scope:
- Scout tiers or scouting spend
- reveal progression over time
- better hidden-info structure
- richer upside / downside reads
- more division-specific search behavior

Acceptance criteria:
- Scouting quality changes what the player can know.
- Re-scouting or time investment improves certainty.
- Tests cover reveal progression and uncertainty tightening.

Why later:
The current fog-of-war MVP is already doing real work.

---

### 8. Presentation and UX unification
Priority: P2
Suggested issue title: `Roadmap: unify dashboard and panel UX across all guidance systems`

Goal:
Make all the advice systems feel like one coherent product instead of stacked widgets.

Scope:
- visual consistency across:
  - objectives
  - assistant actions
  - decision center
  - title picture
  - scouting
  - media
- improve density and scanability
- reduce duplicate information and clutter

Acceptance criteria:
- Core dashboard widgets feel visually and structurally unified.
- The player can scan the dashboard quickly for action.
- UI tests and manual QA confirm improved readability.

Why later:
Important, but not as high leverage as deeper mechanics.

---

## Suggested Milestone Packaging

### Milestone D: Operator Layer
- Smart assistant execution
- dashboard UX tightening

### Milestone E: Consequence Layer
- media-business coupling
- relationship consequences
- advanced title politics

### Milestone F: Long Campaign Layer
- campaign escalation
- deeper AI org strategy
- premium scouting systems

---

## Immediate Next Build Recommendation

If continuing right now, do this next:
1. Smart assistant execution layer
2. Deeper media-business coupling
3. Expanded relationship consequences beyond negotiation

That sequence sharpens the current game the fastest without blowing up complexity.
