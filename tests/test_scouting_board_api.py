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


def test_scouting_board_surfaces_prospects_sleepers_and_division_targets(tmp_path):
    db_path = tmp_path / "scouting_board.db"
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
        roster_anchor = _make_fighter(
            "Roster Anchor",
            weight_class=WeightClass.LIGHTWEIGHT,
            age=29,
            overall_bias=5,
            confidence=72.0,
            hype=68.0,
            popularity=62.0,
            style=FighterStyle.WRESTLER,
        )
        prospect = _make_fighter(
            "Blue Chip Prospect",
            weight_class=WeightClass.WELTERWEIGHT,
            age=23,
            overall_bias=6,
            confidence=85.0,
            hype=58.0,
            popularity=44.0,
        )
        sleeper = _make_fighter(
            "Hidden Gem",
            weight_class=WeightClass.MIDDLEWEIGHT,
            age=25,
            overall_bias=4,
            confidence=80.0,
            hype=36.0,
            popularity=24.0,
            style=FighterStyle.GRAPPLER,
        )
        ready = _make_fighter(
            "Ready Now",
            weight_class=WeightClass.WELTERWEIGHT,
            age=27,
            overall_bias=7,
            confidence=82.0,
            hype=70.0,
            popularity=66.0,
            style=FighterStyle.WRESTLER,
        )
        session.add_all(
            [
                org,
                roster_anchor,
                prospect,
                sleeper,
                ready,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add(
            Contract(
                fighter_id=roster_anchor.id,
                organization_id=org.id,
                status=ContractStatus.ACTIVE,
                salary=110_000,
                fight_count_total=4,
                fights_remaining=3,
                expiry_date=date(2026, 12, 1),
            )
        )
        session.commit()

    services.init_db(db_url)
    board = services.get_scouting_board()

    assert set(board.keys()) == {
        "featured_prospects",
        "under_the_radar",
        "ready_now",
        "division_targets",
    }
    assert any(
        item["name"] == "Blue Chip Prospect" for item in board["featured_prospects"]
    )
    assert any(item["name"] == "Hidden Gem" for item in board["under_the_radar"])
    assert any(item["name"] == "Ready Now" for item in board["ready_now"])
    assert any(
        item["weight_class"] == "Welterweight" for item in board["division_targets"]
    )
    assert all("recommendation" in item for item in board["featured_prospects"])
    assert all("scouting_report" in item for item in board["featured_prospects"])
    assert all(
        "estimated_overall_range" in item["scouting_report"]
        for item in board["featured_prospects"]
    )
    assert all(
        item["scouting_report"]["confidence_label"] in {"Low", "Medium", "High"}
        for item in board["featured_prospects"]
    )
