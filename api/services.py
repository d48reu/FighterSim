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
    TrainingCamp, FighterDevelopment,
)
from simulation.fight_engine import FighterStats, simulate_fight
from simulation.monthly_sim import sim_month
from simulation.rankings import rebuild_rankings, get_rankings as _get_rankings, mark_rankings_dirty
from simulation.narrative import (
    apply_fight_tags, update_goat_scores, update_rivalries,
    generate_fighter_bio, get_tags, display_archetype, suggest_nicknames,
    generate_press_conference,
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
        "nickname": f.nickname,
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
# Nickname system
# ---------------------------------------------------------------------------

def get_nickname_suggestions(fighter_id: int) -> list[str]:
    with _SessionFactory() as session:
        f = session.get(Fighter, fighter_id)
        if not f:
            return []
        return suggest_nicknames(f, session)


def set_nickname(fighter_id: int, nickname: str) -> dict:
    with _SessionFactory() as session:
        f = session.get(Fighter, fighter_id)
        if not f:
            return {"success": False, "message": "Fighter not found."}
        if len(nickname) > 30:
            return {"success": False, "message": "Nickname must be 30 characters or less."}
        f.nickname = nickname.strip() if nickname.strip() else None
        session.commit()
        return {"success": True, "message": f"Nickname set to \"{f.nickname}\".", "fighter": _fighter_dict(f)}


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
        "press_conference": json.loads(fight.press_conference) if fight.press_conference else None,
    }
    return d


def _event_dict(event: Event, session, include_fights=True) -> dict:
    d = {
        "id": event.id,
        "name": event.name,
        "event_date": event.event_date.isoformat(),
        "venue": event.venue,
        "status": event.status.value if hasattr(event.status, "value") else event.status,
        "has_press_conference": event.has_press_conference,
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
        ppv_buys = int(avg_hype * 800)

        # Press conference PPV boost
        pc_ppv_boost = 0
        if event.has_press_conference:
            for fight in event.fights:
                if fight.press_conference:
                    pc_data = json.loads(fight.press_conference)
                    pc_ppv_boost = pc_data.get("ppv_boost", 0)
                    break
        ppv_projection = (ppv_buys + pc_ppv_boost) * 45.0

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
            "has_press_conference": event.has_press_conference,
        }


def get_venues() -> list[dict]:
    return VENUES


def hold_press_conference(event_id: int) -> dict:
    with _SessionFactory() as session:
        event = session.get(Event, event_id)
        if not event:
            return {"error": "Event not found."}
        if event.status != EventStatus.SCHEDULED:
            return {"error": "Can only hold press conferences for scheduled events."}
        if len(event.fights) < 2:
            return {"error": "Need at least 2 fights on the card."}
        if event.has_press_conference:
            return {"error": "Press conference already held for this event."}

        # Get main event (highest card_position)
        main_event = max(event.fights, key=lambda f: f.card_position)
        fa = session.get(Fighter, main_event.fighter_a_id)
        fb = session.get(Fighter, main_event.fighter_b_id)
        if not fa or not fb:
            return {"error": "Main event fighters not found."}

        # Check cornerstone status
        is_cs_a = getattr(fa, "is_cornerstone", False)
        is_cs_b = getattr(fb, "is_cornerstone", False)

        pc_data = generate_press_conference(fa, fb, is_cornerstone_a=is_cs_a, is_cornerstone_b=is_cs_b)

        # Store on main event fight
        main_event.press_conference = json.dumps(pc_data)
        event.has_press_conference = True

        # Apply hype boosts
        hype_boost = pc_data["hype_generated"]
        fa.hype = min(100.0, fa.hype + hype_boost)
        fb.hype = min(100.0, fb.hype + hype_boost)

        session.commit()
        return {
            "success": True,
            "press_conference": pc_data,
            "fighter_a": {"name": fa.name, "hype": round(fa.hype, 1)},
            "fighter_b": {"name": fb.name, "hype": round(fb.hype, 1)},
        }


# ---------------------------------------------------------------------------
# Fighter Development
# ---------------------------------------------------------------------------

