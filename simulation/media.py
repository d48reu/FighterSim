"""Media storyline helpers shared by API, matchmaking, and market systems."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import Contract, ContractStatus, Fighter, Organization, WeightClass
from simulation.rankings import _compute_score


_RIVALRY_IMPACT = {
    "matchup_draw_bonus": 6.0,
    "salary_adjustment": 0.03,
    "acceptance_adjustment": 0.02,
    "sponsorship_adjustment": 0.05,
}

_TITLE_IMPACT = {
    "matchup_draw_bonus": 4.0,
    "salary_adjustment": 0.04,
    "acceptance_adjustment": 0.02,
    "sponsorship_adjustment": 0.04,
}

_PROSPECT_IMPACT = {
    "matchup_draw_bonus": 3.0,
    "salary_adjustment": 0.00,
    "acceptance_adjustment": 0.00,
    "sponsorship_adjustment": 0.00,
}

_POACHING_IMPACT = {
    "matchup_draw_bonus": 0.0,
    "salary_adjustment": 0.02,
    "acceptance_adjustment": 0.01,
    "sponsorship_adjustment": 0.03,
}


def build_media_storylines(session: Session) -> list[dict]:
    storylines: list[dict] = []

    rivalry = _top_rivalry_storyline(session)
    if rivalry:
        storylines.append(rivalry)

    title = _boiling_title_storyline(session)
    if title:
        storylines.append(title)

    prospect = _featured_prospect_storyline(session)
    if prospect:
        storylines.append(prospect)

    poaching = _poaching_storyline(session)
    if poaching:
        storylines.append(poaching)

    return storylines[:4]


def get_matchup_storyline_effects(
    session: Session, fighter_a: Fighter, fighter_b: Fighter
) -> dict:
    labels: list[str] = []
    reasons: list[str] = []
    draw_bonus = 0.0
    primary: str | None = None

    fighter_ids = {fighter_a.id, fighter_b.id}
    for storyline in build_media_storylines(session):
        storyline_ids = set(storyline.get("fighter_ids") or [])
        if not storyline_ids:
            continue
        if not fighter_ids.issubset(storyline_ids):
            continue

        impact = storyline.get("impact", {})
        bonus = float(impact.get("matchup_draw_bonus", 0.0))
        if bonus <= 0:
            continue

        draw_bonus += bonus
        labels.append(storyline["headline"])
        reasons.append(_storyline_reason(storyline["type"], fighter_a, fighter_b))
        if primary is None or bonus > 0:
            primary = storyline["type"]

    return {
        "type": primary,
        "labels": labels,
        "reasons": reasons,
        "draw_bonus": round(draw_bonus, 1),
    }


def get_fighter_storyline_effects(session: Session, fighter: Fighter) -> dict:
    labels: list[str] = []
    salary_adjustment = 0.0
    acceptance_adjustment = 0.0
    sponsorship_adjustment = 0.0

    for storyline in build_media_storylines(session):
        fighter_ids = storyline.get("fighter_ids") or []
        if fighter.id not in fighter_ids:
            continue

        impact = storyline.get("impact", {})
        salary_adjustment += float(impact.get("salary_adjustment", 0.0))
        acceptance_adjustment += float(impact.get("acceptance_adjustment", 0.0))
        sponsorship_adjustment += float(impact.get("sponsorship_adjustment", 0.0))
        labels.append(_storyline_label(storyline["type"]))

    return {
        "labels": labels,
        "salary_adjustment": salary_adjustment,
        "acceptance_adjustment": acceptance_adjustment,
        "sponsorship_adjustment": sponsorship_adjustment,
    }


def _top_rivalry_storyline(session: Session) -> dict | None:
    rivals = (
        session.execute(select(Fighter).where(Fighter.rivalry_with.isnot(None)))
        .scalars()
        .all()
    )

    seen: set[tuple[int, int]] = set()
    best_pair: tuple[Fighter, Fighter] | None = None
    best_score = -1.0

    for fighter in rivals:
        opponent = session.get(Fighter, fighter.rivalry_with)
        if not opponent:
            continue
        pair = tuple(sorted((fighter.id, opponent.id)))
        if pair in seen:
            continue
        seen.add(pair)
        score = fighter.hype + opponent.hype + fighter.popularity + opponent.popularity
        if score > best_score:
            best_score = score
            best_pair = (fighter, opponent)

    if not best_pair:
        return None

    fighter_a, fighter_b = best_pair
    return {
        "type": "rivalry",
        "headline": f"{fighter_a.name} vs {fighter_b.name} is heating up again.",
        "angle": f"Grudge match brewing in {_wc_label(fighter_a.weight_class)}.",
        "urgency": "High",
        "fighter_ids": [fighter_a.id, fighter_b.id],
        "weight_class": _wc_label(fighter_a.weight_class),
        "impact": dict(_RIVALRY_IMPACT),
    }


def _boiling_title_storyline(session: Session) -> dict | None:
    for weight_class in WeightClass:
        fighters = (
            session.execute(
                select(Fighter).where(
                    Fighter.weight_class == weight_class,
                    Fighter.is_retired == False,
                )
            )
            .scalars()
            .all()
        )
        if len(fighters) < 3:
            continue

        ranked = sorted(fighters, key=_compute_score, reverse=True)[:5]
        if len(ranked) < 3:
            continue

        top_hype = [fighter.hype for fighter in ranked]
        avg_hype = sum(top_hype) / len(top_hype) if top_hype else 0.0
        score_gap = abs(_compute_score(ranked[1]) - _compute_score(ranked[2]))
        if avg_hype < 68 or score_gap > 3:
            continue

        featured = ranked[:3]
        return {
            "type": "title",
            "headline": f"{weight_class.value} title picture is boiling over.",
            "angle": "Top contenders are hot and tightly packed.",
            "urgency": "High",
            "fighter_ids": [fighter.id for fighter in featured],
            "weight_class": weight_class.value,
            "impact": dict(_TITLE_IMPACT),
        }

    return None


def _featured_prospect_storyline(session: Session) -> dict | None:
    active_ids = set(
        session.execute(
            select(Contract.fighter_id).where(Contract.status == ContractStatus.ACTIVE)
        )
        .scalars()
        .all()
    )
    prospects = (
        session.execute(
            select(Fighter).where(Fighter.is_retired == False, Fighter.age <= 24)
        )
        .scalars()
        .all()
    )
    free_agent_prospects = [
        fighter for fighter in prospects if fighter.id not in active_ids
    ]
    if not free_agent_prospects:
        return None

    prospect = max(
        free_agent_prospects,
        key=lambda fighter: (fighter.overall, fighter.hype, fighter.popularity),
    )
    return {
        "type": "prospect",
        "headline": f"{prospect.name} is building quiet momentum.",
        "angle": "Scouts think the ceiling is rising.",
        "urgency": "Medium",
        "fighter_ids": [prospect.id],
        "weight_class": _wc_label(prospect.weight_class),
        "impact": dict(_PROSPECT_IMPACT),
    }


def _poaching_storyline(session: Session) -> dict | None:
    player_org = session.execute(
        select(Organization).where(Organization.is_player == True)
    ).scalar_one_or_none()
    if not player_org:
        return None

    ai_orgs = (
        session.execute(select(Organization).where(Organization.is_player == False))
        .scalars()
        .all()
    )
    if not ai_orgs:
        return None

    rival_org = min(ai_orgs, key=lambda org: abs(org.prestige - player_org.prestige))
    active_ids = set(
        session.execute(
            select(Contract.fighter_id).where(Contract.status == ContractStatus.ACTIVE)
        )
        .scalars()
        .all()
    )
    candidates = (
        session.execute(select(Fighter).where(Fighter.is_retired == False))
        .scalars()
        .all()
    )
    free_agents = [fighter for fighter in candidates if fighter.id not in active_ids]
    if not free_agents:
        return None

    target = max(
        free_agents,
        key=lambda fighter: (fighter.overall, fighter.hype, fighter.popularity),
    )
    return {
        "type": "poaching",
        "headline": f"{rival_org.name} is circling {target.name}.",
        "angle": "A nearby rival sees an opening if you wait too long.",
        "urgency": "Medium",
        "fighter_ids": [target.id],
        "weight_class": _wc_label(target.weight_class),
        "impact": dict(_POACHING_IMPACT),
    }


def _storyline_label(storyline_type: str) -> str:
    return {
        "rivalry": "Rivalry Heat",
        "title": "Title Heat",
        "prospect": "Prospect Buzz",
        "poaching": "Poaching Pressure",
    }.get(storyline_type, "Media Buzz")


def _storyline_reason(
    storyline_type: str, fighter_a: Fighter, fighter_b: Fighter
) -> str:
    return {
        "rivalry": f"Bad blood between {fighter_a.name} and {fighter_b.name} gives the fight extra promotional heat.",
        "title": "The division is crowded and hot, so this matchup carries real title-scene consequences.",
        "prospect": "One side has breakout buzz, which gives the booking more upside than a normal developmental fight.",
        "poaching": "Outside interest raises the stakes around how quickly you act.",
    }.get(storyline_type, "Media attention is giving this situation extra weight.")


def _wc_label(weight_class: WeightClass | str) -> str:
    return weight_class.value if hasattr(weight_class, "value") else str(weight_class)
