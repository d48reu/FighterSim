from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api import services
from models.database import Base
from models.models import (
    Contract,
    ContractStatus,
    Event,
    EventStatus,
    Fight,
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


def test_fighter_payload_exposes_negotiation_profile_and_offer_eval_uses_preferences(
    tmp_path,
):
    db_path = tmp_path / "negotiation_profile.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org",
            prestige=68.0,
            bank_balance=5_000_000,
            is_player=True,
        )
        loyal_star = _make_fighter(
            "Loyal Star",
            age=29,
            overall_bias=7,
            confidence=82.0,
            hype=74.0,
            popularity=71.0,
            style=FighterStyle.WRESTLER,
        )
        loyal_star.is_cornerstone = True
        restless_prospect = _make_fighter(
            "Restless Prospect",
            age=23,
            overall_bias=3,
            confidence=68.0,
            hype=32.0,
            popularity=26.0,
        )
        foil = _make_fighter("Foil", age=30, overall_bias=1)
        session.add_all(
            [
                org,
                loyal_star,
                restless_prospect,
                foil,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add(
            Contract(
                fighter_id=loyal_star.id,
                organization_id=org.id,
                status=ContractStatus.ACTIVE,
                salary=150_000,
                fight_count_total=4,
                fights_remaining=2,
                expiry_date=date(2026, 3, 1),
            )
        )
        old_event = Event(
            name="Old Event",
            event_date=date(2025, 3, 1),
            venue="Arena",
            organization_id=org.id,
            status=EventStatus.COMPLETED,
        )
        session.add(old_event)
        session.flush()
        session.add(
            Fight(
                event_id=old_event.id,
                fighter_a_id=restless_prospect.id,
                fighter_b_id=foil.id,
                weight_class=WeightClass.LIGHTWEIGHT,
                winner_id=restless_prospect.id,
                method="KO/TKO",
                round_ended=1,
                time_ended="2:00",
            )
        )
        session.commit()

    services.init_db(db_url)

    fighter_payload = services.get_fighter(1)
    assert fighter_payload is not None
    assert "negotiation_profile" in fighter_payload
    assert fighter_payload["negotiation_profile"]["morale_label"] in {
        "High",
        "Stable",
        "Low",
    }
    assert fighter_payload["negotiation_profile"]["loyalty_label"] in {
        "High",
        "Medium",
        "Low",
    }

    with services._SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one()
        prospect = session.execute(
            select(Fighter).where(Fighter.name == "Restless Prospect")
        ).scalar_one()
        loyal = session.execute(
            select(Fighter).where(Fighter.name == "Loyal Star")
        ).scalar_one()

        short_eval = services._offer_evaluation_dict(
            prospect,
            player_org,
            offered_salary=95_000,
            session=session,
            org_id=player_org.id,
            fight_count=2,
            length_months=12,
        )
        active_eval = services._offer_evaluation_dict(
            prospect,
            player_org,
            offered_salary=95_000,
            session=session,
            org_id=player_org.id,
            fight_count=6,
            length_months=24,
        )
        renewal_eval = services._offer_evaluation_dict(
            loyal,
            player_org,
            offered_salary=150_000,
            session=session,
            org_id=player_org.id,
            is_renewal=True,
            fight_count=5,
            length_months=18,
        )

    assert short_eval["negotiation_profile"]["activity_priority"] in {
        "High",
        "Medium",
        "Low",
    }
    assert any(
        adj["key"] == "activity" for adj in active_eval["preference_adjustments"]
    )
    assert active_eval["acceptance_probability"] > short_eval["acceptance_probability"]
    assert any(
        adj["key"] == "loyalty" for adj in renewal_eval["preference_adjustments"]
    )
    assert renewal_eval["negotiation_profile"]["loyalty_label"] == "High"
