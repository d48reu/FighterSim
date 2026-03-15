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
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
    weight_class=WeightClass.WELTERWEIGHT,
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


def test_media_storylines_surface_rivalry_title_and_prospect_buzz(tmp_path):
    db_path = tmp_path / "media_storylines.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org", prestige=72.0, bank_balance=5_000_000, is_player=True
        )
        champ = _make_fighter(
            "Champion",
            overall_bias=9,
            hype=84,
            popularity=81,
            style=FighterStyle.WRESTLER,
        )
        contender = _make_fighter(
            "Top Contender", overall_bias=8, hype=78, popularity=74
        )
        rival = _make_fighter(
            "Blood Rival",
            overall_bias=7,
            hype=76,
            popularity=70,
            style=FighterStyle.GRAPPLER,
        )
        prospect = _make_fighter(
            "Blue Chip Prospect", age=23, overall_bias=6, hype=58, popularity=42
        )
        champ.rivalry_with = rival.id if rival.id else None
        rival.rivalry_with = champ.id if champ.id else None
        session.add_all(
            [
                org,
                champ,
                contender,
                rival,
                prospect,
                GameState(id=1, current_date=date(2026, 4, 1), player_org_id=1),
            ]
        )
        session.flush()
        champ.rivalry_with = rival.id
        rival.rivalry_with = champ.id
        old_event = Event(
            name="Old Defense",
            event_date=date(2025, 1, 1),
            venue="Arena",
            organization_id=org.id,
            status=EventStatus.COMPLETED,
        )
        recent_event = Event(
            name="Contender Fight",
            event_date=date(2026, 3, 1),
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
                    fighter_b_id=rival.id,
                    weight_class=WeightClass.WELTERWEIGHT,
                    winner_id=champ.id,
                    method="KO/TKO",
                    round_ended=3,
                    time_ended="3:30",
                    is_title_fight=True,
                ),
                Fight(
                    event_id=recent_event.id,
                    fighter_a_id=contender.id,
                    fighter_b_id=rival.id,
                    weight_class=WeightClass.WELTERWEIGHT,
                    winner_id=contender.id,
                    method="Unanimous Decision",
                    round_ended=3,
                    time_ended="5:00",
                ),
            ]
        )
        session.commit()

    services.init_db(db_url)
    storylines = services.get_media_storylines()

    assert len(storylines) >= 3
    assert any(item["type"] == "rivalry" for item in storylines)
    assert any(item["type"] == "title" for item in storylines)
    assert any(item["type"] == "prospect" for item in storylines)
    assert all("headline" in item and "angle" in item for item in storylines)
