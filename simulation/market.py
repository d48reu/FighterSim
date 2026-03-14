"""Market signal helpers shared by contracts, AI signings, and sponsorships."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import Contract, ContractStatus, Fighter, Organization
from simulation.matchmaking import assess_matchup
from simulation.trajectory import analyze_fighter_trajectory


_BOOKING_SCORE = {
    "Low-Value Filler": 0.0,
    "Risky Development Fight": 0.6,
    "Strong Co-Main": 1.3,
    "Strong Main Event": 1.8,
}

_TRAJECTORY_SALARY_ADJUST = {
    "Rising": 0.10,
    "Peaking": 0.06,
    "Volatile": 0.02,
    "Stalled": -0.02,
    "Declining": -0.08,
}

_TRAJECTORY_ACCEPTANCE_ADJUST = {
    "Rising": 0.05,
    "Peaking": 0.03,
    "Volatile": 0.00,
    "Stalled": -0.02,
    "Declining": -0.06,
}

_TRAJECTORY_SPONSORSHIP_ADJUST = {
    "Rising": 0.12,
    "Peaking": 0.08,
    "Volatile": 0.02,
    "Stalled": -0.03,
    "Declining": -0.10,
}


def compute_market_signals(
    fighter: Fighter, session: Session, org_id: int | None = None
) -> dict:
    """Summarize the trajectory and roster-fit signals behind a fighter's value."""
    trajectory = analyze_fighter_trajectory(fighter, session)
    matchup = _best_roster_matchup(fighter, session, org_id)

    trajectory_salary = _TRAJECTORY_SALARY_ADJUST.get(trajectory["label"], 0.0)
    trajectory_salary += _clamp(trajectory["score"] * 0.015, -0.05, 0.08)

    matchup_salary = 0.0
    matchup_acceptance = 0.0
    matchup_sponsorship = 0.0
    ai_interest_bonus = trajectory["score"] * 2.5

    if matchup:
        booking_value = matchup["assessment"]["booking_value"]
        matchup_salary = {
            "Strong Main Event": 0.08,
            "Strong Co-Main": 0.05,
            "Risky Development Fight": 0.02,
            "Low-Value Filler": -0.03,
        }.get(booking_value, 0.0)
        matchup_acceptance = {
            "Strong Main Event": 0.05,
            "Strong Co-Main": 0.03,
            "Risky Development Fight": 0.01,
            "Low-Value Filler": -0.02,
        }.get(booking_value, 0.0)
        matchup_sponsorship = {
            "Strong Main Event": 0.08,
            "Strong Co-Main": 0.05,
            "Risky Development Fight": 0.02,
            "Low-Value Filler": -0.02,
        }.get(booking_value, 0.0)
        ai_interest_bonus += matchup["score"] * 6

    trajectory_acceptance = _TRAJECTORY_ACCEPTANCE_ADJUST.get(trajectory["label"], 0.0)
    trajectory_sponsorship = _TRAJECTORY_SPONSORSHIP_ADJUST.get(
        trajectory["label"], 0.0
    )

    salary_multiplier = _clamp(
        1.0 + trajectory_salary + matchup_salary,
        0.78,
        1.35,
    )
    acceptance_adjustment = _clamp(
        trajectory_acceptance + matchup_acceptance,
        -0.18,
        0.18,
    )
    sponsorship_multiplier = _clamp(
        1.0 + trajectory_sponsorship + matchup_sponsorship,
        0.80,
        1.35,
    )
    sponsorship_acceptance_adjustment = _clamp(
        trajectory_sponsorship * 0.6 + matchup_sponsorship * 0.5,
        -0.15,
        0.18,
    )

    return {
        "trajectory": trajectory,
        "matchup": matchup,
        "salary_multiplier": salary_multiplier,
        "acceptance_adjustment": acceptance_adjustment,
        "ai_interest_score": fighter.overall + ai_interest_bonus,
        "sponsorship_multiplier": sponsorship_multiplier,
        "sponsorship_acceptance_adjustment": sponsorship_acceptance_adjustment,
    }


def compute_asking_salary(
    fighter: Fighter, session: Session, org_id: int | None = None
) -> int:
    """Compute an asking salary adjusted by trend and booking fit."""
    hype = fighter.hype if fighter.hype else 10.0
    wins = fighter.wins or 0
    raw = fighter.overall * 800 * (1 + hype / 200) + wins * 200
    signals = compute_market_signals(fighter, session, org_id)
    return int(round(raw * signals["salary_multiplier"], -2))


def compute_contract_acceptance_probability(
    fighter: Fighter,
    org: Organization,
    offered_salary: float,
    session: Session,
    *,
    org_id: int | None = None,
    is_renewal: bool = False,
) -> float:
    """Compute contract acceptance probability from money, prestige, and signals."""
    effective_org_id = org_id if org_id is not None else org.id
    asking = compute_asking_salary(fighter, session, effective_org_id)
    salary_factor = offered_salary / asking if asking > 0 else 1.0
    prestige_factor = org.prestige / 100

    probability = salary_factor * 0.55 + prestige_factor * 0.35
    probability += compute_market_signals(fighter, session, effective_org_id)[
        "acceptance_adjustment"
    ]
    if is_renewal:
        probability += 0.10

    return _clamp(probability, 0.05, 0.95)


def compute_sponsorship_terms(
    fighter: Fighter,
    base_monthly_stipend: float,
    session: Session,
    *,
    org_id: int | None = None,
) -> dict:
    """Return stipend and acceptance adjustments for sponsorship attempts."""
    signals = compute_market_signals(fighter, session, org_id)
    stipend = round(base_monthly_stipend * signals["sponsorship_multiplier"], 2)
    return {
        "monthly_stipend": stipend,
        "acceptance_adjustment": signals["sponsorship_acceptance_adjustment"],
        "market_signals": signals,
    }


def _best_roster_matchup(
    fighter: Fighter, session: Session, org_id: int | None
) -> dict | None:
    if org_id is None:
        return None

    opponents = (
        session.execute(
            select(Fighter)
            .join(Contract, Contract.fighter_id == Fighter.id)
            .where(
                Contract.organization_id == org_id,
                Contract.status == ContractStatus.ACTIVE,
                Fighter.weight_class == fighter.weight_class,
                Fighter.id != fighter.id,
                Fighter.is_retired == False,
            )
        )
        .scalars()
        .all()
    )
    if not opponents:
        return None

    ranked = []
    for opponent in opponents:
        assessment = assess_matchup(fighter, opponent)
        ranked.append(
            (
                (
                    _BOOKING_SCORE.get(assessment["booking_value"], 0.0),
                    assessment["combined_draw"],
                    -assessment["overall_gap"],
                ),
                opponent,
                assessment,
            )
        )

    ranked.sort(key=lambda row: row[0], reverse=True)
    _, opponent, assessment = ranked[0]
    return {
        "opponent_id": opponent.id,
        "opponent_name": opponent.name,
        "score": _BOOKING_SCORE.get(assessment["booking_value"], 0.0),
        "assessment": assessment,
    }


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
