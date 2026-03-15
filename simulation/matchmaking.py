"""Matchmaking assessment helpers for event booking."""

from __future__ import annotations

from sqlalchemy.orm import object_session

from models.models import Fighter
from simulation.media import get_matchup_storyline_effects


def assess_matchup(a: Fighter, b: Fighter) -> dict:
    """Return a player-facing assessment of the matchup."""
    overall_gap = abs(a.overall - b.overall)
    base_draw = (a.hype + b.hype + a.popularity + b.popularity) / 4
    session = object_session(a) or object_session(b)
    media_storyline = (
        get_matchup_storyline_effects(session, a, b)
        if session is not None and a.id is not None and b.id is not None
        else {"type": None, "labels": [], "reasons": [], "draw_bonus": 0.0}
    )
    combined_draw = base_draw + float(media_storyline.get("draw_bonus", 0.0))
    avg_overall = (a.overall + b.overall) / 2

    competitiveness = "Mismatch"
    if overall_gap <= 3:
        competitiveness = "Toss-Up"
    elif overall_gap <= 7:
        competitiveness = "Competitive"

    star_power = "Low"
    if combined_draw >= 60:
        star_power = "High"
    elif combined_draw >= 38:
        star_power = "Medium"

    younger = a if a.age <= b.age else b
    older = b if younger is a else a
    younger_is_prospect = younger.age < younger.prime_start
    prospect_risk = "Low"
    if younger_is_prospect and (
        older.overall - younger.overall >= 8 or older.age >= older.prime_end
    ):
        prospect_risk = "High"
    elif younger_is_prospect and overall_gap >= 4:
        prospect_risk = "Medium"

    booking_value = "Low-Value Filler"
    if star_power == "High" and competitiveness in {"Toss-Up", "Competitive"}:
        booking_value = "Strong Main Event"
    elif star_power in {"High", "Medium"} and competitiveness != "Mismatch":
        booking_value = "Strong Co-Main"
    elif prospect_risk in {"Medium", "High"}:
        booking_value = "Risky Development Fight"

    reasons: list[str] = []
    if competitiveness == "Toss-Up":
        reasons.append(
            "The overall ratings are close enough to feel like a true coin-flip."
        )
    elif competitiveness == "Competitive":
        reasons.append(
            "The gap is real, but still small enough to produce a credible contest."
        )
    else:
        favorite = a if a.overall >= b.overall else b
        reasons.append(
            f"{favorite.name} has a clear rating edge, so this books more like protection than parity."
        )

    if star_power == "High":
        reasons.append(
            "Both fighters bring enough hype and popularity to carry a featured slot."
        )
    elif star_power == "Medium":
        reasons.append(
            "The matchup has some audience pull, but not automatic headliner juice."
        )
    else:
        reasons.append(
            "The fighters are still light on hype, so this needs support from the rest of the card."
        )

    if prospect_risk == "High":
        reasons.append(
            f"{younger.name} is taking a dangerous development step against a much tougher test."
        )
    elif prospect_risk == "Medium":
        reasons.append(
            f"{younger.name} gets a live developmental test rather than a safe build."
        )

    style_hook = _style_hook(a, b)
    if style_hook:
        reasons.append(style_hook)

    reasons.extend(media_storyline.get("reasons", []))

    return {
        "booking_value": booking_value,
        "competitiveness": competitiveness,
        "star_power": star_power,
        "prospect_risk": prospect_risk,
        "overall_gap": overall_gap,
        "combined_draw": round(combined_draw, 1),
        "avg_overall": round(avg_overall, 1),
        "reasons": reasons[:4],
        "media_storyline": {
            "type": media_storyline.get("type"),
            "labels": media_storyline.get("labels", []),
            "draw_bonus": round(float(media_storyline.get("draw_bonus", 0.0)), 1),
        },
    }


def _style_hook(a: Fighter, b: Fighter) -> str:
    styles = {
        str(a.style.value if hasattr(a.style, "value") else a.style),
        str(b.style.value if hasattr(b.style, "value") else b.style),
    }
    if styles == {"Striker"}:
        return "Pure striker vs striker pairing should read cleanly to fans."
    if "Wrestler" in styles and "Striker" in styles:
        return "Classic striker-versus-wrestler tension gives the fight an easy sales pitch."
    if "Grappler" in styles and "Wrestler" in styles:
        return "This projects as a control-heavy matchup, which may matter for card pacing."
    return ""
