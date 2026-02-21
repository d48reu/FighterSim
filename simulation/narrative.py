"""Narrative engine for FighterSim — tags, bios, GOAT scores, rivalries, hype."""

from __future__ import annotations

import json
import random
from typing import Optional

from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import Session

from models.models import Fighter, Fight, Ranking, WeightClass, Archetype


# ---------------------------------------------------------------------------
# Tag helpers
# ---------------------------------------------------------------------------

def get_tags(fighter: Fighter) -> list[str]:
    if not fighter.narrative_tags:
        return []
    try:
        return json.loads(fighter.narrative_tags)
    except (json.JSONDecodeError, TypeError):
        return []


def add_tag(fighter: Fighter, tag: str) -> None:
    tags = get_tags(fighter)
    if tag not in tags:
        tags.append(tag)
    fighter.narrative_tags = json.dumps(tags)


def remove_tag(fighter: Fighter, tag: str) -> None:
    tags = get_tags(fighter)
    if tag in tags:
        tags.remove(tag)
    fighter.narrative_tags = json.dumps(tags)


def get_traits(fighter: Fighter) -> list[str]:
    if not hasattr(fighter, "traits") or not fighter.traits:
        return []
    try:
        return json.loads(fighter.traits)
    except (json.JSONDecodeError, TypeError):
        return []


# ---------------------------------------------------------------------------
# Fight history helpers
# ---------------------------------------------------------------------------

def _win_streak(fighter_id: int, session: Session) -> int:
    fights = session.execute(
        select(Fight)
        .where(
            or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
            Fight.winner_id.isnot(None),
        )
        .order_by(Fight.id.desc())
    ).scalars().all()
    streak = 0
    for f in fights:
        if f.winner_id == fighter_id:
            streak += 1
        else:
            break
    return streak


def _loss_streak(fighter_id: int, session: Session) -> int:
    fights = session.execute(
        select(Fight)
        .where(
            or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
            Fight.winner_id.isnot(None),
        )
        .order_by(Fight.id.desc())
    ).scalars().all()
    streak = 0
    for f in fights:
        if f.winner_id != fighter_id:
            streak += 1
        else:
            break
    return streak


def _previously_lost_to(winner_id: int, loser_id: int, current_fight_id: int, session: Session) -> bool:
    prior = session.execute(
        select(Fight).where(
            or_(
                and_(Fight.fighter_a_id == winner_id, Fight.fighter_b_id == loser_id),
                and_(Fight.fighter_a_id == loser_id,  Fight.fighter_b_id == winner_id),
            ),
            Fight.winner_id == loser_id,
            Fight.id != current_fight_id,
        )
    ).scalars().first()
    return prior is not None


def _had_prior_loss(fighter_id: int, current_fight_id: int, session: Session) -> bool:
    """True if the fighter has ever lost before this fight."""
    prior = session.execute(
        select(Fight).where(
            or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
            Fight.winner_id != fighter_id,
            Fight.id != current_fight_id,
        )
    ).scalars().first()
    return prior is not None


def _ko_loss_count(fighter_id: int, session: Session) -> int:
    return session.execute(
        select(func.count()).select_from(Fight).where(
            or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
            Fight.winner_id != fighter_id,
            Fight.method == "KO/TKO",
        )
    ).scalar() or 0


def _is_ranked_top_5(fighter_id: int, session: Session) -> bool:
    r = session.execute(
        select(Ranking).where(Ranking.fighter_id == fighter_id, Ranking.rank <= 5)
    ).scalar_one_or_none()
    return r is not None


def _is_ranked(fighter_id: int, session: Session) -> bool:
    return session.execute(
        select(Ranking).where(Ranking.fighter_id == fighter_id)
    ).scalar_one_or_none() is not None


