"""Market signal helpers shared by contracts, AI signings, and sponsorships."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import Contract, ContractStatus, Fighter, Organization
from simulation.matchmaking import assess_matchup
from simulation.media import get_fighter_storyline_effects
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
    storyline = get_fighter_storyline_effects(session, fighter)

    salary_multiplier = _clamp(
        1.0 + trajectory_salary + matchup_salary + storyline["salary_adjustment"],
        0.78,
        1.35,
    )
    acceptance_adjustment = _clamp(
        trajectory_acceptance + matchup_acceptance + storyline["acceptance_adjustment"],
        -0.18,
        0.18,
    )
    sponsorship_multiplier = _clamp(
        1.0
        + trajectory_sponsorship
        + matchup_sponsorship
        + storyline["sponsorship_adjustment"],
        0.80,
        1.35,
    )
    sponsorship_acceptance_adjustment = _clamp(
        trajectory_sponsorship * 0.6
        + matchup_sponsorship * 0.5
        + storyline["sponsorship_adjustment"] * 0.5,
        -0.15,
        0.18,
    )

    return {
        "trajectory": trajectory,
        "matchup": matchup,
        "storyline": storyline,
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


def compute_market_recommendation(
    signals: dict,
    *,
    surface: str,
    offer_ratio: float | None = None,
    days_to_expiry: int | None = None,
    fights_remaining: int | None = None,
    discount_pct: float | None = None,
) -> dict:
    """Convert market signals into an actionable label for a specific UI surface."""
    trajectory = signals.get("trajectory", {})
    trajectory_label = trajectory.get("label", "Stalled")
    salary_multiplier = float(signals.get("salary_multiplier", 1.0))
    acceptance_adjustment = float(signals.get("acceptance_adjustment", 0.0))
    booking_value = (
        (signals.get("matchup", {}) or {}).get("assessment", {}).get("booking_value")
    )

    is_hot = trajectory_label in {"Rising", "Peaking"}
    is_cold = trajectory_label == "Declining" or (
        trajectory_label == "Stalled" and acceptance_adjustment < 0
    )
    is_expensive = salary_multiplier >= 1.18 or acceptance_adjustment >= 0.08

    if surface in {"free_agent", "show_signing"}:
        if is_hot and (discount_pct or 0) >= 10:
            return {
                "label": "Buy Now",
                "tone": "buy-now",
                "reason": "Hot fighter with a favorable contract window.",
            }
        if is_hot and salary_multiplier <= 1.08 and acceptance_adjustment <= 0.04:
            return {
                "label": "Buy Now",
                "tone": "buy-now",
                "reason": "Trajectory is strong and the price is still manageable.",
            }
        if is_expensive or (offer_ratio is not None and offer_ratio >= 1.15):
            return {
                "label": "Overpay Risk",
                "tone": "overpay",
                "reason": "The market is hot enough that this deal can get expensive fast.",
            }
        if is_cold and booking_value in {None, "Low-Value Filler"}:
            return {
                "label": "Low-Interest Asset",
                "tone": "cold-asset",
                "reason": "Market demand is soft and the roster fit is weak.",
            }
        return {
            "label": "Fair Price",
            "tone": "neutral",
            "reason": "Useful asset, but not screaming urgency either way.",
        }

    if surface == "roster":
        if is_cold and salary_multiplier <= 0.97:
            return {
                "label": "Sell Soon",
                "tone": "cold-asset",
                "reason": "Value is slipping and upside is fading.",
            }
        if is_hot and booking_value in {"Strong Main Event", "Strong Co-Main"}:
            return {
                "label": "Core Asset",
                "tone": "buy-now",
                "reason": "This fighter is carrying real strategic value for the roster.",
            }
        return {
            "label": "Fair Value",
            "tone": "neutral",
            "reason": "Solid roster piece without immediate buy/sell pressure.",
        }

    if surface == "expiring_contract":
        if is_hot and (
            (days_to_expiry is not None and days_to_expiry <= 60)
            or (fights_remaining is not None and fights_remaining <= 1)
        ):
            return {
                "label": "High-Leverage Renewal",
                "tone": "buy-now",
                "reason": "Waiting risks losing an asset that is still appreciating.",
            }
        if is_cold:
            return {
                "label": "Replaceable",
                "tone": "cold-asset",
                "reason": "You can likely replace this value without locking into a longer deal.",
            }
        return {
            "label": "Fair Renewal",
            "tone": "neutral",
            "reason": "Worth keeping if the terms stay in range.",
        }

    if surface == "offer_evaluation":
        if offer_ratio is not None and offer_ratio >= 1.15:
            return {
                "label": "Overpay Risk",
                "tone": "overpay",
                "reason": "You are paying a meaningful premium over current market value.",
            }
        if is_hot and offer_ratio is not None and offer_ratio <= 1.0:
            return {
                "label": "Buy Now",
                "tone": "buy-now",
                "reason": "You are catching the fighter before the market runs hotter.",
            }
        return {
            "label": "Fair Price",
            "tone": "neutral",
            "reason": "The offer is broadly aligned with current market conditions.",
        }

    return {
        "label": "Fair Value",
        "tone": "neutral",
        "reason": "No strong recommendation signal was triggered.",
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
