"""Business logic for FighterSim Flask API."""

from __future__ import annotations

import json
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
    WeightClass, ContractStatus, EventStatus, Notification, GameState,
)
from simulation.fight_engine import FighterStats, simulate_fight
from simulation.monthly_sim import sim_month
from simulation.rankings import rebuild_rankings, get_rankings as _get_rankings, mark_rankings_dirty
from simulation.narrative import (
    apply_fight_tags, update_goat_scores, update_rivalries,
    generate_fighter_bio, get_tags, display_archetype,
)

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
# Game State
# ---------------------------------------------------------------------------

def _get_game_date(session) -> date:
    """Return current game date from GameState, falling back to today."""
    gs = session.get(GameState, 1)
    return gs.current_date if gs else date.today()


def get_gamestate() -> dict:
    with _SessionFactory() as session:
        gs = session.get(GameState, 1)
        if not gs:
            return {"current_date": date.today().isoformat(), "player_org_id": None}
        return {
            "current_date": gs.current_date.isoformat(),
            "player_org_id": gs.player_org_id,
        }


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
        "archetype": display_archetype(f),
        "popularity": round(f.popularity, 1),
        "hype": round(f.hype, 1),
        "goat_score": round(f.goat_score, 1),
        "traits": _get_traits_list(f),
    }


