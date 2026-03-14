from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.database import Base
from models.models import (
    Contract,
    ContractStatus,
    Event,
    EventStatus,
    Fight,
    Fighter,
    FighterStyle,
    GameState,
    Organization,
    WeightClass,
)
from simulation.market import (
    compute_asking_salary,
    compute_contract_acceptance_probability,
    compute_market_signals,
    compute_sponsorship_terms,
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


def _seed_recent_results(
    session: Session, fighter: Fighter, opponent: Fighter, *, wins: int, losses: int
):
    org_id = session.execute(
        session.query(Organization.id).limit(1).statement
    ).scalar_one()

    event_year = 2025
    event_month = 12
    for idx in range(wins):
        event = Event(
            name=f"Win Event {idx}",
            event_date=date(event_year, event_month - idx, 1),
            venue="Arena",
            organization_id=org_id,
            status=EventStatus.COMPLETED,
        )
        session.add(event)
        session.flush()
        session.add(
            Fight(
                event_id=event.id,
                fighter_a_id=fighter.id,
                fighter_b_id=opponent.id,
                weight_class=WeightClass.LIGHTWEIGHT,
                winner_id=fighter.id,
                method="KO/TKO",
                round_ended=1,
                time_ended="2:10",
            )
        )

    for idx in range(losses):
        event = Event(
            name=f"Loss Event {idx}",
            event_date=date(event_year - idx, 1, 1),
            venue="Arena",
            organization_id=org_id,
            status=EventStatus.COMPLETED,
        )
        session.add(event)
        session.flush()
        session.add(
            Fight(
                event_id=event.id,
                fighter_a_id=fighter.id,
                fighter_b_id=opponent.id,
                weight_class=WeightClass.LIGHTWEIGHT,
                winner_id=opponent.id,
                method="Unanimous Decision",
                round_ended=3,
                time_ended="5:00",
            )
        )


def _raw_salary_formula(fighter: Fighter) -> int:
    hype = fighter.hype if fighter.hype else 10.0
    wins = fighter.wins or 0
    raw = fighter.overall * 800 * (1 + hype / 200) + wins * 200
    return int(round(raw, -2))


def _build_market_fixture() -> tuple[Session, Organization, Fighter, Fighter]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    org = Organization(
        name="Test Org", prestige=65, bank_balance=1_000_000, is_player=True
    )
    rising = _make_fighter(
        "Rising",
        age=24,
        overall_bias=6,
        confidence=86.0,
        hype=72.0,
        popularity=65.0,
    )
    roster_opponent = _make_fighter(
        "Roster Opponent",
        age=29,
        overall_bias=5,
        confidence=72.0,
        hype=68.0,
        popularity=62.0,
        style=FighterStyle.WRESTLER,
    )
    declining = _make_fighter(
        "Declining",
        age=36,
        overall_bias=2,
        confidence=45.0,
        hype=18.0,
        popularity=20.0,
    )
    foil = _make_fighter("Foil", age=28)

    session.add_all(
        [
            org,
            rising,
            roster_opponent,
            declining,
            foil,
            GameState(id=1, current_date=date(2026, 1, 1), player_org_id=1),
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

    _seed_recent_results(session, rising, foil, wins=3, losses=0)
    _seed_recent_results(session, declining, foil, wins=0, losses=2)
    session.commit()
    return session, org, rising, declining


def test_market_signals_favor_rising_fighter_with_roster_fit():
    session, org, rising, declining = _build_market_fixture()
    try:
        rising_signals = compute_market_signals(rising, session, org.id)
        declining_signals = compute_market_signals(declining, session, org.id)

        assert rising_signals["trajectory"]["label"] in {"Rising", "Peaking"}
        assert rising_signals["matchup"] is not None
        assert rising_signals["matchup"]["assessment"]["booking_value"] in {
            "Strong Main Event",
            "Strong Co-Main",
        }
        assert rising_signals["salary_multiplier"] > 1.0
        assert (
            rising_signals["acceptance_adjustment"]
            > declining_signals["acceptance_adjustment"]
        )
        assert (
            rising_signals["ai_interest_score"] > declining_signals["ai_interest_score"]
        )
    finally:
        session.close()


def test_asking_salary_moves_with_market_signal_direction():
    session, org, rising, declining = _build_market_fixture()
    try:
        rising_raw = _raw_salary_formula(rising)
        declining_raw = _raw_salary_formula(declining)

        assert compute_asking_salary(rising, session, org.id) > rising_raw
        assert compute_asking_salary(declining, session, org.id) < declining_raw
    finally:
        session.close()


def test_renewals_and_sponsorships_use_market_adjustments():
    session, org, rising, declining = _build_market_fixture()
    try:
        rising_offer = compute_asking_salary(rising, session, org.id)
        declining_offer = compute_asking_salary(declining, session, org.id)

        rising_base_accept = compute_contract_acceptance_probability(
            rising,
            org,
            rising_offer,
            session,
            org_id=org.id,
        )
        rising_renewal_accept = compute_contract_acceptance_probability(
            rising,
            org,
            rising_offer,
            session,
            org_id=org.id,
            is_renewal=True,
        )
        declining_base_accept = compute_contract_acceptance_probability(
            declining,
            org,
            declining_offer,
            session,
            org_id=org.id,
        )

        rising_terms = compute_sponsorship_terms(rising, 10_000, session, org_id=org.id)
        declining_terms = compute_sponsorship_terms(
            declining, 10_000, session, org_id=org.id
        )

        assert rising_renewal_accept > rising_base_accept
        assert rising_base_accept > declining_base_accept
        assert rising_terms["monthly_stipend"] > 10_000
        assert declining_terms["monthly_stipend"] < 10_000
        assert rising_terms["acceptance_adjustment"] > 0
        assert declining_terms["acceptance_adjustment"] < 0
    finally:
        session.close()
