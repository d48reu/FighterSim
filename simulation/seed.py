"""Database seeding for MMA Management Simulator."""

from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models.models import (
    Fighter, Organization, Contract,
    WeightClass, FighterStyle, ContractStatus,
)

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
    return orgs


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
    today = date.today()

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
