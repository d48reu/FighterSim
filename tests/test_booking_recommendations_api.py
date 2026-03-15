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
    age: int = 28,
    overall_bias: int = 0,
    confidence: float = 70.0,
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
    weight_class=WeightClass.LIGHTWEIGHT,
) -> Fighter:
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
        confidence=confidence,
        hype=hype,
        popularity=popularity,
    )


def test_booking_recommendations_surface_main_co_main_and_prospect_options(tmp_path):
    db_path = tmp_path / "booking_recommendations.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org",
            prestige=70.0,
            bank_balance=5_000_000,
            is_player=True,
        )
        fighters = [
            _make_fighter("Headliner A", overall_bias=8, hype=78.0, popularity=74.0),
            _make_fighter(
                "Headliner B",
                overall_bias=7,
                hype=75.0,
                popularity=70.0,
                style=FighterStyle.WRESTLER,
            ),
            _make_fighter(
                "Prospect A", age=23, overall_bias=1, hype=32.0, popularity=28.0
            ),
            _make_fighter(
                "Veteran Foil",
                age=35,
                overall_bias=5,
                hype=40.0,
                popularity=42.0,
                style=FighterStyle.WRESTLER,
            ),
            _make_fighter(
                "Solid CoMain",
                overall_bias=4,
                hype=55.0,
                popularity=50.0,
                style=FighterStyle.GRAPPLER,
            ),
        ]
        session.add_all(
            [
                org,
                *fighters,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add_all(
            [
                Contract(
                    fighter_id=f.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=100_000 + (idx * 10_000),
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                )
                for idx, f in enumerate(fighters)
            ]
        )
        session.commit()

    services.init_db(db_url)
    data = services.get_event_booking_recommendations()

    assert set(data.keys()) == {
        "best_main_event",
        "best_co_main",
        "best_prospect_fight",
        "best_safe_money_fight",
    }
    assert data["best_main_event"]["booking_value"] in {
        "Strong Main Event",
        "Strong Co-Main",
    }
    assert (
        data["best_main_event"]["fighter_a_id"]
        != data["best_main_event"]["fighter_b_id"]
    )
    assert data["best_prospect_fight"]["prospect_risk"] in {"Medium", "High"}
    assert data["best_safe_money_fight"]["booking_value"] in {
        "Strong Main Event",
        "Strong Co-Main",
        "Risky Development Fight",
    }
