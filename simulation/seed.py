"""Database seeding for MMA Management Simulator.

Refactored pipeline: quota-first archetype allocation, career-stage-aware
generation, prestige-gated org distribution, integrated name_gen + stat_gen.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import (
    Fighter, Organization, Contract, GameState, TrainingCamp,
    WeightClass, FighterStyle, ContractStatus, Archetype,
)
from simulation.traits import TRAITS, contradicts
from simulation.name_gen import (
    generate_name, create_faker_instances, pick_nationality,
)
from simulation.stat_gen import generate_stats, compute_overall
from simulation.narrative import suggest_nicknames
from simulation.history import fabricate_history


# ---------------------------------------------------------------------------
# Constants (PRESERVED from original)
# ---------------------------------------------------------------------------

WEIGHT_CLASS_LIMITS: dict[str, int] = {
    "Flyweight": 125,
    "Lightweight": 155,
    "Welterweight": 170,
    "Middleweight": 185,
    "Heavyweight": 265,
}

NATURAL_WEIGHT_RANGES: dict[str, tuple[int, int]] = {
    "Flyweight": (130, 150),
    "Lightweight": (160, 180),
    "Welterweight": (178, 198),
    "Middleweight": (195, 215),
    "Heavyweight": (225, 265),
}


# ---------------------------------------------------------------------------
# Archetype quota allocation (pyramid rarity curve)
# ---------------------------------------------------------------------------

ARCHETYPE_QUOTAS: dict[str, float] = {
    "Journeyman":     0.24,
    "Gatekeeper":     0.23,
    "Phenom":         0.22,
    "Late Bloomer":   0.14,
    "Shooting Star":  0.10,
    "GOAT Candidate": 0.07,
}


def allocate_archetypes(count_per_class: int, np_rng: np.random.Generator) -> list[str]:
    """Return a shuffled list of archetype assignments for one weight class.

    Implements pyramid rarity curve with soft quotas (+/-2).
    No single archetype exceeds 25% of count_per_class.
    Journeyman absorbs remainder but is capped; excess goes to Gatekeeper.
    """
    max_per_archetype = int(count_per_class * 0.25)
    slots: list[str] = []
    remaining = count_per_class

    for archetype, ratio in ARCHETYPE_QUOTAS.items():
        if archetype == "Journeyman":
            continue
        base = round(count_per_class * ratio)
        variance = int(np_rng.integers(-2, 3))  # -2 to +2
        n = max(1, min(base + variance, remaining, max_per_archetype))
        slots.extend([archetype] * n)
        remaining -= n

    # Fill remainder with Journeyman, capped at max_per_archetype
    journeyman_count = min(remaining, max_per_archetype)
    slots.extend(["Journeyman"] * journeyman_count)
    remaining -= journeyman_count

    # If still remaining, distribute to Gatekeeper and Phenom
    overflow_targets = ["Gatekeeper", "Phenom", "Late Bloomer"]
    oi = 0
    while remaining > 0 and oi < len(overflow_targets):
        target = overflow_targets[oi]
        current = slots.count(target)
        if current < max_per_archetype:
            add = min(remaining, max_per_archetype - current)
            slots.extend([target] * add)
            remaining -= add
        oi += 1

    # Final safety: pad with Journeyman if somehow still short
    if remaining > 0:
        slots.extend(["Journeyman"] * remaining)

    # Ensure exact count
    slots = slots[:count_per_class]

    np_rng.shuffle(slots)
    return slots


# ---------------------------------------------------------------------------
# Career stage assignment (archetype-constrained)
# ---------------------------------------------------------------------------

# Validity matrix: which career stages are valid for each archetype
_ARCHETYPE_VALID_STAGES: dict[str, list[str]] = {
    "GOAT Candidate": ["prime", "veteran"],
    "Late Bloomer":   ["prime", "veteran"],        # bloomed late, now may be aging
    "Shooting Star":  ["prime", "transitional"],   # peak then decline
    "Phenom":         ["prospect", "prime"],
    "Gatekeeper":     ["prospect", "prime", "veteran", "transitional"],
    "Journeyman":     ["prospect", "prime", "veteran", "transitional"],
}

# Career stage weights per archetype -- tuned so the overall distribution
# across all archetypes approximates 20% prospect / 35% prime / 25% veteran / 20% transitional
_CAREER_STAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "GOAT Candidate": {"prime": 0.55, "veteran": 0.45},
    "Late Bloomer":   {"prime": 0.65, "veteran": 0.35},
    "Shooting Star":  {"prime": 0.60, "transitional": 0.40},
    "Phenom":         {"prospect": 0.60, "prime": 0.40},
    "Gatekeeper":     {"prospect": 0.25, "prime": 0.20, "veteran": 0.30, "transitional": 0.25},
    "Journeyman":     {"prospect": 0.25, "prime": 0.15, "veteran": 0.30, "transitional": 0.30},
}

# Age ranges per career stage
_CAREER_STAGE_AGE_RANGES: dict[str, tuple[int, int]] = {
    "prospect":      (20, 24),
    "prime":         (25, 31),
    "veteran":       (32, 37),
    "transitional":  (27, 33),
}


def assign_career_stage(archetype: str, py_rng: random.Random) -> str:
    """Return a career stage constrained by archetype validity matrix."""
    weights_map = _CAREER_STAGE_WEIGHTS.get(archetype, _CAREER_STAGE_WEIGHTS["Journeyman"])
    stages = list(weights_map.keys())
    weights = list(weights_map.values())
    return py_rng.choices(stages, weights=weights, k=1)[0]


def _age_from_career_stage(career_stage: str, py_rng: random.Random) -> int:
    """Derive age from career stage range."""
    lo, hi = _CAREER_STAGE_AGE_RANGES[career_stage]
    return py_rng.randint(lo, hi)


# ---------------------------------------------------------------------------
# Fight record generation (enhanced for career stage)
# ---------------------------------------------------------------------------

def _gen_record(age: int, career_stage: str, py_rng: random.Random) -> dict:
    """Generate career-stage-appropriate fight record.

    Prospects get 1-5 fights, prime 8-20, veterans 15-30, transitional 10-22.
    """
    if career_stage == "prospect":
        total = py_rng.randint(1, 5)
    elif career_stage == "prime":
        total = py_rng.randint(8, 20)
    elif career_stage == "veteran":
        total = py_rng.randint(15, 30)
    else:  # transitional
        total = py_rng.randint(10, 22)

    if total == 0:
        return {"wins": 0, "losses": 0, "draws": 0, "ko_wins": 0, "sub_wins": 0}

    wins = py_rng.randint(int(total * 0.4), max(int(total * 0.4), int(total * 0.75)))
    losses = total - wins
    draws = py_rng.randint(0, 1) if total > 5 else 0
    wins = max(0, wins - draws)

    ko_wins = int(wins * py_rng.uniform(0.1, 0.45))
    sub_wins = int((wins - ko_wins) * py_rng.uniform(0.1, 0.4))
    ko_wins = min(ko_wins, wins)
    sub_wins = min(sub_wins, wins - ko_wins)

    return {
        "wins": wins, "losses": losses, "draws": draws,
        "ko_wins": ko_wins, "sub_wins": sub_wins,
    }


# ---------------------------------------------------------------------------
# Prime window derivation
# ---------------------------------------------------------------------------

def _prime_window(career_stage: str, age: int, py_rng: random.Random) -> tuple[int, int]:
    """Derive prime_start/prime_end based on career stage and age."""
    if career_stage == "prospect":
        prime_start = py_rng.randint(25, 27)
        prime_end = prime_start + py_rng.randint(5, 8)
    elif career_stage == "prime":
        # Currently in prime
        prime_start = py_rng.randint(max(23, age - 3), age)
        prime_end = prime_start + py_rng.randint(5, 8)
    elif career_stage == "veteran":
        # Past prime
        prime_start = py_rng.randint(24, 27)
        prime_end = py_rng.randint(max(prime_start + 4, 29), min(prime_start + 8, age))
    else:  # transitional
        prime_start = py_rng.randint(25, 28)
        prime_end = prime_start + py_rng.randint(4, 7)

    return prime_start, prime_end


# ---------------------------------------------------------------------------
# Organization distribution (prestige-gated)
# ---------------------------------------------------------------------------

# Salary ranges per archetype (annual)
_ARCHETYPE_SALARY: dict[str, tuple[int, int]] = {
    "GOAT Candidate": (80_000, 200_000),
    "Shooting Star":  (50_000, 120_000),
    "Phenom":         (30_000, 80_000),
    "Late Bloomer":   (15_000, 50_000),
    "Gatekeeper":     (12_000, 40_000),
    "Journeyman":     (8_000, 25_000),
}


# ---------------------------------------------------------------------------
# Origin configurations (player starting conditions)
# ---------------------------------------------------------------------------

ORIGIN_CONFIGS = {
    "The Heir": {
        "label": "The Heir",
        "tagline": "Inherited a mid-tier promotion. Prove you belong.",
        "budget": 8_000_000,
        "prestige": 55.0,
        "roster_target": 20,
        "roster_quality": "inherited",
    },
    "The Matchmaker": {
        "label": "The Matchmaker",
        "tagline": "10 years booking for UCC. Now building your own vision.",
        "budget": 4_000_000,
        "prestige": 40.0,
        "roster_target": 12,
        "roster_quality": "hand_picked",
    },
    "The Comeback": {
        "label": "The Comeback",
        "tagline": "Washed-out fighter. Nobody believes in you.",
        "budget": 1_500_000,
        "prestige": 25.0,
        "roster_target": 6,
        "roster_quality": "scrappy",
    },
}


def _assign_organization(
    career_stage: str,
    archetype_str: str,
    orgs: list[Organization],
    py_rng: random.Random,
    free_agent_count: int,
    total_fighters: int,
    max_free_agents: int,
) -> Organization | None:
    """Assign fighter to an org based on prestige/career stage, or None for free agent.

    Returns None if the fighter should be a free agent.
    """
    # Free agent logic: 10-15% target
    # GOAT Candidates are never free agents
    if archetype_str != "GOAT Candidate" and free_agent_count < max_free_agents:
        # Weighted toward prospects and veterans
        fa_chance = {
            "prospect": 0.20,
            "veteran": 0.18,
            "transitional": 0.12,
            "prime": 0.08,
        }
        if py_rng.random() < fa_chance.get(career_stage, 0.10):
            return None

    # Sort orgs by prestige descending
    sorted_orgs = sorted(orgs, key=lambda o: o.prestige, reverse=True)

    # Prestige-gated distribution weights based on career stage
    if career_stage in ("prime", "veteran"):
        # Better fighters go to higher-prestige orgs
        # UCC: 40%, One: 25%, Bellator: 25%, Player: 10%
        weights = [40, 25, 25, 10]
    elif career_stage == "prospect":
        # Prospects distributed more evenly, player gets more
        # UCC: 10%, One: 20%, Bellator: 20%, Player: 50%
        weights = [10, 20, 20, 50]
    else:  # transitional
        # Moderately distributed
        # UCC: 20%, One: 25%, Bellator: 30%, Player: 25%
        weights = [20, 25, 30, 25]

    return py_rng.choices(sorted_orgs, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Preserved helper functions
# ---------------------------------------------------------------------------

def seed_organizations(
    session: Session,
    player_org_name: str = "Player Promotion",
    player_org_prestige: float = 50.0,
    player_org_balance: float = 5_000_000.0,
    origin_type: str | None = None,
) -> list[Organization]:
    orgs = [
        Organization(name="Ultimate Combat Championship", prestige=90.0,
                     bank_balance=50_000_000.0, is_player=False),
        Organization(name="Bellator MMA", prestige=70.0,
                     bank_balance=20_000_000.0, is_player=False),
        Organization(name="One Championship", prestige=75.0,
                     bank_balance=25_000_000.0, is_player=False),
        Organization(name=player_org_name, prestige=player_org_prestige,
                     bank_balance=player_org_balance, is_player=True),
    ]
    for org in orgs:
        session.add(org)
    session.flush()

    # Initialize game state with game start date
    player_org = next((o for o in orgs if o.is_player), None)
    game_state = GameState(
        id=1,
        current_date=date(2026, 1, 1),
        player_org_id=player_org.id if player_org else None,
        origin_type=origin_type,
    )
    session.add(game_state)
    session.flush()

    return orgs


def enforce_roster_target(session: Session, player_org_id: int, target: int) -> int:
    """Release excess fighters from player org to hit roster target. Returns released count."""
    # Get all active contracts for the player org, joined with Fighter
    active_contracts = (
        session.execute(
            select(Contract)
            .join(Fighter, Contract.fighter_id == Fighter.id)
            .where(
                Contract.organization_id == player_org_id,
                Contract.status == ContractStatus.ACTIVE,
            )
        )
        .scalars()
        .all()
    )

    if len(active_contracts) <= target:
        return 0

    # Batch load fighter overalls to avoid N+1 queries
    fighter_ids = [c.fighter_id for c in active_contracts]
    rows = session.execute(
        select(Fighter.id, Fighter.overall).where(Fighter.id.in_(fighter_ids))
    ).all()
    overall_map = {row.id: row.overall for row in rows}

    active_contracts.sort(key=lambda c: overall_map.get(c.fighter_id, 0))

    # Release the weakest fighters beyond the target
    excess = len(active_contracts) - target
    released = 0
    for contract in active_contracts[:excess]:
        session.delete(contract)
        released += 1

    session.flush()
    return released


def enforce_roster_quality(session: Session, player_org_id: int, quality_type: str) -> int:
    """Adjust roster composition to match origin theme. Returns number of releases."""
    if quality_type == "inherited":
        # Natural distribution is fine for The Heir
        return 0

    active_contracts = (
        session.execute(
            select(Contract)
            .where(
                Contract.organization_id == player_org_id,
                Contract.status == ContractStatus.ACTIVE,
            )
        )
        .scalars()
        .all()
    )

    # Batch load fighters to avoid N+1 queries
    fighter_ids = [c.fighter_id for c in active_contracts]
    fighters = session.execute(
        select(Fighter).where(Fighter.id.in_(fighter_ids))
    ).scalars().all()
    fighter_map = {f.id: f for f in fighters}

    released = 0

    if quality_type == "hand_picked":
        # Release any prospect-stage fighters (keep prime + veteran only)
        for contract in active_contracts:
            fighter = fighter_map.get(contract.fighter_id)
            if not fighter:
                continue
            if fighter.age < fighter.prime_start:
                session.delete(contract)
                released += 1

    elif quality_type == "scrappy":
        # Release any fighter with overall > 75 or archetype == GOAT_CANDIDATE
        for contract in active_contracts:
            fighter = fighter_map.get(contract.fighter_id)
            if not fighter:
                continue
            if fighter.overall > 75 or fighter.archetype == Archetype.GOAT_CANDIDATE:
                session.delete(contract)
                released += 1

    session.flush()
    return released


def _starting_popularity_hype(archetype: Archetype, rng: random.Random) -> tuple[float, float]:
    ranges = {
        Archetype.GOAT_CANDIDATE: ((40, 60), (60, 80)),
        Archetype.PHENOM:         ((20, 40), (50, 70)),
        Archetype.GATEKEEPER:     ((30, 50), (10, 20)),
        Archetype.JOURNEYMAN:     ((5,  20), (5,  15)),
        Archetype.LATE_BLOOMER:   ((10, 30), (20, 40)),
        Archetype.SHOOTING_STAR:  ((10, 30), (20, 40)),
    }
    (plo, phi), (hlo, hhi) = ranges[archetype]
    return round(rng.uniform(plo, phi), 1), round(rng.uniform(hlo, hhi), 1)


def _assign_traits(archetype: Archetype, fighter: Fighter, rng: random.Random) -> list[str]:
    """Return 1-3 trait names for a fighter based on archetype + stats."""
    traits: list[str] = []

    # Guaranteed traits
    career_fights = fighter.wins + fighter.losses + fighter.draws
    if archetype == Archetype.GATEKEEPER:
        if fighter.age >= 27 or career_fights >= 12:
            traits.append("veteran_iq")
        elif fighter.striking >= fighter.grappling:
            traits.append("pressure_fighter")
        else:
            traits.append("fast_hands")
    elif archetype == Archetype.JOURNEYMAN:
        traits.append("journeyman_heart")
    elif archetype == Archetype.GOAT_CANDIDATE:
        anchor = rng.choice(["gas_tank", "iron_chin", "comeback_king"])
        traits.append(anchor)

    # Archetype-based weighted pool
    _pools: dict[Archetype, list[tuple[str, int]]] = {
        Archetype.GOAT_CANDIDATE: [
            ("knockout_artist", 3), ("fast_hands", 3), ("pressure_fighter", 2),
            ("ground_and_pound_specialist", 2), ("veteran_iq", 1), ("media_darling", 1),
        ],
        Archetype.PHENOM: [
            ("fast_hands", 4), ("pressure_fighter", 3), ("knockout_artist", 3),
            ("gas_tank", 2), ("comeback_king", 2), ("slow_starter", 1),
        ],
        Archetype.GATEKEEPER: [
            ("iron_chin", 3), ("comeback_king", 3), ("slow_starter", 2),
            ("gas_tank", 2), ("ground_and_pound_specialist", 2), ("journeyman_heart", 1),
        ],
        Archetype.JOURNEYMAN: [
            ("iron_chin", 3), ("veteran_iq", 3), ("slow_starter", 2),
            ("comeback_king", 2), ("submission_magnet", 2), ("media_darling", 1),
        ],
        Archetype.LATE_BLOOMER: [
            ("veteran_iq", 4), ("slow_starter", 3), ("iron_chin", 2),
            ("comeback_king", 2), ("gas_tank", 2), ("ground_and_pound_specialist", 1),
        ],
        Archetype.SHOOTING_STAR: [
            ("knockout_artist", 4), ("fast_hands", 3), ("submission_magnet", 3),
            ("pressure_fighter", 2), ("media_darling", 2), ("gas_tank", 1),
        ],
    }

    pool = list(_pools.get(archetype, []))

    # Gate veteran_iq: requires age >= 27 or career_fights >= 12
    if fighter.age < 27 and career_fights < 12:
        pool = [(t, w) for t, w in pool if t != "veteran_iq"]

    # Stat-based bonus weights
    if fighter.striking >= 80:
        pool = [(t, w + (2 if t in ("fast_hands", "knockout_artist", "pressure_fighter") else 0)) for t, w in pool]
    if fighter.cardio >= 80:
        pool = [(t, w + (2 if t == "gas_tank" else 0)) for t, w in pool]
    if fighter.chin >= 80:
        pool = [(t, w + (2 if t in ("iron_chin", "comeback_king") else 0)) for t, w in pool]
    if fighter.grappling >= 80:
        pool = [(t, w + (2 if t == "ground_and_pound_specialist" else 0)) for t, w in pool]

    target = rng.randint(1, 3)
    attempts = 0
    while len(traits) < target and pool and attempts < 20:
        attempts += 1
        candidates = [(t, w) for t, w in pool if t not in traits and not contradicts(t, traits)]
        if not candidates:
            break
        names, weights = zip(*candidates)
        chosen = rng.choices(list(names), weights=list(weights), k=1)[0]
        traits.append(chosen)

    return traits[:3]


def _adjust_record_for_archetype(
    f: Fighter,
    archetype: Archetype,
    rng: random.Random,
) -> None:
    """Adjust W-L record so it fits the archetype narrative."""
    total = f.wins + f.losses + f.draws
    if total == 0:
        return

    if archetype == Archetype.GOAT_CANDIDATE:
        min_rate = 0.70
    elif archetype == Archetype.SHOOTING_STAR:
        min_rate = 0.60
    else:
        return

    fight_total = f.wins + f.losses
    if fight_total == 0:
        return

    current_rate = f.wins / fight_total
    if current_rate >= min_rate:
        return

    new_wins = max(f.wins, int(fight_total * min_rate) + 1)
    new_wins = min(new_wins, fight_total)
    old_wins = f.wins

    f.wins = new_wins
    f.losses = fight_total - new_wins

    if old_wins > 0:
        ratio = new_wins / old_wins
        f.ko_wins = min(int(f.ko_wins * ratio), new_wins)
        f.sub_wins = min(int(f.sub_wins * ratio), new_wins - f.ko_wins)
    else:
        f.ko_wins = int(new_wins * rng.uniform(0.15, 0.40))
        f.sub_wins = int((new_wins - f.ko_wins) * rng.uniform(0.1, 0.35))


# ---------------------------------------------------------------------------
# Archetype string -> Enum lookup
# ---------------------------------------------------------------------------

_ARCHETYPE_ENUM_MAP: dict[str, Archetype] = {
    "Journeyman":     Archetype.JOURNEYMAN,
    "Gatekeeper":     Archetype.GATEKEEPER,
    "Phenom":         Archetype.PHENOM,
    "Late Bloomer":   Archetype.LATE_BLOOMER,
    "Shooting Star":  Archetype.SHOOTING_STAR,
    "GOAT Candidate": Archetype.GOAT_CANDIDATE,
}


# ---------------------------------------------------------------------------
# Main seed pipeline
# ---------------------------------------------------------------------------

def seed_fighters(
    session: Session,
    orgs: list[Organization],
    seed: int = 42,
    count: int = 450,
) -> list[Fighter]:
    """Seed fighters using quota-first archetype allocation.

    Pipeline:
    1. Initialize dual RNGs (stdlib + numpy) and Faker instances
    2. Compute per-weight-class archetype quotas
    3. Generate fighters per weight class with career-stage-aware stats
    4. Distribute fighters to orgs based on prestige
    5. Assign nicknames
    """
    # 1. Initialize RNGs
    py_rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    faker_instances = create_faker_instances(seed)

    weight_classes = list(WeightClass)
    styles = list(FighterStyle)
    fighters: list[Fighter] = []
    used_names: set[str] = set()

    # Game start date for contract expiry
    game_state = session.get(GameState, 1)
    today = game_state.current_date if game_state else date(2026, 1, 1)

    # Compute per-weight-class count
    count_per_class = count // len(weight_classes)
    # Distribute remainder across first N classes
    remainder = count - (count_per_class * len(weight_classes))

    # Free agent tracking
    target_free_agent_pct = py_rng.uniform(0.10, 0.15)
    max_free_agents = int(count * target_free_agent_pct)
    free_agent_count = 0

    # 2-4. Generate fighters per weight class
    for wc_idx, wc in enumerate(weight_classes):
        class_count = count_per_class + (1 if wc_idx < remainder else 0)
        wc_val = wc.value if hasattr(wc, "value") else wc

        # Allocate archetypes for this weight class
        archetype_slots = allocate_archetypes(class_count, np_rng)

        limit = WEIGHT_CLASS_LIMITS.get(wc_val, 185)
        nat_lo, nat_hi = NATURAL_WEIGHT_RANGES.get(wc_val, (limit, limit + 20))

        for slot_idx in range(class_count):
            archetype_str = archetype_slots[slot_idx]

            # Assign career stage (constrained by archetype)
            career_stage = assign_career_stage(archetype_str, py_rng)

            # Derive age from career stage
            age = _age_from_career_stage(career_stage, py_rng)

            # Pick nationality and generate name
            nationality = pick_nationality(py_rng)
            name = generate_name(nationality, faker_instances, py_rng, used_names)

            # Pick style
            style_enum = py_rng.choice(styles)
            style_str = style_enum.value if hasattr(style_enum, "value") else style_enum

            # Generate stats using stat_gen module
            stats = generate_stats(archetype_str, style_str, career_stage, np_rng)

            # Generate fight record (career-stage-aware)
            record = _gen_record(age, career_stage, py_rng)

            # Prime window
            prime_start, prime_end = _prime_window(career_stage, age, py_rng)

            # Natural weight
            natural_wt = round(py_rng.uniform(nat_lo, nat_hi), 1)

            # Create Fighter
            archetype_enum = _ARCHETYPE_ENUM_MAP[archetype_str]

            f = Fighter(
                name=name,
                age=age,
                nationality=nationality,
                weight_class=wc,
                style=style_enum,
                striking=stats["striking"],
                grappling=stats["grappling"],
                wrestling=stats["wrestling"],
                cardio=stats["cardio"],
                chin=stats["chin"],
                speed=stats["speed"],
                prime_start=prime_start,
                prime_end=prime_end,
                wins=record["wins"],
                losses=record["losses"],
                draws=record["draws"],
                ko_wins=record["ko_wins"],
                sub_wins=record["sub_wins"],
                natural_weight=natural_wt,
                fighting_weight=float(limit),
                confidence=70.0,
                archetype=archetype_enum,
            )
            session.add(f)
            session.flush()

            # Adjust record for GOAT Candidates and Shooting Stars
            _adjust_record_for_archetype(f, archetype_enum, py_rng)

            # Popularity and hype
            popularity, hype = _starting_popularity_hype(archetype_enum, py_rng)
            f.popularity = popularity
            f.hype = hype
            f.narrative_tags = "[]"
            f.goat_score = 0.0

            # Traits
            f.traits = json.dumps(_assign_traits(archetype_enum, f, py_rng))

            # Assign nickname
            nicknames = suggest_nicknames(f, session)
            f.nickname = nicknames[0] if nicknames else "The Fighter"

            # 5. Org distribution
            org = _assign_organization(
                career_stage, archetype_str, orgs, py_rng,
                free_agent_count, len(fighters), max_free_agents,
            )

            if org is not None:
                # Create contract
                salary_lo, salary_hi = _ARCHETYPE_SALARY.get(
                    archetype_str, (8_000, 25_000)
                )
                contract = Contract(
                    fighter_id=f.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=round(py_rng.uniform(salary_lo, salary_hi), 2),
                    fight_count_total=4,
                    fights_remaining=py_rng.randint(1, 4),
                    expiry_date=today + timedelta(days=py_rng.randint(90, 730)),
                )
                session.add(contract)
            else:
                free_agent_count += 1

            fighters.append(f)

    # Force remaining fighters to be free agents if we haven't hit minimum
    # This ensures the 10-15% target is met
    min_free_agents = int(count * 0.10)
    if free_agent_count < min_free_agents:
        # Find signed fighters that can be converted to free agents
        # Prefer prospects and veterans for realism
        signed_fighters = [
            f for f in fighters
            if f.id not in {fa.id for fa in fighters[:free_agent_count]}
        ]
        # Get fighters with contracts, sort by suitability for free agency
        from sqlalchemy import and_
        for f in fighters:
            if free_agent_count >= min_free_agents:
                break
            arch_val = f.archetype.value if hasattr(f.archetype, 'value') else f.archetype
            if arch_val == "GOAT Candidate":
                continue
            # Check if fighter has an active contract
            existing_contract = session.execute(
                select(Contract).where(
                    Contract.fighter_id == f.id,
                    Contract.status == ContractStatus.ACTIVE,
                )
            ).scalars().first()
            if existing_contract and (f.age <= 24 or f.age >= 32):
                session.delete(existing_contract)
                free_agent_count += 1

    # Seed training camps
    _seed_training_camps(session)

    session.commit()
    return fighters


# ---------------------------------------------------------------------------
# Training camps (PRESERVED)
# ---------------------------------------------------------------------------

TRAINING_CAMPS = [
    # Tier 1
    {"name": "Local Gym", "specialty": "Well-Rounded", "tier": 1, "cost": 2000, "prestige_required": 0, "slots": 10},
    {"name": "City Boxing Club", "specialty": "Striking", "tier": 1, "cost": 2500, "prestige_required": 0, "slots": 8},
    {"name": "Community Wrestling Center", "specialty": "Wrestling", "tier": 1, "cost": 2000, "prestige_required": 0, "slots": 8},
    {"name": "BJJ Academy", "specialty": "Grappling", "tier": 1, "cost": 2500, "prestige_required": 0, "slots": 8},
    {"name": "Conditioning Lab", "specialty": "Conditioning", "tier": 1, "cost": 3000, "prestige_required": 0, "slots": 6},
    # Tier 2
    {"name": "Elite Striking Academy", "specialty": "Striking", "tier": 2, "cost": 6000, "prestige_required": 40, "slots": 6},
    {"name": "Championship Wrestling Room", "specialty": "Wrestling", "tier": 2, "cost": 6000, "prestige_required": 40, "slots": 6},
    {"name": "World-Class BJJ", "specialty": "Grappling", "tier": 2, "cost": 7000, "prestige_required": 40, "slots": 5},
    {"name": "Performance Institute", "specialty": "Conditioning", "tier": 2, "cost": 8000, "prestige_required": 40, "slots": 5},
    {"name": "MMA Combine", "specialty": "Well-Rounded", "tier": 2, "cost": 7000, "prestige_required": 40, "slots": 6},
    # Tier 3
    {"name": "The Factory", "specialty": "Well-Rounded", "tier": 3, "cost": 15000, "prestige_required": 70, "slots": 4},
    {"name": "Apex Striking", "specialty": "Striking", "tier": 3, "cost": 14000, "prestige_required": 70, "slots": 4},
    {"name": "Elite Wrestling Institute", "specialty": "Wrestling", "tier": 3, "cost": 14000, "prestige_required": 70, "slots": 4},
    {"name": "Submission Lab", "specialty": "Grappling", "tier": 3, "cost": 16000, "prestige_required": 70, "slots": 3},
    {"name": "Human Performance Center", "specialty": "Conditioning", "tier": 3, "cost": 18000, "prestige_required": 70, "slots": 3},
]


def _seed_training_camps(session: Session) -> None:
    """Create all training camps if they don't already exist."""
    existing = session.execute(select(TrainingCamp)).scalars().first()
    if existing:
        return
    for camp_data in TRAINING_CAMPS:
        session.add(TrainingCamp(
            name=camp_data["name"],
            specialty=camp_data["specialty"],
            tier=camp_data["tier"],
            cost_per_month=camp_data["cost"],
            prestige_required=camp_data["prestige_required"],
            slots=camp_data["slots"],
        ))
