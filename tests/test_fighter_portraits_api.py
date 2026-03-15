from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api import services
from models.database import Base
from models.models import Fighter, FighterStyle, GameState, Organization, WeightClass


def _make_fighter(name: str) -> Fighter:
    return Fighter(
        name=name,
        age=27,
        nationality="American",
        weight_class=WeightClass.LIGHTWEIGHT,
        style=FighterStyle.STRIKER,
        striking=74,
        grappling=68,
        wrestling=66,
        cardio=71,
        chin=69,
        speed=73,
        wins=10,
        losses=3,
        draws=0,
        ko_wins=4,
        sub_wins=2,
        prime_start=25,
        prime_end=31,
        confidence=70.0,
        popularity=45.0,
        hype=42.0,
        portrait_key="prime/striker/global_01.svg",
    )


def test_get_fighter_exposes_portrait_url(tmp_path):
    db_path = tmp_path / "fighter_portraits.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org", prestige=55.0, bank_balance=5_000_000, is_player=True
        )
        fighter = _make_fighter("Portrait Prospect")
        session.add_all(
            [
                org,
                fighter,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.commit()
        fighter_id = fighter.id

    services.init_db(db_url)
    payload = services.get_fighter(fighter_id)

    assert payload is not None
    assert payload["portrait_key"] == "prime/striker/global_01.svg"
    assert (
        payload["portrait_url"]
        == "/static/assets/portraits/prime/striker/global_01.svg"
    )


def test_fighter_panel_template_includes_portrait_slot():
    html = Path("frontend/templates/index.html").read_text(encoding="utf-8")
    assert 'id="panel-portrait"' in html
    assert 'id="panel-portrait-fallback"' in html
