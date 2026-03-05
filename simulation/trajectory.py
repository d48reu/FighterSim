"""Fighter trajectory analysis helpers.

Produces player-facing trend labels and short reasons that explain
where a fighter's career is heading right now.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models.models import Event, Fight, Fighter, FighterDevelopment, GameState


def analyze_fighter_trajectory(fighter: Fighter, session: Session) -> dict:
    """Return a compact trend summary for a fighter."""
    today = _get_game_date(session)
    fights = session.execute(
        select(Fight, Event)
        .join(Event, Fight.event_id == Event.id)
        .where(
            or_(Fight.fighter_a_id == fighter.id, Fight.fighter_b_id == fighter.id),
            Fight.winner_id.isnot(None),
        )
        .order_by(Event.event_date.desc(), Fight.id.desc())
        .limit(3)
    ).all()

    recent_wins = 0
    recent_losses = 0
    finish_wins = 0
    recent_event_date: date | None = None
    volatile = False

    for fight, event in fights:
        if recent_event_date is None:
            recent_event_date = event.event_date
        won = fight.winner_id == fighter.id
        if won:
            recent_wins += 1
            method = (
                fight.method.value if hasattr(fight.method, "value") else fight.method
            )
            if method in ("KO/TKO", "Submission"):
                finish_wins += 1
        else:
            recent_losses += 1

    if len(fights) >= 3:
        results = [fight.winner_id == fighter.id for fight, _ in fights]
        volatile = results == [True, False, True] or results == [False, True, False]

    dev = session.execute(
        select(FighterDevelopment).where(FighterDevelopment.fighter_id == fighter.id)
    ).scalar_one_or_none()

    days_inactive = (today - recent_event_date).days if recent_event_date else 999
    age_vs_prime = _age_vs_prime(fighter)

    score = 0
    reasons: list[str] = []

    if recent_wins >= 2:
        score += 2
        reasons.append(f"Won {recent_wins} of the last {len(fights)} fights.")
    elif recent_losses >= 2 and fights:
        score -= 2
        reasons.append(f"Lost {recent_losses} of the last {len(fights)} fights.")

    if finish_wins >= 2:
        score += 1
        reasons.append("Recent wins are coming with finishes.")

    if age_vs_prime == "pre-prime":
        score += 1
        reasons.append("Still developing before the prime window.")
    elif age_vs_prime == "prime":
        score += 1
        reasons.append("Operating inside the athletic prime.")
    else:
        score -= 1
        reasons.append("Past the prime years, so decline risk is rising.")

    confidence = getattr(fighter, "confidence", 70.0) or 70.0
    if confidence >= 82:
        score += 1
        reasons.append("Confidence is unusually high right now.")
    elif confidence <= 50:
        score -= 1
        reasons.append("Confidence has dipped into a danger zone.")

    if fighter.hype >= 65:
        score += 1
        reasons.append("Strong hype is pushing momentum upward.")
    elif fighter.hype <= 20:
        score -= 1
        reasons.append("Low hype is limiting career momentum.")

    if days_inactive >= 300:
        score -= 2
        reasons.append("Long inactivity is cooling the career off.")
    elif days_inactive >= 180:
        score -= 1
        reasons.append("Inactivity is starting to slow momentum.")

    if dev and dev.camp_id is not None:
        score += 1
        reasons.append("Active training camp assignment supports improvement.")

    label = "Stalled"
    if volatile:
        label = "Volatile"
    elif score >= 4:
        label = "Rising"
    elif score >= 2:
        label = "Peaking"
    elif score <= -3:
        label = "Declining"
    elif score <= -1:
        label = "Stalled"

    market_value = _market_value_hint(fighter, recent_wins, recent_losses, age_vs_prime)
    return {
        "label": label,
        "score": score,
        "reasons": reasons[:3],
        "recent_form": f"{recent_wins}-{recent_losses}"
        if fights
        else "No recent fights",
        "days_inactive": days_inactive if recent_event_date else None,
        "age_phase": age_vs_prime,
        "market_value_hint": market_value,
    }


def _get_game_date(session: Session) -> date:
    gs = session.get(GameState, 1)
    return gs.current_date if gs else date(2026, 1, 1)


def _age_vs_prime(fighter: Fighter) -> str:
    if fighter.age < fighter.prime_start:
        return "pre-prime"
    if fighter.age <= fighter.prime_end:
        return "prime"
    return "post-prime"


def _market_value_hint(
    fighter: Fighter, recent_wins: int, recent_losses: int, age_vs_prime: str
) -> str:
    if age_vs_prime == "post-prime" and recent_losses >= 2:
        return "Sell-high window may be closing."
    if age_vs_prime == "pre-prime" and recent_wins >= 2:
        return "Prospect value is climbing."
    if fighter.hype >= 65 and recent_wins >= 1:
        return "Drawing power is moving up."
    if fighter.hype <= 20 and recent_losses >= 1:
        return "Market value is soft right now."
    return "Current value looks stable."
