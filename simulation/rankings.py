"""Rankings computation for MMA Management Simulator."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import Fighter, Ranking, WeightClass


def mark_rankings_dirty(session: Session, weight_class: WeightClass) -> None:
    existing = session.execute(
        select(Ranking).where(Ranking.weight_class == weight_class)
    ).scalars().all()
    for r in existing:
        r.dirty = True


def rebuild_rankings(session: Session, weight_class: WeightClass) -> None:
    fighters = session.execute(
        select(Fighter).where(Fighter.weight_class == weight_class)
    ).scalars().all()

    scored = sorted(fighters, key=_compute_score, reverse=True)

    # Clear existing rankings for this weight class
    existing = session.execute(
        select(Ranking).where(Ranking.weight_class == weight_class)
    ).scalars().all()
    for r in existing:
        session.delete(r)
    session.flush()

    for rank, fighter in enumerate(scored, 1):
        score = _compute_score(fighter)
        session.add(Ranking(
            weight_class=weight_class,
            fighter_id=fighter.id,
            rank=rank,
            score=round(score, 2),
            dirty=False,
        ))
        fighter.ranking_score = score

    session.flush()


def get_rankings(session: Session, weight_class: WeightClass, top_n: int = 10) -> list[dict]:
    rows = session.execute(
        select(Ranking, Fighter)
        .join(Fighter, Ranking.fighter_id == Fighter.id)
        .where(Ranking.weight_class == weight_class)
        .order_by(Ranking.rank)
        .limit(top_n)
    ).all()

    return [
        {
            "rank": ranking.rank,
            "name": fighter.name,
            "record": fighter.record,
            "overall": fighter.overall,
            "score": round(ranking.score, 2),
        }
        for ranking, fighter in rows
    ]


def _compute_score(fighter: Fighter) -> float:
    score = fighter.overall * 0.5
    total = fighter.wins + fighter.losses
    if total > 0:
        score += (fighter.wins / total) * 30
        score += fighter.finish_rate * 15
    score += min(total * 0.5, 10)
    return score
