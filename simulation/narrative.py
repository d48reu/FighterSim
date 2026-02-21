"""Narrative engine for FighterSim — tags, bios, GOAT scores, rivalries, hype."""

from __future__ import annotations

import json
import random
from datetime import date
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

    # ── Loser tags ───────────────────────────────────────────────────────────

    if loser.losses == 1:
        add_tag(loser, "first_setback")

    ls = _loss_streak(loser.id, session)
    if ls >= 3:
        add_tag(loser, "fading")
    elif ls >= 2:
        add_tag(loser, "at_the_crossroads")

    if fight.method == "KO/TKO" and _ko_loss_count(loser.id, session) >= 2:
        add_tag(loser, "chin_concerns")

    # ── Hype updates ─────────────────────────────────────────────────────────

    hype_gain = 30 if is_upset else (25 if is_finish else 15)
    winner.hype = min(100.0, winner.hype + hype_gain)
    loser.hype  = max(0.0,  loser.hype  - 10.0)

    # Popularity drifts slowly toward hype
    winner.popularity = min(100.0, winner.popularity + (winner.hype - winner.popularity) * 0.1)
    loser.popularity  = max(0.0,   loser.popularity  + (loser.hype  - loser.popularity)  * 0.1)


# ---------------------------------------------------------------------------
# decay_hype
# ---------------------------------------------------------------------------

def decay_hype(session: Session, rng: random.Random) -> None:
    """Monthly hype decay for all fighters. Fight results will add hype back."""
    fighters = session.execute(select(Fighter)).scalars().all()
    for f in fighters:
        decay = rng.uniform(5, 10)
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
        score += tags.count("champion") * 5   # counts each time tag was re-added

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
# generate_fighter_bio
# ---------------------------------------------------------------------------

