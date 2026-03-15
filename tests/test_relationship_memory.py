from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine, select
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
    hype: float = 40.0,
    popularity: float = 40.0,
    confidence: float = 70.0,
    style=FighterStyle.STRIKER,
) -> Fighter:
    base = 70 + overall_bias
    return Fighter(
        name=name,
        age=age,
        nationality="American",
        weight_class=WeightClass.LIGHTWEIGHT,
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


def test_lowball_rejection_persists_relationship_memory_and_hurts_future_talks(
    tmp_path,
):
    db_path = tmp_path / "relationship_memory.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org", prestige=62.0, bank_balance=5_000_000, is_player=True
        )
        fighter = _make_fighter(
            "Tough Negotiator", age=27, overall_bias=6, hype=66.0, popularity=58.0
        )
        session.add_all(
            [
                org,
                fighter,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.commit()

    services.init_db(db_url)

    with services._SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one()
        fighter = session.execute(
            select(Fighter).where(Fighter.name == "Tough Negotiator")
        ).scalar_one()
        baseline = services._offer_evaluation_dict(
            fighter,
            player_org,
            offered_salary=120_000,
            session=session,
            org_id=player_org.id,
            fight_count=4,
            length_months=18,
        )

    with patch("api.services.random.random", return_value=0.99):
        rejected = services.make_contract_offer(
            fighter_id=1,
            salary=50_000,
            fight_count=2,
            length_months=12,
        )
    assert rejected["accepted"] is False

    payload = services.get_fighter(1)
    assert payload is not None
    assert "relationship_memory" in payload
    assert payload["relationship_memory"]["lowball_offer_count"] == 1
    assert payload["relationship_memory"]["rejected_offer_count"] == 1

    with services._SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one()
        fighter = session.execute(
            select(Fighter).where(Fighter.name == "Tough Negotiator")
        ).scalar_one()
        after = services._offer_evaluation_dict(
            fighter,
            player_org,
            offered_salary=120_000,
            session=session,
            org_id=player_org.id,
            fight_count=4,
            length_months=18,
        )

    assert any(adj["key"] == "relationship" for adj in after["preference_adjustments"])
    assert after["acceptance_probability"] < baseline["acceptance_probability"]


def test_successful_renewal_improves_relationship_memory(tmp_path):
    db_path = tmp_path / "relationship_renewal.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org", prestige=70.0, bank_balance=5_000_000, is_player=True
        )
        fighter = _make_fighter(
            "Loyal Veteran",
            age=31,
            overall_bias=5,
            hype=72.0,
            popularity=69.0,
            style=FighterStyle.WRESTLER,
        )
        session.add_all(
            [
                org,
                fighter,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add(
            Contract(
                fighter_id=fighter.id,
                organization_id=org.id,
                status=ContractStatus.ACTIVE,
                salary=150_000,
                fight_count_total=4,
                fights_remaining=1,
                expiry_date=date(2026, 2, 1),
            )
        )
        session.commit()

    services.init_db(db_url)

    with patch("api.services.random.random", return_value=0.0):
        accepted = services.renew_contract(
            fighter_id=1,
            salary=150_000,
            fight_count=5,
            length_months=18,
        )
    assert accepted["accepted"] is True

    payload = services.get_fighter(1)
    assert payload is not None
    assert payload["relationship_memory"]["successful_renewals"] == 1
    assert payload["relationship_memory"]["trust_label"] in {"Medium", "High"}

    with services._SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one()
        fighter = session.execute(
            select(Fighter).where(Fighter.name == "Loyal Veteran")
        ).scalar_one()
        evaluation = services._offer_evaluation_dict(
            fighter,
            player_org,
            offered_salary=150_000,
            session=session,
            org_id=player_org.id,
            is_renewal=True,
            fight_count=5,
            length_months=18,
        )

    assert any(
        adj["key"] == "relationship" for adj in evaluation["preference_adjustments"]
    )
    assert evaluation["relationship_memory"]["successful_renewals"] == 1