_FOCUS_MULTIPLIERS = {
    "Striking":  {"striking": 2.0, "speed": 1.2, "grappling": 0.5, "wrestling": 0.5, "cardio": 0.8, "chin": 1.0},
    "Grappling": {"grappling": 2.0, "wrestling": 1.3, "striking": 0.5, "speed": 0.7, "cardio": 0.8, "chin": 1.0},
    "Wrestling": {"wrestling": 2.0, "cardio": 1.3, "striking": 0.6, "grappling": 1.2, "speed": 0.8, "chin": 1.0},
    "Cardio":    {"cardio": 2.5, "wrestling": 1.0, "striking": 0.7, "grappling": 0.7, "speed": 1.2, "chin": 1.0},
    "Balanced":  {"striking": 1.0, "grappling": 1.0, "wrestling": 1.0, "cardio": 1.0, "speed": 1.0, "chin": 1.0},
}

_BASE_GAIN = {1: 0.3, 2: 0.6, 3: 1.0}

_ATTR_FIELDS = ("striking", "grappling", "wrestling", "cardio", "chin", "speed")


def get_training_camps(org_prestige: Optional[float] = None) -> list[dict]:
    with _SessionFactory() as session:
        if org_prestige is None:
            player_org = session.execute(
                select(Organization).where(Organization.is_player == True)
            ).scalar_one_or_none()
            org_prestige = player_org.prestige if player_org else 0.0

        camps = session.execute(
            select(TrainingCamp).order_by(TrainingCamp.tier, TrainingCamp.name)
        ).scalars().all()

        results = []
        for camp in camps:
            enrolled = session.execute(
                select(FighterDevelopment).where(
                    FighterDevelopment.camp_id == camp.id
                )
            ).scalars().all()
            results.append({
                "id": camp.id,
                "name": camp.name,
                "specialty": camp.specialty,
                "tier": camp.tier,
                "cost_per_month": camp.cost_per_month,
                "prestige_required": camp.prestige_required,
                "slots": camp.slots,
                "enrolled": len(enrolled),
                "available": camp.slots - len(enrolled),
                "locked": camp.prestige_required > org_prestige,
            })
        return results


