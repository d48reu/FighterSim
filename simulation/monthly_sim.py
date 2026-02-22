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
from sqlalchemy import select, update, or_ as db_or, and_ as db_and

from models.models import (
    Fighter, Organization, Contract, Event, Fight,
    Ranking, WeightClass, ContractStatus, EventStatus, Notification, GameState,
    BroadcastDeal, BroadcastDealStatus,
    Sponsorship, SponsorshipStatus,
    RealityShow, ShowContestant, ShowEpisode, ShowStatus,
    NewsHeadline,
)
from simulation.fight_engine import FighterStats, simulate_fight
from simulation.rankings import mark_rankings_dirty
from simulation.narrative import (
    apply_fight_tags, decay_hype, update_goat_scores, update_rivalries,
    generate_fight_headline, generate_signing_headline,
)


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

            # Simulate — compute weight cut severity
            a_stats = _fighter_to_stats(fa)
            b_stats = _fighter_to_stats(fb)
            sev_a = _get_cut_severity(fa)
            sev_b = _get_cut_severity(fb)
            result = simulate_fight(a_stats, b_stats, seed=rng.randint(0, 999999),
                                    cut_severity_a=sev_a, cut_severity_b=sev_b)

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

            # Generate headline
            headline_text = generate_fight_headline(winner, loser, fight, session)
            if headline_text:
                cat = "title" if fight.is_title_fight else ("upset" if loser.overall - winner.overall >= 10 else "fight_result")
                session.add(NewsHeadline(
                    headline=headline_text, category=cat,
                    game_date=sim_date, fighter_id=winner.id, event_id=event.id,
                ))

            paired.add(fa.id)
            paired.add(fb.id)
            card_position += 1

            if card_position >= 8:
                break

        if card_position >= 8:
            break

    # Cache last event info on org
    org.last_event_name = event.name
    org.last_event_date = sim_date

    # Deduct salaries for fighters on this event
    total_salaries = sum(
        c.salary for c, f in active_contracts if f.id in paired
    )
    org.bank_balance -= total_salaries + event.gate_revenue * 0.4  # costs
    org.bank_balance += event.total_revenue


def _get_cut_severity(f: Fighter) -> str:
    """Calculate weight cut severity for a fighter."""
    if not getattr(f, "natural_weight", None) or not getattr(f, "fighting_weight", None):
        return "easy"
    if f.natural_weight <= f.fighting_weight:
        return "easy"
    cut_pct = (f.natural_weight - f.fighting_weight) / f.natural_weight * 100
    if cut_pct < 5:
        return "easy"
    elif cut_pct < 10:
        return "moderate"
    elif cut_pct < 15:
        return "severe"
    return "extreme"


