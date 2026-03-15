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
    Contract,
    ContractStatus,
)


def _make_fighter(
    name: str,
    *,
    overall_bias: int = 0,
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
):
    base = 70 + overall_bias
    return Fighter(
        name=name,
        age=28,
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
        confidence=70.0,
        hype=hype,
        popularity=popularity,
    )


def test_inactive_champion_cannot_be_booked_in_non_title_fight(tmp_path):
    db_path = tmp_path / "title_lock.db"
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
            hype=82,
            popularity=80,
            style=FighterStyle.WRESTLER,
        )
        contender = _make_fighter("Contender", overall_bias=7, hype=74, popularity=70)
        foil = _make_fighter(
            "Foil", overall_bias=5, hype=60, popularity=54, style=FighterStyle.GRAPPLER
        )
        session.add_all(
            [
                org,
                champ,
                contender,
                foil,
                GameState(id=1, current_date=date(2026, 4, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add_all(
            [
                Contract(
                    fighter_id=champ.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=180_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
                Contract(
                    fighter_id=contender.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=140_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
                Contract(
                    fighter_id=foil.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=120_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
            ]
        )
        old_title = Event(
            name="Old Title Fight",
            event_date=date(2025, 1, 1),
            venue="Arena",
            organization_id=org.id,
            status=EventStatus.COMPLETED,
        )
        session.add(old_title)
        session.flush()
        session.add(
            Fight(
                event_id=old_title.id,
                fighter_a_id=champ.id,
                fighter_b_id=foil.id,
                weight_class=WeightClass.WELTERWEIGHT,
                winner_id=champ.id,
                method="Unanimous Decision",
                round_ended=5,
                time_ended="5:00",
                is_title_fight=True,
            )
        )
        upcoming = Event(
            name="Upcoming Card",
            event_date=date(2026, 4, 15),
            venue="Arena",
            organization_id=org.id,
            status=EventStatus.SCHEDULED,
        )
        session.add(upcoming)
        session.commit()
        upcoming_id = upcoming.id
        champ_id = champ.id
        contender_id = contender.id

    services.init_db(db_url)

    blocked = services.add_fight_to_event(
        upcoming_id, champ_id, contender_id, is_title_fight=False
    )
    assert "error" in blocked
    assert "title defense" in blocked["error"].lower()

    allowed = services.add_fight_to_event(
        upcoming_id, champ_id, contender_id, is_title_fight=True
    )
    assert "error" not in allowed
