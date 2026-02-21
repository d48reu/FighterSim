"""Business logic for FighterSim Flask API."""

from __future__ import annotations

import random
import threading
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    Fighter, Organization, Contract, Event, Fight,
    WeightClass, ContractStatus,
)
from simulation.fight_engine import FighterStats, simulate_fight
from simulation.monthly_sim import sim_month
from simulation.rankings import rebuild_rankings, get_rankings as _get_rankings, mark_rankings_dirty

# ---------------------------------------------------------------------------
# Module-level DB state
# ---------------------------------------------------------------------------

_SessionFactory = None
_tasks: dict = {}
_tasks_lock = threading.Lock()


def init_db(db_url: str) -> None:
    global _SessionFactory
    engine = create_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},  # required for SQLite + threads
    )
    Base.metadata.create_all(engine)
    _SessionFactory = sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------

def _new_task() -> str:
    task_id = uuid.uuid4().hex[:8]
    with _tasks_lock:
        _tasks[task_id] = {"status": "pending", "result": None}
    return task_id


def _task_done(task_id: str, result: dict) -> None:
    with _tasks_lock:
        _tasks[task_id] = {"status": "done", "result": result}


def _task_error(task_id: str, error: str) -> None:
    with _tasks_lock:
        _tasks[task_id] = {"status": "error", "error": error}


def get_task(task_id: str) -> Optional[dict]:
    with _tasks_lock:
        return _tasks.get(task_id)


# ---------------------------------------------------------------------------
# Fighters
# ---------------------------------------------------------------------------

def get_fighters(weight_class: Optional[str] = None, limit: int = 100) -> list[dict]:
    with _SessionFactory() as session:
        q = select(Fighter)
        if weight_class:
            q = q.where(Fighter.weight_class == weight_class)
        q = q.order_by(Fighter.name).limit(limit)
        return [_fighter_dict(f) for f in session.execute(q).scalars().all()]


def get_fighter(fighter_id: int) -> Optional[dict]:
    with _SessionFactory() as session:
        f = session.get(Fighter, fighter_id)
        return _fighter_dict(f) if f else None


def _fighter_dict(f: Fighter) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "age": f.age,
        "nationality": f.nationality,
        "weight_class": f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class,
        "style": f.style.value if hasattr(f.style, "value") else f.style,
        "striking": f.striking,
        "grappling": f.grappling,
        "wrestling": f.wrestling,
        "cardio": f.cardio,
        "chin": f.chin,
        "speed": f.speed,
        "overall": f.overall,
        "record": f.record,
        "wins": f.wins,
        "losses": f.losses,
        "draws": f.draws,
        "ko_wins": f.ko_wins,
        "sub_wins": f.sub_wins,
        "condition": round(f.condition, 1),
        "injury_months": f.injury_months,
    }


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

def get_player_org() -> Optional[dict]:
    with _SessionFactory() as session:
        org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not org:
            return None
        roster_count = len(
            session.execute(
                select(Contract).where(
                    Contract.organization_id == org.id,
                    Contract.status == ContractStatus.ACTIVE,
                )
            ).scalars().all()
        )
        return {
            "id": org.id,
            "name": org.name,
            "prestige": round(org.prestige, 1),
            "bank_balance": round(org.bank_balance, 2),
            "roster_count": roster_count,
        }


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

def get_rankings_for_class(weight_class_str: str) -> list[dict]:
    try:
        wc = WeightClass(weight_class_str)
    except ValueError:
        return []
    with _SessionFactory() as session:
        rebuild_rankings(session, wc)
        session.commit()
        return _get_rankings(session, wc, top_n=15)


# ---------------------------------------------------------------------------
# Async: simulate event
# ---------------------------------------------------------------------------

def start_simulate_event() -> str:
    task_id = _new_task()
    threading.Thread(
        target=_run_simulate_event,
        args=(task_id, random.randint(0, 999_999)),
        daemon=True,
    ).start()
    return task_id


