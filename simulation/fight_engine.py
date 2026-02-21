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

    # Permanent traits — list of trait name strings
    traits: list[str] = field(default_factory=list)

    # Style — used for style matchup system
    style: str = "Well-Rounded"

    # Runtime state — set at fight start
    stamina: float = 100.0
    damage: float = 0.0
    standing_damage: float = 0.0
    ground_damage: float = 0.0

    # Knockdown / hurt state
    knockdowns_suffered: int = 0
    is_hurt: bool = False
    hurt_ticks_remaining: int = 0
    round_knockdowns: int = 0

    # Momentum system (-1.0 to 1.0)
    momentum: float = 0.0

    # Per-round tracking
    strikes_landed_this_round: int = 0
    current_round: int = 1

    def _has(self, trait: str) -> bool:
        return trait in self.traits

    def _hurt_penalty(self) -> float:
        return 0.75 if self.is_hurt else 1.0

    def effective_striking(self) -> float:
        stamina_factor = 0.5 + 0.5 * (self.stamina / 100)
        val = self.striking * stamina_factor
        # slow_starter
        if self._has("slow_starter"):
            if self.current_round == 1:
                val *= 0.85
            elif self.current_round >= 3:
                val *= 1.08
        # veteran_iq
        if self._has("veteran_iq") and self.current_round >= 3:
            val += 4
        return val * self._hurt_penalty()

    def effective_grappling(self) -> float:
        stamina_factor = 0.6 + 0.4 * (self.stamina / 100)
        val = self.grappling * stamina_factor
        # veteran_iq
        if self._has("veteran_iq") and self.current_round >= 3:
            val += 4
        return val * self._hurt_penalty()

    def effective_wrestling(self) -> float:
        stamina_factor = 0.6 + 0.4 * (self.stamina / 100)
        val = self.wrestling * stamina_factor
        # slow_starter
        if self._has("slow_starter"):
            if self.current_round == 1:
                val *= 0.85
            elif self.current_round >= 3:
                val *= 1.08
        # veteran_iq
        if self._has("veteran_iq") and self.current_round >= 3:
            val += 4
        return val * self._hurt_penalty()

    def is_finished_by_strikes(self, opponent_momentum: float = 0.0) -> bool:
        """Check if cumulative standing damage causes a KO."""
        threshold = 68 + (self.chin - 50) * 0.8
        # iron_chin: +8 then *1.12
        if self._has("iron_chin"):
            threshold += 8
            threshold *= 1.12
        # comeback_king: +5
        if self._has("comeback_king"):
            threshold += 5
        # journeyman_heart: floor at 55 then *1.20
        if self._has("journeyman_heart"):
            threshold = max(55, threshold)
            threshold *= 1.20
        # Opponent momentum affects finish threshold
        if opponent_momentum > 0.5:
            threshold *= 0.90  # easier to finish
        elif opponent_momentum < -0.5:
            threshold *= 1.10  # harder to finish
        return self.standing_damage >= threshold

    def is_finished_by_grappling(self, opponent_momentum: float = 0.0) -> bool:
        """Check if ground damage causes a stoppage."""
        threshold = 70.0
        if self._has("submission_magnet"):
            threshold = 55.0
        # Opponent momentum
        if opponent_momentum > 0.5:
            threshold *= 0.90
        elif opponent_momentum < -0.5:
            threshold *= 1.10
        return self.ground_damage >= threshold

    def adjust_momentum(self, delta: float) -> None:
        self.momentum = max(-1.0, min(1.0, self.momentum + delta))

    def momentum_multiplier(self) -> float:
        return 1.0 + self.momentum * 0.2


# ---------------------------------------------------------------------------
# Round / fight result DTOs
# ---------------------------------------------------------------------------

