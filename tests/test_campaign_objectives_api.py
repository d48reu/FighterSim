from datetime import date

from sqlalchemy import create_engine
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
    overall_bias: int = 0,
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
) -> Fighter:
    base = 70 + overall_bias
    return Fighter(
        name=name,
        age=28,
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
        confidence=70.0,
        hype=hype,
        popularity=popularity,
    )


def test_campaign_objectives_track_origin_progress(tmp_path):
    db_path = tmp_path / "campaign_objectives.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org", prestige=36.0, bank_balance=3_200_000, is_player=True
        )
        fighters = [
            _make_fighter(f"Roster {idx}", overall_bias=idx % 3) for idx in range(10)
        ]
        session.add_all(
            [
                org,
                *fighters,
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
                    fighter_id=f.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=80_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                )
                for f in fighters
            ]
        )
        event = Event(
            name="Comeback Card",
            event_date=date(2026, 3, 1),
            venue="Arena",
            organization_id=org.id,
            status=EventStatus.COMPLETED,
        )
        session.add(event)
        session.flush()
        session.add_all(
            [
                Fight(
                    event_id=event.id,
                    fighter_a_id=fighters[0].id,
                    fighter_b_id=fighters[1].id,
                    weight_class=WeightClass.LIGHTWEIGHT,
                    winner_id=fighters[0].id,
                    method="KO/TKO",
                    round_ended=2,
                    time_ended="3:00",
                ),
                Fight(
                    event_id=event.id,
                    fighter_a_id=fighters[2].id,
                    fighter_b_id=fighters[3].id,
                    weight_class=WeightClass.LIGHTWEIGHT,
                    winner_id=fighters[2].id,
                    method="Unanimous Decision",
                    round_ended=3,
                    time_ended="5:00",
                ),
            ]
        )
        session.commit()

    services.init_db(db_url)
    objectives = services.get_campaign_objectives()

    assert objectives["origin_type"] == "The Comeback"
    assert objectives["origin_label"] == "The Comeback"
    assert objectives["summary"]
    assert objectives["completed_count"] >= 2
    assert len(objectives["objectives"]) >= 3
    assert all("progress_pct" in obj for obj in objectives["objectives"])
    assert any(obj["completed"] for obj in objectives["objectives"])
    assert any(obj["key"] == "prestige" for obj in objectives["objectives"])
