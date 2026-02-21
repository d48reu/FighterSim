"""
Monthly simulation cycle for MMA Management Simulator.

Handles aging, contracts, condition, and AI org events.
Must complete in under 2 seconds for any roster size.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from typing import Callable

from sqlalchemy.orm import Session
from sqlalchemy import select, update

from models.models import (
    Fighter, Organization, Contract, Event, Fight,
    Ranking, WeightClass, ContractStatus, EventStatus, Notification, GameState
)
from simulation.fight_engine import FighterStats, simulate_fight
from simulation.rankings import mark_rankings_dirty
from simulation.narrative import apply_fight_tags, decay_hype, update_goat_scores, update_rivalries


# ---------------------------------------------------------------------------
# Aging & attribute progression
# ---------------------------------------------------------------------------

_ATTR_FIELDS = ("striking", "grappling", "wrestling", "cardio", "chin", "speed")


def _age_fighter(fighter: Fighter, rng: random.Random) -> None:
    """Increment age and adjust attributes based on career stage."""
    # 1/12 chance to age by 1 year (one month tick = 1/12 of a year)
    if rng.random() > (1 / 12):
        return

    fighter.age += 1

    in_prime = fighter.prime_start <= fighter.age <= fighter.prime_end
    past_prime = fighter.age > fighter.prime_end
    pre_prime = fighter.age < fighter.prime_start

    for attr in _ATTR_FIELDS:
        val = getattr(fighter, attr)
        if pre_prime:
            # Developing — small gains
            delta = rng.randint(0, 2)
        elif in_prime:
            # Peak — minor fluctuation
            delta = rng.randint(-1, 1)
        else:
            # Decline — attrition, cardio and speed fall faster
            if attr in ("cardio", "speed"):
                delta = rng.randint(-3, -1)
            elif attr == "chin":
                delta = rng.randint(-2, 0)
            else:
                delta = rng.randint(-2, 1)

        new_val = max(1, min(100, val + delta))
        setattr(fighter, attr, new_val)


# ---------------------------------------------------------------------------
# Contract management
# ---------------------------------------------------------------------------

def _process_contracts(session: Session, today: date, rng: random.Random) -> None:
    """Expire contracts past their date and auto-renew or release fighters."""
    # Notify about contracts expiring within 60 days (before processing expirations)
    cutoff = today + timedelta(days=60)
    expiring_soon = (
        session.execute(
            select(Contract).where(
                Contract.expiry_date <= cutoff,
                Contract.expiry_date > today,
                Contract.status == ContractStatus.ACTIVE,
            )
        )
        .scalars()
        .all()
    )
    for contract in expiring_soon:
        fighter = session.get(Fighter, contract.fighter_id)
        org = session.get(Organization, contract.organization_id)
        if org and org.is_player and fighter:
            session.add(Notification(
                message=f"{fighter.name}'s contract expires soon ({contract.expiry_date.isoformat()})",
                type="contract_expiring_soon",
                created_date=today,
            ))

    # Process expired contracts
    expired = (
        session.execute(
            select(Contract).where(
                Contract.expiry_date <= today,
                Contract.status == ContractStatus.ACTIVE,
            )
        )
        .scalars()
        .all()
    )

    for contract in expired:
        fighter = session.get(Fighter, contract.fighter_id)
        org = session.get(Organization, contract.organization_id)

        # 60% chance AI org renews; player org handled via UI
        if org and not org.is_player and rng.random() < 0.6:
            # Renew for another 12 months, 4 fights
            contract.expiry_date = today + timedelta(days=365)
            contract.fights_remaining = 4
            contract.fight_count_total = 4
            # Slight salary bump
            contract.salary = round(contract.salary * rng.uniform(1.0, 1.15), 2)
        else:
            contract.status = ContractStatus.EXPIRED
            if org and org.is_player and fighter:
                session.add(Notification(
                    message=f"{fighter.name}'s contract has expired",
                    type="contract_expired",
                    created_date=today,
                ))


# ---------------------------------------------------------------------------
# Injury recovery
# ---------------------------------------------------------------------------

def _recover_injuries(session: Session) -> None:
    """Tick down injury counters and restore condition."""
    injured = (
        session.execute(
            select(Fighter).where(Fighter.injury_months > 0)
        )
        .scalars()
        .all()
    )
    for f in injured:
        f.injury_months = max(0, f.injury_months - 1)
        if f.injury_months == 0:
            f.condition = min(100.0, f.condition + 30)


# ---------------------------------------------------------------------------
# AI event generation
# ---------------------------------------------------------------------------

_VENUES = [
    "Madison Square Garden", "T-Mobile Arena", "Barclays Center",
    "United Center", "Crypto.com Arena", "Chase Center",
    "Rogers Centre", "O2 Arena", "Melbourne Arena",
]

_EVENT_PREFIXES = [
    "Combat Night", "Fight Night", "Battle at the", "Rumble in",
    "Collision Course", "War at", "Championship Series",
]


def _generate_ai_event(
    session: Session,
    org: Organization,
    sim_date: date,
    rng: random.Random,
) -> None:
    """Book and simulate an AI org event with random fighters on its roster."""
    # Find active contracts for this org
    active_contracts = (
        session.execute(
            select(Contract, Fighter)
            .join(Fighter, Contract.fighter_id == Fighter.id)
            .where(
                Contract.organization_id == org.id,
                Contract.status == ContractStatus.ACTIVE,
                Contract.fights_remaining > 0,
                Fighter.injury_months == 0,
            )
        )
        .all()
    )

    if len(active_contracts) < 4:
        return  # not enough fighters for an event

    fighters = [f for _, f in active_contracts]
    rng.shuffle(fighters)

    venue = rng.choice(_VENUES)
    event_name = f"{rng.choice(_EVENT_PREFIXES)} {venue.split()[0]} {sim_date.year}"

    event = Event(
        name=event_name,
        event_date=sim_date,
        venue=venue,
        organization_id=org.id,
        status=EventStatus.COMPLETED,
        gate_revenue=rng.uniform(100_000, 800_000),
        ppv_buys=rng.randint(0, 50_000),
    )
    session.add(event)
    session.flush()

    # Pair fighters (same weight class preferred)
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

            # Simulate
            a_stats = _fighter_to_stats(fa)
            b_stats = _fighter_to_stats(fb)
            result = simulate_fight(a_stats, b_stats, seed=rng.randint(0, 999999))

            fight.winner_id = result.winner_id
            fight.method = result.method
            fight.round_ended = result.round_ended
            fight.time_ended = result.time_ended
            fight.narrative = result.narrative

            # Update records
            winner = fa if result.winner_id == fa.id else fb
            loser = fb if result.winner_id == fa.id else fa
            winner.wins += 1
            loser.losses += 1
            if result.method == "KO/TKO":
                winner.ko_wins += 1
            elif result.method == "Submission":
                winner.sub_wins += 1

            # Decrease fights remaining
            for contract, f in active_contracts:
                if f.id in (fa.id, fb.id):
                    contract.fights_remaining = max(0, contract.fights_remaining - 1)

            # Mark rankings dirty
            mark_rankings_dirty(session, WeightClass(fa.weight_class))

            # Narrative tags and hype
            apply_fight_tags(winner, loser, fight, session)

            paired.add(fa.id)
            paired.add(fb.id)
            card_position += 1

            if card_position >= 8:
                break

        if card_position >= 8:
            break

    # Deduct salaries for fighters on this event
    total_salaries = sum(
        c.salary for c, f in active_contracts if f.id in paired
    )
    org.bank_balance -= total_salaries + event.gate_revenue * 0.4  # costs
    org.bank_balance += event.total_revenue


def _fighter_to_stats(f: Fighter) -> FighterStats:
    try:
        traits = json.loads(f.traits) if f.traits else []
    except (json.JSONDecodeError, TypeError):
        traits = []
    style = f.style.value if hasattr(f.style, "value") else str(f.style)
    return FighterStats(
        id=f.id,
        name=f.name,
        striking=f.striking,
        grappling=f.grappling,
        wrestling=f.wrestling,
        cardio=f.cardio,
        chin=f.chin,
        speed=f.speed,
        traits=traits,
        style=style,
    )


# ---------------------------------------------------------------------------
# Main monthly tick
# ---------------------------------------------------------------------------

def sim_month(
    session: Session,
    sim_date: date | None = None,
    seed: Optional[int] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Advance simulation by one month.

    Reads current_date from GameState, uses it for all logic,
    then advances it by one month and saves.

    Args:
        session: Active SQLAlchemy session.
        sim_date: Ignored if GameState exists (kept for test compat).
        seed: Optional RNG seed.
        progress_callback: Optional callable for progress updates.

    Returns:
        Summary dict with actions taken.
    """
    from typing import Optional  # local to avoid circular at module level

    # Read game clock — authoritative date source
    game_state = session.get(GameState, 1)
    if game_state:
        sim_date = game_state.current_date
    elif sim_date is None:
        sim_date = date.today()

    rng = random.Random(seed)
    summary: dict = {
        "date": sim_date.isoformat(),
        "fighters_aged": 0,
        "contracts_expired": 0,
        "injuries_healed": 0,
        "events_simulated": 0,
    }

    # 0. Player org monthly payroll deduction
    player_org = session.execute(
        select(Organization).where(Organization.is_player == True)
    ).scalar_one_or_none()
    if player_org:
        active_player_contracts = session.execute(
            select(Contract).where(
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalars().all()
        monthly_payroll = sum(c.salary / 12 for c in active_player_contracts)
        player_org.bank_balance -= monthly_payroll
        if player_org.bank_balance < 0:
            session.add(Notification(
                message="Your organization's finances are in the red. Consider releasing fighters.",
                type="finances_critical",
                created_date=sim_date,
            ))
        if player_org.bank_balance < -500_000:
            session.add(Notification(
                message="Bankruptcy warning! Your debt exceeds $500,000. Take immediate action.",
                type="bankruptcy_warning",
                created_date=sim_date,
            ))

    # 1. Age all fighters (bulk update — fast regardless of roster size)
    all_fighters = session.execute(select(Fighter)).scalars().all()
    for fighter in all_fighters:
        _age_fighter(fighter, rng)
        summary["fighters_aged"] += 1

    if progress_callback:
        progress_callback(f"Aged {summary['fighters_aged']} fighters")

    # 2. Recover injuries
    _recover_injuries(session)

    # 3. Process contracts
    before_count = summary["contracts_expired"]
    _process_contracts(session, sim_date, rng)

    # 4. AI organizations generate events (roughly 1-in-3 chance per org per month)
    ai_orgs = (
        session.execute(
            select(Organization).where(Organization.is_player == False)
        )
        .scalars()
        .all()
    )

    # 3b. Decay hype before events (fights will restore it via apply_fight_tags)
    decay_hype(session, rng)

    for org in ai_orgs:
        if rng.random() < 0.4:
            _generate_ai_event(session, org, sim_date, rng)
            summary["events_simulated"] += 1

    # Post-event narrative updates
    update_goat_scores(session)
    update_rivalries(session)

    # Advance game clock by one month
    if game_state:
        month = sim_date.month
        year = sim_date.year
        if month == 12:
            game_state.current_date = date(year + 1, 1, 1)
        else:
            game_state.current_date = date(year, month + 1, 1)

    session.commit()

    if progress_callback:
        progress_callback(f"Month {sim_date} complete")

    return summary


# Avoid circular import
from typing import Optional