@dataclass
class RoundResult:
    """Outcome of a single round."""
    round_num: int
    winner_id: Optional[int] = None
    method: Optional[str] = None
    time: Optional[str] = None
    events: list[str] = field(default_factory=list)
    knockdowns: dict[int, int] = field(default_factory=dict)
    momentum_swings: list[str] = field(default_factory=list)


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
    total_knockdowns: dict[int, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Style matchup system
# ---------------------------------------------------------------------------

@dataclass
class _StyleContext:
    td_mod_a: float = 0.0
    td_mod_b: float = 0.0
    clinch_prob: float = 0.20
    ground_stickiness: float = 1.0
    style_narrative: str = ""


# Takedown modifiers: (attacker_style, defender_style) -> modifier
STYLE_TAKEDOWN_MODS: dict[tuple[str, str], float] = {
    ("Wrestler", "Striker"): +0.10,
    ("Wrestler", "Grappler"): +0.03,
    ("Wrestler", "Wrestler"): +0.05,
    ("Wrestler", "Well-Rounded"): +0.05,
    ("Striker", "Wrestler"): -0.08,
    ("Striker", "Grappler"): -0.04,
    ("Striker", "Striker"): -0.05,
    ("Striker", "Well-Rounded"): -0.02,
    ("Grappler", "Striker"): +0.08,
    ("Grappler", "Grappler"): +0.08,
    ("Grappler", "Wrestler"): +0.03,
    ("Grappler", "Well-Rounded"): +0.03,
}


def _compute_style_context(a: FighterStats, b: FighterStats) -> _StyleContext:
    ctx = _StyleContext()
    sa, sb = a.style, b.style

    ctx.td_mod_a = STYLE_TAKEDOWN_MODS.get((sa, sb), 0.0)
    ctx.td_mod_b = STYLE_TAKEDOWN_MODS.get((sb, sa), 0.0)

    # Striker vs Striker: low clinch
    if sa == "Striker" and sb == "Striker":
        ctx.clinch_prob = 0.10
        ctx.style_narrative = "striking battle"
    # Wrestler vs Striker (either order)
    elif (sa == "Wrestler" and sb == "Striker") or (sa == "Striker" and sb == "Wrestler"):
        ctx.clinch_prob = 0.30
        ctx.style_narrative = "takedown battle"
    # Grappler vs Grappler
    elif sa == "Grappler" and sb == "Grappler":
        ctx.ground_stickiness = 0.80  # 20% reduction in scramble probability
        ctx.style_narrative = "grappling clinic"

    return ctx


# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

ROUND_DURATION_SECONDS = 300
TICK_DURATION_SECONDS = 30
TICKS_PER_ROUND = ROUND_DURATION_SECONDS // TICK_DURATION_SECONDS  # 10

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
    rng = random.Random(seed)

    # Reset runtime state
    for f in (a, b):
        f.stamina = 100.0
        f.damage = 0.0
        f.standing_damage = 0.0
        f.ground_damage = 0.0
        f.knockdowns_suffered = 0
        f.is_hurt = False
        f.hurt_ticks_remaining = 0
        f.round_knockdowns = 0
        f.momentum = 0.0
        f.strikes_landed_this_round = 0
        f.current_round = 1

    # Compute style context once
    style_ctx = _compute_style_context(a, b)

    round_results: list[RoundResult] = []
    total_knockdowns: dict[int, int] = {a.id: 0, b.id: 0}

    for round_num in range(1, max_rounds + 1):
        # Per-round resets
        for f in (a, b):
            f.current_round = round_num
            f.round_knockdowns = 0
            f.is_hurt = False
            f.hurt_ticks_remaining = 0
            f.strikes_landed_this_round = 0

        result = _simulate_round(a, b, round_num, rng, style_ctx)
        round_results.append(result)

        # Accumulate knockdowns
        for fid, kd in result.knockdowns.items():
            total_knockdowns[fid] = total_knockdowns.get(fid, 0) + kd

        if result.winner_id is not None:
            winner = a if result.winner_id == a.id else b
            loser = b if result.winner_id == a.id else a
            narrative = _build_narrative(a, b, round_results, result.method, winner, style_ctx, total_knockdowns)
            return FightResult(
                winner_id=winner.id,
                loser_id=loser.id,
                method=result.method,
                round_ended=round_num,
                time_ended=result.time,
                narrative=narrative,
                total_knockdowns=total_knockdowns,
            )

        _apply_round_fatigue(a, round_num)
        _apply_round_fatigue(b, round_num)

    # Judges' decision
    winner, method = _judges_decision(a, b, round_results, rng, total_knockdowns)
    loser = b if winner.id == a.id else a
    narrative = _build_narrative(a, b, round_results, method, winner, style_ctx, total_knockdowns)
    return FightResult(
        winner_id=winner.id,
        loser_id=loser.id,
        method=method,
        round_ended=max_rounds,
        time_ended="5:00",
        narrative=narrative,
        total_knockdowns=total_knockdowns,
    )


# ---------------------------------------------------------------------------
# Round simulation
# ---------------------------------------------------------------------------

def _simulate_round(
    a: FighterStats, b: FighterStats, round_num: int,
    rng: random.Random, style_ctx: _StyleContext,
) -> RoundResult:
    result = RoundResult(round_num=round_num)
    was_ground = False

    for tick in range(TICKS_PER_ROUND):
        # Decay hurt state
        for f in (a, b):
            if f.hurt_ticks_remaining > 0:
                f.hurt_ticks_remaining -= 1
                if f.hurt_ticks_remaining == 0:
                    f.is_hurt = False

        # Momentum decay toward 0
        for f in (a, b):
            if f.momentum > 0:
                f.momentum = max(0.0, f.momentum - 0.02)
            elif f.momentum < 0:
                f.momentum = min(0.0, f.momentum + 0.02)

        # Takedown probability with style mods
        td_prob_a = _takedown_probability(a, b) + style_ctx.td_mod_a
        td_prob_b = _takedown_probability(b, a) + style_ctx.td_mod_b

        # Well-Rounded: if losing on feet, boost takedown attempts
        if a.style == "Well-Rounded" and a.standing_damage > b.standing_damage:
            td_prob_a += 0.10
        if b.style == "Well-Rounded" and b.standing_damage > a.standing_damage:
            td_prob_b += 0.10

        takedown_prob = max(td_prob_a, td_prob_b)
        clinch_roll = rng.random()

        # Ground stickiness: if we were on ground last tick, reduce standup chance
        if was_ground:
            standup_chance = rng.random()
            if standup_chance > style_ctx.ground_stickiness:
                # Stayed on the ground
                _simulate_ground_tick(a, b, rng, result)
                # Check for in-tick finishes
                if result.winner_id is not None:
                    elapsed = (tick + 1) * TICK_DURATION_SECONDS
                    result.time = f"{elapsed // 60}:{elapsed % 60:02d}"
                    return result
                _drain_stamina(a, rng)
                _drain_stamina(b, rng)
                continue
            was_ground = False

        if rng.random() < takedown_prob:
            was_ground = True
            # Momentum for successful takedown
            if td_prob_a >= td_prob_b:
                a.adjust_momentum(+0.15)
                b.adjust_momentum(-0.05)
            else:
                b.adjust_momentum(+0.15)
                a.adjust_momentum(-0.05)
            _simulate_ground_tick(a, b, rng, result)
        elif clinch_roll < style_ctx.clinch_prob:
            _simulate_clinch_tick(a, b, rng, result, round_num, style_ctx)
        else:
            _simulate_striking_tick(a, b, rng, result, round_num)

        # Check for in-tick finishes (knockdown TKOs set winner_id during tick)
        if result.winner_id is not None:
            elapsed = (tick + 1) * TICK_DURATION_SECONDS
            result.time = f"{elapsed // 60}:{elapsed % 60:02d}"
            return result

        # Check cumulative finish thresholds
        elapsed_seconds = (tick + 1) * TICK_DURATION_SECONDS
        time_str = f"{elapsed_seconds // 60}:{elapsed_seconds % 60:02d}"

        if a.is_finished_by_strikes(b.momentum):
            result.winner_id = b.id
            result.method = "KO/TKO"
            result.time = time_str
            result.events.append(f"{b.name} finishes {a.name} with strikes")
            return result

        if b.is_finished_by_strikes(a.momentum):
            result.winner_id = a.id
            result.method = "KO/TKO"
            result.time = time_str
            result.events.append(f"{a.name} finishes {b.name} with strikes")
            return result

        if a.is_finished_by_grappling(b.momentum):
            result.winner_id = b.id
            result.method = "Submission"
            result.time = time_str
            result.events.append(f"{b.name} submits {a.name}")
            return result

        if b.is_finished_by_grappling(a.momentum):
            result.winner_id = a.id
            result.method = "Submission"
            result.time = time_str
            result.events.append(f"{a.name} submits {b.name}")
            return result

        _drain_stamina(a, rng)
        _drain_stamina(b, rng)

    return result


# ---------------------------------------------------------------------------
# Striking
# ---------------------------------------------------------------------------

def _simulate_striking_tick(
    a: FighterStats, b: FighterStats, rng: random.Random,
    result: RoundResult, round_num: int = 1,
) -> None:
    # Determine initiative based on speed (+ fast_hands bonus)
    speed_a = a.speed + (8 if a._has("fast_hands") else 0)
    speed_b = b.speed + (8 if b._has("fast_hands") else 0)

    if speed_a >= speed_b:
        first, second = a, b
    else:
        first, second = b, a

    _process_strike(first, second, rng, result, is_initiator=True)
    if result.winner_id is not None:
        return
    _process_strike(second, first, rng, result, is_initiator=False)


def _process_strike(
    attacker: FighterStats, defender: FighterStats,
    rng: random.Random, result: RoundResult,
    is_initiator: bool = False,
) -> None:
    hit_prob = _hit_probability(attacker, defender)
    # First-strike bonus for initiator
    if is_initiator:
        hit_prob = min(0.85, hit_prob + 0.05)

    if rng.random() >= hit_prob:
        return

    # Damage multipliers
    mult = attacker.momentum_multiplier()

    # slow_starter (already in effective_striking, but damage mult for late rounds)
    if attacker._has("slow_starter") and attacker.current_round >= 3:
        mult *= 1.05

    # pressure_fighter tiered bonus
    if attacker._has("pressure_fighter"):
        if defender.stamina < 30:
            mult *= 1.25
        elif defender.stamina < 50:
            mult *= 1.15
        elif defender.stamina < 70:
            mult *= 1.05

    # comeback_king: extra output when absorbing damage
    if attacker._has("comeback_king") and attacker.standing_damage > 25:
        mult *= 1.20

    dmg = _strike_damage(attacker, defender, rng) * mult
    defender.standing_damage += dmg
    defender.damage += dmg * 0.5
    attacker.strikes_landed_this_round += 1
    result.events.append(f"{attacker.name} lands strike ({dmg:.1f} dmg)")

    # Momentum for landing/getting hit
    attacker.adjust_momentum(+0.05)
    defender.adjust_momentum(-0.05)

    # Knockdown check: only for significant strikes
    if dmg > 12:
        kd_prob = (dmg - 10) / 100 * (1 - defender.chin / 120)
        if rng.random() < kd_prob:
            defender.is_hurt = True
            defender.hurt_ticks_remaining = 2
            defender.knockdowns_suffered += 1
            defender.round_knockdowns += 1
            result.knockdowns[defender.id] = result.knockdowns.get(defender.id, 0) + 1
            result.events.append(f"{attacker.name} scores a knockdown on {defender.name}!")
            result.momentum_swings.append(f"Knockdown: {attacker.name} drops {defender.name}")

            # Momentum swing for knockdown
            attacker.adjust_momentum(+0.30)
            defender.adjust_momentum(-0.30)

            # Ref stoppage: 12% chance on knockdown
            if rng.random() < 0.12:
                result.winner_id = attacker.id
                result.method = "KO/TKO"
                result.events.append(f"Referee stops the fight! {attacker.name} wins by TKO after knockdown")
                return

            # Double knockdown in same round: auto TKO
            if defender.round_knockdowns >= 2:
                result.winner_id = attacker.id
                result.method = "KO/TKO"
                result.events.append(f"Second knockdown in the round! {attacker.name} wins by TKO")
                return

    # Knockout artist: small per-strike chance of bonus impact
    if attacker._has("knockout_artist") and rng.random() < 0.04:
        defender.standing_damage += 25


# ---------------------------------------------------------------------------
# Clinch
# ---------------------------------------------------------------------------

def _simulate_clinch_tick(
    a: FighterStats, b: FighterStats, rng: random.Random,
    result: RoundResult, round_num: int = 1,
    style_ctx: Optional[_StyleContext] = None,
) -> None:
    if rng.random() < 0.5:
        dmg = _strike_damage(a, b, rng) * 0.6 * a.momentum_multiplier()
        if a._has("slow_starter") and round_num == 1:
            dmg *= 0.85
        b.standing_damage += dmg
        b.damage += dmg * 0.3
    if rng.random() < 0.5:
        dmg = _strike_damage(b, a, rng) * 0.6 * b.momentum_multiplier()
        if b._has("slow_starter") and round_num == 1:
            dmg *= 0.85
        a.standing_damage += dmg
        a.damage += dmg * 0.3

    # Wrestler cage work: attempt takedown from clinch
    if style_ctx:
        wrestler = None
        opponent = None
        if a.style == "Wrestler":
            wrestler, opponent = a, b
        elif b.style == "Wrestler":
            wrestler, opponent = b, a

        if wrestler and rng.random() < 0.40:
            td_prob = _takedown_probability(wrestler, opponent) + 0.10
            if rng.random() < td_prob:
                result.events.append(f"{wrestler.name} drags {opponent.name} down from the clinch")
                wrestler.adjust_momentum(+0.15)
                _simulate_ground_tick(a, b, rng, result)


# ---------------------------------------------------------------------------
# Ground
# ---------------------------------------------------------------------------

def _simulate_ground_tick(
    a: FighterStats, b: FighterStats, rng: random.Random, result: RoundResult
) -> None:
    # Determine who has top position (attacker = higher wrestling)
    if a.effective_wrestling() >= b.effective_wrestling():
        attacker, defender = a, b
    else:
        attacker, defender = b, a

    # submission_magnet: all ground damage amplified when defending
    sub_magnet_mult = 1.20 if defender._has("submission_magnet") else 1.0

    # Ground and pound
    if rng.random() < 0.65:
        dmg = rng.uniform(6, 15) * (attacker.effective_striking() / 100)
        if attacker._has("ground_and_pound_specialist"):
            dmg *= 1.25
        dmg *= attacker.momentum_multiplier()
        dmg *= sub_magnet_mult
        defender.ground_damage += dmg * 0.6
        defender.standing_damage += dmg * 0.1
        result.events.append(f"{attacker.name} lands GnP")

    # Submission attempt
    sub_rate = 0.32 if attacker.effective_grappling() > 80 else 0.22
    if rng.random() < sub_rate:
        # Escape probability
        escape_prob = (defender.effective_grappling() * 0.7 + defender.effective_wrestling() * 0.3) / 180
        escape_prob = max(0.22, escape_prob)  # minimum floor — no fighter is completely helpless

        # Penalties/bonuses to escape
        if defender.is_hurt:
            escape_prob *= 0.70
        if defender._has("submission_magnet"):
            escape_prob *= 0.80
        if defender.style == "Well-Rounded":
            escape_prob *= 1.15

        roll = rng.random()
        if roll < escape_prob * 0.5:
            # Full escape
            result.events.append(f"{defender.name} escapes submission cleanly!")
            defender.adjust_momentum(+0.10)
            attacker.adjust_momentum(-0.10)
        elif roll < escape_prob:
            # Partial escape — 50% damage, stays on ground
            sub_dmg = rng.uniform(25, 40) * 0.5
            sub_dmg *= attacker.momentum_multiplier()
            sub_dmg *= sub_magnet_mult
            defender.ground_damage += sub_dmg
            result.events.append(f"{defender.name} partially escapes, still in danger")
        else:
            # No escape — full submission damage
            sub_dmg = rng.uniform(25, 40)
            sub_dmg *= attacker.momentum_multiplier()
            sub_dmg *= sub_magnet_mult
            defender.ground_damage += sub_dmg
            result.events.append(f"{attacker.name} locks in submission attempt")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _takedown_probability(a: FighterStats, b: FighterStats) -> float:
    shoot = (a.effective_wrestling() / 100) * 0.20
    defense = (b.effective_wrestling() / 100) * 0.12
    return max(0.02, min(0.35, shoot - defense + 0.04))


def _hit_probability(attacker: FighterStats, defender: FighterStats) -> float:
    base = 0.4
    speed_advantage = (attacker.effective_striking() - defender.speed) / 200
    prob = base + speed_advantage
    # fast_hands always adds +0.08
    if attacker._has("fast_hands"):
        prob += 0.08
    return max(0.15, min(0.85, prob))


def _strike_damage(attacker: FighterStats, defender: FighterStats, rng: random.Random) -> float:
    power = attacker.effective_striking() / 100
    chin_reduction = defender.chin / 100
    base = rng.uniform(4, 14)
    return base * power * (1.2 - chin_reduction * 0.4)


def _drain_stamina(fighter: FighterStats, rng: random.Random) -> None:
    base_drain = rng.uniform(1.5, 3.5)
    cardio_factor = 1.0 - (fighter.cardio / 150)
    if fighter._has("gas_tank"):
        cardio_factor *= 0.55
    if fighter._has("veteran_iq") and fighter.current_round >= 3:
        cardio_factor *= 0.90
    fighter.stamina = max(0, fighter.stamina - base_drain * cardio_factor)


def _apply_round_fatigue(fighter: FighterStats, completed_round: int) -> None:
    recovery = max(3, 15 - completed_round * 2)
    if fighter._has("gas_tank"):
        recovery += 5
    fighter.stamina = min(100, fighter.stamina + recovery)
    if fighter.cardio < 60 and not fighter._has("gas_tank"):
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
    total_knockdowns: Optional[dict[int, int]] = None,
) -> tuple[FighterStats, str]:
    # Score based on damage dealt
    a_score = b.damage + b.standing_damage * 0.5
    b_score = a.damage + a.standing_damage * 0.5

    # Knockdown bonus: each knockdown = +10 points
    if total_knockdowns:
        # a's knockdowns on b (stored under b's id) benefit a
        a_score += total_knockdowns.get(b.id, 0) * 10
        b_score += total_knockdowns.get(a.id, 0) * 10

    # Judging subjectivity
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
    style_ctx: Optional[_StyleContext] = None,
    total_knockdowns: Optional[dict[int, int]] = None,
) -> str:
    loser = b if winner.id == a.id else a
    templates = _NARRATIVE_TEMPLATES.get(method, ["A competitive fight ended with {winner} defeating {loser}."])
    template = random.choice(templates)
    text = template.format(
        winner=winner.name,
        loser=loser.name,
        round=rounds[-1].round_num,
    )

    # Append knockdown counts
    if total_knockdowns:
        kd_parts = []
        for fid, count in total_knockdowns.items():
            if count > 0:
                name = a.name if fid == a.id else b.name
                kd_parts.append(f"{name} was knocked down {count} time{'s' if count > 1 else ''}")
        if kd_parts:
            text += " " + ". ".join(kd_parts) + "."

    # Style flavor text
    if style_ctx and style_ctx.style_narrative:
        if method == "Submission" and style_ctx.style_narrative == "grappling clinic":
            text += f" A true {style_ctx.style_narrative}."
        elif style_ctx.style_narrative == "striking battle":
            text += f" It was a {style_ctx.style_narrative} from start to finish."
        elif style_ctx.style_narrative == "takedown battle":
            text += f" Cage pressure and takedowns defined this {style_ctx.style_narrative}."

    return text