def _is_ranked_number_one(fighter_id: int, weight_class, session: Session) -> bool:
    wc_val = weight_class.value if hasattr(weight_class, "value") else weight_class
    r = session.execute(
        select(Ranking).where(
            Ranking.fighter_id == fighter_id,
            Ranking.weight_class == wc_val,
            Ranking.rank == 1,
        )
    ).scalar_one_or_none()
    return r is not None


# ---------------------------------------------------------------------------
# apply_fight_tags
# ---------------------------------------------------------------------------

def apply_fight_tags(winner: Fighter, loser: Fighter, fight: Fight, session: Session) -> None:
    """Evaluate fight context and append narrative tags to both fighters."""

    is_finish = fight.method in ("KO/TKO", "Submission")
    is_upset = is_finish and loser.overall > winner.overall
    winner_traits = get_traits(winner)
    loser_traits  = get_traits(loser)

    # ── Winner tags ──────────────────────────────────────────────────────────

    if winner.wins == 1:
        add_tag(winner, "first_win")

    ws = _win_streak(winner.id, session)
    if ws >= 5:
        add_tag(winner, "unstoppable")
    elif ws >= 3:
        add_tag(winner, "on_a_tear")

    if is_upset:
        add_tag(winner, "upset_finish")

    if _previously_lost_to(winner.id, loser.id, fight.id, session):
        add_tag(winner, "redemption")

    if _is_ranked_top_5(loser.id, session) and not _is_ranked(winner.id, session):
        add_tag(winner, "giant_killer")

    if winner.age > winner.prime_end:
        add_tag(winner, "ageless_wonder")

    archetype_val = winner.archetype.value if hasattr(winner.archetype, "value") else winner.archetype
    if archetype_val == "GOAT Candidate" and winner.wins >= 10:
        add_tag(winner, "goat_watch")

    if _is_ranked_number_one(winner.id, winner.weight_class, session):
        add_tag(winner, "champion")

    # comeback_king: won after having at least one prior loss
    if "comeback_king" in winner_traits and _had_prior_loss(winner.id, fight.id, session):
        add_tag(winner, "answered_doubters")

    # ── Loser tags ───────────────────────────────────────────────────────────

    if loser.losses == 1:
        add_tag(loser, "first_setback")

    ls = _loss_streak(loser.id, session)
    if ls >= 3:
        if "journeyman_heart" not in loser_traits:
            add_tag(loser, "fading")
        else:
            remove_tag(loser, "fading")
    elif ls >= 2:
        add_tag(loser, "at_the_crossroads")

    if fight.method == "KO/TKO" and _ko_loss_count(loser.id, session) >= 2:
        if "journeyman_heart" not in loser_traits:
            add_tag(loser, "chin_concerns")

    # ── Hype updates ─────────────────────────────────────────────────────────

    hype_gain = 30 if is_upset else (25 if is_finish else 15)
    winner.hype = min(100.0, winner.hype + hype_gain)
    loser.hype  = max(0.0,  loser.hype  - 10.0)

    # Popularity drifts toward hype; media_darling boosts gain
    pop_mult = 1.30 if "media_darling" in winner_traits else 1.0
    winner.popularity = min(100.0, winner.popularity + (winner.hype - winner.popularity) * 0.1 * pop_mult)
    loser.popularity  = max(0.0,   loser.popularity  + (loser.hype  - loser.popularity)  * 0.1)


# ---------------------------------------------------------------------------
# decay_hype
# ---------------------------------------------------------------------------

def decay_hype(session: Session, rng: random.Random) -> None:
    """Monthly hype decay for all fighters. Fight results will add hype back."""
    fighters = session.execute(select(Fighter)).scalars().all()
    for f in fighters:
        traits = get_traits(f)
        # media_darling: hype decays at 40% of the normal rate
        decay_mult = 0.40 if "media_darling" in traits else 1.0
        decay = rng.uniform(5, 10) * decay_mult
        f.hype = max(0.0, f.hype - decay)
        f.popularity = max(0.0, min(100.0, f.popularity + (f.hype - f.popularity) * 0.05))
    session.flush()


