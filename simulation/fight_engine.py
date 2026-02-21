"""
Fight simulation engine for MMA Management Simulator.

Completely decoupled from Flask — no web framework imports.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data transfer objects (engine works with these, not ORM models directly)
# ---------------------------------------------------------------------------

@dataclass
class FighterStats:
    """Lightweight snapshot of fighter attributes used during simulation."""
    id: int
    name: str
    striking: int
    grappling: int
    wrestling: int
    cardio: int
    chin: int
    speed: int

    # Runtime state — set at fight start
    stamina: float = 100.0          # 0–100, degrades over rounds
    damage: float = 0.0             # accumulated damage
    standing_damage: float = 0.0   # head/body damage tracking
    ground_damage: float = 0.0

    def effective_striking(self) -> float:
        stamina_factor = 0.5 + 0.5 * (self.stamina / 100)
        return self.striking * stamina_factor

    def effective_grappling(self) -> float:
        stamina_factor = 0.6 + 0.4 * (self.stamina / 100)
        return self.grappling * stamina_factor

    def effective_wrestling(self) -> float:
        stamina_factor = 0.6 + 0.4 * (self.stamina / 100)
        return self.wrestling * stamina_factor

    def is_finished_by_strikes(self) -> bool:
        """Check if cumulative standing damage causes a KO."""
        chin_threshold = 60 + (self.chin - 50) * 0.8
        return self.standing_damage >= chin_threshold

    def is_finished_by_grappling(self) -> bool:
        """Check if ground damage + grappling exposure causes a stoppage."""
        return self.ground_damage >= 70


@dataclass
class RoundResult:
    """Outcome of a single round."""
    round_num: int
    winner_id: Optional[int] = None   # None = no finish
    method: Optional[str] = None      # KO/TKO, Submission, or None
    time: Optional[str] = None
    events: list[str] = field(default_factory=list)


@dataclass
class FightResult:
    """Full fight outcome."""
    winner_id: int
    loser_id: int
    method: str
    round_ended: int
    time_ended: str
    narrative: str
    is_draw: bool = False


# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

ROUND_DURATION_SECONDS = 300   # 5 minutes
TICK_DURATION_SECONDS = 30     # simulate in 30-second ticks
TICKS_PER_ROUND = ROUND_DURATION_SECONDS // TICK_DURATION_SECONDS   # 10

MAX_ROUNDS_CHAMPIONSHIP = 5
MAX_ROUNDS_STANDARD = 3


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def simulate_fight(
    a: FighterStats,
    b: FighterStats,
    max_rounds: int = 3,
    seed: Optional[int] = None,
) -> FightResult:
    """
    Simulate a fight between two fighters.

    Args:
        a: First fighter's stats snapshot.
        b: Second fighter's stats snapshot.
        max_rounds: 3 for standard bouts, 5 for championship.
        seed: Optional RNG seed for deterministic results.

    Returns:
        FightResult with winner, method, timing and narrative.
    """
    rng = random.Random(seed)

    # Reset runtime state
    a.stamina = 100.0
    b.stamina = 100.0
    a.damage = 0.0
    b.damage = 0.0
    a.standing_damage = 0.0
    b.standing_damage = 0.0
    a.ground_damage = 0.0
    b.ground_damage = 0.0

    round_results: list[RoundResult] = []

    for round_num in range(1, max_rounds + 1):
        result = _simulate_round(a, b, round_num, rng)
        round_results.append(result)
        if result.winner_id is not None:
            # Fight ended inside this round
            winner = a if result.winner_id == a.id else b
            loser = b if result.winner_id == a.id else a
            narrative = _build_narrative(a, b, round_results, result.method, winner)
            return FightResult(
                winner_id=winner.id,
                loser_id=loser.id,
                method=result.method,
                round_ended=round_num,
                time_ended=result.time,
                narrative=narrative,
            )

        # Cardio degradation between rounds
        _apply_round_fatigue(a, round_num)
        _apply_round_fatigue(b, round_num)

    # Judges' decision
    winner, method = _judges_decision(a, b, round_results, rng)
    loser = b if winner.id == a.id else a
    narrative = _build_narrative(a, b, round_results, method, winner)
    return FightResult(
        winner_id=winner.id,
        loser_id=loser.id,
        method=method,
        round_ended=max_rounds,
        time_ended="5:00",
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# Round simulation
# ---------------------------------------------------------------------------

def _simulate_round(
    a: FighterStats, b: FighterStats, round_num: int, rng: random.Random
) -> RoundResult:
    """Simulate one round tick by tick."""
    result = RoundResult(round_num=round_num)

    for tick in range(TICKS_PER_ROUND):
        # Determine fight zone this tick (standing or ground)
        # Either fighter can shoot — use the higher of the two probabilities
        takedown_prob = max(_takedown_probability(a, b), _takedown_probability(b, a))
        in_clinch = rng.random() < 0.2

        if rng.random() < takedown_prob:
            # Ground phase
            _simulate_ground_tick(a, b, rng, result)
        elif in_clinch:
            _simulate_clinch_tick(a, b, rng, result)
        else:
            # Striking exchange
            _simulate_striking_tick(a, b, rng, result)

        # Check for finish after each tick
        elapsed_seconds = (tick + 1) * TICK_DURATION_SECONDS
        time_str = f"{elapsed_seconds // 60}:{elapsed_seconds % 60:02d}"

        if a.is_finished_by_strikes():
            result.winner_id = b.id
            result.method = "KO/TKO"
            result.time = time_str
            result.events.append(f"{b.name} finishes {a.name} with strikes")
            return result

        if b.is_finished_by_strikes():
            result.winner_id = a.id
            result.method = "KO/TKO"
            result.time = time_str
            result.events.append(f"{a.name} finishes {b.name} with strikes")
            return result

        if a.is_finished_by_grappling():
            result.winner_id = b.id
            result.method = "Submission"
            result.time = time_str
            result.events.append(f"{b.name} submits {a.name}")
            return result

        if b.is_finished_by_grappling():
            result.winner_id = a.id
            result.method = "Submission"
            result.time = time_str
            result.events.append(f"{a.name} submits {b.name}")
            return result

        # Stamina drain per tick
        _drain_stamina(a, rng)
        _drain_stamina(b, rng)

    return result  # round goes the distance


def _simulate_striking_tick(
    a: FighterStats, b: FighterStats, rng: random.Random, result: RoundResult
) -> None:
    """Model a brief striking exchange."""
    # A attacks B
    if rng.random() < _hit_probability(a, b):
        dmg = _strike_damage(a, b, rng)
        b.standing_damage += dmg
        b.damage += dmg * 0.5
        result.events.append(f"{a.name} lands strike ({dmg:.1f} dmg)")

    # B attacks A
    if rng.random() < _hit_probability(b, a):
        dmg = _strike_damage(b, a, rng)
        a.standing_damage += dmg
        a.damage += dmg * 0.5
        result.events.append(f"{b.name} lands strike ({dmg:.1f} dmg)")


def _simulate_clinch_tick(
    a: FighterStats, b: FighterStats, rng: random.Random, result: RoundResult
) -> None:
    """Clinch work — knees, elbows, and wrestling scrambles."""
    # Reduced damage output in clinch
    if rng.random() < 0.5:
        dmg = _strike_damage(a, b, rng) * 0.6
        b.standing_damage += dmg
        b.damage += dmg * 0.3
    if rng.random() < 0.5:
        dmg = _strike_damage(b, a, rng) * 0.6
        a.standing_damage += dmg
        a.damage += dmg * 0.3


def _simulate_ground_tick(
    a: FighterStats, b: FighterStats, rng: random.Random, result: RoundResult
) -> None:
    """Model ground and pound or submission attempt."""
    # Determine who initiated (attacker = higher wrestling)
    if a.effective_wrestling() >= b.effective_wrestling():
        attacker, defender = a, b
    else:
        attacker, defender = b, a

    # Ground and pound — more impactful, less standing damage (controlled position)
    if rng.random() < 0.65:
        dmg = rng.uniform(6, 15) * (attacker.effective_striking() / 100)
        defender.ground_damage += dmg * 0.6
        defender.standing_damage += dmg * 0.1
        result.events.append(f"{attacker.name} lands GnP")

    # Submission attempt — scales with grappling advantage
    grappling_edge = (attacker.effective_grappling() - defender.effective_grappling()) / 100
    sub_prob = max(0.05, min(0.40, 0.15 + grappling_edge * 0.5))
    if rng.random() < sub_prob:
        # Escape difficulty based purely on defender's grappling + wrestling
        escape_prob = min(0.75, (defender.effective_grappling() + defender.effective_wrestling()) / 200)
        if rng.random() > escape_prob:
            defender.ground_damage += rng.uniform(25, 45)
            result.events.append(f"{attacker.name} locks in submission attempt")
        else:
            result.events.append(f"{defender.name} escapes submission")


def _takedown_probability(a: FighterStats, b: FighterStats) -> float:
    """Probability a shoot for a takedown succeeds this tick."""
    advantage = (a.effective_wrestling() - b.effective_wrestling()) / 100
    return max(0.02, min(0.60, 0.12 + advantage * 0.55))


def _hit_probability(attacker: FighterStats, defender: FighterStats) -> float:
    """Probability attacker's strike lands."""
    base = 0.4
    speed_advantage = (attacker.effective_striking() - defender.speed) / 200
    return max(0.15, min(0.85, base + speed_advantage))


