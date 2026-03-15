from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.app import create_app
from models.database import Base
from models.models import GameState, Organization


def test_dashboard_template_promotes_business_signals_over_duplicate_stats(tmp_path):
    db_path = tmp_path / "dashboard_ui.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org",
            prestige=55.0,
            bank_balance=5_000_000,
            is_player=True,
        )
        session.add(org)
        session.flush()
        session.add(
            GameState(id=1, current_date=date(2026, 1, 1), player_org_id=org.id)
        )
        session.commit()

    app = create_app(db_url)
    client = app.test_client()
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="dash-broadcast-status"' in html
    assert 'id="dash-sponsorship-income"' in html
    assert 'id="dash-balance"' not in html
    assert 'id="dash-roster-size"' not in html


def test_dashboard_empty_states_use_actionable_copy_and_keep_business_widgets_visible():
    js = Path("frontend/static/js/app.js").read_text(encoding="utf-8")

    assert "No event booked this month." in js
    assert "Open Events and build a card before you burn a month." in js
    assert "No completed shows yet." in js
    assert (
        "Book and simulate an event so the promotion starts generating history." in js
    )
    assert "No broadcast deal yet." in js
    assert "Open TV Deals and lock in distribution before prestige stalls." in js
    assert "No active sponsor income." in js
    assert "Use Roster to target marketable fighters and start monetizing them." in js
    assert "No reality show running." in js
    assert "Start one if you want prospect hype and a discounted winner signing." in js
    assert "No upcoming events. Go to Events to create one." not in js
    assert "No completed events yet." not in js
