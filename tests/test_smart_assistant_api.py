from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api import services
from models.database import Base
from models.models import (
    Contract,
    ContractStatus,
    Fighter,
    FighterStyle,
    GameState,
    Organization,
    WeightClass,
)


def _make_fighter(
    name: str,
    *,
    weight_class=WeightClass.LIGHTWEIGHT,
    age: int = 28,
    overall_bias: int = 0,
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
):
    base = 70 + overall_bias
    return Fighter(
        name=name,
        age=age,
        nationality="American",
        weight_class=weight_class,
        style=style,
        striking=base,
        grappling=base,
        wrestling=base,
        cardio=base,
        chin=base,
        speed=base,
        wins=10,
        losses=3,
        draws=0,
        ko_wins=5,
        sub_wins=1,
        prime_start=25,
        prime_end=31,
        confidence=70.0,
        hype=hype,
        popularity=popularity,
    )


def test_smart_assistant_actions_surface_best_move_categories(tmp_path):
    db_path = tmp_path / "smart_assistant.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org", prestige=36.0, bank_balance=3_500_000, is_player=True
        )
        roster_fighters = [
            _make_fighter("Core Prospect", overall_bias=6, hype=72, popularity=66),
            _make_fighter("Aging Vet", age=36, overall_bias=1, hype=20, popularity=24),
            _make_fighter(
                "Welterweight Anchor",
                weight_class=WeightClass.WELTERWEIGHT,
                overall_bias=5,
                hype=60,
                popularity=58,
                style=FighterStyle.WRESTLER,
            ),
        ]
        free_agent = _make_fighter(
            "Buy Candidate",
            weight_class=WeightClass.WELTERWEIGHT,
            age=24,
            overall_bias=7,
            hype=70,
            popularity=64,
        )
        opponent = _make_fighter(
            "Opponent",
            overall_bias=5,
            hype=62,
            popularity=57,
            style=FighterStyle.GRAPPLER,
        )
        session.add_all(
            [
                org,
                *roster_fighters,
                free_agent,
                opponent,
                GameState(
                    id=1,
                    current_date=date(2026, 4, 1),
                    player_org_id=1,
                    origin_type="The Comeback",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                Contract(
                    fighter_id=roster_fighters[0].id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=120_000,
                    fight_count_total=4,
                    fights_remaining=1,
                    expiry_date=date(2026, 5, 1),
                ),
                Contract(
                    fighter_id=roster_fighters[1].id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=140_000,
                    fight_count_total=4,
                    fights_remaining=3,
                    expiry_date=date(2026, 8, 1),
                ),
                Contract(
                    fighter_id=roster_fighters[2].id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=110_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
                Contract(
                    fighter_id=opponent.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=105_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
            ]
        )
        session.commit()

    services.init_db(db_url)
    actions = services.get_smart_assistant_actions()

    assert set(actions.keys()) == {
        "best_signing",
        "best_renewal",
        "best_booking",
        "biggest_risk",
    }
    assert actions["best_signing"]["headline"]
    assert actions["best_renewal"]["headline"]
    assert actions["best_booking"]["headline"]
    assert actions["biggest_risk"]["headline"]
    assert actions["best_signing"]["fighter_name"] == "Buy Candidate"
    assert actions["best_renewal"]["fighter_name"] == "Core Prospect"
    assert actions["biggest_risk"]["fighter_name"] in {"Core Prospect", "Aging Vet"}
    assert actions["best_signing"]["action"]["kind"] == "open_free_agent"
    assert actions["best_renewal"]["action"]["kind"] == "open_renewal"
    assert actions["best_booking"]["action"]["kind"] == "prepare_booking"
    assert actions["biggest_risk"]["action"]["kind"] == "open_roster_fighter"
