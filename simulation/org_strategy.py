"""Shared organization identity and strategy helpers for AI org behavior."""

from __future__ import annotations

from models.models import Fighter, Organization


def _weight_class_value(fighter: Fighter) -> str:
    return (
        fighter.weight_class.value
        if hasattr(fighter.weight_class, "value")
        else str(fighter.weight_class)
    )


def derive_org_identity(org: Organization, fighters: list[Fighter]) -> dict:
    if not fighters:
        return {
            "label": "Talent Factory",
            "focus": "Building young talent and looking for developmental upside.",
            "focus_weight_class": None,
        }

    avg_age = sum(f.age for f in fighters) / len(fighters)
    avg_popularity = sum(f.popularity for f in fighters) / len(fighters)
    avg_overall = sum(f.overall for f in fighters) / len(fighters)
    weight_counts: dict[str, int] = {}
    for fighter in fighters:
        wc = _weight_class_value(fighter)
        weight_counts[wc] = weight_counts.get(wc, 0) + 1
    focus_weight_class = max(weight_counts, key=weight_counts.get)

    if org.prestige >= 82 or avg_overall >= 79:
        return {
            "label": "Prestige Hunter",
            "focus": "Chases elite names and marquee fights to defend top status.",
            "focus_weight_class": focus_weight_class,
        }
    if avg_age <= 26.5:
        return {
            "label": "Talent Factory",
            "focus": "Targets young upside and long-term development pieces.",
            "focus_weight_class": focus_weight_class,
        }
    if avg_popularity >= 55:
        return {
            "label": "Star Chaser",
            "focus": "Pays for proven draws and visible names.",
            "focus_weight_class": focus_weight_class,
        }
    return {
        "label": "Division Sniper",
        "focus": f"Concentrates resources on winning the {focus_weight_class} division.",
        "focus_weight_class": focus_weight_class,
    }


def candidate_strategy_score(
    fighter: Fighter,
    identity: dict,
    market_signals: dict | None = None,
    *,
    thin_division: bool = False,
) -> float:
    market_signals = market_signals or {}
    label = identity.get("label", "Talent Factory")
    focus_wc = identity.get("focus_weight_class")
    wc = _weight_class_value(fighter)

    score = float(fighter.overall)
    score += float(fighter.hype) * 0.35
    score += float(fighter.popularity) * 0.25
    score += float(market_signals.get("ai_interest_score", fighter.overall)) * 0.2

    if thin_division:
        score += 8
    if focus_wc and wc == focus_wc:
        score += 6

    if label == "Prestige Hunter":
        score += fighter.overall * 0.8 + fighter.popularity * 0.6 + fighter.hype * 0.6
        score -= max(0, 25 - fighter.age) * 0.5
    elif label == "Talent Factory":
        score += max(0, 28 - fighter.age) * 4
        score -= max(0, fighter.age - 29) * 2
        score += float(market_signals.get("salary_multiplier", 1.0) <= 1.0) * 4
    elif label == "Star Chaser":
        score += fighter.popularity * 0.9 + fighter.hype * 0.8
        score += 6 if market_signals.get("matchup") else 0
    elif label == "Division Sniper":
        score += 10 if focus_wc and wc == focus_wc else -6
        score += fighter.overall * 0.4

    return round(score, 3)


def event_pairing_strategy_score(
    fighter_a: Fighter,
    fighter_b: Fighter,
    analysis: dict,
    identity: dict,
) -> float:
    label = identity.get("label", "Talent Factory")
    focus_wc = identity.get("focus_weight_class")
    wc = _weight_class_value(fighter_a)
    booking_value = analysis.get("booking_value")
    combined_draw = float(analysis.get("combined_draw", 0.0))
    prospect_risk = analysis.get("prospect_risk", "Low")

    booking_bonus = {
        "Strong Main Event": 40,
        "Strong Co-Main": 25,
        "Risky Development Fight": 12,
        "Low-Value Filler": 0,
    }.get(booking_value, 0)

    score = booking_bonus + combined_draw
    if label == "Prestige Hunter":
        score += 18 if booking_value == "Strong Main Event" else 0
        score += (fighter_a.popularity + fighter_b.popularity) * 0.2
    elif label == "Talent Factory":
        young_count = int(fighter_a.age <= 24) + int(fighter_b.age <= 24)
        score += young_count * 12
        score += 8 if prospect_risk in {"Medium", "High"} else 0
    elif label == "Star Chaser":
        score += (
            fighter_a.hype
            + fighter_b.hype
            + fighter_a.popularity
            + fighter_b.popularity
        ) * 0.18
    elif label == "Division Sniper":
        score += 15 if focus_wc and wc == focus_wc else -4
        score += 10 if booking_value in {"Strong Main Event", "Strong Co-Main"} else 0

    return round(score, 3)
