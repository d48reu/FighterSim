from datetime import date

from sqlalchemy import create_engine, select
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
        confidence=confidence,
        hype=hype,
        popularity=popularity,
    )


def test_rival_info_exposes_identity_and_bidding_pressure(tmp_path):
    db_path = tmp_path / "rival_strategy.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        ucc = Organization(
            name="Ultimate Combat Championship",
            prestige=90.0,
            bank_balance=50_000_000,
            is_player=False,
        )
        bellator = Organization(
            name="Bellator MMA", prestige=70.0, bank_balance=20_000_000, is_player=False
        )
        one = Organization(
            name="One Championship",
            prestige=75.0,
            bank_balance=25_000_000,
            is_player=False,
        )
        player = Organization(
            name="Player Org", prestige=72.0, bank_balance=5_000_000, is_player=True
        )
        session.add_all(
            [
                ucc,
                bellator,
                one,
                player,
                GameState(id=1, current_date=date(2026, 1, 1), player_org_id=4),
            ]
        )
        session.flush()

        star = _make_fighter(
            "Bidding War Star",
            age=27,
            overall_bias=8,
            hype=78,
            popularity=74,
            style=FighterStyle.WRESTLER,
            weight_class=WeightClass.WELTERWEIGHT,
        )
        ucc_headliner = _make_fighter(
            "UCC Star",
            age=31,
            overall_bias=9,
            hype=82,
            popularity=80,
            weight_class=WeightClass.WELTERWEIGHT,
        )
        bellator_prospect = _make_fighter(
            "Bellator Prospect",
            age=23,
            overall_bias=4,
            hype=46,
            popularity=32,
            weight_class=WeightClass.WELTERWEIGHT,
        )
        one_draw = _make_fighter(
            "One Draw",
            age=29,
            overall_bias=6,
            hype=64,
            popularity=60,
            style=FighterStyle.GRAPPLER,
            weight_class=WeightClass.WELTERWEIGHT,
        )
        session.add_all([star, ucc_headliner, bellator_prospect, one_draw])
        session.flush()

        session.add_all(
            [
                Contract(
                    fighter_id=ucc_headliner.id,
                    organization_id=ucc.id,
                    status=ContractStatus.ACTIVE,
                    salary=300_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
                Contract(
                    fighter_id=bellator_prospect.id,
                    organization_id=bellator.id,
                    status=ContractStatus.ACTIVE,
                    salary=120_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
                Contract(
                    fighter_id=one_draw.id,
                    organization_id=one.id,
                    status=ContractStatus.ACTIVE,
                    salary=180_000,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=date(2026, 12, 1),
                ),
            ]
        )
        session.commit()

    services.init_db(db_url)

    rival = services.get_rival_info()
    assert rival["rival"] is not None
    assert "identity" in rival["rival"]
    assert rival["rival"]["identity"]["label"] in {
        "Prestige Hunter",
        "Talent Factory",
        "Star Chaser",
        "Division Sniper",
    }
    assert "top_targets" in rival["rival"]

    with services._SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one()
        fighter = session.execute(
            select(Fighter).where(Fighter.name == "Bidding War Star")
        ).scalar_one()
        evaluation = services._offer_evaluation_dict(
            fighter,
            player_org,
            offered_salary=180_000,
            session=session,
            org_id=player_org.id,
            fight_count=5,
            length_months=18,
        )

    assert "bidding_pressure" in evaluation
    assert evaluation["bidding_pressure"]["level"] in {"Low", "Medium", "High"}
    assert isinstance(evaluation["bidding_pressure"]["interested_orgs"], list)
    assert any(
        adj["key"] == "competition" for adj in evaluation["preference_adjustments"]
    )
