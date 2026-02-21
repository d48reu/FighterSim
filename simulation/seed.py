"""Database seeding for MMA Management Simulator."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import (
    Fighter, Organization, Contract, GameState, TrainingCamp,
    WeightClass, FighterStyle, ContractStatus, Archetype,
)
from simulation.traits import TRAITS, contradicts

_FIRST_NAMES = [
    "Carlos", "Luis", "Andre", "Marcus", "Kevin", "Jake", "Tony", "Darian",
    "Ramon", "Victor", "Elias", "Jordan", "Miles", "Cole", "Dante", "Felix",
    "Bruno", "Ivan", "Diego", "Marco", "Sergio", "Omar", "Javier", "Rafael",
    "Kris", "Shane", "Derek", "Corey", "Trevor", "Nathan", "Brendan", "Kyle",
    "Tyson", "Aaron", "Eric", "Jason", "Scott", "Chad", "Brett", "Sean",
    "Yusuf", "Hamza", "Tariq", "Hassan", "Ibrahim", "Khalid", "Amir", "Samir",
    "Wei", "Liang", "Chao", "Jin", "Ryu", "Ken", "Hiroshi", "Takeshi",
    "Dmitri", "Alexei", "Pavel", "Nikolai", "Boris", "Yuri", "Andrei", "Sergei",
    "Patrick", "Conor", "Seamus", "Declan", "Finn", "Ronan", "Cian", "Oisin",
    "Lars", "Bjorn", "Erik", "Magnus", "Sven", "Gunnar", "Leif", "Ragnar",
]

_LAST_NAMES = [
    "Silva", "Santos", "Lima", "Costa", "Pereira", "Ferreira", "Alves", "Souza",
    "Johnson", "Williams", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
    "Garcia", "Martinez", "Lopez", "Gonzalez", "Hernandez", "Ramirez", "Torres", "Flores",
    "Ali", "Hassan", "Khan", "Ahmed", "Malik", "Hussain", "Akhtar", "Sheikh",
    "Zhang", "Wang", "Li", "Chen", "Liu", "Yang", "Huang", "Wu",
    "Ivanov", "Petrov", "Volkov", "Sokolov", "Morozov", "Fedorov", "Popov", "Lebedev",
    "Murphy", "Kelly", "O'Brien", "Walsh", "Ryan", "O'Connor", "Byrne", "McCarthy",
    "Eriksson", "Lindqvist", "Andersson", "Johansson", "Carlsson", "Nilsson", "Larsson", "Olsson",
    "Smith", "Jones", "Evans", "Thomas", "Roberts", "Harris", "Lewis", "Walker",
    "Diaz", "Reyes", "Morales", "Jimenez", "Vargas", "Castillo", "Romero", "Gutierrez",
]

_NATIONALITIES = [
    "American", "Brazilian", "Mexican", "Russian", "Irish", "British",
    "Canadian", "Australian", "Swedish", "Norwegian", "Japanese", "South Korean",
    "Georgian", "Dagestani", "Polish", "Dutch", "French", "German",
    "Nigerian", "Cameroonian", "South African", "New Zealander", "Jamaican",
]

_USED_NAMES: set[str] = set()


def _random_name(rng: random.Random) -> str:
    for _ in range(200):
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        if name not in _USED_NAMES:
            _USED_NAMES.add(name)
            return name
    # Fallback with suffix
    name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)} Jr."
    _USED_NAMES.add(name)
    return name


def seed_organizations(session: Session) -> list[Organization]:
    _USED_NAMES.clear()
    orgs = [
        Organization(name="Ultimate Combat Championship", prestige=90.0,
                     bank_balance=50_000_000.0, is_player=False),
        Organization(name="Bellator MMA", prestige=70.0,
                     bank_balance=20_000_000.0, is_player=False),
        Organization(name="One Championship", prestige=75.0,
                     bank_balance=25_000_000.0, is_player=False),
        Organization(name="Player Promotion", prestige=50.0,
                     bank_balance=5_000_000.0, is_player=True),
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
    )
    session.add(game_state)
    session.flush()

    return orgs


def _gen_record(age: int, rng: random.Random) -> dict:
    """Generate age-appropriate fight record (assumes pro debut at 18-20)."""
    max_fights_by_age = {
        19: 3, 20: 5, 21: 7, 22: 9, 23: 12, 24: 15,
        25: 18, 26: 22, 27: 26, 28: 30,
    }
    max_fights = max_fights_by_age.get(age, min(40, (age - 18) * 3))

    if age <= 21:
        total = rng.randint(0, min(6, max_fights))
    elif age <= 23:
        total = rng.randint(2, min(10, max_fights))
    elif age <= 25:
        total = rng.randint(4, min(16, max_fights))
    elif age <= 28:
        total = rng.randint(8, min(24, max_fights))
    elif age <= 32:
        total = rng.randint(12, min(32, max_fights))
    else:
        total = rng.randint(16, min(40, max_fights))

    wins = rng.randint(int(total * 0.4), int(total * 0.75))
    losses = total - wins
    draws = rng.randint(0, 1) if total > 5 else 0
    wins = max(0, wins - draws)

    ko_wins = int(wins * rng.uniform(0.1, 0.45))
    sub_wins = int((wins - ko_wins) * rng.uniform(0.1, 0.4))
    ko_wins = min(ko_wins, wins)
    sub_wins = min(sub_wins, wins - ko_wins)

    return {
        "wins": wins, "losses": losses, "draws": draws,
        "ko_wins": ko_wins, "sub_wins": sub_wins,
    }


def _assign_archetype(
    f: Fighter,
    goat_counts: dict[str, int],
    rng: random.Random,
) -> Archetype:
    """Assign archetype based on fighter attributes. GOAT Candidate capped at 2/wc."""
    wc = f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class

    if (
        f.overall >= 75
        and 22 <= f.age <= 26
        and (f.prime_end - f.prime_start) >= 8
        and goat_counts.get(wc, 0) < 2
        and f.wins > f.losses * 2
    ):
        goat_counts[wc] = goat_counts.get(wc, 0) + 1
        return Archetype.GOAT_CANDIDATE

    if f.overall >= 70 and 19 <= f.age <= 24 and f.losses <= 2:
        return Archetype.PHENOM

    if f.overall >= 68 and f.prime_end <= 29 and f.cardio < 60 and f.wins > f.losses:
        return Archetype.SHOOTING_STAR

    if f.overall < 62 and 29 <= f.prime_start <= 31:
        return Archetype.LATE_BLOOMER

    career_fights = f.wins + f.losses + f.draws
    gk_age_ok = f.age >= 28 or (f.age >= 25 and career_fights >= 10)
    if gk_age_ok and 60 <= f.overall <= 68 and f.losses >= f.wins:
        return Archetype.GATEKEEPER

    if f.losses >= f.wins:
        return Archetype.JOURNEYMAN

    return Archetype.PHENOM


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
        # Always gets one elite defensive trait
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

    # Pick additional traits from pool up to target count (1-3 total)
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
    """Adjust W-L record so it fits the archetype narrative.

    Keeps total fights the same; redistributes losses to wins
    (and scales ko_wins/sub_wins proportionally) when needed.
    """
    total = f.wins + f.losses + f.draws
    if total == 0:
        return

    if archetype == Archetype.GOAT_CANDIDATE:
        min_rate = 0.70
    elif archetype == Archetype.SHOOTING_STAR:
        min_rate = 0.60
    else:
        return  # Other archetypes don't need adjustment

    fight_total = f.wins + f.losses  # excluding draws
    if fight_total == 0:
        return

    current_rate = f.wins / fight_total
    if current_rate >= min_rate:
        return

    # Calculate new wins needed for the minimum rate
    new_wins = max(f.wins, int(fight_total * min_rate) + 1)
    new_wins = min(new_wins, fight_total)  # can't exceed total
    old_wins = f.wins

    f.wins = new_wins
    f.losses = fight_total - new_wins

    # Scale ko_wins and sub_wins proportionally
    if old_wins > 0:
        ratio = new_wins / old_wins
        f.ko_wins = min(int(f.ko_wins * ratio), new_wins)
        f.sub_wins = min(int(f.sub_wins * ratio), new_wins - f.ko_wins)
    else:
        # Had zero wins before, assign some finish methods
        f.ko_wins = int(new_wins * rng.uniform(0.15, 0.40))
        f.sub_wins = int((new_wins - f.ko_wins) * rng.uniform(0.1, 0.35))


def seed_fighters(
    session: Session,
    orgs: list[Organization],
    seed: int = 42,
    count: int = 100,
) -> list[Fighter]:
    rng = random.Random(seed)
    ai_orgs = [o for o in orgs if not o.is_player]
    weight_classes = list(WeightClass)
    styles = list(FighterStyle)
    fighters: list[Fighter] = []
    # Use game start date, not real date
    game_state = session.get(GameState, 1)
    today = game_state.current_date if game_state else date(2026, 1, 1)
    goat_counts: dict[str, int] = {}

    for _ in range(count):
        age = rng.randint(20, 37)
        prime_start = rng.randint(24, 27)
        prime_end = prime_start + rng.randint(4, 8)

        record = _gen_record(age, rng)
        f = Fighter(
            name=_random_name(rng),
            age=age,
            nationality=rng.choice(_NATIONALITIES),
            weight_class=rng.choice(weight_classes),
            style=rng.choice(styles),
            striking=rng.randint(40, 92),
            grappling=rng.randint(40, 92),
            wrestling=rng.randint(40, 92),
            cardio=rng.randint(40, 92),
            chin=rng.randint(40, 92),
            speed=rng.randint(40, 92),
            prime_start=prime_start,
            prime_end=prime_end,
            wins=record["wins"],
            losses=record["losses"],
            draws=record["draws"],
            ko_wins=record["ko_wins"],
            sub_wins=record["sub_wins"],
        )
        session.add(f)
        session.flush()

        archetype = _assign_archetype(f, goat_counts, rng)
        _adjust_record_for_archetype(f, archetype, rng)
        popularity, hype = _starting_popularity_hype(archetype, rng)
        f.archetype = archetype
        f.popularity = popularity
        f.hype = hype
        f.narrative_tags = "[]"
        f.goat_score = 0.0
        f.traits = json.dumps(_assign_traits(archetype, f, rng))

        org = rng.choice(ai_orgs)
        contract = Contract(
            fighter_id=f.id,
            organization_id=org.id,
            status=ContractStatus.ACTIVE,
            salary=round(rng.uniform(8_000, 120_000), 2),
            fight_count_total=4,
            fights_remaining=rng.randint(1, 4),
            expiry_date=today + timedelta(days=rng.randint(90, 730)),
        )
        session.add(contract)
        fighters.append(f)

    # Seed training camps
    _seed_training_camps(session)

    session.commit()
    return fighters


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
