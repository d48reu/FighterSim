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
    confidence: float = 70.0,
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
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


def test_decision_center_groups_roster_pressure_and_buy_targets(tmp_path):
    db_path = tmp_path / "decision_center.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        player_org = Organization(
            name="Player Org",
            prestige=65.0,
            bank_balance=5_000_000,
            is_player=True,
        )
        hot_prospect = _make_fighter(
            "Hot Prospect",
            age=24,
            overall_bias=6,
            confidence=86.0,
            hype=72.0,
            popularity=65.0,
        )
        fading_vet = _make_fighter(
            "Fading Vet",
            age=36,
            overall_bias=1,
            confidence=45.0,
            hype=18.0,
            popularity=20.0,
        )
        free_agent = _make_fighter(
            "Buy Candidate",
            weight_class=WeightClass.WELTERWEIGHT,
            age=23,
            overall_bias=5,
            confidence=84.0,
            hype=60.0,
            popularity=55.0,
        )
        welterweight_anchor = _make_fighter(
            "Welterweight Anchor",
            weight_class=WeightClass.WELTERWEIGHT,
            age=29,
            overall_bias=4,
            confidence=72.0,
            hype=52.0,
            popularity=48.0,
            style=FighterStyle.WRESTLER,
        )
        session.add_all(
            [
                player_org,
                hot_prospect,
                fading_vet,
                free_agent,
                welterweight_anchor,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add_all(
            [
                Contract(
                    fighter_id=hot_prospect.id,
                    organization_id=player_org.id,
                    status=ContractStatus.ACTIVE,
                    salary=110_000,
                    fight_count_total=4,
                    fights_remaining=1,
                    expiry_date=date(2026, 2, 1),
                ),
                Contract(
                    fighter_id=fading_vet.id,
                    organization_id=player_org.id,
                    status=ContractStatus.ACTIVE,
                    salary=140_000,
                    fight_count_total=4,
                    fights_remaining=3,
                    expiry_date=date(2026, 6, 1),
                ),
                Contract(
                    fighter_id=welterweight_anchor.id,
                    organization_id=player_org.id,
                    status=ContractStatus.ACTIVE,
                    salary=95_000,
                    fight_count_total=4,
                    fights_remaining=3,
                    expiry_date=date(2026, 7, 1),
                ),
            ]
        )
        session.commit()

    services.init_db(db_url)
    center = services.get_roster_decision_center()

    assert set(center.keys()) == {
        "expiring_contracts",
        "sell_candidates",
        "buy_targets",
        "division_outlook",
    }
    assert any(item["name"] == "Hot Prospect" for item in center["expiring_contracts"])
    assert any(item["name"] == "Fading Vet" for item in center["sell_candidates"])
    assert any(item["name"] == "Buy Candidate" for item in center["buy_targets"])
    assert any(
        item["weight_class"] == "Welterweight" for item in center["division_outlook"]
    )
    assert all("recommendation" in item for item in center["expiring_contracts"])
    assert all("recommendation" in item for item in center["sell_candidates"])
    assert all("recommendation" in item for item in center["buy_targets"])