def _process_broadcast_deals(session: Session, sim_date: date, player_org: Organization) -> list[str]:
    """Check broadcast deal compliance, expiry, and apply prestige gain."""
    notifications = []
    if not player_org:
        return notifications

    deals = session.execute(
        select(BroadcastDeal).where(
            BroadcastDeal.organization_id == player_org.id,
            BroadcastDeal.status == BroadcastDealStatus.ACTIVE,
        )
    ).scalars().all()

    for deal in deals:
        # Check expiry
        if sim_date >= deal.expiry_date:
            deal.status = BroadcastDealStatus.EXPIRED
            notifications.append(f"Your {deal.tier} deal with {deal.network_name} has expired.")
            continue

        # Apply monthly prestige gain
        player_org.prestige = min(100.0, player_org.prestige + deal.prestige_per_month)

        # Check if prestige dropped too far below minimum
        if player_org.prestige < deal.min_prestige - 10:
            deal.status = BroadcastDealStatus.CANCELLED
            player_org.prestige = max(0.0, player_org.prestige - 5.0)
            notifications.append(
                f"DEAL CANCELLED: {deal.network_name} terminated your {deal.tier} deal — prestige fell too far below minimum."
            )
            continue

        # Every 3 months: check event pace
        months_elapsed = max(1, (sim_date - deal.start_date).days // 30)
        if months_elapsed > 0 and months_elapsed % 3 == 0:
            expected_events = deal.min_events_per_year * months_elapsed / 12
            if deal.events_delivered < expected_events:
                deal.compliance_warnings += 1
                if deal.compliance_warnings >= 2:
                    deal.status = BroadcastDealStatus.CANCELLED
                    player_org.prestige = max(0.0, player_org.prestige - 5.0)
                    notifications.append(
                        f"DEAL CANCELLED: {deal.network_name} terminated your {deal.tier} deal — insufficient events."
                    )
                else:
                    notifications.append(
                        f"WARNING: {deal.network_name} is concerned about your event pace ({deal.events_delivered} events, expected {expected_events:.0f}). Warning {deal.compliance_warnings}/2."
                    )

    return notifications


def _process_sponsorships(session: Session, sim_date: date, player_org: Organization) -> list[str]:
    """Process sponsorship payments, expiry, and compliance checks."""
    notifications = []
    if not player_org:
        return notifications

    sponsorships = session.execute(
        select(Sponsorship).where(
            Sponsorship.organization_id == player_org.id,
            Sponsorship.status == SponsorshipStatus.ACTIVE,
        )
    ).scalars().all()

    total_income = 0.0
    for sp in sponsorships:
        fighter = session.get(Fighter, sp.fighter_id)

        # 1. Expiry check
        if sim_date >= sp.expiry_date:
            sp.status = SponsorshipStatus.EXPIRED
            notifications.append(
                f"{sp.brand_name} sponsorship for {fighter.name if fighter else 'Unknown'} has expired ({sp.tier})."
            )
            continue

        # 2. Contract check — fighter must still be on player roster
        active_contract = session.execute(
            select(Contract).where(
                Contract.fighter_id == sp.fighter_id,
                Contract.organization_id == player_org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalar_one_or_none()
        if not active_contract:
            sp.status = SponsorshipStatus.CANCELLED
            notifications.append(
                f"{sp.brand_name} dropped {fighter.name if fighter else 'Unknown'} — no longer on roster."
            )
            continue

        # 3. Compliance check — hype must not fall too far below minimum
        if fighter and fighter.hype < sp.min_hype - 15:
            sp.status = SponsorshipStatus.CANCELLED
            notifications.append(
                f"{sp.brand_name} dropped {fighter.name} — hype fell too low ({sp.tier})."
            )
            continue

        # 4. Pay stipend
        player_org.bank_balance += sp.monthly_stipend
        sp.total_paid += sp.monthly_stipend
        total_income += sp.monthly_stipend

    if total_income > 0:
        notifications.append(f"Sponsorship income this month: ${total_income:,.0f}")

    return notifications


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
        confidence=getattr(f, "confidence", 70.0) or 70.0,
    )


# ---------------------------------------------------------------------------
# Reality Show processing
# ---------------------------------------------------------------------------

def _process_reality_show(
    session: Session, sim_date: date, player_org: Organization, rng: random.Random
) -> list[str]:
    """Process one episode of an active reality show. Returns notification messages."""
    notifications = []
    if not player_org:
        return notifications

    show = session.execute(
        select(RealityShow).where(
            RealityShow.organization_id == player_org.id,
            RealityShow.status == ShowStatus.IN_PROGRESS,
        )
    ).scalar_one_or_none()
    if not show:
        return notifications

    from api.services import SHENANIGANS, SHOW_PRODUCTION_COST

    total_episodes = 4 if show.format_size == 8 else 5
    ep_num = show.episodes_aired + 1

    # Determine episode type
    if show.format_size == 8:
        ep_types = ["intro", "quarterfinal", "semifinal", "finale"]
    else:
        ep_types = ["intro", "first_round", "quarterfinal", "semifinal", "finale"]

    if ep_num > total_episodes:
        return notifications

    ep_type = ep_types[ep_num - 1]
    is_fight_episode = ep_type != "intro"

    # Get active contestants
    contestants = session.execute(
        select(ShowContestant).where(
            ShowContestant.show_id == show.id,
        )
    ).scalars().all()
    active_contestants = [sc for sc in contestants if sc.status == "active"]
    suspended_contestants = [sc for sc in contestants if sc.status == "suspended"]

    # Un-suspend fighters at start of new episode
    for sc in suspended_contestants:
        sc.status = "active"
        active_contestants.append(sc)

    # --- Generate shenanigans ---
    shenanigan_slots = 4 if ep_type == "intro" else 3
    shenanigan_results = []
    shenanigan_targets_count: dict[int, int] = {}

    for _ in range(shenanigan_slots):
        if rng.random() > 0.70:
            continue
        if not active_contestants:
            break

        # Positive vs negative
        is_positive = rng.random() < 0.40
        category = "positive" if is_positive else "negative"
        pool = SHENANIGANS[category]

        # Weight selection
        weights = [s["weight"] for s in pool]

        # Pick a target fighter
        eligible_targets = [
            sc for sc in active_contestants
            if shenanigan_targets_count.get(sc.fighter_id, 0) < 2
        ]
        if not eligible_targets:
            continue

        # Weight targets by traits
        target_weights = []
        for sc in eligible_targets:
            fighter = session.get(Fighter, sc.fighter_id)
            tags = []
            try:
                tags = json.loads(fighter.narrative_tags) if fighter and fighter.narrative_tags else []
            except (json.JSONDecodeError, TypeError):
                pass
            w = 1.0
            if not is_positive:
                if "hothead" in tags or "loose_cannon" in tags:
                    w = 2.0
            else:
                if "fan_favorite" in tags or "media_darling" in tags:
                    w = 1.5
            target_weights.append(w)

        target_sc = rng.choices(eligible_targets, weights=target_weights, k=1)[0]
        shenanigan_targets_count[target_sc.fighter_id] = shenanigan_targets_count.get(target_sc.fighter_id, 0) + 1

        shenanigan = rng.choices(pool, weights=weights, k=1)[0]
        fighter = session.get(Fighter, target_sc.fighter_id)

        # Skip short_notice_step_up unless someone was recently eliminated
        eliminated_this_ep = [s for s in shenanigan_results if s.get("eliminated")]
        if shenanigan["type"] == "short_notice_step_up" and not eliminated_this_ep:
            continue

        # Build description
        desc = rng.choice(shenanigan["templates"]).format(
            name=fighter.name if fighter else "Unknown",
            target=rng.choice([sc for sc in active_contestants if sc.fighter_id != target_sc.fighter_id]).fighter_id
            if shenanigan["type"] == "callout_favorite" and len(active_contestants) > 1
            else ""
        )

        # For callout_favorite, pick actual target name
        if shenanigan["type"] == "callout_favorite" and len(active_contestants) > 1:
            others = [sc for sc in active_contestants if sc.fighter_id != target_sc.fighter_id]
            if others:
                other_sc = rng.choice(others)
                other_fighter = session.get(Fighter, other_sc.fighter_id)
                desc = rng.choice(shenanigan["templates"]).format(
                    name=fighter.name, target=other_fighter.name if other_fighter else "Unknown"
                )
                # Apply hype to both
                if other_fighter:
                    other_fighter.hype = min(100.0, other_fighter.hype + 6)
                    # Create rivalry
                    if fighter and not fighter.rivalry_with:
                        fighter.rivalry_with = other_fighter.id
                    if other_fighter and not other_fighter.rivalry_with:
                        other_fighter.rivalry_with = fighter.id

        effects = shenanigan["effects"]
        result_entry = {
            "type": shenanigan["type"],
            "category": category,
            "description": desc,
            "fighter_id": target_sc.fighter_id,
            "fighter_name": fighter.name if fighter else "Unknown",
            "tag": shenanigan["tag"],
            "eliminated": False,
        }

        # Apply effects
        if fighter:
            if effects.get("popularity"):
                fighter.popularity = min(100.0, max(0.0, fighter.popularity + effects["popularity"]))
            if effects.get("hype"):
                fighter.hype = min(100.0, max(0.0, fighter.hype + effects["hype"]))
                target_sc.show_hype_earned += abs(effects["hype"])
            if effects.get("confidence"):
                fighter.confidence = min(100.0, max(0.0, fighter.confidence + effects["confidence"]))
            if effects.get("cardio"):
                fighter.cardio = max(1, min(100, fighter.cardio + effects["cardio"]))
            if effects.get("speed"):
                fighter.speed = max(1, min(100, fighter.speed + effects["speed"]))
            if effects.get("random_attr"):
                attr = rng.choice(["striking", "grappling", "wrestling", "cardio", "chin", "speed"])
                val = getattr(fighter, attr)
                setattr(fighter, attr, min(85, val + effects["random_attr"]))

            # Apply tag
            if shenanigan["tag"]:
                try:
                    tags = json.loads(fighter.narrative_tags) if fighter.narrative_tags else []
                except (json.JSONDecodeError, TypeError):
                    tags = []
                if shenanigan["tag"] not in tags:
                    tags.append(shenanigan["tag"])
                    fighter.narrative_tags = json.dumps(tags)

        # Special effects
        if effects.get("suspend"):
            target_sc.status = "suspended"
            if target_sc in active_contestants:
                active_contestants.remove(target_sc)
            result_entry["suspended"] = True

        if effects.get("eliminate"):
            target_sc.status = "eliminated"
            target_sc.eliminated_round = show.current_round
            target_sc.eliminated_by = "quit"
            if target_sc in active_contestants:
                active_contestants.remove(target_sc)
            result_entry["eliminated"] = True

        if effects.get("eliminate_if_fighting") and is_fight_episode:
            target_sc.status = "eliminated"
            target_sc.eliminated_round = show.current_round
            target_sc.eliminated_by = "injury"
            if target_sc in active_contestants:
                active_contestants.remove(target_sc)
            result_entry["eliminated"] = True

        if effects.get("fine"):
            player_org.bank_balance -= effects["fine"]

        if effects.get("show_hype"):
            show.show_hype = max(0.0, min(100.0, show.show_hype + effects["show_hype"]))

        if effects.get("others_confidence"):
            other_active = [sc for sc in active_contestants if sc.fighter_id != target_sc.fighter_id]
            targets = rng.sample(other_active, min(2, len(other_active)))
            for osc in targets:
                of = session.get(Fighter, osc.fighter_id)
                if of:
                    of.confidence = max(0.0, min(100.0, of.confidence + effects["others_confidence"]))

        target_sc.shenanigan_count += 1
        shenanigan_results.append(result_entry)

    # --- Simulate fights if fight episode ---
    fight_results = []
    if is_fight_episode:
        # Build matchups from bracket
        contestants_by_seed = {sc.seed: sc for sc in contestants}
        matchups = _get_round_matchups(show, ep_type, contestants_by_seed, session)

        for seed_a, seed_b in matchups:
            sc_a = contestants_by_seed.get(seed_a)
            sc_b = contestants_by_seed.get(seed_b)

            if not sc_a or not sc_b:
                continue

            fa = session.get(Fighter, sc_a.fighter_id) if sc_a else None
            fb = session.get(Fighter, sc_b.fighter_id) if sc_b else None

            # Handle walkovers
            a_can_fight = sc_a.status == "active" and fa and fa.injury_months == 0
            b_can_fight = sc_b.status == "active" and fb and fb.injury_months == 0

            if not a_can_fight and not b_can_fight:
                continue
            if not a_can_fight:
                sc_b.show_wins += 1
                fight_results.append({
                    "fighter_a_id": fa.id if fa else None,
                    "fighter_a": fa.name if fa else "Unknown",
                    "fighter_b_id": fb.id if fb else None,
                    "fighter_b": fb.name if fb else "Unknown",
                    "winner_id": fb.id if fb else None,
                    "winner": fb.name if fb else "Unknown",
                    "is_walkover": True,
                    "method": "Walkover",
                    "round": None,
                    "time": None,
                    "narrative": f"{fb.name} advances via walkover — opponent was unable to compete.",
                })
                sc_a.status = "eliminated"
                sc_a.eliminated_round = show.current_round + 1
                sc_a.eliminated_by = "walkover"
                sc_a.show_losses += 1
                continue
            if not b_can_fight:
                sc_a.show_wins += 1
                fight_results.append({
                    "fighter_a_id": fa.id if fa else None,
                    "fighter_a": fa.name if fa else "Unknown",
                    "fighter_b_id": fb.id if fb else None,
                    "fighter_b": fb.name if fb else "Unknown",
                    "winner_id": fa.id if fa else None,
                    "winner": fa.name if fa else "Unknown",
                    "is_walkover": True,
                    "method": "Walkover",
                    "round": None,
                    "time": None,
                    "narrative": f"{fa.name} advances via walkover — opponent was unable to compete.",
                })
                sc_b.status = "eliminated"
                sc_b.eliminated_round = show.current_round + 1
                sc_b.eliminated_by = "walkover"
                sc_b.show_losses += 1
                continue

            # Simulate fight (3 rounds)
            a_stats = _fighter_to_stats(fa)
            b_stats = _fighter_to_stats(fb)
            result = simulate_fight(a_stats, b_stats, seed=rng.randint(0, 999999), max_rounds=3)

            winner = fa if result.winner_id == fa.id else fb
            loser = fb if winner is fa else fa
            winner_sc = sc_a if winner is fa else sc_b
            loser_sc = sc_b if winner is fa else sc_a

            # Update records
            winner.wins += 1
            loser.losses += 1
            if result.method == "KO/TKO":
                winner.ko_wins += 1
            elif result.method == "Submission":
                winner.sub_wins += 1

            winner_sc.show_wins += 1
            loser_sc.show_losses += 1
            loser_sc.status = "eliminated"
            loser_sc.eliminated_round = show.current_round + 1
            loser_sc.eliminated_by = "loss"

            # Hype changes
            winner.hype = min(100.0, winner.hype + 15)
            loser.hype = max(0.0, loser.hype - 5)
            winner_sc.show_hype_earned += 15

            mark_rankings_dirty(session, WeightClass(fa.weight_class))

            fight_results.append({
                "fighter_a_id": fa.id,
                "fighter_a": fa.name,
                "fighter_b_id": fb.id,
                "fighter_b": fb.name,
                "winner_id": result.winner_id,
                "winner": winner.name,
                "loser": loser.name,
                "is_walkover": False,
                "method": result.method,
                "round": result.round_ended,
                "time": result.time_ended,
                "narrative": result.narrative,
            })

    # --- Training gains for all active contestants ---
    still_active = [sc for sc in contestants if sc.status == "active"]
    for sc in still_active:
        fighter = session.get(Fighter, sc.fighter_id)
        if fighter:
            attr = rng.choice(["striking", "grappling", "wrestling", "cardio", "chin", "speed"])
            gain = rng.randint(1, 3)
            current = getattr(fighter, attr)
            setattr(fighter, attr, min(85, current + gain))

    # --- Update show hype ---
    hype_base = rng.uniform(5, 10)
    finish_bonus = sum(3 for fr in fight_results if fr.get("method") in ("KO/TKO", "Submission"))
    drama_bonus = sum(2 for s in shenanigan_results if s["category"] == "negative")
    hype_generated = hype_base + finish_bonus + drama_bonus
    show.show_hype = min(100.0, show.show_hype + hype_generated)

    # --- Update round counter ---
    if ep_type == "intro":
        show.current_round = 0
    elif ep_type == "first_round":
        show.current_round = 1
    elif ep_type == "quarterfinal":
        show.current_round = 2 if show.format_size == 16 else 1
    elif ep_type == "semifinal":
        show.current_round = 3 if show.format_size == 16 else 2
    elif ep_type == "finale":
        show.current_round = 4 if show.format_size == 16 else 3

    # --- Create Event record for broadcast compliance ---
    broadcast_revenue = 0.0
    active_deal = session.execute(
        select(BroadcastDeal).where(
            BroadcastDeal.organization_id == player_org.id,
            BroadcastDeal.status == BroadcastDealStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if active_deal:
        broadcast_revenue = active_deal.fee_per_event
        active_deal.events_delivered += 1

    event = Event(
        name=f"{show.name} - Episode {ep_num}",
        event_date=sim_date,
        venue="TV Studio",
        organization_id=player_org.id,
        status=EventStatus.COMPLETED,
        gate_revenue=0.0,
        ppv_buys=0,
        broadcast_revenue=broadcast_revenue,
        venue_rental_cost=0.0,
        tickets_sold=0,
        venue_capacity=0,
    )
    session.add(event)
    session.flush()

    show.total_revenue += broadcast_revenue

    # --- Deduct production cost ---
    if ep_num > 1:  # First episode was already deducted at creation
        player_org.bank_balance -= show.production_cost_per_episode
        show.total_production_spend += show.production_cost_per_episode

    # --- Store episode ---
    episode_narrative = f"Episode {ep_num}: {ep_type.replace('_', ' ').title()}"
    if shenanigan_results:
        episode_narrative += f" — {len(shenanigan_results)} shenanigan(s)"
    if fight_results:
        episode_narrative += f", {len(fight_results)} fight(s)"

    episode = ShowEpisode(
        show_id=show.id,
        episode_number=ep_num,
        episode_type=ep_type,
        air_date=sim_date,
        fight_results=json.dumps(fight_results) if fight_results else None,
        shenanigans=json.dumps(shenanigan_results) if shenanigan_results else None,
        episode_narrative=episode_narrative,
        episode_rating=min(10.0, show.show_hype / 10),
        hype_generated=hype_generated,
        event_id=event.id,
    )
    session.add(episode)

    show.episodes_aired = ep_num

    # --- Check if finale ---
    if ep_type == "finale":
        _conclude_show(session, show, contestants, sim_date, player_org)
        notifications.append(f"Reality show '{show.name}' has concluded!")
    else:
        notifications.append(f"'{show.name}' Episode {ep_num} aired — {ep_type.replace('_', ' ').title()}")

    return notifications


def _get_round_matchups(show, ep_type, contestants_by_seed, session):
    """Return list of (seed_a, seed_b) matchups for the current round."""
    if show.format_size == 8:
        if ep_type == "quarterfinal":
            return [(1, 8), (4, 5), (3, 6), (2, 7)]
        elif ep_type == "semifinal":
            # Get QF winners from episode results
            return _get_next_round_matchups(show, "quarterfinal", contestants_by_seed, session)
        elif ep_type == "finale":
            return _get_next_round_matchups(show, "semifinal", contestants_by_seed, session)
    else:
        if ep_type == "first_round":
            return [(1, 16), (8, 9), (4, 13), (5, 12), (3, 14), (6, 11), (2, 15), (7, 10)]
        elif ep_type == "quarterfinal":
            return _get_next_round_matchups(show, "first_round", contestants_by_seed, session)
        elif ep_type == "semifinal":
            return _get_next_round_matchups(show, "quarterfinal", contestants_by_seed, session)
        elif ep_type == "finale":
            return _get_next_round_matchups(show, "semifinal", contestants_by_seed, session)
    return []


def _get_next_round_matchups(show, prev_ep_type, contestants_by_seed, session):
    """Determine next round matchups from previous round results."""
    # Find the previous round episode
    prev_ep = session.execute(
        select(ShowEpisode).where(
            ShowEpisode.show_id == show.id,
            ShowEpisode.episode_type == prev_ep_type,
        )
    ).scalar_one_or_none()

    if not prev_ep or not prev_ep.fight_results:
        return []

    fight_data = json.loads(prev_ep.fight_results)
    winner_ids = [fr["winner_id"] for fr in fight_data if fr.get("winner_id")]

    # Map winner IDs back to seeds
    id_to_seed = {}
    for seed, sc in contestants_by_seed.items():
        id_to_seed[sc.fighter_id] = seed

    winner_seeds = [id_to_seed.get(wid) for wid in winner_ids if id_to_seed.get(wid) is not None]

    # Pair winners sequentially: 1st vs 2nd, 3rd vs 4th, etc.
    matchups = []
    for i in range(0, len(winner_seeds), 2):
        if i + 1 < len(winner_seeds):
            matchups.append((winner_seeds[i], winner_seeds[i + 1]))
    return matchups


def _conclude_show(session, show, contestants, sim_date, player_org):
    """Handle show completion: set winner, apply tags, prestige, revenue."""
    # Find winner and runner-up from the finale fight
    finale_ep = session.execute(
        select(ShowEpisode).where(
            ShowEpisode.show_id == show.id,
            ShowEpisode.episode_type == "finale",
        )
    ).scalar_one_or_none()

    if finale_ep and finale_ep.fight_results:
        fight_data = json.loads(finale_ep.fight_results)
        if fight_data:
            finale_fight = fight_data[0]
            show.winner_id = finale_fight.get("winner_id")
            # Runner-up is the loser of the finale
            fighter_ids = {finale_fight.get("fighter_a_id"), finale_fight.get("fighter_b_id")}
            fighter_ids.discard(show.winner_id)
            if fighter_ids:
                show.runner_up_id = fighter_ids.pop()

    show.status = ShowStatus.COMPLETED
    show.end_date = sim_date

    # Apply post-show effects
    for sc in contestants:
        fighter = session.get(Fighter, sc.fighter_id)
        if not fighter:
            continue

        try:
            tags = json.loads(fighter.narrative_tags) if fighter.narrative_tags else []
        except (json.JSONDecodeError, TypeError):
            tags = []

        if fighter.id == show.winner_id:
            if "show_winner" not in tags:
                tags.append("show_winner")
            fighter.hype = min(100.0, fighter.hype + 30)
            fighter.popularity = min(100.0, fighter.popularity + 20)
        elif fighter.id == show.runner_up_id:
            if "show_runner_up" not in tags:
                tags.append("show_runner_up")
            fighter.hype = min(100.0, fighter.hype + 15)
            fighter.popularity = min(100.0, fighter.popularity + 10)
        elif sc.eliminated_round and sc.eliminated_round >= (3 if show.format_size == 16 else 2):
            if "show_veteran" not in tags:
                tags.append("show_veteran")
            fighter.hype = min(100.0, fighter.hype + 8)
            fighter.popularity = min(100.0, fighter.popularity + 5)
        else:
            if "show_veteran" not in tags:
                tags.append("show_veteran")
            fighter.hype = min(100.0, fighter.hype + 3)
            fighter.popularity = min(100.0, fighter.popularity + 3)

        fighter.narrative_tags = json.dumps(tags)

    # Org prestige gain
    prestige_gain = 3
    if show.show_hype > 70:
        prestige_gain = 8
    elif show.show_hype > 50:
        prestige_gain = 5
    player_org.prestige = min(100.0, player_org.prestige + prestige_gain)

    # Completion bonus
    completion_bonus = show.show_hype * 500
    show.total_revenue += completion_bonus
    player_org.bank_balance += completion_bonus

    # Winner contract auto-offer notification
    if show.winner_id:
        winner = session.get(Fighter, show.winner_id)
        if winner:
            session.add(Notification(
                message=f"{winner.name} won '{show.name}'! Sign them at a 25% discount.",
                type="show_winner",
                created_date=sim_date,
            ))


# ---------------------------------------------------------------------------
# AI rival behaviors
# ---------------------------------------------------------------------------

def _ai_sign_free_agents(
    session: Session, ai_orgs: list, sim_date: date, rng: random.Random, player_org
) -> None:
    """Each AI org evaluates free agents and signs 1-2 per month."""
    # Build set of fighter IDs with active contracts
    active_ids = set(
        session.execute(
            select(Contract.fighter_id).where(Contract.status == ContractStatus.ACTIVE)
        ).scalars().all()
    )

    # Also exclude fighters on active reality shows or shows that just completed this month
    show_ids = set(
        session.execute(
            select(ShowContestant.fighter_id)
            .join(RealityShow, ShowContestant.show_id == RealityShow.id)
            .where(
                db_or(
                    RealityShow.status == ShowStatus.IN_PROGRESS,
                    db_and(
                        RealityShow.status == ShowStatus.COMPLETED,
                        RealityShow.end_date == sim_date,
                    ),
                )
            )
        ).scalars().all()
    )
    excluded_ids = active_ids | show_ids

    all_fighters = session.execute(select(Fighter)).scalars().all()
    free_agents = [f for f in all_fighters if f.id not in excluded_ids]

    if not free_agents:
        return

    player_prestige = player_org.prestige if player_org else 50.0

    for org in ai_orgs:
        # Max signings: 1 base, 2 if within 15 prestige of player (rival-tier)
        is_rival_tier = abs(org.prestige - player_prestige) <= 15
        max_signings = 2 if is_rival_tier else 1
        signed = 0

        # Min overall filter based on org prestige
        min_ovr = max(45, int(org.prestige * 0.55))

        # Count roster by weight class for thin-class logic
        org_contracts = session.execute(
            select(Contract.fighter_id).where(
                Contract.organization_id == org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalars().all()
        org_fighter_ids = set(org_contracts)
        wc_counts: dict[str, int] = {}
        for f in all_fighters:
            if f.id in org_fighter_ids:
                wc = f.weight_class.value if hasattr(f.weight_class, "value") else str(f.weight_class)
                wc_counts[wc] = wc_counts.get(wc, 0) + 1

        candidates = [f for f in free_agents if f.overall >= min_ovr]
        rng.shuffle(candidates)

        for fighter in candidates:
            if signed >= max_signings:
                break

            # Prefer thin weight classes — 70% skip for non-thin
            wc = fighter.weight_class.value if hasattr(fighter.weight_class, "value") else str(fighter.weight_class)
            if wc_counts.get(wc, 0) >= 4 and rng.random() < 0.70:
                continue

            # Salary offer and acceptance
            asking = fighter.overall * 800 * (1 + (fighter.hype or 10.0) / 200) + (fighter.wins or 0) * 200
            asking = int(round(asking, -2))
            offer_salary = round(asking * rng.uniform(0.8, 1.1), 2)

            # Budget gate: 3x salary in bank
            if org.bank_balance < offer_salary * 3:
                continue

            # Acceptance formula (same as player)
            salary_factor = offer_salary / asking if asking > 0 else 1.0
            prestige_factor = org.prestige / 100
            acceptance_prob = min(0.95, salary_factor * 0.6 + prestige_factor * 0.4)

            if rng.random() < acceptance_prob:
                expiry = sim_date + timedelta(days=365)
                contract = Contract(
                    fighter_id=fighter.id,
                    organization_id=org.id,
                    status=ContractStatus.ACTIVE,
                    salary=offer_salary,
                    fight_count_total=4,
                    fights_remaining=4,
                    expiry_date=expiry,
                )
                session.add(contract)
                active_ids.add(fighter.id)
                signed += 1

                # Notify player for high-overall signings
                if player_org and fighter.overall >= 65:
                    session.add(Notification(
                        message=f"{org.name} signed free agent {fighter.name} (OVR {fighter.overall})",
                        type="rival_signed",
                        created_date=sim_date,
                    ))

                # Generate signing headline for notable signings
                signing_hl = generate_signing_headline(fighter, org)
                if signing_hl:
                    session.add(NewsHeadline(
                        headline=signing_hl, category="signing",
                        game_date=sim_date, fighter_id=fighter.id,
                    ))

        # Remove signed fighters from free_agents list for next org
        free_agents = [f for f in free_agents if f.id not in active_ids]


def _ai_poach_expiring(
    session: Session, ai_orgs: list, player_org, sim_date: date, rng: random.Random
) -> None:
    """AI orgs attempt to poach player fighters with expiring contracts."""
    if not player_org:
        return

    cutoff = sim_date + timedelta(days=60)
    expiring = session.execute(
        select(Contract, Fighter)
        .join(Fighter, Contract.fighter_id == Fighter.id)
        .where(
            Contract.organization_id == player_org.id,
            Contract.status == ContractStatus.ACTIVE,
            Contract.expiry_date <= cutoff,
            Contract.expiry_date > sim_date,
        )
    ).all()

    player_prestige = player_org.prestige

    for contract, fighter in expiring:
        if fighter.overall < 62:
            continue

        # Pick one AI org to attempt (weighted by prestige)
        if not ai_orgs:
            break
        weights = [max(1.0, o.prestige) for o in ai_orgs]
        ai_org = rng.choices(ai_orgs, weights=weights, k=1)[0]

        # Poach probability
        prob = 0.15
        if abs(ai_org.prestige - player_prestige) <= 15:
            prob += 0.10
        if fighter.overall >= 75:
            prob += 0.05
        if ai_org.prestige > player_prestige:
            prob += 0.05

        if rng.random() < prob:
            session.add(Notification(
                message=f"{ai_org.name} has made an offer to {fighter.name}. Renew now or risk losing them!",
                type="rival_poach",
                created_date=sim_date,
            ))


def _ai_claim_expired_fighters(
    session: Session, ai_orgs: list, player_org, sim_date: date, rng: random.Random
) -> None:
    """AI orgs pick up fighters whose contracts just expired."""
    # Find fighters with no active contract and overall >= 62
    active_ids = set(
        session.execute(
            select(Contract.fighter_id).where(Contract.status == ContractStatus.ACTIVE)
        ).scalars().all()
    )

    # Exclude show contestants (active or just-completed)
    show_ids = set(
        session.execute(
            select(ShowContestant.fighter_id)
            .join(RealityShow, ShowContestant.show_id == RealityShow.id)
            .where(
                db_or(
                    RealityShow.status == ShowStatus.IN_PROGRESS,
                    db_and(
                        RealityShow.status == ShowStatus.COMPLETED,
                        RealityShow.end_date == sim_date,
                    ),
                )
            )
        ).scalars().all()
    )
    excluded_ids = active_ids | show_ids

    # Find recently expired contracts (expired this cycle)
    recently_expired = session.execute(
        select(Contract, Fighter)
        .join(Fighter, Contract.fighter_id == Fighter.id)
        .where(
            Contract.status == ContractStatus.EXPIRED,
            Contract.expiry_date >= sim_date - timedelta(days=31),
            Contract.expiry_date <= sim_date,
        )
    ).all()

    player_prestige = player_org.prestige if player_org else 50.0

    for contract, fighter in recently_expired:
        if fighter.id in excluded_ids:
            continue
        if fighter.overall < 62:
            continue

        # Org selection weighted by prestige
        if not ai_orgs:
            break
        weights = [max(1.0, o.prestige) for o in ai_orgs]
        ai_org = rng.choices(ai_orgs, weights=weights, k=1)[0]

        # Sign probability
        sign_prob = ai_org.prestige / (ai_org.prestige + player_prestige + 1)

        if rng.random() < sign_prob:
            asking = fighter.overall * 800 * (1 + (fighter.hype or 10.0) / 200) + (fighter.wins or 0) * 200
            offer_salary = round(int(round(asking, -2)) * rng.uniform(0.85, 1.05), 2)

            expiry = sim_date + timedelta(days=365)
            new_contract = Contract(
                fighter_id=fighter.id,
                organization_id=ai_org.id,
                status=ContractStatus.ACTIVE,
                salary=offer_salary,
                fight_count_total=4,
                fights_remaining=4,
                expiry_date=expiry,
            )
            session.add(new_contract)
            active_ids.add(fighter.id)

            # Notify player
            if player_org:
                was_player_fighter = contract.organization_id == player_org.id
                if was_player_fighter or fighter.overall >= 65:
                    session.add(Notification(
                        message=f"{ai_org.name} claimed {fighter.name} (OVR {fighter.overall})",
                        type="rival_signed",
                        created_date=sim_date,
                    ))

            # Generate signing headline for notable signings
            signing_hl = generate_signing_headline(fighter, ai_org)
            if signing_hl:
                session.add(NewsHeadline(
                    headline=signing_hl, category="signing",
                    game_date=sim_date, fighter_id=fighter.id,
                ))


def _fluctuate_ai_prestige(
    session: Session, ai_orgs: list, sim_date: date, rng: random.Random
) -> None:
    """Monthly prestige fluctuation for AI orgs."""
    for org in ai_orgs:
        # Base drift
        delta = rng.uniform(-0.5, 0.5)

        # Activity bonus: +0.3 per event in last 90 days, max +0.9
        recent_cutoff = sim_date - timedelta(days=90)
        recent_events = session.execute(
            select(Event).where(
                Event.organization_id == org.id,
                Event.status == EventStatus.COMPLETED,
                Event.event_date >= recent_cutoff,
            )
        ).scalars().all()
        activity_bonus = min(0.9, len(recent_events) * 0.3)
        delta += activity_bonus

        # Roster quality bonus: avg overall of top 5 fighters
        org_fighter_ids = session.execute(
            select(Contract.fighter_id).where(
                Contract.organization_id == org.id,
                Contract.status == ContractStatus.ACTIVE,
            )
        ).scalars().all()
        if org_fighter_ids:
            org_fighters = session.execute(
                select(Fighter).where(Fighter.id.in_(org_fighter_ids))
            ).scalars().all()
            top5 = sorted(org_fighters, key=lambda f: f.overall, reverse=True)[:5]
            avg_ovr = sum(f.overall for f in top5) / len(top5)
            if avg_ovr >= 75:
                delta += 0.3
            elif avg_ovr >= 65:
                delta += 0.1

        # Mean reversion
        if org.prestige > 95:
            delta -= 0.5
        elif org.prestige < 40:
            delta += 0.3

        org.prestige = max(20.0, min(99.0, org.prestige + delta))


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
        # Confidence decay toward 70 (baseline)
        conf = getattr(fighter, "confidence", 70.0) or 70.0
        if conf > 70:
            fighter.confidence = max(70.0, conf - 2.0)
        elif conf < 70:
            fighter.confidence = min(70.0, conf + 2.0)
        summary["fighters_aged"] += 1

    if progress_callback:
        progress_callback(f"Aged {summary['fighters_aged']} fighters")

    # 1b. Fighter development (player org only)
    if player_org:
        from api.services import process_fighter_development
        dev_notifications = process_fighter_development(session, player_org.id, sim_date)
        for msg in dev_notifications:
            session.add(Notification(
                message=msg,
                type="development",
                created_date=sim_date,
            ))

    # 1c. Process broadcast deals (player org only)
    if player_org:
        broadcast_notifications = _process_broadcast_deals(session, sim_date, player_org)
        for msg in broadcast_notifications:
            session.add(Notification(
                message=msg,
                type="broadcast",
                created_date=sim_date,
            ))

    # 1d. Process sponsorships (player org only)
    if player_org:
        sponsorship_notifications = _process_sponsorships(session, sim_date, player_org)
        for msg in sponsorship_notifications:
            session.add(Notification(
                message=msg,
                type="sponsorship",
                created_date=sim_date,
            ))

    # 1e. Process reality show episode (player org only)
    if player_org:
        show_notifications = _process_reality_show(session, sim_date, player_org, rng)
        for msg in show_notifications:
            session.add(Notification(
                message=msg,
                type="show",
                created_date=sim_date,
            ))

    # 2. Recover injuries
    _recover_injuries(session)

    # 3. Process contracts
    before_count = summary["contracts_expired"]
    _process_contracts(session, sim_date, rng)

    # Query AI orgs early (used by multiple steps)
    ai_orgs = (
        session.execute(
            select(Organization).where(Organization.is_player == False)
        )
        .scalars()
        .all()
    )

    # 3a. AI poach expiring player fighters
    _ai_poach_expiring(session, ai_orgs, player_org, sim_date, rng)

    # 3b. AI claim expired fighters
    _ai_claim_expired_fighters(session, ai_orgs, player_org, sim_date, rng)

    # 3c. Decay hype before events (fights will restore it via apply_fight_tags)
    decay_hype(session, rng)

    # 4. AI sign free agents
    _ai_sign_free_agents(session, ai_orgs, sim_date, rng, player_org)

    # 4b. AI organizations generate events (roughly 1-in-3 chance per org per month)
    for org in ai_orgs:
        if rng.random() < 0.4:
            _generate_ai_event(session, org, sim_date, rng)
            summary["events_simulated"] += 1

    # 4c. AI prestige fluctuation
    _fluctuate_ai_prestige(session, ai_orgs, sim_date, rng)

    # 5. Post-event narrative updates
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