# ---------------------------------------------------------------------------
# update_goat_scores
# ---------------------------------------------------------------------------

def update_goat_scores(session: Session) -> None:
    """Recalculate and cache goat_score for every fighter."""
    fighters = session.execute(select(Fighter)).scalars().all()

    for f in fighters:
        score = f.wins * 2.0

        # Quality bonus — opponent overall for each win
        wins_a = session.execute(
            select(Fight, Fighter)
            .join(Fighter, Fight.fighter_b_id == Fighter.id)
            .where(Fight.fighter_a_id == f.id, Fight.winner_id == f.id)
        ).all()
        wins_b = session.execute(
            select(Fight, Fighter)
            .join(Fighter, Fight.fighter_a_id == Fighter.id)
            .where(Fight.fighter_b_id == f.id, Fight.winner_id == f.id)
        ).all()
        for _, opp in wins_a + wins_b:
            score += (opp.overall / 100) * 3

        score += (f.ko_wins + f.sub_wins) * 1.5

        tags = get_tags(f)
        score += tags.count("champion") * 5

        if f.age > f.prime_end and f.wins > 15:
            score += 10.0

        score -= f.losses * 0.5

        f.goat_score = max(0.0, round(score, 2))

    session.flush()


# ---------------------------------------------------------------------------
# update_rivalries
# ---------------------------------------------------------------------------

def update_rivalries(session: Session) -> list[dict]:
    """Set rivalry_with for fighter pairs who have fought 2+ times."""
    fights = session.execute(
        select(Fight).where(Fight.winner_id.isnot(None))
    ).scalars().all()

    pair_counts: dict[tuple[int, int], int] = {}
    for fight in fights:
        pair = (min(fight.fighter_a_id, fight.fighter_b_id),
                max(fight.fighter_a_id, fight.fighter_b_id))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1

    rivalries = []
    for (id_a, id_b), count in pair_counts.items():
        if count < 2:
            continue
        fa = session.get(Fighter, id_a)
        fb = session.get(Fighter, id_b)
        if not fa or not fb:
            continue
        fa.rivalry_with = id_b
        fb.rivalry_with = id_a
        if count >= 3:
            add_tag(fa, "legendary_rivalry")
            add_tag(fb, "legendary_rivalry")
        rivalries.append({
            "fighter_a": fa.name,
            "fighter_b": fb.name,
            "fight_count": count,
        })

    session.flush()
    return rivalries


# ---------------------------------------------------------------------------
# generate_fighter_bio — no archetype names ever appear in output text
# ---------------------------------------------------------------------------

# Priority order for selecting the most narratively significant tag
_TAG_PRIORITY = [
    "goat_watch", "legendary_rivalry", "unstoppable", "ageless_wonder",
    "answered_doubters", "redemption", "giant_killer", "champion",
    "on_a_tear", "chin_concerns", "fading", "at_the_crossroads",
    "first_setback", "first_win",
]

