from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
from simulation.trajectory import analyze_fighter_trajectory


def _make_fighter(
    name: str, age: int, confidence: float = 70.0, hype: float = 30.0
) -> Fighter:
    return Fighter(
        name=name,
        age=age,
        nationality="American",
        weight_class=WeightClass.LIGHTWEIGHT,
        style=FighterStyle.STRIKER,
        striking=70,
        grappling=65,
        wrestling=60,
        cardio=72,
        chin=68,
        speed=73,
        wins=8,
        losses=3,
        draws=0,
        ko_wins=4,
        sub_wins=1,
        prime_start=25,
        prime_end=31,
        confidence=confidence,
        hype=hype,
        popularity=35.0,
    )


def test_rising_trajectory_for_young_fighter_on_streak():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        org = Organization(
            name="Test Org", prestige=50, bank_balance=1_000_000, is_player=True
        )
        a = _make_fighter("Alpha", 24, confidence=86.0, hype=72.0)
        b = _make_fighter("Bravo", 29)
        session.add_all(
            [org, a, b, GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1)]
        )
        session.flush()

        for idx in range(3):
            event = Event(
                name=f"Event {idx}",
                event_date=date(2025, 12 - idx, 1),
                venue="Arena",
                organization_id=org.id,
                status=EventStatus.COMPLETED,
            )
            session.add(event)
            session.flush()
            session.add(
                Fight(
                    event_id=event.id,
                    fighter_a_id=a.id,
                    fighter_b_id=b.id,
                    weight_class=WeightClass.LIGHTWEIGHT,
                    winner_id=a.id,
                    method="KO/TKO",
                    round_ended=1,
                    time_ended="2:10",
                )
            )
        session.commit()

        result = analyze_fighter_trajectory(a, session)
        assert result["label"] in {"Rising", "Peaking"}
        assert result["recent_form"] == "3-0"
        assert result["reasons"]


def test_declining_trajectory_for_older_inactive_fighter():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        org = Organization(
            name="Test Org", prestige=50, bank_balance=1_000_000, is_player=True
        )
        a = _make_fighter("Aging Vet", 36, confidence=45.0, hype=18.0)
        b = _make_fighter("Opponent", 28)
        session.add_all(
            [org, a, b, GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1)]
        )
        session.flush()

        for idx in range(2):
            event = Event(
                name=f"Past Event {idx}",
                event_date=date(2025, 1 - idx if idx == 0 else 1, 1),
                venue="Arena",
                organization_id=org.id,
                status=EventStatus.COMPLETED,
            )
            # keep dates valid and old
            event.event_date = date(2025 - idx, 1, 1)
            session.add(event)
            session.flush()
            session.add(
                Fight(
                    event_id=event.id,
                    fighter_a_id=a.id,
                    fighter_b_id=b.id,
                    weight_class=WeightClass.LIGHTWEIGHT,
                    winner_id=b.id,
                    method="Unanimous Decision",
                    round_ended=3,
                    time_ended="5:00",
                )
            )
        session.commit()

        result = analyze_fighter_trajectory(a, session)
        assert result["label"] in {"Declining", "Stalled"}
        assert result["age_phase"] == "post-prime"
