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
        confidence=confidence,
        hype=hype,
        popularity=popularity,
    )


def test_free_agents_expose_market_context_and_offers_return_evaluation(tmp_path):
    db_path = tmp_path / "market_api.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        player_org = Organization(
            name="Player Org",
            prestige=65.0,
            bank_balance=5_000_000,
            is_player=True,
        )
        target = _make_fighter(
            "Rising Target",
            age=24,
            overall_bias=6,
            confidence=86.0,
            hype=72.0,
            popularity=65.0,
        )
        roster_anchor = _make_fighter(
            "Roster Anchor",
            age=29,
            overall_bias=5,
            confidence=72.0,
            hype=68.0,
            popularity=62.0,
            style=FighterStyle.WRESTLER,
        )
        session.add_all(
            [
                player_org,
                target,
                roster_anchor,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
            ]
        )
        session.flush()
        session.add(
            Contract(
                fighter_id=roster_anchor.id,
                organization_id=player_org.id,
                status=ContractStatus.ACTIVE,
                salary=100_000,
                fight_count_total=4,
                fights_remaining=4,
                expiry_date=date(2026, 12, 1),
            )
        )
        session.commit()

    services.init_db(db_url)

    free_agents = services.get_free_agents(weight_class="Lightweight")
    target_entry = next(f for f in free_agents if f["name"] == "Rising Target")

    assert "market_context" in target_entry
    market_context = target_entry["market_context"]
    assert market_context["trajectory_label"] in {
        "Rising",
        "Peaking",
        "Volatile",
        "Stalled",
        "Declining",
    }
    assert "salary_multiplier" in market_context
    assert "acceptance_adjustment" in market_context
    assert "market_value_hint" in market_context

    result = services.make_contract_offer(
        fighter_id=target_entry["id"],
        salary=target_entry["asking_salary"],
        fight_count=4,
        length_months=12,
    )

    assert "offer_evaluation" in result
    evaluation = result["offer_evaluation"]
    assert evaluation["asking_salary"] == target_entry["asking_salary"]
    assert evaluation["offered_salary"] == target_entry["asking_salary"]
    assert 0.0 < evaluation["acceptance_probability"] <= 1.0
    assert (
        evaluation["market_context"]["trajectory_label"]
        == market_context["trajectory_label"]
    )