# Trait sentences — describe the effect naturally, never name the trait
_TRAIT_BIO_LINES: dict[str, list[str]] = {
    "iron_chin": [
        "He's been dropped before. He gets up. That's not bravado — at this point it's just a pattern.",
        "There's a durability to {name} that opponents keep testing and failing to break.",
    ],
    "comeback_king": [
        "He doesn't panic when hurt. He finds something. Opponents who think they have him finished often end up on the wrong end of the highlight reel.",
        "{name} has been in deep water in the {division} cage before. He keeps swimming — and that's a very specific kind of toughness.",
    ],
    "gas_tank": [
        "His conditioning is remarkable. The pace he sets in round one is essentially the pace he finishes at.",
        "Late rounds belong to {name}. While opponents slow down, he stays at the same level. It's a genuine weapon.",
    ],
    "slow_starter": [
        "He's rarely impressive in the first round. By the third, he's usually taken the fight apart piece by piece.",
        "Opponents often take round one and then wonder what happened. {name} doesn't rush — he builds.",
    ],
    "knockout_artist": [
        "Anybody who steps in with him knows it could end any second. That weight accumulates over five rounds.",
        "The power travels across all ranges. {name} doesn't need to wind up — clean contact is enough.",
    ],
    "fast_hands": [
        "His hand speed creates problems that reach and footwork alone can't solve.",
        "The hands move faster than the eyes expect. That gap is where {name} does most of his best work.",
    ],
    "ground_and_pound_specialist": [
        "Once the fight hits the canvas, the dynamic changes entirely. The short punches from top position have ended more than one {division} career.",
        "Nobody in {division} wants to be on the ground with him. The positional control and ground striking are genuinely elite.",
    ],
    "pressure_fighter": [
        "When an opponent begins to tire, {name} accelerates. A close fight doesn't stay close for long once the legs go.",
        "He feeds on fatigue. The deeper into a fight, the more dangerous — which is a very specific kind of problem.",
    ],
    "veteran_iq": [
        "He reads opponents like he's been in that fight before — because in every important way, he has.",
        "At this stage, the fight IQ compensates for anything else. {name} doesn't need to be the fastest in the cage. Just the smartest.",
    ],
    "submission_magnet": [
        "The ground game remains an area opponents continue to target. Elite grapplers in {division} have noted it, and they study it.",
    ],
    "journeyman_heart": [
        "He doesn't get stopped. That's a genuine statement — the heart is as real as any other attribute in the arsenal.",
        "Fighters who expected to break {name} found out that wasn't on offer. He competes until the final bell, whatever the scorecards look like.",
    ],
    "media_darling": [
        "He delivers, and he knows it. The cameras follow for a reason — what happens when he enters the cage tends to be worth watching.",
    ],
}

# Trait priority for bio selection (most narratively interesting first)
_TRAIT_BIO_PRIORITY = [
    "iron_chin", "comeback_king", "knockout_artist", "gas_tank",
    "fast_hands", "ground_and_pound_specialist", "pressure_fighter",
    "slow_starter", "veteran_iq", "journeyman_heart", "submission_magnet", "media_darling",
]

