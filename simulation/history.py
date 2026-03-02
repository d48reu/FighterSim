"""Fight history fabrication for FighterSim.

Generates 2-3 years of pre-game fight history as real Fight+Event database rows.
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
    Fighter, Organization, Contract, Event, Fight,
    WeightClass, FightMethod, FighterStyle, EventStatus, ContractStatus,
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
        1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
        6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
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

    templates = HISTORY_NARRATIVE_TEMPLATES.get(key, HISTORY_NARRATIVE_TEMPLATES.get((method_val, "standard"), [
        "{winner} defeated {loser}."
    ]))

    template = py_rng.choice(templates)

    # Get division name from winner's weight class
    division = winner.weight_class.value if hasattr(winner.weight_class, "value") else str(winner.weight_class)

    narrative = template.format(
        winner=winner.name,
        loser=loser.name,
        round=round_ended,
        round_word=_round_word(round_ended),
        division=division,
        defense_ordinal=_ordinal(defense_count) if defense_count > 0 else "first",
    )

    # Apply style modifier if winner won outside their primary style
    winner_style = winner.style.value if hasattr(winner.style, "value") else str(winner.style)
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
    "Striker":      {"KO/TKO": 45, "Submission": 10, "Unanimous Decision": 25, "Split Decision": 12, "Majority Decision": 8},
    "Grappler":     {"KO/TKO": 10, "Submission": 45, "Unanimous Decision": 25, "Split Decision": 12, "Majority Decision": 8},
    "Wrestler":     {"KO/TKO": 15, "Submission": 15, "Unanimous Decision": 40, "Split Decision": 18, "Majority Decision": 12},
    "Well-Rounded": {"KO/TKO": 25, "Submission": 20, "Unanimous Decision": 30, "Split Decision": 15, "Majority Decision": 10},
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
    method_weights = _STYLE_METHOD_WEIGHTS.get(style, _STYLE_METHOD_WEIGHTS["Well-Rounded"])

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