_TEMPLATES: dict[tuple[str, Optional[str]], list[str]] = {
    # ── GOAT Candidate ───────────────────────────────────────────────────────
    ("GOAT Candidate", "goat_watch"): [
        "The debate has already started. {name}'s {wins}-win total, packed with quality opposition, has the MMA world drawing comparisons to the all-time greats. The {division} division may be watching history unfold.",
        "Numbers don't lie, and {name}'s do the talking. A {record} record against top-level opponents has pundits asking a simple question: is this the best {division} fighter of all time?",
        "Ten wins in, and the conversation has already shifted from 'contender' to 'legacy.' {name} is doing things in the {division} division that simply don't come around often.",
    ],
    ("GOAT Candidate", "unstoppable"): [
        "At some point you stop calling it a winning streak and start calling it a reign. {name} has been untouchable in the {division} division, dismantling {wins} consecutive opponents with a finishing rate that leaves no doubt.",
        "The {division} field has run out of answers for {name}. Every game plan ends the same way — another dominant performance, another name on a growing list of victims.",
    ],
    ("GOAT Candidate", "ageless_wonder"): [
        "Father Time catches everyone — everyone except {name}. Past their athletic prime yet somehow sharper than ever, this {division} fighter is rewriting the book on longevity at the top level.",
        "{name} shouldn't be this good at this stage of their career. The {division} division is grateful, and quietly terrified.",
    ],
    ("GOAT Candidate", None): [
        "Labeled a once-in-a-generation prospect, {name} is starting to live up to every bit of the hype. The {division} division is watching closely.",
        "There are fighters, there are champions, and then there's {name}. A {record} record barely scratches the surface of what this {division} contender is capable of.",
        "Few fighters generate the kind of buzz {name} does. The tools are there. The results are following. The {division} division has a problem.",
    ],
    # ── Phenom ───────────────────────────────────────────────────────────────
    ("Phenom", "on_a_tear"): [
        "A generational talent, {name} has taken the {division} division by storm with {wins} straight victories. Scouts have been talking since the amateur days, and the professional scene is confirming every bit of the hype.",
        "{name} was supposed to take time to develop. Nobody sent that memo. {wins} wins deep and the {division} division is already looking for someone to slow this fighter down.",
    ],
    ("Phenom", "giant_killer"): [
        "Phenoms are supposed to ease in. Nobody told {name}, who bypassed soft matchmaking entirely and went straight for established names — picking up a signature upset in the process.",
        "The best prospects don't need a learning curve. {name} proved that by going straight for the top of the {division} division and coming out with a statement win.",
    ],
    ("Phenom", "first_win"): [
        "The career is just beginning, but first impressions count. {name} stepped into the {division} spotlight and looked every bit the fighter people said they would be.",
        "First fights reveal character. {name}'s {division} debut showed technique, composure, and finishing instinct. The future is very bright.",
    ],
    ("Phenom", None): [
        "The word 'prospect' doesn't quite cover it. {name} arrived in the {division} scene with tools that take most fighters a decade to develop — and the results have followed immediately.",
        "Youth and talent are a dangerous combination. In {name}'s case, add an uncommon level of composure, and the {division} division has a serious problem on its hands.",
        "Once in a while a fighter comes along who doesn't look like they belong — because they're too good. {name} is that fighter in {division}.",
    ],
    # ── Gatekeeper ───────────────────────────────────────────────────────────
    ("Gatekeeper", "giant_killer"): [
        "{name} has never been anyone's favorite, but their upset sent shockwaves through the {division} rankings. Don't sleep on a fighter who has seen it all and beaten the best.",
        "The {division} establishment wrote {name} off one too many times. One signature upset later, the conversation has changed entirely.",
    ],
    ("Gatekeeper", "at_the_crossroads"): [
        "A fighter of {name}'s caliber doesn't fall without a fight, but consecutive losses have opened up questions about where the career goes from here. The {division} crossroads is a brutal place.",
        "Every fighter hits a wall eventually. {name} is there now, searching for answers after back-to-back setbacks in the {division} weight class.",
    ],
    ("Gatekeeper", None): [
        "Gatekeepers don't get enough credit. {name} has been in the {division} trenches long enough to know every trick in the book — and to test every prospect who walks through the door.",
        "The {division} division is full of rising stars. {name} is the fighter who tells you whether those stars are real — a walking, breathing litmus test for {division} contenders.",
        "A {record} record tells a story of someone who has been in the thick of it. {name} may not be a title threat, but nobody in {division} takes this fight lightly.",
    ],
    # ── Journeyman ───────────────────────────────────────────────────────────
    ("Journeyman", "giant_killer"): [
        "{name} has never been anyone's favorite, but their upset sent shockwaves through the {division} rankings. Don't sleep on a fighter who has been written off before.",
        "The {division} establishment learned a hard lesson: never underestimate {name}. A shocking upset has rewritten the story of a career everyone thought they had figured out.",
    ],
    ("Journeyman", "fading"): [
        "The miles are starting to show. After years of service to the {division} division, {name} faces the toughest stretch of their career yet — and the decisions are getting harder.",
        "Every road warrior hits the end of the line eventually. For {name}, that moment may be approaching in {division}, though this fighter has defied expectations before.",
    ],
    ("Journeyman", None): [
        "Every champion needs someone to test them on the way up, and {name} has filled that role more than once in the {division} division. The {record} record tells only part of the story.",
        "There's no shame in being a journeyman. {name} has shared the {division} cage with fighters who went on to be champions — and made them work for every second of it.",
        "Not every fighter is meant to hold a belt. {name} knows that, accepts it, and keeps showing up anyway. The {division} division is better for having them in it.",
    ],
    # ── Late Bloomer ─────────────────────────────────────────────────────────
    ("Late Bloomer", "on_a_tear"): [
        "They said it would take time, and it did. But {name} has fully arrived in the {division} division, racking up {wins} straight wins and proving that the wait was worth it.",
        "Late bloomers are misunderstood. {name} always had the tools — it just took time for everything to click. Now it has, and the {division} division is paying the price.",
    ],
    ("Late Bloomer", None): [
        "Late bloomers are the most underrated fighters in any division. {name} hasn't reached peak form yet — and the {division} weight class should be very worried about what that looks like.",
        "Some fighters need time. {name} is one of them — and patience is paying off. The {division} division is starting to take notice of a talent that was always there.",
        "Development isn't linear, and {name} is proof. Overlooked for years, this {division} fighter is putting it all together at exactly the right moment.",
    ],
    # ── Shooting Star ────────────────────────────────────────────────────────
    ("Shooting Star", "chin_concerns"): [
        "The finishing power was never in question. But recent stoppages have raised durability concerns for {name}, who may need to fight smarter as the {division} career progresses.",
        "Bright for a moment, but {name}'s {division} run has hit turbulence. The chin questions that scouts whispered about are now front-page news.",
    ],
    ("Shooting Star", "fading"): [
        "The ceiling came faster than expected. {name} blazed into the {division} scene with intensity, but sustaining that pace has proven harder than anticipated.",
        "Every shooting star burns out eventually. The question for {name} is whether there's enough fuel left to make one more run in the {division} weight class.",
    ],
    ("Shooting Star", None): [
        "Bright, fast, and devastating while it lasts. {name} has lit up the {division} division with a combination of finishing ability and athleticism you don't see often.",
        "The {division} division has a new problem, and its name is {name}. Explosive, unpredictable, and more dangerous than the record suggests.",
        "There are fighters built for the long haul, and there are fighters who burn bright and take your breath away. {name} is the latter — and the {division} scene is better for it.",
    ],
}

_TAG_PRIORITY = [
    "goat_watch", "legendary_rivalry", "unstoppable", "ageless_wonder",
    "redemption", "giant_killer", "champion", "on_a_tear",
    "chin_concerns", "fading", "at_the_crossroads", "first_setback", "first_win",
]


def generate_fighter_bio(fighter: Fighter) -> str:
    """Return a 2-3 sentence bio based on archetype and narrative tags."""
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

    key_tag: Optional[str] = None
    for t in _TAG_PRIORITY:
        if t in tags:
            key_tag = t
            break

    # Try (archetype, key_tag), then (archetype, None)
    templates = (
        _TEMPLATES.get((archetype_val, key_tag))
        or _TEMPLATES.get((archetype_val, None))
        or ["{name} is a {division} fighter with a {record} record."]
    )

    template = random.choice(templates)
    return template.format(
        name=fighter.name,
        division=division,
        record=fighter.record,
        wins=fighter.wins,
    )