# Main bio templates by (archetype_value, key_tag)
# RULE: never include the words Phenom, Gatekeeper, Journeyman, Late Bloomer,
#       Shooting Star, or GOAT Candidate anywhere in the template text.
_TEMPLATES: dict[tuple[str, Optional[str]], list[str]] = {

    # ── GOAT Candidate ───────────────────────────────────────────────────────
    ("GOAT Candidate", "goat_watch"): [
        "The conversation has already started — not about whether {name} belongs, but where he ranks historically in {division}. {wins} wins against quality opposition doesn't happen by accident.",
        "People keep setting milestones expecting {name} to plateau. He keeps clearing them. The {division} weight class is running out of benchmarks.",
        "At {age}, {name} is building something in {division} that the sport hasn't seen in a long time. The numbers are one thing. The quality of the names on his record is another.",
    ],
    ("GOAT Candidate", "champion"): [
        "Champions get challenged. {name} gets studied. Every camp in the {division} division has tape on him — and so far, nobody has found the answer.",
        "{name} didn't just reach the top of the {division} division. He made it look like it was always going to happen.",
        "The belt is just the punctuation. What {name} is doing in {division} is the actual sentence — {wins} wins, finishing ability, and an aura that changes the energy in the building.",
    ],
    ("GOAT Candidate", "ageless_wonder"): [
        "Age brackets were invented for fighters who decline on schedule. {name} at {age} hasn't received that memo. The {division} division's younger contenders are doing the math — and getting nervous.",
        "At {age}, {name} should theoretically be mentoring. Instead, he's competing at the highest level {division} has to offer. Nobody has fully explained how.",
    ],
    ("GOAT Candidate", "unstoppable"): [
        "Run back {name}'s last {wins} appearances in {division}. One story, told {wins} different ways: dominant from start to finish.",
        "The {division} field has run out of answers. {name}'s record is built on an uncomfortable truth — he's simply better than almost everyone wants to publicly admit.",
    ],
    ("GOAT Candidate", None): [
        "Labeled a once-in-a-generation talent, {name} is starting to make that label feel conservative. {wins} wins, top-level opposition, a finish rate that leaves no room for debate. The {division} division has a genuine problem.",
        "The tools were obvious from day one. The results have followed. {name}'s {record} record in {division} is less a surprise than a confirmation of everything scouts said early.",
        "Some fighters build toward greatness. {name} arrived looking for it — and found it faster than anyone expected. The {division} weight class is still adjusting.",
        "{name} is the kind of fighter other fighters study. The {division} record of {wins}-{losses} doesn't fully capture what's happening in there.",
    ],

    # ── Phenom ───────────────────────────────────────────────────────────────
    ("Phenom", "giant_killer"): [
        "{name} stepped over the expected path and went straight for a {division} name on the way up. At {age}, this kind of confidence shouldn't be possible — and yet.",
        "Prospects aren't supposed to pick hard fights early. {name} picked one anyway, won, and changed the entire conversation about what he is.",
        "He arrived at {age} expecting to be tested. The {division} division obliged — and he passed every test, including the one everyone thought would slow him down.",
    ],
    ("Phenom", "on_a_tear"): [
        "{wins} straight wins at {age}. Some fighters spend a career chasing numbers like that. {name} is treating them as a starting point in the {division} division.",
        "The wins have come fast and they've come with authority. {name}'s rise through {division} has been the kind of run that forces established names to pay attention whether they want to or not.",
        "At {age}, the level of competition should still be modest. {name} disagrees — {wins} wins in {division} against increasingly serious opposition.",
    ],
    ("Phenom", "first_win"): [
        "The debut is done, the first win is logged, and {name} at {age} looks exactly as advertised. The {division} division just got more interesting.",
        "First impressions matter. {name}'s first appearance in {division} was the kind of debut that scouts replay four or five times just to confirm what they think they're seeing.",
    ],
    ("Phenom", "chin_concerns"): [
        "The talent was never the question. At {age}, {name} has the tools to do real damage in {division} — the question is whether the durability questions get answered before they become the headline.",
    ],
    ("Phenom", None): [
        "At {age}, {name} has already developed the kind of technical package that most {division} fighters spend a decade building. The results are following the tools.",
        "Youth and skill are a dangerous combination in {division}. {name}, at {age}, has both — and the composure to not waste either.",
        "The trajectory is obvious if you've watched {name} fight. The only question left for the {division} weight class is: how far does it go?",
        "Once in a while a fighter walks in and immediately looks like they belong at a higher level. {name} in {division} is that fighter.",
    ],

    # ── Gatekeeper ───────────────────────────────────────────────────────────
    ("Gatekeeper", "giant_killer"): [
        "{name} has never been anyone's pick. That underestimation has a price — and more than one {division} name has found out the hard way.",
        "The {division} record of {wins}-{losses} tells one story. The signature upset tells another. {name} is more dangerous than the rankings suggest.",
        "Nobody put {name} on a poster. Nobody picked him to win. That's exactly how he likes it — and exactly why the {division} division should stay cautious.",
    ],
    ("Gatekeeper", "at_the_crossroads"): [
        "After {losses} losses, the question isn't whether {name} can still compete in {division} — it's what comes next. That answer isn't obvious. Neither is the trajectory.",
        "Consecutive setbacks in {division} are a hard thing. {name} has been at the top of the divisional tier for years. The path back is narrow but it's not closed.",
        "Every fight career has a crossroads. {name}'s is here. The {division} résumé is real — the question is whether there's a new chapter ahead.",
    ],
    ("Gatekeeper", "ageless_wonder"): [
        "At {age}, {name} has outlasted most of the {division} fighters he came up with. There's something to be said for durability — and for fighters who refuse to accept what they're supposed to do next.",
        "The {division} division has changed around {name}, but he's still here. At {age}, he remains exactly what he's always been: a problem that needs solving.",
    ],
    ("Gatekeeper", None): [
        "Some fighters test champions on the way up. {name} has been that test in {division} more than once — and made them work for every second of it.",
        "The {record} record understates what {name} brings into a {division} cage. He's been in there with the best in the world. That experience isn't nothing.",
        "The {division} division is full of rising stars. {name} is the fighter who tells you which ones are real — a walking litmus test for contenders.",
        "Veterans don't get enough credit. {name} has been in the {division} trenches long enough to have seen every trick in the book — and a few that haven't been invented yet.",
    ],

    # ── Journeyman ───────────────────────────────────────────────────────────
    ("Journeyman", "giant_killer"): [
        "Nobody bet on {name}. Nobody predicted the upset. That's been the story of a {division} career that refuses to follow the expected script.",
        "The {division} establishment underestimated {name}. They have the record to prove it — and so does he.",
        "Don't let the losses fool you. {name} is capable of beating anyone in {division} on a given night — and has done exactly that when the moment arrived.",
    ],
    ("Journeyman", "fading"): [
        "The miles are beginning to show. {name} has given a lot to the {division} division over the years — the question now is how much is left and what the next chapter looks like.",
        "A {record} record over a long career in {division} is an honest résumé. {name} has been in fights that mattered. Whether more of those are ahead is genuinely less certain.",
    ],
    ("Journeyman", "redemption"): [
        "{name} was written off. He came back. That's the short version — the longer one involves more determination than most {division} fighters will ever have to find.",
        "Redemption is rare. When it happens, it's worth watching. {name} got his in {division}, and the division had to adjust its expectations all over again.",
    ],
    ("Journeyman", "answered_doubters"): [
        "He's had setbacks. He came back from them. That's the whole story — and it keeps repeating in {division} every time the narrative says it's over.",
        "{name} answered the doubters in {division} the only way that actually counts. Another win, another chapter.",
    ],
    ("Journeyman", None): [
        "Not every fight career is a title chase. {name}'s {division} record of {wins}-{losses} is an honest account of a fighter who showed up and competed against serious opposition.",
        "Some fighters exist to test the contenders. {name} has served that role in {division} and done it with more ability than the résumé suggests.",
        "Nobody put {name} on a poster. He kept fighting anyway. The {division} division is better for it.",
        "A career like {name}'s in {division} is undervalued. {wins} wins, {losses} losses — an honest decade of competition against people who belong at this level.",
    ],

    # ── Late Bloomer ─────────────────────────────────────────────────────────
    ("Late Bloomer", "on_a_tear"): [
        "It took {age} years to get here, but {name} has arrived with authority — {wins} straight wins in {division} that suggest the slow start was simply an adjustment period.",
        "At {age}, {name} is running out of patience with being overlooked. The {wins}-fight run is {division}'s problem now.",
        "Some fighters develop at 22. {name} developed at {age}. The {division} record doesn't show everything that changed to make the current version possible.",
    ],
    ("Late Bloomer", "giant_killer"): [
        "The {division} establishment dismissed {name} for years. The upset that changed the conversation wasn't luck — it was the result of a fighter who quietly became better than anyone was paying attention to.",
        "At {age}, {name} engineered a result in {division} that nobody predicted. The surprising part is that it was surprising at all.",
    ],
    ("Late Bloomer", None): [
        "Development is non-linear. {name}'s {division} career has taken the long route — and is arriving exactly where it was always going, just on a different timeline.",
        "The best fighters sometimes need time. {name} has spent the early part of a {division} career building something. The results are starting to show what it is.",
        "At {age}, {name} is in the middle of the career that scouts thought was years away. The {division} weight class is adjusting its expectations accordingly.",
        "Second acts are underrated. {name} in {division} is on one — and the current version of this fighter is more dangerous than the early record suggested.",
    ],

    # ── Shooting Star ────────────────────────────────────────────────────────
    ("Shooting Star", "chin_concerns"): [
        "The explosive upside was never in question. But recent finishes have raised durability questions that {name} will need to answer if the {division} ceiling is ever going to be reached.",
        "The {division} division saw a spectacular run from {name}. The question now is whether the chin can hold up as the competition level rises — it's a fair question and an important one.",
        "Explosive, dangerous, electric when it's working. {name}'s {division} career has had the highlights. The consistency question is real and unresolved.",
    ],
    ("Shooting Star", "fading"): [
        "The burst that announced {name} in {division} may not be sustainable — recent results have raised questions about whether the peak was the starting line or the finish line.",
        "Every fighter runs at a different pace. {name} ran fast and made {division} pay attention. Whether there's fuel for another run is genuinely unclear.",
        "The {division} debut was memorable. The trajectory since has been harder to read. {name} still has the tools — the question is whether they're assembling correctly.",
    ],
    ("Shooting Star", "on_a_tear"): [
        "Explosive, dangerous, and producing results that are hard to contextualize at {age}. {name} is in the middle of a {division} run that isn't supposed to happen this early.",
        "{name} arrived in {division} and immediately turned the volume up. Nothing has changed since — the {wins}-fight run is evidence.",
    ],
    ("Shooting Star", "unstoppable"): [
        "{wins} straight in {division} at {age}. The finishing ability plus the athleticism plus the momentum — it's a combination the {division} weight class hasn't fully solved.",
    ],
    ("Shooting Star", None): [
        "Brilliant, athletic, and capable of finishing anyone in {division} on a given night. The ceiling is visible. The consistency question will define the career.",
        "The {division} division has a new variable. Unpredictable, explosive, dangerous. The ceiling is real and the floor is hard to locate.",
        "Some fighters burn bright from the first bell. {name} is one of them — and the {division} weight class has felt that heat since the opening appearance.",
        "Athleticism like {name}'s in {division} doesn't come along often. The talent is exceptional. The consistency question will define what this career actually becomes.",
    ],
}