def _get_traits_list(f: Fighter) -> list[str]:
    try:
        return json.loads(f.traits) if f.traits else []
    except (json.JSONDecodeError, TypeError):
        return []


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

            # Only use fighters on the player org's roster
            available = session.execute(
                select(Contract, Fighter)
                .join(Fighter, Contract.fighter_id == Fighter.id)
                .where(
                    Contract.organization_id == player_org.id,
                    Contract.status == ContractStatus.ACTIVE,
                    Contract.fights_remaining > 0,
                    Fighter.injury_months == 0,
                )
            ).all()

            if len(available) < 2:
                _task_error(task_id, "Not enough available fighters on your roster (need at least 2)")
                return

            rng = random.Random(seed)
            fighters = [f for _, f in available]
            rng.shuffle(fighters)

            game_date = _get_game_date(session)
            event = Event(
                name=f"Fight Night — {game_date.strftime('%B %Y')}",
                event_date=game_date,
                venue="Player Arena",
                organization_id=player_org.id,
                status=EventStatus.COMPLETED,
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
                    apply_fight_tags(winner, loser, fight, session)

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
    style = f.style.value if hasattr(f.style, "value") else str(f.style)
    return FighterStats(
        id=f.id, name=f.name,
        striking=f.striking, grappling=f.grappling, wrestling=f.wrestling,
        cardio=f.cardio, chin=f.chin, speed=f.speed,
        traits=_get_traits_list(f),
        style=style,
    )


# ---------------------------------------------------------------------------
# Async: advance month
# ---------------------------------------------------------------------------

def start_advance_month() -> str:
    task_id = _new_task()
    threading.Thread(
        target=_run_advance_month,
        args=(task_id, random.randint(0, 999_999)),
        daemon=True,
    ).start()
    return task_id


def _run_advance_month(task_id: str, seed: int) -> None:
    try:
        with _SessionFactory() as session:
            summary = sim_month(session, seed=seed)
        _task_done(task_id, summary)
    except Exception as e:
        _task_error(task_id, str(e))


# ---------------------------------------------------------------------------
# Narrative: fighter bio, GOAT scores, rivalries, tags
# ---------------------------------------------------------------------------

def get_fighter_bio(fighter_id: int) -> Optional[str]:
    with _SessionFactory() as session:
        f = session.get(Fighter, fighter_id)
        if not f:
            return None
        return generate_fighter_bio(f)


def get_goat_scores(top_n: int = 10) -> list[dict]:
    with _SessionFactory() as session:
        fighters = (
            session.execute(
                select(Fighter).order_by(Fighter.goat_score.desc()).limit(top_n)
            )
            .scalars()
            .all()
        )
        return [
            {
                "rank": i + 1,
                "id": f.id,
                "name": f.name,
                "weight_class": f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class,
                "archetype": display_archetype(f),
                "record": f.record,
                "overall": f.overall,
                "goat_score": round(f.goat_score, 1),
                "tags": get_tags(f),
            }
            for i, f in enumerate(fighters)
        ]


def get_rivalries() -> list[dict]:
    with _SessionFactory() as session:
        # Find fighters who have a rivalry_with set
        rivals = (
            session.execute(
                select(Fighter).where(Fighter.rivalry_with.isnot(None))
            )
            .scalars()
            .all()
        )
        seen: set[tuple] = set()
        result = []
        for f in rivals:
            other = session.get(Fighter, f.rivalry_with)
            if not other:
                continue
            pair = tuple(sorted([f.id, other.id]))
            if pair in seen:
                continue
            seen.add(pair)
            result.append({
                "fighter_a": {"id": f.id, "name": f.name, "record": f.record},
                "fighter_b": {"id": other.id, "name": other.name, "record": other.record},
                "weight_class": f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class,
            })
        return result


def get_fighter_tags(fighter_id: int) -> Optional[list[str]]:
    with _SessionFactory() as session:
        f = session.get(Fighter, fighter_id)
        if not f:
            return None
        return get_tags(f)


# ---------------------------------------------------------------------------
# Contract negotiation: free agents, roster, offers, releases, renewals
# ---------------------------------------------------------------------------

def _asking_salary(fighter: Fighter) -> int:
    ovr = fighter.overall
    hype = fighter.hype if fighter.hype else 10.0
    wins = fighter.wins or 0
    raw = ovr * 800 * (1 + hype / 200) + wins * 200
    return int(round(raw, -2))


def _asking_fights(fighter: Fighter) -> int:
    age = fighter.age
    if age < 25:
        return random.choice([5, 6])
    elif age <= 30:
        return random.choice([3, 4])
    else:
        return random.choice([2, 3])


def _asking_length_months(fighter: Fighter) -> int:
    age = fighter.age
    if age < 25:
        return 24
    elif age <= 30:
        return 18
    else:
        return 12


def get_free_agents(
    weight_class: Optional[str] = None,
    style: Optional[str] = None,
    min_overall: Optional[int] = None,
    sort_by: Optional[str] = None,
) -> list[dict]:
    with _SessionFactory() as session:
        from sqlalchemy import and_, or_

        # Subquery: fighter IDs with an active contract
        active_ids = (
            session.execute(
                select(Contract.fighter_id).where(
                    Contract.status == ContractStatus.ACTIVE
                )
            ).scalars().all()
        )
        active_set = set(active_ids)

        q = select(Fighter)
        if weight_class:
            q = q.where(Fighter.weight_class == weight_class)
        if style:
            q = q.where(Fighter.style == style)

        fighters = session.execute(q).scalars().all()
        results = []
        for f in fighters:
            if f.id in active_set:
                continue
            if min_overall and f.overall < min_overall:
                continue
            d = _fighter_dict(f)
            d["asking_salary"] = _asking_salary(f)
            d["asking_fights"] = _asking_fights(f)
            d["asking_length_months"] = _asking_length_months(f)
            results.append(d)

        if sort_by == "overall":
            results.sort(key=lambda x: x["overall"], reverse=True)
        elif sort_by == "salary":
            results.sort(key=lambda x: x["asking_salary"], reverse=True)
        elif sort_by == "age":
            results.sort(key=lambda x: x["age"])
        elif sort_by == "hype":
            results.sort(key=lambda x: x["hype"], reverse=True)
        else:
            results.sort(key=lambda x: x["overall"], reverse=True)

        return results


def get_roster() -> list[dict]:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return []

        rows = session.execute(
            select(Contract, Fighter)
            .join(Fighter, Contract.fighter_id == Fighter.id)
            .where(
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).all()

        results = []
        for contract, fighter in rows:
            d = _fighter_dict(fighter)
            d["salary"] = contract.salary
            d["fights_remaining"] = contract.fights_remaining
            d["fight_count_total"] = contract.fight_count_total
            d["expiry_date"] = contract.expiry_date.isoformat() if contract.expiry_date else None
            results.append(d)
        return results


_OFFER_ACCEPTED_MSGS = [
    "{name} is excited to join your organization!",
    "{name} has signed on the dotted line. Welcome aboard!",
    "{name} agrees to terms — ready to fight under your banner.",
    "{name} shakes hands on the deal. Let's go!",
    "{name} accepts your offer and is eager to prove their worth.",
    "{name} liked what they saw. Contract signed!",
]

_OFFER_REJECTED_MSGS = [
    "{name} felt the offer was too low and walked away.",
    "{name} is looking for a bigger payday elsewhere.",
    "{name} turned down the contract — not enough money on the table.",
    "{name} wasn't convinced by the offer. Try sweetening the deal.",
]


def make_contract_offer(fighter_id: int, salary: float, fight_count: int, length_months: int) -> dict:
    with _SessionFactory() as session:
        fighter = session.get(Fighter, fighter_id)
        if not fighter:
            return {"accepted": False, "message": "Fighter not found."}

        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return {"accepted": False, "message": "No player organization found."}

        # Check if fighter already has an active contract
        existing = session.execute(
            select(Contract).where(
                Contract.fighter_id == fighter_id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalar_one_or_none()
        if existing:
            return {"accepted": False, "message": f"{fighter.name} already has an active contract."}

        # Affordability check
        if player_org.bank_balance < salary * 3:
            return {"accepted": False, "message": "You can't afford this contract. Need at least 3x the salary in the bank."}

        asking = _asking_salary(fighter)
        salary_factor = salary / asking if asking > 0 else 1.0
        prestige_factor = player_org.prestige / 100
        acceptance_prob = min(0.95, salary_factor * 0.6 + prestige_factor * 0.4)

        if random.random() < acceptance_prob:
            from datetime import timedelta
            game_date = _get_game_date(session)
            expiry = game_date + timedelta(days=length_months * 30)
            contract = Contract(
                fighter_id=fighter_id,
                organization_id=player_org.id,
                status=ContractStatus.ACTIVE,
                salary=salary,
                fight_count_total=fight_count,
                fights_remaining=fight_count,
                expiry_date=expiry,
            )
            session.add(contract)
            session.commit()
            msg = random.choice(_OFFER_ACCEPTED_MSGS).format(name=fighter.name)
            return {"accepted": True, "message": msg}
        else:
            msg = random.choice(_OFFER_REJECTED_MSGS).format(name=fighter.name)
            return {"accepted": False, "message": msg}


def release_fighter(fighter_id: int) -> dict:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return {"success": False, "message": "No player organization found."}

        contract = session.execute(
            select(Contract).where(
                Contract.fighter_id == fighter_id,
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalar_one_or_none()
        if not contract:
            return {"success": False, "message": "No active contract found for this fighter."}

        fighter = session.get(Fighter, fighter_id)
        contract.status = ContractStatus.TERMINATED

        game_date = _get_game_date(session)
        notif = Notification(
            message=f"{fighter.name} has been released from your roster.",
            type="fighter_released",
            created_date=game_date,
        )
        session.add(notif)
        session.commit()
        return {"success": True, "message": f"{fighter.name} has been released."}


def get_expiring_contracts() -> list[dict]:
    from datetime import timedelta
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return []

        game_date = _get_game_date(session)
        cutoff = game_date + timedelta(days=60)
        rows = session.execute(
            select(Contract, Fighter)
            .join(Fighter, Contract.fighter_id == Fighter.id)
            .where(
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).all()

        results = []
        for contract, fighter in rows:
            if contract.expiry_date <= cutoff or contract.fights_remaining == 0:
                d = _fighter_dict(fighter)
                d["salary"] = contract.salary
                d["fights_remaining"] = contract.fights_remaining
                d["expiry_date"] = contract.expiry_date.isoformat() if contract.expiry_date else None
                results.append(d)
        return results


def renew_contract(fighter_id: int, salary: float, fight_count: int, length_months: int) -> dict:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return {"accepted": False, "message": "No player organization found."}

        fighter = session.get(Fighter, fighter_id)
        if not fighter:
            return {"accepted": False, "message": "Fighter not found."}

        contract = session.execute(
            select(Contract).where(
                Contract.fighter_id == fighter_id,
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalar_one_or_none()
        if not contract:
            return {"accepted": False, "message": "No active contract to renew."}

        if player_org.bank_balance < salary * 3:
            return {"accepted": False, "message": "You can't afford this renewal. Need at least 3x the salary in the bank."}

        asking = _asking_salary(fighter)
        salary_factor = salary / asking if asking > 0 else 1.0
        prestige_factor = player_org.prestige / 100
        acceptance_prob = min(0.95, salary_factor * 0.6 + prestige_factor * 0.4)
        acceptance_prob = min(0.95, acceptance_prob * 1.15)  # loyalty bonus

        if random.random() < acceptance_prob:
            from datetime import timedelta
            game_date = _get_game_date(session)
            contract.expiry_date = game_date + timedelta(days=length_months * 30)
            contract.salary = salary
            contract.fight_count_total = fight_count
            contract.fights_remaining = fight_count
            session.commit()
            msg = random.choice(_OFFER_ACCEPTED_MSGS).format(name=fighter.name)
            return {"accepted": True, "message": msg}
        else:
            msg = random.choice(_OFFER_REJECTED_MSGS).format(name=fighter.name)
            return {"accepted": False, "message": msg}


def get_finances() -> dict:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return {}

        active_contracts = session.execute(
            select(Contract).where(
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalars().all()

        total_salaries = sum(c.salary for c in active_contracts)
        monthly_payroll = total_salaries / 12
        projected_fight_costs = sum(c.salary * c.fights_remaining for c in active_contracts)

        return {
            "bank_balance": round(player_org.bank_balance, 2),
            "monthly_payroll": round(monthly_payroll, 2),
            "total_annual_salaries": round(total_salaries, 2),
            "projected_fight_costs": round(projected_fight_costs, 2),
            "roster_size": len(active_contracts),
            "prestige": round(player_org.prestige, 1),
        }


def get_notifications() -> list[dict]:
    with _SessionFactory() as session:
        notifs = session.execute(
            select(Notification)
            .where(Notification.read == False)
            .order_by(Notification.created_date.desc())
            .limit(20)
        ).scalars().all()
        return [
            {
                "id": n.id,
                "message": n.message,
                "type": n.type,
                "created_date": n.created_date.isoformat(),
                "read": n.read,
            }
            for n in notifs
        ]


def mark_notification_read(notification_id: int) -> dict:
    with _SessionFactory() as session:
        notif = session.get(Notification, notification_id)
        if not notif:
            return {"success": False}
        notif.read = True
        session.commit()
        return {"success": True}


# ---------------------------------------------------------------------------
# Event Booking
# ---------------------------------------------------------------------------

VENUES = [
    {"name": "Local Gym", "capacity": 500, "base_gate": 15000},
    {"name": "Convention Center", "capacity": 2000, "base_gate": 60000},
    {"name": "Municipal Arena", "capacity": 5000, "base_gate": 150000},
    {"name": "Sports Complex", "capacity": 10000, "base_gate": 300000},
    {"name": "Major Arena", "capacity": 18000, "base_gate": 550000},
    {"name": "Stadium", "capacity": 45000, "base_gate": 1200000},
]


def _fight_dict(fight: Fight, session) -> dict:
    fa = session.get(Fighter, fight.fighter_a_id)
    fb = session.get(Fighter, fight.fighter_b_id)
    wc = fight.weight_class.value if hasattr(fight.weight_class, "value") else fight.weight_class
    d = {
        "id": fight.id,
        "fighter_a": _fighter_dict(fa) if fa else {"id": fight.fighter_a_id, "name": "Unknown"},
        "fighter_b": _fighter_dict(fb) if fb else {"id": fight.fighter_b_id, "name": "Unknown"},
        "weight_class": wc,
        "card_position": fight.card_position,
        "is_title_fight": fight.is_title_fight,
        "winner_id": fight.winner_id,
        "method": fight.method.value if hasattr(fight.method, "value") else fight.method,
        "round_ended": fight.round_ended,
        "time_ended": fight.time_ended,
        "narrative": fight.narrative,
    }
    return d


def _event_dict(event: Event, session, include_fights=True) -> dict:
    d = {
        "id": event.id,
        "name": event.name,
        "event_date": event.event_date.isoformat(),
        "venue": event.venue,
        "status": event.status.value if hasattr(event.status, "value") else event.status,
        "gate_revenue": round(event.gate_revenue, 2),
        "ppv_buys": event.ppv_buys,
        "total_revenue": round(event.total_revenue, 2),
        "fight_count": len(event.fights),
    }
    if include_fights:
        d["fights"] = [_fight_dict(f, session) for f in event.fights]
    if event.fights:
        main_event = max(event.fights, key=lambda f: f.card_position)
        if main_event.winner_id:
            winner = session.get(Fighter, main_event.winner_id)
            method = main_event.method.value if hasattr(main_event.method, "value") else main_event.method
            d["main_event_result"] = f"{winner.name if winner else 'Unknown'} via {method}" if method else None
        else:
            d["main_event_result"] = None
    else:
        d["main_event_result"] = None
    return d


def get_bookable_fighters() -> list[dict]:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return []

        # Fighters on active contracts with fights remaining, not injured
        rows = session.execute(
            select(Contract, Fighter)
            .join(Fighter, Contract.fighter_id == Fighter.id)
            .where(
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
                Contract.fights_remaining > 0,
                Fighter.injury_months == 0,
            )
        ).all()

        # Find fighter IDs already booked on scheduled events
        scheduled_events = session.execute(
            select(Event).where(
                Event.organization_id == player_org.id,
                Event.status == EventStatus.SCHEDULED,
            )
        ).scalars().all()
        booked_ids = set()
        for ev in scheduled_events:
            for fight in ev.fights:
                booked_ids.add(fight.fighter_a_id)
                booked_ids.add(fight.fighter_b_id)

        # Get last fight date for each fighter
        game_date = _get_game_date(session)
        results = []
        for contract, fighter in rows:
            if fighter.id in booked_ids:
                continue
            # Find most recent completed fight
            last_fight = session.execute(
                select(Fight)
                .join(Event, Fight.event_id == Event.id)
                .where(
                    Event.status == EventStatus.COMPLETED,
                    ((Fight.fighter_a_id == fighter.id) | (Fight.fighter_b_id == fighter.id)),
                    Fight.winner_id.isnot(None),
                )
                .order_by(Event.event_date.desc())
                .limit(1)
            ).scalar_one_or_none()

            if last_fight:
                last_event = session.get(Event, last_fight.event_id)
                days_since = (game_date - last_event.event_date).days if last_event else 999
            else:
                days_since = 999

            d = _fighter_dict(fighter)
            d["days_since_last_fight"] = days_since
            d["salary"] = contract.salary
            d["fights_remaining"] = contract.fights_remaining
            results.append(d)

        results.sort(key=lambda x: x["overall"], reverse=True)
        return results


def create_event(name: str, venue: str, event_date_str: str) -> dict:
    from datetime import datetime
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return {"error": "No player organization found."}

        game_date = _get_game_date(session)
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        if event_date <= game_date:
            return {"error": "Event date must be after the current game date."}

        event = Event(
            name=name,
            event_date=event_date,
            venue=venue,
            organization_id=player_org.id,
            status=EventStatus.SCHEDULED,
        )
        session.add(event)
        session.commit()
        return _event_dict(event, session)


def add_fight_to_event(event_id: int, fighter_a_id: int, fighter_b_id: int, is_title_fight: bool = False) -> dict:
    with _SessionFactory() as session:
        event = session.get(Event, event_id)
        if not event:
            return {"error": "Event not found."}
        if event.status != EventStatus.SCHEDULED:
            return {"error": "Can only add fights to scheduled events."}

        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org or event.organization_id != player_org.id:
            return {"error": "Event does not belong to your organization."}

        fa = session.get(Fighter, fighter_a_id)
        fb = session.get(Fighter, fighter_b_id)
        if not fa or not fb:
            return {"error": "One or both fighters not found."}

        # Check same weight class
        fa_wc = fa.weight_class.value if hasattr(fa.weight_class, "value") else fa.weight_class
        fb_wc = fb.weight_class.value if hasattr(fb.weight_class, "value") else fb.weight_class
        if fa_wc != fb_wc:
            return {"error": "Fighters must be in the same weight class."}

        # Check not already booked on this event
        for fight in event.fights:
            if fighter_a_id in (fight.fighter_a_id, fight.fighter_b_id):
                return {"error": f"{fa.name} is already booked on this event."}
            if fighter_b_id in (fight.fighter_a_id, fight.fighter_b_id):
                return {"error": f"{fb.name} is already booked on this event."}

        # Validate both have active contracts with player org
        for fid, fname in [(fighter_a_id, fa.name), (fighter_b_id, fb.name)]:
            contract = session.execute(
                select(Contract).where(
                    Contract.fighter_id == fid,
                    Contract.organization_id == player_org.id,
                    Contract.status == ContractStatus.ACTIVE,
                    Contract.fights_remaining > 0,
                )
            ).scalar_one_or_none()
            if not contract:
                return {"error": f"{fname} does not have a valid contract with fights remaining."}

        card_position = len(event.fights)
        fight = Fight(
            event_id=event.id,
            fighter_a_id=fighter_a_id,
            fighter_b_id=fighter_b_id,
            weight_class=fa.weight_class,
            card_position=card_position,
            is_title_fight=is_title_fight,
        )
        session.add(fight)
        session.commit()
        # Refresh event fights
        session.refresh(event)
        return _event_dict(event, session)


def remove_fight_from_event(event_id: int, fight_id: int) -> dict:
    with _SessionFactory() as session:
        event = session.get(Event, event_id)
        if not event:
            return {"error": "Event not found."}
        if event.status != EventStatus.SCHEDULED:
            return {"error": "Can only remove fights from scheduled events."}

        fight = session.get(Fight, fight_id)
        if not fight or fight.event_id != event_id:
            return {"error": "Fight not found on this event."}
        if fight.winner_id is not None:
            return {"error": "Cannot remove a completed fight."}

        session.delete(fight)
        session.commit()
        session.refresh(event)
        return _event_dict(event, session)


def start_simulate_player_event(event_id: int) -> str:
    task_id = _new_task()
    threading.Thread(
        target=_run_simulate_player_event,
        args=(task_id, event_id, random.randint(0, 999_999)),
        daemon=True,
    ).start()
    return task_id


def _run_simulate_player_event(task_id: str, event_id: int, seed: int) -> None:
    try:
        with _SessionFactory() as session:
            event = session.get(Event, event_id)
            if not event:
                _task_error(task_id, "Event not found.")
                return
            if event.status != EventStatus.SCHEDULED:
                _task_error(task_id, "Event is not scheduled.")
                return
            if len(event.fights) < 2:
                _task_error(task_id, "Need at least 2 fights on the card.")
                return

            player_org = session.execute(
                select(Organization).where(Organization.is_player == True)
            ).scalar_one_or_none()
            if not player_org:
                _task_error(task_id, "No player organization found.")
                return

            rng = random.Random(seed)
            fight_results = []
            total_fighter_salaries = 0.0

            for fight in sorted(event.fights, key=lambda f: f.card_position):
                fa = session.get(Fighter, fight.fighter_a_id)
                fb = session.get(Fighter, fight.fighter_b_id)
                if not fa or not fb:
                    continue

                result = simulate_fight(
                    _to_stats(fa), _to_stats(fb),
                    seed=rng.randint(0, 999_999),
                )

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

                # Decrease fights remaining on contracts
                for fid in (fa.id, fb.id):
                    contract = session.execute(
                        select(Contract).where(
                            Contract.fighter_id == fid,
                            Contract.organization_id == player_org.id,
                            Contract.status == ContractStatus.ACTIVE,
                        )
                    ).scalar_one_or_none()
                    if contract:
                        contract.fights_remaining = max(0, contract.fights_remaining - 1)
                        total_fighter_salaries += contract.salary

                mark_rankings_dirty(session, WeightClass(fa.weight_class))
                apply_fight_tags(winner, loser, fight, session)

                fight_results.append({
                    "fight_id": fight.id,
                    "fighter_a": fa.name,
                    "fighter_a_id": fa.id,
                    "fighter_b": fb.name,
                    "fighter_b_id": fb.id,
                    "winner": winner.name,
                    "winner_id": winner.id,
                    "loser": loser.name,
                    "method": result.method,
                    "round": result.round_ended,
                    "time": result.time_ended,
                    "narrative": result.narrative,
                    "is_title_fight": fight.is_title_fight,
                    "weight_class": fa.weight_class.value if hasattr(fa.weight_class, "value") else fa.weight_class,
                })

            # Calculate revenue
            card_fighters = []
            for fight in event.fights:
                fa = session.get(Fighter, fight.fighter_a_id)
                fb = session.get(Fighter, fight.fighter_b_id)
                if fa:
                    card_fighters.append(fa)
                if fb:
                    card_fighters.append(fb)

            # Find venue base_gate
            venue_info = next((v for v in VENUES if v["name"] == event.venue), VENUES[0])
            card_size = len(event.fights)
            pop_sum = sum(f.popularity for f in card_fighters)
            gate_revenue = venue_info["base_gate"] * (pop_sum / (card_size * 100)) if card_size > 0 else 0

            # PPV from top 2 hype fighters
            sorted_by_hype = sorted(card_fighters, key=lambda f: f.hype, reverse=True)
            top_hype = sorted_by_hype[:2]
            avg_hype = sum(f.hype for f in top_hype) / len(top_hype) if top_hype else 0
            ppv_buys = int(avg_hype * 800)

            event.gate_revenue = gate_revenue
            event.ppv_buys = ppv_buys
            event.status = EventStatus.COMPLETED

            total_revenue = event.total_revenue
            player_org.bank_balance += total_revenue - total_fighter_salaries

            # Narrative updates
            update_goat_scores(session)
            update_rivalries(session)

            session.commit()

            _task_done(task_id, {
                "event_id": event.id,
                "event_name": event.name,
                "fights_simulated": len(fight_results),
                "fights": fight_results,
                "gate_revenue": round(gate_revenue, 2),
                "ppv_buys": ppv_buys,
                "ppv_revenue": round(ppv_buys * 45.0, 2),
                "total_revenue": round(total_revenue, 2),
                "total_costs": round(total_fighter_salaries, 2),
                "profit": round(total_revenue - total_fighter_salaries, 2),
            })
    except Exception as e:
        _task_error(task_id, str(e))


def get_scheduled_events() -> list[dict]:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return []

        events = session.execute(
            select(Event).where(
                Event.organization_id == player_org.id,
                Event.status == EventStatus.SCHEDULED,
            ).order_by(Event.event_date.asc())
        ).scalars().all()

        return [_event_dict(e, session) for e in events]


def get_event_history(limit: int = 20) -> list[dict]:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return []

        events = session.execute(
            select(Event).where(
                Event.organization_id == player_org.id,
                Event.status == EventStatus.COMPLETED,
            ).order_by(Event.event_date.desc()).limit(limit)
        ).scalars().all()

        return [_event_dict(e, session, include_fights=False) for e in events]


def get_event(event_id: int) -> Optional[dict]:
    with _SessionFactory() as session:
        event = session.get(Event, event_id)
        if not event:
            return None
        return _event_dict(event, session)


def calculate_event_projection(event_id: int) -> dict:
    with _SessionFactory() as session:
        event = session.get(Event, event_id)
        if not event:
            return {"error": "Event not found."}

        card_fighters = []
        total_salaries = 0.0
        for fight in event.fights:
            fa = session.get(Fighter, fight.fighter_a_id)
            fb = session.get(Fighter, fight.fighter_b_id)
            if fa:
                card_fighters.append(fa)
            if fb:
                card_fighters.append(fb)
            # Sum salaries
            for fid in (fight.fighter_a_id, fight.fighter_b_id):
                contract = session.execute(
                    select(Contract).where(
                        Contract.fighter_id == fid,
                        Contract.status == ContractStatus.ACTIVE,
                    )
                ).scalar_one_or_none()
                if contract:
                    total_salaries += contract.salary

        venue_info = next((v for v in VENUES if v["name"] == event.venue), VENUES[0])
        card_size = len(event.fights)
        pop_sum = sum(f.popularity for f in card_fighters)
        gate_projection = venue_info["base_gate"] * (pop_sum / (card_size * 100)) if card_size > 0 else 0

        sorted_by_hype = sorted(card_fighters, key=lambda f: f.hype, reverse=True)
        top_hype = sorted_by_hype[:2]
        avg_hype = sum(f.hype for f in top_hype) / len(top_hype) if top_hype else 0
        ppv_projection = int(avg_hype * 800) * 45.0

        total_revenue = gate_projection + ppv_projection
        profit = total_revenue - total_salaries

        return {
            "gate_projection": round(gate_projection, 2),
            "ppv_projection": round(ppv_projection, 2),
            "total_revenue": round(total_revenue, 2),
            "total_costs": round(total_salaries, 2),
            "projected_profit": round(profit, 2),
            "fight_count": card_size,
            "venue": event.venue,
            "venue_capacity": venue_info["capacity"],
        }


def get_venues() -> list[dict]:
    return VENUES
