from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api import services
from models.database import Base
from models.models import (
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
        weight_class=WeightClass.WELTERWEIGHT,
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


def test_title_picture_surfaces_champion_contenders_eliminator_and_heat(tmp_path):
    db_path = tmp_path / "title_picture.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org", prestige=70.0, bank_balance=5_000_000, is_player=True
        )
        champ = _make_fighter(
            "Champion",
            overall_bias=10,
            hype=82.0,
            popularity=80.0,
            style=FighterStyle.WRESTLER,
        )
        contender1 = _make_fighter(
            "Contender One", overall_bias=8, hype=75.0, popularity=70.0
        )
        contender2 = _make_fighter(
            "Contender Two",
            overall_bias=7,
            hype=68.0,
            popularity=63.0,
            style=FighterStyle.GRAPPLER,
        )
        contender3 = _make_fighter(
            "Contender Three", overall_bias=5, hype=60.0, popularity=55.0
        )
        session.add_all(
            [
                org,
                champ,
                contender1,
                contender2,
                contender3,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.flush()

        old_event = Event(
            name="Old Defense",
            event_date=date(2025, 1, 1),
            venue="Arena",
            organization_id=org.id,
            status=EventStatus.COMPLETED,
        )
        recent_event = Event(
            name="Recent Eliminator",
            event_date=date(2025, 12, 1),
            venue="Arena",
            organization_id=org.id,
            status=EventStatus.COMPLETED,
        )
        session.add_all([old_event, recent_event])
        session.flush()
        session.add_all(
            [
                Fight(
                    event_id=old_event.id,
                    fighter_a_id=champ.id,
                    fighter_b_id=contender3.id,
                    weight_class=WeightClass.WELTERWEIGHT,
                    winner_id=champ.id,
                    method="Unanimous Decision",
                    round_ended=5,
                    time_ended="5:00",
                    is_title_fight=True,
                ),
                Fight(
                    event_id=recent_event.id,
                    fighter_a_id=contender1.id,
                    fighter_b_id=contender2.id,
                    weight_class=WeightClass.WELTERWEIGHT,
                    winner_id=contender1.id,
                    method="KO/TKO",
                    round_ended=2,
                    time_ended="3:15",
                ),
            ]
        )
        session.commit()

    services.init_db(db_url)
    picture = services.get_title_picture("Welterweight")

    assert picture["champion"]["name"] == "Champion"
    assert len(picture["contenders"]) >= 3
    assert picture["title_eliminator"]["fighter_a"]["name"] == "Contender One"
    assert picture["division_heat"]["label"] in {"Boiling", "Warm", "Cold"}
    assert picture["politics"]