def _build_bio_from_traits(fighter: Fighter, division: str) -> str:
    """Return 0-2 trait description sentences, picking the most narratively interesting traits."""
    traits = get_traits(fighter)
    if not traits:
        return ""

    # Pick up to 2 traits in priority order
    selected = [t for t in _TRAIT_BIO_PRIORITY if t in traits][:2]
    sentences = []
    for trait in selected:
        lines = _TRAIT_BIO_LINES.get(trait, [])
        if lines:
            line = random.choice(lines)
            sentences.append(line.format(name=fighter.name, division=division))

    return " ".join(sentences)


def generate_fighter_bio(fighter: Fighter) -> str:
    """Return a 2-4 sentence bio based on situation and narrative tags.

    NEVER references archetype names in output text.
    """
    archetype_val = (
        fighter.archetype.value
        if hasattr(fighter.archetype, "value")
        else (fighter.archetype or "Journeyman")
    )
    tags = get_tags(fighter)
    division = (
        fighter.weight_class.value
        if hasattr(fighter.weight_class, "value")
        else str(fighter.weight_class)
    ).lower()

    # Pick most significant tag
    key_tag: Optional[str] = None
    for t in _TAG_PRIORITY:
        if t in tags:
            key_tag = t
            break

    # Select template
    templates = (
        _TEMPLATES.get((archetype_val, key_tag))
        or _TEMPLATES.get((archetype_val, None))
        or ["{name} is a {division} fighter with a {record} record — {wins} wins, {losses} losses."]
    )

    template = random.choice(templates)
    main_bio = template.format(
        name=fighter.name,
        division=division,
        record=fighter.record,
        wins=fighter.wins,
        losses=fighter.losses,
        age=fighter.age,
    )

    # Append trait flavour sentences
    trait_text = _build_bio_from_traits(fighter, division)
    if trait_text:
        return f"{main_bio} {trait_text}"
    return main_bio
