"""Database seeding for MMA Management Simulator."""

from __future__ import annotations

import json
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models.models import (
    Fighter, Organization, Contract, GameState,
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
    ):
        goat_counts[wc] = goat_counts.get(wc, 0) + 1
        return Archetype.GOAT_CANDIDATE

    if f.overall >= 70 and 19 <= f.age <= 24 and f.losses <= 2:
        return Archetype.PHENOM

    if f.overall >= 68 and f.prime_end <= 29 and f.cardio < 60:
        return Archetype.SHOOTING_STAR

    if f.overall < 62 and 29 <= f.prime_start <= 31:
        return Archetype.LATE_BLOOMER

    if 28 <= f.age <= 34 and 60 <= f.overall <= 68 and f.losses >= f.wins:
        return Archetype.GATEKEEPER

    if f.losses > f.wins:
        return Archetype.JOURNEYMAN

    return rng.choice([Archetype.PHENOM, Archetype.GATEKEEPER, Archetype.JOURNEYMAN])


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
    if archetype == Archetype.GATEKEEPER:
        traits.append("veteran_iq")
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
            wins=rng.randint(0, 15),
            losses=rng.randint(0, 8),
        )
        session.add(f)
        session.flush()

        archetype = _assign_archetype(f, goat_counts, rng)
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

    session.commit()
    return fighters
