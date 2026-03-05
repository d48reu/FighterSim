"""Fight history fabrication for FighterSim.

Generates 5 years of pre-game fight history (2021-2025) as real Fight+Event database rows.
Transforms bare W/L/D numbers from seed pipeline into actual fight records with
narratives, champions, and rivalries.

ZERO Flask dependencies -- this module is decoupled for testing and desktop packaging.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.models import (
    Fighter,
    Organization,
    Contract,
    Event,
    Fight,
    WeightClass,
    FightMethod,
    EventStatus,
    ContractStatus,
)


# ---------------------------------------------------------------------------
# Round word and ordinal helpers
# ---------------------------------------------------------------------------


def _round_word(n: int) -> str:
    """Convert round number to word: 1 -> 'first', 2 -> 'second', 3 -> 'third'."""
    words = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}
    return words.get(n, f"{n}th")


def _ordinal(n: int) -> str:
    """Convert integer to ordinal word: 1 -> 'first', 2 -> 'second', etc."""
    words = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
    }
    if n in words:
        return words[n]
    # Fallback for larger numbers
    suffix = "th"
    if n % 10 == 1 and n % 100 != 11:
        suffix = "st"
    elif n % 10 == 2 and n % 100 != 12:
        suffix = "nd"
    elif n % 10 == 3 and n % 100 != 13:
        suffix = "rd"
    return f"{n}{suffix}"


# ---------------------------------------------------------------------------
# Narrative template pools
# ---------------------------------------------------------------------------

# Dict keyed by (FightMethod_value, context_str) -> list of template strings
# Contexts: "title", "rivalry", "upset", "prospect_debut", "standard"
# Variables: {winner}, {loser}, {round}, {round_word}, {division}, {defense_ordinal}

HISTORY_NARRATIVE_TEMPLATES: dict[tuple[str, str], list[str]] = {
    # ----- KO/TKO -----
    ("KO/TKO", "title"): [
        "{winner} captured the {division} crown with a devastating knockout in the {round_word} round.",
        "{winner} defended the belt for the {defense_ordinal} time, stopping {loser} in the {round_word} round.",
        "{winner} claimed the {division} title with a thunderous stoppage of {loser} in round {round}.",
    ],
    ("KO/TKO", "rivalry"): [
        "{winner} settled the score with a thunderous knockout of {loser} in the {round_word} round.",
        "{winner} avenged a previous loss, finishing {loser} emphatically in round {round}.",
        "{winner} ended the rivalry with a knockout of {loser} in the {round_word} round.",
    ],
    ("KO/TKO", "upset"): [
        "In a shocking upset, {winner} stunned {loser} with a knockout in the {round_word} round.",
        "The underdog {winner} pulled off a sensational stoppage of {loser} in round {round}.",
        "Nobody saw it coming as {winner} knocked out {loser} in the {round_word} round.",
    ],
    ("KO/TKO", "prospect_debut"): [
        "{winner} earned a debut victory with a stoppage in the {round_word} round.",
        "{winner} made a successful debut, stopping {loser} in round {round}.",
        "A promising start for {winner}, who finished {loser} in the {round_word} round.",
    ],
    ("KO/TKO", "standard"): [
        "{winner} put {loser} away in the {round_word} round.",
        "{winner} finished {loser} with strikes in round {round}.",
        "{winner} dropped {loser} and earned the stoppage in the {round_word} round.",
    ],
    # ----- Submission -----
    ("Submission", "title"): [
        "{winner} captured the {division} crown with a submission of {loser} in the {round_word} round.",
        "{winner} defended the belt for the {defense_ordinal} time, submitting {loser} in round {round}.",
        "{winner} locked in the finish to claim the {division} title in the {round_word} round.",
    ],
    ("Submission", "rivalry"): [
        "{winner} submitted {loser} in their rematch, getting the tap in the {round_word} round.",
        "{winner} avenged a previous loss by submitting {loser} in round {round}.",
        "{winner} proved the superior grappler, submitting {loser} in the {round_word} round of their rematch.",
    ],
    ("Submission", "upset"): [
        "In a stunning upset, {winner} submitted {loser} in the {round_word} round.",
        "The underdog {winner} caught {loser} in a submission in round {round}.",
        "Against all odds, {winner} locked in a submission on {loser} in the {round_word} round.",
    ],
    ("Submission", "prospect_debut"): [
        "{winner} earned a debut submission victory in the {round_word} round.",
        "{winner} showed slick ground skills on debut, tapping {loser} in round {round}.",
        "A confident debut for {winner}, who submitted {loser} in the {round_word} round.",
    ],
    ("Submission", "standard"): [
        "{winner} submitted {loser} in the {round_word} round.",
        "{winner} forced {loser} to tap in round {round}.",
        "{winner} locked in the submission on {loser} in the {round_word} round.",
    ],
    # ----- Unanimous Decision -----
    ("Unanimous Decision", "title"): [
        "{winner} claimed the {division} title by unanimous decision over {loser} after three dominant rounds.",
        "{winner} defended the belt for the {defense_ordinal} time, outpointing {loser} across three rounds.",
        "{winner} earned the {division} crown with a commanding unanimous decision over {loser}.",
    ],
    ("Unanimous Decision", "rivalry"): [
        "{winner} edged {loser} in a closely contested unanimous decision in their rematch.",
        "{winner} avenged a previous loss with a clear unanimous decision over {loser}.",
        "{winner} settled the score, outpointing {loser} across three rounds on all scorecards.",
    ],
    ("Unanimous Decision", "upset"): [
        "In a surprising result, {winner} outpointed {loser} for a unanimous decision victory.",
        "The underdog {winner} dominated the scorecards against {loser} for a unanimous decision upset.",
        "Few expected it, but {winner} earned a clear unanimous decision over {loser}.",
    ],
    ("Unanimous Decision", "prospect_debut"): [
        "{winner} earned a debut victory by unanimous decision over {loser}.",
        "{winner} showed composure in a debut win, taking a unanimous decision over {loser}.",
        "A solid debut for {winner}, who outpointed {loser} on all scorecards.",
    ],
    ("Unanimous Decision", "standard"): [
        "{winner} outpointed {loser} across three rounds for a unanimous decision.",
        "{winner} dominated on the scorecards, earning a unanimous decision over {loser}.",
        "{winner} controlled the action for a clear unanimous decision over {loser}.",
    ],
    # ----- Split Decision -----
    ("Split Decision", "title"): [
        "{winner} claimed the {division} title in a razor-close split decision over {loser}.",
        "{winner} defended the belt for the {defense_ordinal} time, edging {loser} in a split decision.",
        "{winner} earned the {division} crown by the narrowest of margins in a split decision.",
    ],
    ("Split Decision", "rivalry"): [
        "{winner} edged {loser} in a controversial split decision in their rematch.",
        "{winner} survived a back-and-forth war to take a split decision over {loser}.",
        "In a fight that could have gone either way, {winner} took the split decision over {loser}.",
    ],
    ("Split Decision", "upset"): [
        "In a shocking split decision, {winner} upset {loser} in a closely contested fight.",
        "The underdog {winner} pulled off a narrow split decision upset over {loser}.",
        "Against the odds, {winner} earned a split decision over the favored {loser}.",
    ],
    ("Split Decision", "prospect_debut"): [
        "{winner} survived a tough debut, winning a split decision over {loser}.",
        "{winner} showed grit in a debut split decision victory over {loser}.",
        "A hard-fought debut for {winner}, who took a split decision over {loser}.",
    ],
    ("Split Decision", "standard"): [
        "{winner} survived a late scare to win a split decision over {loser}.",
        "{winner} edged {loser} in a competitive split decision.",
        "{winner} took a hard-fought split decision over {loser} after three rounds.",
    ],
    # ----- Majority Decision -----
    ("Majority Decision", "title"): [
        "{winner} claimed the {division} title by majority decision over {loser}.",
        "{winner} defended the belt for the {defense_ordinal} time via majority decision over {loser}.",
        "{winner} earned the {division} crown by majority decision in a grueling contest with {loser}.",
    ],
    ("Majority Decision", "rivalry"): [
        "{winner} took a majority decision over {loser} in an intense rematch.",
        "{winner} edged {loser} by majority decision in a closely fought rivalry bout.",
        "The judges narrowly favored {winner} in a majority decision over {loser} in their rematch.",
    ],
    ("Majority Decision", "upset"): [
        "In a mild upset, {winner} took a majority decision over {loser}.",
        "The underdog {winner} surprised the judges, earning a majority decision over {loser}.",
        "{winner} earned a surprising majority decision victory over the favored {loser}.",
    ],
    ("Majority Decision", "prospect_debut"): [
        "{winner} earned a debut victory via majority decision over {loser}.",
        "{winner} showed enough in a debut majority decision win over {loser}.",
        "A grinding debut for {winner}, who took a majority decision over {loser}.",
    ],
    ("Majority Decision", "standard"): [
        "{winner} took a majority decision over {loser} after three rounds.",
        "{winner} earned a gritty majority decision over {loser}.",
        "Two judges favored {winner} in a majority decision over {loser}.",
    ],
}


# ---------------------------------------------------------------------------
# Style-aware narrative modifiers
# ---------------------------------------------------------------------------

# Applied when a fighter wins OUTSIDE their primary style.
# Keyed by (FighterStyle_value, FightMethod_value).

STYLE_NARRATIVE_MODIFIERS: dict[tuple[str, str], list[str]] = {
    ("Grappler", "KO/TKO"): [
        "In a shocking display of power, ",
        "Surprising everyone with striking prowess, ",
        "Showing unexpected knockout power, ",
    ],
    ("Striker", "Submission"): [
        "Showing unexpected ground skills, ",
        "In a surprising submission finish, ",
        "Catching everyone off guard with grappling, ",
    ],
    ("Wrestler", "KO/TKO"): [
        "Trading the takedowns for fists, ",
        "Showing a new dimension to the game, ",
        "Demonstrating improved striking, ",
    ],
    # Wrestler winning by submission is normal (wrestlers submit people)
    # Well-Rounded has no mismatches by definition
}


# ---------------------------------------------------------------------------
# Narrative generator
# ---------------------------------------------------------------------------


def _generate_narrative(
    winner: Fighter,
    loser: Fighter,
    method: FightMethod,
    round_ended: int,
    context: str,
    defense_count: int,
    py_rng: random.Random,
) -> str:
    """Generate a one-line narrative for a fabricated fight.

    Args:
        winner: The winning Fighter object.
        loser: The losing Fighter object.
        method: The FightMethod enum value.
        round_ended: The round in which the fight ended.
        context: One of "title", "rivalry", "upset", "prospect_debut", "standard".
        defense_count: Number of title defenses (used for title context).
        py_rng: Deterministic RNG instance.

    Returns:
        A one-line narrative string.
    """
    method_val = method.value if hasattr(method, "value") else str(method)
    key = (method_val, context)

    templates = HISTORY_NARRATIVE_TEMPLATES.get(
        key,
        HISTORY_NARRATIVE_TEMPLATES.get(
            (method_val, "standard"), ["{winner} defeated {loser}."]
        ),
    )

    template = py_rng.choice(templates)

    # Get division name from winner's weight class
    division = (
        winner.weight_class.value
        if hasattr(winner.weight_class, "value")
        else str(winner.weight_class)
    )

    narrative = template.format(
        winner=winner.name,
        loser=loser.name,
        round=round_ended,
        round_word=_round_word(round_ended),
        division=division,
        defense_ordinal=_ordinal(defense_count) if defense_count > 0 else "first",
    )

    # Apply style modifier if winner won outside their primary style
    winner_style = (
        winner.style.value if hasattr(winner.style, "value") else str(winner.style)
    )
    modifier_key = (winner_style, method_val)
    if modifier_key in STYLE_NARRATIVE_MODIFIERS:
        modifier = py_rng.choice(STYLE_NARRATIVE_MODIFIERS[modifier_key])
        narrative = modifier + narrative[0].lower() + narrative[1:]

    return narrative


# ---------------------------------------------------------------------------
# Fast fight outcome resolver
# ---------------------------------------------------------------------------

# Method distribution weights by winner's FighterStyle
_STYLE_METHOD_WEIGHTS: dict[str, dict[str, int]] = {
    "Striker": {
        "KO/TKO": 45,
        "Submission": 10,
        "Unanimous Decision": 25,
        "Split Decision": 12,
        "Majority Decision": 8,
    },
    "Grappler": {
        "KO/TKO": 10,
        "Submission": 45,
        "Unanimous Decision": 25,
        "Split Decision": 12,
        "Majority Decision": 8,
    },
    "Wrestler": {
        "KO/TKO": 15,
        "Submission": 15,
        "Unanimous Decision": 40,
        "Split Decision": 18,
        "Majority Decision": 12,
    },
    "Well-Rounded": {
        "KO/TKO": 25,
        "Submission": 20,
        "Unanimous Decision": 30,
        "Split Decision": 15,
        "Majority Decision": 10,
    },
}

# Round weights for finishes (KO/Submission)
_FINISH_ROUND_WEIGHTS = [35, 40, 25]  # rounds 1, 2, 3


def _resolve_fight_outcome(
    fighter_a: Fighter,
    fighter_b: Fighter,
    winner_id: int,
    py_rng: random.Random,
) -> dict:
    """Return {method: FightMethod, round_ended: int} for a predetermined winner.

    Method distribution is weighted by the winner's FighterStyle.
    Finishes (KO/Sub) are weighted across rounds 1-3.
    Decisions always go the distance (round 3).
    """
    winner = fighter_a if winner_id == fighter_a.id else fighter_b

    # Get style string
    style = winner.style.value if hasattr(winner.style, "value") else str(winner.style)
    method_weights = _STYLE_METHOD_WEIGHTS.get(
        style, _STYLE_METHOD_WEIGHTS["Well-Rounded"]
    )

    # Pick method
    methods = list(method_weights.keys())
    weights = list(method_weights.values())
    method_str = py_rng.choices(methods, weights=weights, k=1)[0]

    # Convert to FightMethod enum
    method = FightMethod(method_str)

    # Determine round
    if method_str in ("KO/TKO", "Submission"):
        round_ended = py_rng.choices([1, 2, 3], weights=_FINISH_ROUND_WEIGHTS, k=1)[0]
    else:
        round_ended = 3  # decisions always go the distance

    return {"method": method, "round_ended": round_ended}


def _resolve_draw_outcome(py_rng: random.Random) -> dict:
    """Return outcome for a draw: majority draw, round 3."""
    return {"method": FightMethod.MAJORITY_DECISION, "round_ended": 3, "is_draw": True}


# ---------------------------------------------------------------------------
# Venue pool (decoupled from monthly_sim)
# ---------------------------------------------------------------------------

_HISTORY_VENUES = [
    "Madison Square Garden",
    "T-Mobile Arena",
    "Barclays Center",
    "United Center",
    "Crypto.com Arena",
    "Chase Center",
    "Rogers Centre",
    "O2 Arena",
    "Melbourne Arena",
    "Toyota Center",
    "Scotiabank Arena",
    "Saitama Super Arena",
    "Singapore Indoor Stadium",
    "Axiata Arena",
]


# ---------------------------------------------------------------------------
# Event timeline builder
# ---------------------------------------------------------------------------


def _build_event_timeline(
    orgs: list[Organization],
    start_date: date,
    end_date: date,
    py_rng: random.Random,
) -> list[tuple[date, Organization]]:
    """Generate chronological event schedule for all orgs.

    Each org gets an event every ~2 weeks (10-18 day gaps).
    Returns list of (event_date, org) tuples sorted by date.
    """
    timeline: list[tuple[date, Organization]] = []

    for org in orgs:
        # Stagger start dates: random 0-14 day offset per org
        current = start_date + timedelta(days=py_rng.randint(0, 14))
        while current < end_date:
            timeline.append((current, org))
            gap_days = py_rng.randint(10, 18)  # ~2 weeks per org
            current += timedelta(days=gap_days)

    timeline.sort(key=lambda t: t[0])
    return timeline


# ---------------------------------------------------------------------------
# Rivalry pair pre-generation
# ---------------------------------------------------------------------------


def _generate_rivalry_pairs(
    fighters_by_org_wc: dict[tuple[int, str], list[Fighter]],
    py_rng: random.Random,
) -> dict[str, list[tuple[int, int]]]:
    """Pre-generate 2-3 rival pairs per weight class.

    For each weight class, picks pairs of fighters from the same org who will
    be deliberately rematched to trigger update_rivalries() detection.
    At least one rivalry per weight class involves a high-overall fighter.

    Returns dict keyed by weight_class value -> list of (fighter_a_id, fighter_b_id).
    """
    rivalry_pairs: dict[str, list[tuple[int, int]]] = {}
    used_fighters: set[int] = set()

    # Collect all fighters per weight class across all orgs
    fighters_by_wc: dict[str, list[tuple[int, Fighter]]] = defaultdict(list)
    for (org_id, wc_val), roster in fighters_by_org_wc.items():
        for f in roster:
            fighters_by_wc[wc_val].append((org_id, f))

    for wc in WeightClass:
        wc_val = wc.value
        wc_fighters = fighters_by_wc.get(wc_val, [])
        if len(wc_fighters) < 4:
            continue

        pairs: list[tuple[int, int]] = []
        num_pairs = py_rng.randint(2, 3)

        # Sort by overall descending to ensure first pair includes a top fighter
        sorted_fighters = sorted(wc_fighters, key=lambda x: x[1].overall, reverse=True)

        # Group by org for same-org pairing
        org_groups: dict[int, list[Fighter]] = defaultdict(list)
        for org_id, f in sorted_fighters:
            org_groups[org_id].append(f)

        for org_id, roster in org_groups.items():
            if len(pairs) >= num_pairs:
                break
            available = [f for f in roster if f.id not in used_fighters]
            if len(available) < 2:
                continue

            # First pair: top fighter vs second available (marquee rivalry)
            if not pairs:
                f_a = available[0]
                f_b = available[1]
            else:
                # Subsequent pairs: random pairing
                pair_picks = py_rng.sample(available, min(2, len(available)))
                if len(pair_picks) < 2:
                    continue
                f_a, f_b = pair_picks[0], pair_picks[1]

            pairs.append((f_a.id, f_b.id))
            used_fighters.add(f_a.id)
            used_fighters.add(f_b.id)

        # If we need more pairs from other orgs
        for org_id, roster in org_groups.items():
            if len(pairs) >= num_pairs:
                break
            available = [f for f in roster if f.id not in used_fighters]
            if len(available) < 2:
                continue
            pair_picks = py_rng.sample(available, 2)
            pairs.append((pair_picks[0].id, pair_picks[1].id))
            used_fighters.add(pair_picks[0].id)
            used_fighters.add(pair_picks[1].id)

        rivalry_pairs[wc_val] = pairs

    return rivalry_pairs


# ---------------------------------------------------------------------------
# Matchmaker
# ---------------------------------------------------------------------------


def _matchmake_card(
    org: Organization,
    fighters_by_wc: dict[str, list[Fighter]],
    remaining_fights: dict[int, int],
    remaining_wins: dict[int, int],
    remaining_losses: dict[int, int],
    remaining_draws: dict[int, int],
    matchup_history: dict[tuple[int, int], int],
    champion_state: dict[tuple[int, str], dict],
    rivalry_pairs: dict[str, list[tuple[int, int]]],
    rivalry_booked: dict[tuple[int, int], int],
    event_num: int,
    fighter_lookup: dict[int, Fighter],
    py_rng: random.Random,
) -> list[dict]:
    """Produce 8-12 fight specs for one event card.

    Each fight spec: {fighter_a_id, fighter_b_id, weight_class, is_title_fight,
                      card_position, winner_id, is_draw, is_rivalry}

    Handles title fight scheduling, rivalry rebooking, and record matching.
    """
    card: list[dict] = []
    booked_this_event: set[int] = set()
    target_fights = py_rng.randint(8, 12)

    # Get org's roster: only fighters with remaining fights in THIS org
    org_roster_by_wc: dict[str, list[Fighter]] = defaultdict(list)
    for wc_val, fighters in fighters_by_wc.items():
        for f in fighters:
            if remaining_fights.get(f.id, 0) > 0:
                org_roster_by_wc[wc_val].append(f)

    # Determine if this event should have a title fight
    # Schedule title fight every 4-6 events per org
    schedule_title = False
    if event_num >= 3:  # No titles in first 2 events
        # Check if it's time for a title fight
        title_interval = py_rng.randint(4, 6)
        if event_num % title_interval == 0 or event_num == 3:
            schedule_title = True

    # --- Title fight ---
    if schedule_title:
        # Pick a weight class that can support a title fight
        wc_candidates = []
        for wc in WeightClass:
            wc_val = wc.value
            available = [
                f
                for f in org_roster_by_wc.get(wc_val, [])
                if f.id not in booked_this_event
            ]
            if len(available) >= 2:
                wc_candidates.append((wc_val, available))

        if wc_candidates:
            wc_val, available = py_rng.choice(wc_candidates)
            key = (org.id, wc_val)
            champ_info = champion_state.get(key)

            if champ_info is not None:
                # Defense: champion vs challenger
                champ_id = champ_info["champion_id"]
                champ = fighter_lookup.get(champ_id)
                if (
                    champ
                    and remaining_fights.get(champ_id, 0) > 0
                    and champ_id not in booked_this_event
                ):
                    challengers = [f for f in available if f.id != champ_id]
                    if challengers:
                        # Pick top challenger by overall
                        challengers.sort(key=lambda f: f.overall, reverse=True)
                        challenger = challengers[0]
                        winner_id, is_draw = _determine_winner(
                            champ,
                            challenger,
                            remaining_wins,
                            remaining_losses,
                            remaining_draws,
                            py_rng,
                        )
                        card.append(
                            {
                                "fighter_a_id": champ.id,
                                "fighter_b_id": challenger.id,
                                "weight_class": wc_val,
                                "is_title_fight": True,
                                "card_position": target_fights,  # main event
                                "winner_id": winner_id,
                                "is_draw": is_draw,
                                "is_rivalry": False,
                            }
                        )
                        booked_this_event.add(champ.id)
                        booked_this_event.add(challenger.id)
                        _decrement_records(
                            champ.id,
                            challenger.id,
                            winner_id,
                            is_draw,
                            remaining_fights,
                            remaining_wins,
                            remaining_losses,
                            remaining_draws,
                        )
                        pair_key = (
                            min(champ.id, challenger.id),
                            max(champ.id, challenger.id),
                        )
                        matchup_history[pair_key] = matchup_history.get(pair_key, 0) + 1
            else:
                # Inaugural title fight: pick top 2 fighters
                available_sorted = sorted(
                    available, key=lambda f: f.overall, reverse=True
                )
                if len(available_sorted) >= 2:
                    f_a = available_sorted[0]
                    f_b = available_sorted[1]
                    winner_id, is_draw = _determine_winner(
                        f_a,
                        f_b,
                        remaining_wins,
                        remaining_losses,
                        remaining_draws,
                        py_rng,
                    )
                    # Inaugural title fight should not be a draw
                    if is_draw:
                        # Force a winner for inaugural
                        if remaining_wins.get(f_a.id, 0) > 0:
                            winner_id = f_a.id
                            is_draw = False
                        elif remaining_wins.get(f_b.id, 0) > 0:
                            winner_id = f_b.id
                            is_draw = False
                    card.append(
                        {
                            "fighter_a_id": f_a.id,
                            "fighter_b_id": f_b.id,
                            "weight_class": wc_val,
                            "is_title_fight": True,
                            "card_position": target_fights,
                            "winner_id": winner_id,
                            "is_draw": is_draw,
                            "is_rivalry": False,
                        }
                    )
                    booked_this_event.add(f_a.id)
                    booked_this_event.add(f_b.id)
                    _decrement_records(
                        f_a.id,
                        f_b.id,
                        winner_id,
                        is_draw,
                        remaining_fights,
                        remaining_wins,
                        remaining_losses,
                        remaining_draws,
                    )
                    pair_key = (min(f_a.id, f_b.id), max(f_a.id, f_b.id))
                    matchup_history[pair_key] = matchup_history.get(pair_key, 0) + 1

    # --- Rivalry rematches ---
    for wc_val, pairs in rivalry_pairs.items():
        if len(card) >= target_fights:
            break
        for pair in pairs:
            if len(card) >= target_fights:
                break
            a_id, b_id = pair
            pair_key = (min(a_id, b_id), max(a_id, b_id))
            # Only book rivalry if we haven't met the 2-fight minimum yet
            if rivalry_booked.get(pair_key, 0) >= 3:
                continue
            # Check both fighters are available for this org
            a_fighter = fighter_lookup.get(a_id)
            b_fighter = fighter_lookup.get(b_id)
            if not a_fighter or not b_fighter:
                continue
            if a_id in booked_this_event or b_id in booked_this_event:
                continue
            if remaining_fights.get(a_id, 0) <= 0 or remaining_fights.get(b_id, 0) <= 0:
                continue
            # Check they belong to this org's roster
            a_in_roster = any(f.id == a_id for f in org_roster_by_wc.get(wc_val, []))
            b_in_roster = any(f.id == b_id for f in org_roster_by_wc.get(wc_val, []))
            if not a_in_roster or not b_in_roster:
                continue

            winner_id, is_draw = _determine_winner(
                a_fighter,
                b_fighter,
                remaining_wins,
                remaining_losses,
                remaining_draws,
                py_rng,
            )
            is_rivalry = rivalry_booked.get(pair_key, 0) >= 1  # 2nd+ fight is a rematch
            card.append(
                {
                    "fighter_a_id": a_id,
                    "fighter_b_id": b_id,
                    "weight_class": wc_val,
                    "is_title_fight": False,
                    "card_position": len(card),
                    "winner_id": winner_id,
                    "is_draw": is_draw,
                    "is_rivalry": is_rivalry,
                }
            )
            booked_this_event.add(a_id)
            booked_this_event.add(b_id)
            _decrement_records(
                a_id,
                b_id,
                winner_id,
                is_draw,
                remaining_fights,
                remaining_wins,
                remaining_losses,
                remaining_draws,
            )
            rivalry_booked[pair_key] = rivalry_booked.get(pair_key, 0) + 1
            matchup_history[pair_key] = matchup_history.get(pair_key, 0) + 1

    # --- Fill remaining card slots ---
    wc_list = list(WeightClass)
    py_rng.shuffle(wc_list)

    for wc in wc_list:
        if len(card) >= target_fights:
            break
        wc_val = wc.value
        available = [
            f
            for f in org_roster_by_wc.get(wc_val, [])
            if f.id not in booked_this_event and remaining_fights.get(f.id, 0) > 0
        ]
        # Sort by remaining fight budget (descending), with deterministic
        # tiebreaker by id. This ensures high-budget veterans get booked first.
        available.sort(key=lambda f: (-remaining_fights.get(f.id, 0), f.id))

        matched: set[int] = set()
        for idx_a, f_a in enumerate(available):
            if len(card) >= target_fights:
                break
            if f_a.id in matched:
                continue
            # Scan for best valid opponent (first unmatched, under rematch cap)
            for idx_b in range(idx_a + 1, len(available)):
                f_b = available[idx_b]
                if f_b.id in matched:
                    continue
                pair_key = (min(f_a.id, f_b.id), max(f_a.id, f_b.id))
                if matchup_history.get(pair_key, 0) >= 3:
                    continue  # Try next opponent instead of giving up

                winner_id, is_draw = _determine_winner(
                    f_a, f_b, remaining_wins, remaining_losses, remaining_draws, py_rng
                )
                card.append(
                    {
                        "fighter_a_id": f_a.id,
                        "fighter_b_id": f_b.id,
                        "weight_class": wc_val,
                        "is_title_fight": False,
                        "card_position": len(card),
                        "winner_id": winner_id,
                        "is_draw": is_draw,
                        "is_rivalry": False,
                    }
                )
                booked_this_event.add(f_a.id)
                booked_this_event.add(f_b.id)
                matched.add(f_a.id)
                matched.add(f_b.id)
                _decrement_records(
                    f_a.id,
                    f_b.id,
                    winner_id,
                    is_draw,
                    remaining_fights,
                    remaining_wins,
                    remaining_losses,
                    remaining_draws,
                )
                matchup_history[pair_key] = matchup_history.get(pair_key, 0) + 1
                break  # f_a is matched, move to next fighter

    # Fix card positions: title fight = highest, rest ordered
    non_title = [f for f in card if not f["is_title_fight"]]
    title = [f for f in card if f["is_title_fight"]]
    for idx, fight in enumerate(non_title):
        fight["card_position"] = idx
    for fight in title:
        fight["card_position"] = len(card) - 1

    return card


def _determine_winner(
    f_a: Fighter,
    f_b: Fighter,
    remaining_wins: dict[int, int],
    remaining_losses: dict[int, int],
    remaining_draws: dict[int, int],
    py_rng: random.Random,
) -> tuple[Optional[int], bool]:
    """Determine the winner of a fight to match target records.

    Returns (winner_id, is_draw). If is_draw is True, winner_id is None.
    """
    a_can_win = (
        remaining_wins.get(f_a.id, 0) > 0 and remaining_losses.get(f_b.id, 0) > 0
    )
    b_can_win = (
        remaining_wins.get(f_b.id, 0) > 0 and remaining_losses.get(f_a.id, 0) > 0
    )
    can_draw = remaining_draws.get(f_a.id, 0) > 0 and remaining_draws.get(f_b.id, 0) > 0

    if a_can_win and b_can_win:
        # Both can win: weight by overall stat
        a_weight = max(f_a.overall, 1)
        b_weight = max(f_b.overall, 1)
        winner = py_rng.choices([f_a.id, f_b.id], weights=[a_weight, b_weight], k=1)[0]
        return winner, False
    elif a_can_win:
        return f_a.id, False
    elif b_can_win:
        return f_b.id, False
    elif can_draw:
        return None, True
    else:
        # Edge case: both fighters have exhausted their record budgets.
        # Fall back to a winner based on overall (this creates a small mismatch).
        if f_a.overall >= f_b.overall:
            return f_a.id, False
        else:
            return f_b.id, False


def _decrement_records(
    a_id: int,
    b_id: int,
    winner_id: Optional[int],
    is_draw: bool,
    remaining_fights: dict[int, int],
    remaining_wins: dict[int, int],
    remaining_losses: dict[int, int],
    remaining_draws: dict[int, int],
) -> None:
    """Decrement remaining record counters after a fight is booked."""
    remaining_fights[a_id] = max(0, remaining_fights.get(a_id, 0) - 1)
    remaining_fights[b_id] = max(0, remaining_fights.get(b_id, 0) - 1)

    if is_draw:
        remaining_draws[a_id] = max(0, remaining_draws.get(a_id, 0) - 1)
        remaining_draws[b_id] = max(0, remaining_draws.get(b_id, 0) - 1)
    elif winner_id == a_id:
        remaining_wins[a_id] = max(0, remaining_wins.get(a_id, 0) - 1)
        remaining_losses[b_id] = max(0, remaining_losses.get(b_id, 0) - 1)
    elif winner_id == b_id:
        remaining_wins[b_id] = max(0, remaining_wins.get(b_id, 0) - 1)
        remaining_losses[a_id] = max(0, remaining_losses.get(a_id, 0) - 1)


# ---------------------------------------------------------------------------
# Champion tracking
# ---------------------------------------------------------------------------


def _update_champion_state(
    fight_spec: dict,
    org_id: int,
    champion_state: dict[tuple[int, str], dict],
    event_id: int,
) -> int:
    """Update champion state based on a title fight result.

    Returns the defense_count for narrative generation.
    """
    if not fight_spec["is_title_fight"]:
        return 0

    wc_val = fight_spec["weight_class"]
    key = (org_id, wc_val)
    winner_id = fight_spec["winner_id"]
    current = champion_state.get(key)

    if fight_spec["is_draw"]:
        # Draw in title fight: champion retains (if there is one)
        if current:
            return current["defense_count"]
        return 0

    if current is None:
        # Inaugural champion
        champion_state[key] = {
            "champion_id": winner_id,
            "defense_count": 0,
            "reign_start_event_id": event_id,
        }
        return 0
    elif winner_id == current["champion_id"]:
        # Successful defense
        current["defense_count"] += 1
        return current["defense_count"]
    else:
        # Title change
        champion_state[key] = {
            "champion_id": winner_id,
            "defense_count": 0,
            "reign_start_event_id": event_id,
        }
        return 0


# ---------------------------------------------------------------------------
# Narrative context determination
# ---------------------------------------------------------------------------


def _determine_narrative_context(
    fight_spec: dict,
    fighter_lookup: dict[int, Fighter],
    fights_completed: dict[int, int],
) -> str:
    """Determine the narrative context for a fight.

    Returns one of: "title", "rivalry", "upset", "prospect_debut", "standard".
    """
    if fight_spec["is_title_fight"]:
        return "title"
    if fight_spec.get("is_rivalry", False):
        return "rivalry"

    winner_id = fight_spec["winner_id"]
    loser_id = (
        fight_spec["fighter_b_id"]
        if winner_id == fight_spec["fighter_a_id"]
        else fight_spec["fighter_a_id"]
    )

    winner = fighter_lookup.get(winner_id)
    loser = fighter_lookup.get(loser_id)

    if winner and loser:
        # Prospect debut: winner has 0-2 completed fights so far
        if fights_completed.get(winner_id, 0) <= 2:
            return "prospect_debut"
        # Upset: winner has significantly lower overall than loser
        if winner.overall < loser.overall - 10:
            return "upset"

    return "standard"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def fabricate_history(
    session: Session,
    fighters: list[Fighter],
    orgs: list[Organization],
    seed: int = 42,
) -> dict:
    """Fabricate 2-3 years of pre-game fight history.

    Creates real Event+Fight database rows matching each fighter's existing
    W/L/D counts. Establishes champions, seeds rivalries, and generates
    one-line narratives for every fight.

    Args:
        session: SQLAlchemy session.
        fighters: List of Fighter objects from seed_fighters().
        orgs: List of Organization objects.
        seed: RNG seed (offset from seed.py to avoid state entanglement).

    Returns:
        Summary dict: {events_created, fights_created, champions, rivalries}
    """
    # Lazy import to avoid circular dependency at module load time
    from simulation.narrative import update_rivalries
    from simulation.rankings import rebuild_rankings

    py_rng = random.Random(seed + 1000)

    # --- Build fighter lookup structures ---
    fighter_lookup: dict[int, Fighter] = {f.id: f for f in fighters}

    # Query contracts to map fighters to orgs
    contracts = (
        session.execute(
            select(Contract).where(Contract.status == ContractStatus.ACTIVE)
        )
        .scalars()
        .all()
    )

    fighter_org_map: dict[int, int] = {}  # fighter_id -> org_id
    for c in contracts:
        fighter_org_map[c.fighter_id] = c.organization_id

    # Build a deterministic historical org map for all fighters. Free agents
    # still need prior bouts, so they get a plausible historical home.
    historical_org_map: dict[int, int] = {}
    weighted_orgs = list(orgs)
    org_weights = [max(1.0, float(o.prestige)) for o in weighted_orgs]
    for f in fighters:
        current_org_id = fighter_org_map.get(f.id)
        if current_org_id is not None:
            historical_org_map[f.id] = current_org_id
        else:
            assigned_org = py_rng.choices(weighted_orgs, weights=org_weights, k=1)[0]
            historical_org_map[f.id] = assigned_org.id

    # Build fighters by org+weight_class using current or historical orgs.
    fighters_by_org_wc: dict[tuple[int, str], list[Fighter]] = defaultdict(list)
    for f in fighters:
        org_id = historical_org_map.get(f.id)
        if org_id is None:
            continue
        wc_val = (
            f.weight_class.value
            if hasattr(f.weight_class, "value")
            else str(f.weight_class)
        )
        fighters_by_org_wc[(org_id, wc_val)].append(f)

    # Sort rosters by id for determinism
    for key in fighters_by_org_wc:
        fighters_by_org_wc[key].sort(key=lambda f: f.id)

    # --- Initialize record budgets ---
    remaining_fights: dict[int, int] = {}
    remaining_wins: dict[int, int] = {}
    remaining_losses: dict[int, int] = {}
    remaining_draws: dict[int, int] = {}

    for f in fighters:
        org_id = historical_org_map.get(f.id)
        if org_id is None:
            continue
        total = f.wins + f.losses + f.draws
        remaining_fights[f.id] = total
        remaining_wins[f.id] = f.wins
        remaining_losses[f.id] = f.losses
        remaining_draws[f.id] = f.draws

    # --- Generate rivalry pairs ---
    rivalry_pairs = _generate_rivalry_pairs(fighters_by_org_wc, py_rng)
    rivalry_booked: dict[tuple[int, int], int] = {}

    # --- Build event timeline ---
    # 5-year history window (2021-2025) for deeper career records
    history_start = date(2021, 1, 1)
    history_end = date(2025, 12, 15)
    timeline = _build_event_timeline(orgs, history_start, history_end, py_rng)

    # --- Tracking state ---
    champion_state: dict[tuple[int, str], dict] = {}
    matchup_history: dict[tuple[int, int], int] = {}
    event_counters: dict[int, int] = defaultdict(int)  # org_id -> event number
    fights_completed: dict[int, int] = defaultdict(
        int
    )  # fighter_id -> fights done so far

    events_created = 0
    fights_created = 0

    # --- Process each event ---
    for event_date, org in timeline:
        event_counters[org.id] += 1
        event_num = event_counters[org.id]

        # Build per-org roster for this event's matchmaking
        org_fighters_by_wc: dict[str, list[Fighter]] = {}
        for wc in WeightClass:
            wc_val = wc.value
            key = (org.id, wc_val)
            if key in fighters_by_org_wc:
                org_fighters_by_wc[wc_val] = fighters_by_org_wc[key]

        # Matchmake card
        card = _matchmake_card(
            org=org,
            fighters_by_wc=org_fighters_by_wc,
            remaining_fights=remaining_fights,
            remaining_wins=remaining_wins,
            remaining_losses=remaining_losses,
            remaining_draws=remaining_draws,
            matchup_history=matchup_history,
            champion_state=champion_state,
            rivalry_pairs=rivalry_pairs,
            rivalry_booked=rivalry_booked,
            event_num=event_num,
            fighter_lookup=fighter_lookup,
            py_rng=py_rng,
        )

        if not card:
            continue  # Skip event if no fights could be made

        # Create Event row
        venue = py_rng.choice(_HISTORY_VENUES)
        event = Event(
            name=f"{org.name} {event_num}",
            event_date=event_date,
            venue=venue,
            organization_id=org.id,
            status=EventStatus.COMPLETED,
            has_press_conference=False,
            gate_revenue=0.0,
            ppv_buys=0,
            broadcast_revenue=0.0,
            venue_rental_cost=0.0,
            tickets_sold=0,
            venue_capacity=0,
        )
        session.add(event)
        session.flush()  # Get event.id

        # --- Resolve each fight on the card ---
        fight_rows: list[Fight] = []
        for fight_spec in card:
            f_a = fighter_lookup[fight_spec["fighter_a_id"]]
            f_b = fighter_lookup[fight_spec["fighter_b_id"]]

            # Update champion state for title fights
            defense_count = _update_champion_state(
                fight_spec, org.id, champion_state, event.id
            )

            if fight_spec["is_draw"]:
                outcome = _resolve_draw_outcome(py_rng)
                winner_id_db = None
            else:
                outcome = _resolve_fight_outcome(
                    f_a, f_b, fight_spec["winner_id"], py_rng
                )
                winner_id_db = fight_spec["winner_id"]

            # Determine narrative context
            context = _determine_narrative_context(
                fight_spec, fighter_lookup, fights_completed
            )

            # Generate narrative
            if fight_spec["is_draw"]:
                wc_display = (
                    f_a.weight_class.value
                    if hasattr(f_a.weight_class, "value")
                    else str(f_a.weight_class)
                )
                narrative = f"{f_a.name} and {f_b.name} fought to a majority draw after three rounds."
            else:
                winner = fighter_lookup[fight_spec["winner_id"]]
                loser_id = (
                    fight_spec["fighter_b_id"]
                    if fight_spec["winner_id"] == fight_spec["fighter_a_id"]
                    else fight_spec["fighter_a_id"]
                )
                loser = fighter_lookup[loser_id]
                narrative = _generate_narrative(
                    winner=winner,
                    loser=loser,
                    method=outcome["method"],
                    round_ended=outcome["round_ended"],
                    context=context,
                    defense_count=defense_count,
                    py_rng=py_rng,
                )

            wc_enum = (
                f_a.weight_class
                if hasattr(f_a.weight_class, "value")
                else WeightClass(f_a.weight_class)
            )

            fight = Fight(
                event_id=event.id,
                fighter_a_id=fight_spec["fighter_a_id"],
                fighter_b_id=fight_spec["fighter_b_id"],
                weight_class=wc_enum,
                card_position=fight_spec["card_position"],
                is_title_fight=fight_spec["is_title_fight"],
                winner_id=winner_id_db,
                method=outcome["method"],
                round_ended=outcome["round_ended"],
                narrative=narrative,
            )
            fight_rows.append(fight)

            # Track completed fights per fighter
            fights_completed[fight_spec["fighter_a_id"]] += 1
            fights_completed[fight_spec["fighter_b_id"]] += 1

        session.add_all(fight_rows)
        session.flush()

        events_created += 1
        fights_created += len(fight_rows)

    # --- Post-fabrication: update rivalries ---
    rivalries = update_rivalries(session)

    # --- Post-fabrication: rebuild rankings ---
    for wc in WeightClass:
        rebuild_rankings(session, wc)

    # --- Reconcile fighter records to match actual Fight rows ---
    # With limited event slots (~60-70 events, ~400 fights), not all of every
    # fighter's original W/L/D budget can be consumed. Update Fighter records
    # to match the actual Fight row counts so data stays consistent.
    mismatches = 0
    all_fights = session.execute(select(Fight)).scalars().all()

    # Pre-compute actual win/loss/draw counts per fighter
    actual_wins_count: dict[int, int] = defaultdict(int)
    actual_losses_count: dict[int, int] = defaultdict(int)
    actual_draws_count: dict[int, int] = defaultdict(int)
    actual_ko_wins: dict[int, int] = defaultdict(int)
    actual_sub_wins: dict[int, int] = defaultdict(int)

    for fight in all_fights:
        if fight.winner_id is None:
            # Draw
            actual_draws_count[fight.fighter_a_id] += 1
            actual_draws_count[fight.fighter_b_id] += 1
        else:
            actual_wins_count[fight.winner_id] += 1
            loser_id = (
                fight.fighter_b_id
                if fight.winner_id == fight.fighter_a_id
                else fight.fighter_a_id
            )
            actual_losses_count[loser_id] += 1
            # Track KO and sub wins
            method_val = (
                fight.method.value
                if hasattr(fight.method, "value")
                else str(fight.method)
            )
            if method_val == "KO/TKO":
                actual_ko_wins[fight.winner_id] += 1
            elif method_val == "Submission":
                actual_sub_wins[fight.winner_id] += 1

    for f in fighters:
        new_wins = actual_wins_count.get(f.id, 0)
        new_losses = actual_losses_count.get(f.id, 0)
        new_draws = actual_draws_count.get(f.id, 0)
        new_ko = actual_ko_wins.get(f.id, 0)
        new_sub = actual_sub_wins.get(f.id, 0)

        if f.wins != new_wins or f.losses != new_losses or f.draws != new_draws:
            mismatches += 1

        f.wins = new_wins
        f.losses = new_losses
        f.draws = new_draws
        f.ko_wins = new_ko
        f.sub_wins = new_sub

    session.commit()

    # --- Build summary ---
    summary = {
        "events_created": events_created,
        "fights_created": fights_created,
        "champions": {f"{k[1]}": v["champion_id"] for k, v in champion_state.items()},
        "rivalries": len(rivalries),
        "records_reconciled": mismatches,
    }

    return summary