def _run_simulate_event(task_id: str, seed: int) -> None:
    try:
        with _SessionFactory() as session:
            player_org = session.execute(
                select(Organization).where(Organization.is_player == True)
            ).scalar_one_or_none()
            if not player_org:
                _task_error(task_id, "No player organization found")
                return

            # Use any available fighters (player org starts with none)
            available = session.execute(
                select(Contract, Fighter)
                .join(Fighter, Contract.fighter_id == Fighter.id)
                .where(
                    Contract.status == ContractStatus.ACTIVE,
                    Contract.fights_remaining > 0,
                    Fighter.injury_months == 0,
                )
            ).all()

            if len(available) < 4:
                _task_error(task_id, "Not enough available fighters (need at least 4)")
                return

            rng = random.Random(seed)
            fighters = [f for _, f in available]
            rng.shuffle(fighters)

            event = Event(
                name=f"Fight Night — {date.today().strftime('%B %Y')}",
                event_date=date.today(),
                venue="Player Arena",
                organization_id=player_org.id,
                gate_revenue=rng.uniform(100_000, 500_000),
                ppv_buys=rng.randint(0, 100_000),
            )
            session.add(event)
            session.flush()

            fight_results = []
            paired: set[int] = set()
            card_position = 0

            for i, fa in enumerate(fighters):
                if fa.id in paired:
                    continue
                for fb in fighters[i + 1:]:
                    if fb.id in paired or fb.weight_class != fa.weight_class:
                        continue

                    fight = Fight(
                        event_id=event.id,
                        fighter_a_id=fa.id,
                        fighter_b_id=fb.id,
                        weight_class=fa.weight_class,
                        card_position=card_position,
                    )
                    session.add(fight)
                    session.flush()

                    result = simulate_fight(_to_stats(fa), _to_stats(fb), seed=rng.randint(0, 999_999))

                    fight.winner_id = result.winner_id
                    fight.method = result.method
                    fight.round_ended = result.round_ended
                    fight.time_ended = result.time_ended
                    fight.narrative = result.narrative

                    winner = fa if result.winner_id == fa.id else fb
                    loser = fb if winner is fa else fa
                    winner.wins += 1
                    loser.losses += 1
                    if result.method == "KO/TKO":
                        winner.ko_wins += 1
                    elif result.method == "Submission":
                        winner.sub_wins += 1

                    for contract, f in available:
                        if f.id in (fa.id, fb.id):
                            contract.fights_remaining = max(0, contract.fights_remaining - 1)

                    mark_rankings_dirty(session, WeightClass(fa.weight_class))

                    fight_results.append({
                        "fighter_a": fa.name,
                        "fighter_b": fb.name,
                        "winner": winner.name,
                        "loser": loser.name,
                        "method": result.method,
                        "round": result.round_ended,
                        "time": result.time_ended,
                        "narrative": result.narrative,
                    })

                    paired.add(fa.id)
                    paired.add(fb.id)
                    card_position += 1
                    if card_position >= 8:
                        break
                if card_position >= 8:
                    break

            session.commit()
            _task_done(task_id, {
                "event_name": event.name,
                "fights_simulated": len(fight_results),
                "fights": fight_results,
            })
    except Exception as e:
        _task_error(task_id, str(e))


def _to_stats(f: Fighter) -> FighterStats:
    return FighterStats(
        id=f.id, name=f.name,
        striking=f.striking, grappling=f.grappling, wrestling=f.wrestling,
        cardio=f.cardio, chin=f.chin, speed=f.speed,
    )


# ---------------------------------------------------------------------------
# Async: advance month
# ---------------------------------------------------------------------------

def start_advance_month() -> str:
    task_id = _new_task()
    threading.Thread(
        target=_run_advance_month,
        args=(task_id, date.today(), random.randint(0, 999_999)),
        daemon=True,
    ).start()
    return task_id


def _run_advance_month(task_id: str, sim_date: date, seed: int) -> None:
    try:
        with _SessionFactory() as session:
            summary = sim_month(session, sim_date, seed=seed)
        _task_done(task_id, summary)
    except Exception as e:
        _task_error(task_id, str(e))
