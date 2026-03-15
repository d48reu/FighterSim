from datetime import date

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