def _strike_damage(attacker: FighterStats, defender: FighterStats, rng: random.Random) -> float:
    """Raw damage value for a landed strike."""
    power = attacker.effective_striking() / 100
    chin_reduction = defender.chin / 100
    base = rng.uniform(5, 15)
    return base * power * (1.2 - chin_reduction * 0.4)


def _drain_stamina(fighter: FighterStats, rng: random.Random) -> None:
    """Drain stamina per tick based on cardio."""
    base_drain = rng.uniform(1.5, 3.5)
    cardio_factor = 1.0 - (fighter.cardio / 150)  # high cardio = less drain
    fighter.stamina = max(0, fighter.stamina - base_drain * cardio_factor)


def _apply_round_fatigue(fighter: FighterStats, completed_round: int) -> None:
    """Between rounds: partial recovery, but gets harder in later rounds."""
    recovery = max(3, 15 - completed_round * 2)
    fighter.stamina = min(100, fighter.stamina + recovery)
    # Stamina ceiling drops each round for low-cardio fighters
    if fighter.cardio < 60:
        max_stamina = 100 - (completed_round * (60 - fighter.cardio) * 0.3)
        fighter.stamina = min(fighter.stamina, max_stamina)


# ---------------------------------------------------------------------------
# Judges' decision
# ---------------------------------------------------------------------------

