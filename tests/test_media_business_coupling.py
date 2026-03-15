from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
from simulation.market import compute_market_signals
from simulation.matchmaking import assess_matchup


def _make_fighter(
    name: str,
    *,
    age: int = 28,
    overall_bias: int = 0,
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
        confidence=70.0,
        hype=hype,
        popularity=popularity,
    )


def test_rivalry_storyline_can_upgrade_matchup_value():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        a = _make_fighter("A Side", overall_bias=6, hype=55.0, popularity=55.0)
        b = _make_fighter(
            "B Side",
            overall_bias=5,
            hype=55.0,
            popularity=55.0,
            style=FighterStyle.WRESTLER,
        )
        session.add_all([a, b])
        session.flush()

        baseline = assess_matchup(a, b)
        assert baseline["booking_value"] == "Strong Co-Main"

        a.rivalry_with = b.id
        b.rivalry_with = a.id
        session.flush()

        heated = assess_matchup(a, b)

        assert heated["media_storyline"]["type"] == "rivalry"
        assert heated["booking_value"] == "Strong Main Event"
        assert heated["combined_draw"] > baseline["combined_draw"]


def test_media_storyline_bonuses_flow_into_market_signals():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org",
            prestige=65.0,
            bank_balance=2_000_000,
            is_player=True,
        )
        free_agent = _make_fighter(
            "Buzz Prospect",
            age=23,
            overall_bias=6,
            hype=58.0,
            popularity=42.0,
        )
        roster_opponent = _make_fighter(
            "Roster Opponent",
            overall_bias=5,
            hype=54.0,
            popularity=50.0,
            style=FighterStyle.GRAPPLER,
        )
        session.add_all(
            [
                org,
                free_agent,
                roster_opponent,
                GameState(id=1, current_date=date(2026, 4, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add(
            Contract(
                fighter_id=roster_opponent.id,
                organization_id=org.id,
                status=ContractStatus.ACTIVE,
                salary=100_000,
                fight_count_total=4,
                fights_remaining=4,
                expiry_date=date(2026, 12, 1),
            )
        )
        session.flush()

        baseline = compute_market_signals(free_agent, session, org.id)
        assert "Rivalry Heat" not in baseline["storyline"]["labels"]

        free_agent.rivalry_with = roster_opponent.id
        roster_opponent.rivalry_with = free_agent.id
        session.flush()

        heated = compute_market_signals(free_agent, session, org.id)

        assert "Rivalry Heat" in heated["storyline"]["labels"]
        assert heated["salary_multiplier"] > baseline["salary_multiplier"]
        assert heated["sponsorship_multiplier"] > baseline["sponsorship_multiplier"]