def assign_fighter_to_camp(fighter_id: int, camp_id: int, focus: str) -> dict:
    with _SessionFactory() as session:
        player_org = session.execute(
            select(Organization).where(Organization.is_player == True)
        ).scalar_one_or_none()
        if not player_org:
            return {"error": "No player organization found."}

        # Validate fighter is on player roster
        contract = session.execute(
            select(Contract).where(
                Contract.fighter_id == fighter_id,
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalar_one_or_none()
        if not contract:
            return {"error": "Fighter is not on your roster."}

        camp = session.get(TrainingCamp, camp_id)
        if not camp:
            return {"error": "Training camp not found."}

        # Validate prestige
        if camp.prestige_required > player_org.prestige:
            return {"error": f"Your organization needs {camp.prestige_required} prestige to access this camp."}

        # Validate slots
        enrolled = session.execute(
            select(FighterDevelopment).where(
                FighterDevelopment.camp_id == camp_id
            )
        ).scalars().all()
        # Exclude this fighter if already at this camp
        enrolled_ids = [d.fighter_id for d in enrolled]
        if fighter_id not in enrolled_ids and len(enrolled) >= camp.slots:
            return {"error": "This camp is full."}

        # Validate focus
        if focus not in _FOCUS_MULTIPLIERS:
            return {"error": f"Invalid focus. Choose from: {', '.join(_FOCUS_MULTIPLIERS.keys())}"}

        # Validate affordability
        if player_org.bank_balance < camp.cost_per_month:
            return {"error": "You can't afford this camp's monthly cost."}

        # Create or update development record
        dev = session.execute(
            select(FighterDevelopment).where(
                FighterDevelopment.fighter_id == fighter_id
            )
        ).scalar_one_or_none()

        if dev:
            if dev.camp_id != camp_id:
                dev.months_at_camp = 0  # Reset consistency when changing camps
            dev.camp_id = camp_id
            dev.focus = focus
        else:
            dev = FighterDevelopment(
                fighter_id=fighter_id,
                camp_id=camp_id,
                focus=focus,
                months_at_camp=0,
                total_development_spend=0.0,
            )
            session.add(dev)

        session.commit()
        fighter = session.get(Fighter, fighter_id)
        return {
            "success": True,
            "message": f"{fighter.name} assigned to {camp.name} with {focus} focus.",
            "development": _development_dict(dev, session),
        }


def remove_fighter_from_camp(fighter_id: int) -> dict:
    with _SessionFactory() as session:
        dev = session.execute(
            select(FighterDevelopment).where(
                FighterDevelopment.fighter_id == fighter_id
            )
        ).scalar_one_or_none()
        if not dev or not dev.camp_id:
            return {"error": "Fighter is not assigned to any camp."}

        fighter = session.get(Fighter, fighter_id)
        dev.camp_id = None
        dev.months_at_camp = 0
        dev.focus = "Balanced"
        session.commit()
        return {"success": True, "message": f"{fighter.name} removed from camp."}


def get_roster_development() -> list[dict]:
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
            dev = session.execute(
                select(FighterDevelopment).where(
                    FighterDevelopment.fighter_id == fighter.id
                )
            ).scalar_one_or_none()

            d = _fighter_dict(fighter)
            d["salary"] = contract.salary

            if dev and dev.camp_id:
                camp = session.get(TrainingCamp, dev.camp_id)
                d["camp_name"] = camp.name if camp else None
                d["camp_tier"] = camp.tier if camp else None
                d["camp_specialty"] = camp.specialty if camp else None
                d["camp_cost"] = camp.cost_per_month if camp else 0
                d["focus"] = dev.focus
                d["months_at_camp"] = dev.months_at_camp
                d["total_development_spend"] = dev.total_development_spend
                d["status"] = "training"
            else:
                d["camp_name"] = None
                d["camp_tier"] = None
                d["camp_specialty"] = None
                d["camp_cost"] = 0
                d["focus"] = None
                d["months_at_camp"] = 0
                d["total_development_spend"] = dev.total_development_spend if dev else 0
                # Determine status based on age / prime
                past_prime = fighter.age > fighter.prime_end
                d["status"] = "declining" if past_prime else "idle"

            results.append(d)
        return results


def _development_dict(dev: FighterDevelopment, session) -> dict:
    camp = session.get(TrainingCamp, dev.camp_id) if dev.camp_id else None
    return {
        "fighter_id": dev.fighter_id,
        "camp_id": dev.camp_id,
        "camp_name": camp.name if camp else None,
        "camp_tier": camp.tier if camp else None,
        "focus": dev.focus,
        "months_at_camp": dev.months_at_camp,
        "total_development_spend": dev.total_development_spend,
        "last_trained": dev.last_trained.isoformat() if dev.last_trained else None,
    }


def _calc_projected_gain(fighter: Fighter, camp: TrainingCamp, focus: str,
                         months: int, dev_months_at_camp: int = 0) -> dict:
    """Calculate projected attribute gains over N months."""
    rng = random.Random(fighter.id)  # deterministic for projection
    projected = {attr: getattr(fighter, attr) for attr in _ATTR_FIELDS}
    monthly_snapshots = {}

    focus_mults = _FOCUS_MULTIPLIERS.get(focus, _FOCUS_MULTIPLIERS["Balanced"])
    base_gain = _BASE_GAIN.get(camp.tier, 0.3)
    specialty_bonus = 1.3 if camp.specialty == focus or camp.specialty == "Well-Rounded" else 1.0

    if fighter.age < 24:
        age_modifier = 1.4
    elif fighter.age < 27:
        age_modifier = 1.2
    elif fighter.age < 30:
        age_modifier = 1.0
    elif fighter.age < 33:
        age_modifier = 0.7
    else:
        age_modifier = 0.4

    prime_modifier = 1.1 if fighter.prime_start <= fighter.age <= fighter.prime_end else 0.9

    for m in range(1, months + 1):
        camp_months = dev_months_at_camp + m
        consistency_bonus = min(1.2, 1.0 + camp_months * 0.02)

        for attr in _ATTR_FIELDS:
            multiplier = focus_mults[attr]
            gain = base_gain * multiplier * specialty_bonus * age_modifier * prime_modifier * consistency_bonus
            # Use average randomness for projections (1.0 instead of random)
            current = projected[attr]
            if current >= 85:
                gain *= 0.4
            elif current >= 75:
                gain *= 0.7
            projected[attr] = min(99, current + gain)

        if m in (3, 6, 12):
            monthly_snapshots[m] = {attr: round(projected[attr]) for attr in _ATTR_FIELDS}
            monthly_snapshots[m]["overall"] = round(
                projected["striking"] * 0.2 + projected["grappling"] * 0.2
                + projected["wrestling"] * 0.15 + projected["cardio"] * 0.15
                + projected["chin"] * 0.15 + projected["speed"] * 0.15
            )

    return monthly_snapshots


def get_development_projections(fighter_id: int, camp_id: int, focus: str, months: int = 12) -> dict:
    with _SessionFactory() as session:
        fighter = session.get(Fighter, fighter_id)
        if not fighter:
            return {"error": "Fighter not found."}

        camp = session.get(TrainingCamp, camp_id)
        if not camp:
            return {"error": "Camp not found."}

        if focus not in _FOCUS_MULTIPLIERS:
            return {"error": "Invalid focus."}

        dev = session.execute(
            select(FighterDevelopment).where(
                FighterDevelopment.fighter_id == fighter_id
            )
        ).scalar_one_or_none()
        dev_months = dev.months_at_camp if dev and dev.camp_id == camp_id else 0

        now = {attr: getattr(fighter, attr) for attr in _ATTR_FIELDS}
        now["overall"] = fighter.overall

        projections = _calc_projected_gain(fighter, camp, focus, months, dev_months)

        return {
            "now": now,
            "projections": projections,
        }


def process_fighter_development(session, org_id: int, sim_date) -> list[dict]:
    """Process monthly development for all player roster fighters.

    Called from sim_month(). Returns list of notification messages.
    """
    rng = random.Random()
    notifications = []

    # Get all player roster fighters
    rows = session.execute(
        select(Contract, Fighter)
        .join(Fighter, Contract.fighter_id == Fighter.id)
        .where(
            Contract.organization_id == org_id,
            Contract.status == ContractStatus.ACTIVE,
        )
    ).all()

    org = session.get(Organization, org_id)

    for contract, fighter in rows:
        dev = session.execute(
            select(FighterDevelopment).where(
                FighterDevelopment.fighter_id == fighter.id
            )
        ).scalar_one_or_none()

        old_overall = fighter.overall

        if dev and dev.camp_id:
            camp = session.get(TrainingCamp, dev.camp_id)
            if not camp:
                continue

            focus = dev.focus if dev.focus in _FOCUS_MULTIPLIERS else "Balanced"
            focus_mults = _FOCUS_MULTIPLIERS[focus]
            base_gain = _BASE_GAIN.get(camp.tier, 0.3)
            specialty_bonus = 1.3 if camp.specialty == focus or camp.specialty == "Well-Rounded" else 1.0

            if fighter.age < 24:
                age_modifier = 1.4
            elif fighter.age < 27:
                age_modifier = 1.2
            elif fighter.age < 30:
                age_modifier = 1.0
            elif fighter.age < 33:
                age_modifier = 0.7
            else:
                age_modifier = 0.4

            prime_modifier = 1.1 if fighter.prime_start <= fighter.age <= fighter.prime_end else 0.9
            consistency_bonus = min(1.2, 1.0 + dev.months_at_camp * 0.02)

            for attr in _ATTR_FIELDS:
                multiplier = focus_mults[attr]
                gain = base_gain * multiplier * specialty_bonus * age_modifier * prime_modifier * consistency_bonus
                gain *= rng.uniform(0.7, 1.3)

                current = getattr(fighter, attr)
                if current >= 85:
                    gain *= 0.4
                elif current >= 75:
                    gain *= 0.7

                new_val = min(99, current + gain)
                setattr(fighter, attr, round(new_val))

            # Deduct camp cost
            if org:
                org.bank_balance -= camp.cost_per_month

            dev.months_at_camp += 1
            dev.total_development_spend += camp.cost_per_month
            dev.last_trained = sim_date

            # Consistency notification at 6 months
            if dev.months_at_camp == 6:
                msg = f"{fighter.name} has been at {camp.name} for 6 months — consistency bonus active"
                notifications.append(msg)

        else:
            # No camp assigned — natural decay/growth
            past_prime = fighter.age > fighter.prime_end
            young = fighter.age < fighter.prime_start

            if past_prime:
                # Decay for cardio and speed
                for attr in ("cardio", "speed"):
                    decay = rng.uniform(0.2, 0.5)
                    current = getattr(fighter, attr)
                    setattr(fighter, attr, max(1, round(current - decay)))
            elif young:
                # Small natural growth
                for attr in _ATTR_FIELDS:
                    gain = rng.uniform(0.1, 0.2)
                    current = getattr(fighter, attr)
                    setattr(fighter, attr, min(99, round(current + gain)))

        # Check milestone notifications
        new_overall = fighter.overall
        for threshold in (70, 75, 80, 85):
            if old_overall < threshold <= new_overall:
                notifications.append(f"{fighter.name} reached Overall {threshold}")
            if old_overall >= threshold > new_overall:
                notifications.append(f"{fighter.name} is declining — consider adjusting training")

    return notifications