def _judges_decision(
    a: FighterStats,
    b: FighterStats,
    rounds: list[RoundResult],
    rng: random.Random,
) -> tuple[FighterStats, str]:
    """Determine winner by judges' scorecard."""
    # Score based on damage dealt (proxy for 10-point must system)
    a_score = b.damage + b.standing_damage * 0.5
    b_score = a.damage + a.standing_damage * 0.5

    # Add slight randomness to reflect judging subjectivity
    a_score += rng.uniform(-5, 5)
    b_score += rng.uniform(-5, 5)

    margin = abs(a_score - b_score)
    if a_score > b_score:
        winner = a
    else:
        winner = b

    if margin < 3:
        method = rng.choice(["Split Decision", "Majority Decision"])
    else:
        method = "Unanimous Decision"

    return winner, method


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------

_NARRATIVE_TEMPLATES = {
    "KO/TKO": [
        "{winner} controlled the fight with sharp striking before putting {loser} away in round {round}. The finish came via brutal ground and pound after a knockdown.",
        "{winner} stalked {loser} from the opening bell, landing cleaner shots each exchange. A precise combination in round {round} ended matters emphatically.",
        "After a competitive start, {winner} found the range and began teeing off on {loser}. The referee stepped in to stop it in round {round}.",
    ],
    "Submission": [
        "{winner} dragged the fight to the mat early and worked methodically, securing the submission in round {round} after {loser} couldn't escape the hold.",
        "{loser} was competitive on the feet, but once {winner} got the takedown in round {round}, there was no escape from the submission attempt.",
        "{winner} showed world-class grappling, threading the needle for a slick submission in round {round} after neutralizing {loser}'s striking game.",
    ],
    "Unanimous Decision": [
        "{winner} outworked {loser} for the full {round} rounds, controlling range and landing the cleaner shots to take a clear decision.",
        "A technical battle that went the distance, with {winner} edging out {loser} on all three judges' scorecards over {round} rounds.",
    ],
    "Split Decision": [
        "{winner} and {loser} had a back-and-forth war that split the judges. Two of three scorecards favored {winner}'s output and aggression.",
        "Neither fighter was able to impose their will completely, and {winner} squeaked out a split decision after {round} competitive rounds.",
    ],
    "Majority Decision": [
        "{winner} did enough to claim a majority decision over {loser} after {round} rounds, with two judges scoring it in their favor.",
        "An even fight that could have gone either way. {winner} gets the nod on two scorecards with the third seeing it a draw.",
    ],
}


def _build_narrative(
    a: FighterStats,
    b: FighterStats,
    rounds: list[RoundResult],
    method: str,
    winner: FighterStats,
) -> str:
    loser = b if winner.id == a.id else a
    templates = _NARRATIVE_TEMPLATES.get(method, ["A competitive fight ended with {winner} defeating {loser}."])
    template = random.choice(templates)
    return template.format(
        winner=winner.name,
        loser=loser.name,
        round=rounds[-1].round_num,
    )
