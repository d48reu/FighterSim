"""Narrative engine for FighterSim — tags, bios, GOAT scores, rivalries, hype."""

from __future__ import annotations

import json
import random
from typing import Optional

from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import Session

from models.models import Fighter, Fight, Ranking, WeightClass, Archetype, FighterDevelopment, Organization


# ---------------------------------------------------------------------------
# Nationality data structures (consumed by Tasks 2-4)
# ---------------------------------------------------------------------------

NATIONALITY_STYLE_MAP: dict[str, str] = {
    "Brazilian": "Grappler",
    "Russian": "Wrestler",
    "Dagestani": "Wrestler",
    "Georgian": "Wrestler",
    "Irish": "Striker",
    "British": "Striker",
    "Dutch": "Striker",
    "Japanese": "Striker",
    "Swedish": "Wrestler",
    "Norwegian": "Wrestler",
    "Mexican": "Striker",
    "South Korean": "Striker",
    "Nigerian": "Striker",
    "Cameroonian": "Wrestler",
    "New Zealander": "Grappler",
    "French": "Grappler",
}

_NATIONALITY_FLAVOR_LINES: dict[str, list[str]] = {
    "Brazilian": [
        "Trained in the grappling tradition that Brazilian fighters have brought to the sport, {name} carries that pedigree into every exchange on the mat.",
        "The Brazilian jiu-jitsu roots run deep. {name} fights with the technical confidence that comes from a lifetime on the mats.",
    ],
    "Russian": [
        "The wrestling base that Russian fighters are known for gives {name} a positional advantage most opponents struggle to overcome.",
        "{name} brings the relentless pressure and iron discipline that Russian combat sports programs produce.",
    ],
    "Dagestani": [
        "Dagestani wrestling is a different breed. {name} carries that chain-wrestling pressure that has redefined grappling in the sport.",
        "The mountains produce fighters differently. {name} fights with the grinding, suffocating style that Dagestan is known for.",
    ],
    "Georgian": [
        "Georgian wrestling traditions have shaped {name} into a fighter whose takedowns come from a place opponents rarely expect.",
        "{name} brings the explosive clinch work and heavy hips that Georgian wrestling demands.",
    ],
    "Irish": [
        "There is a certain directness to Irish strikers. {name} embodies that willingness to stand and trade with absolute conviction.",
        "{name} carries the confidence of a fighter from a country that has punched well above its weight in combat sports.",
    ],
    "Dutch": [
        "The Dutch kickboxing lineage shows in everything {name} does on the feet. The combinations are crisp and the intent is clear.",
        "{name} fights with the technical striking precision that has made Dutch fighters a force in the sport.",
    ],
    "Japanese": [
        "Japanese martial arts tradition emphasizes discipline and precision. {name} brings both into the cage with quiet intensity.",
        "{name} fights with the kind of technical sharpness and composure that Japanese combat sports culture demands.",
    ],
    "Mexican": [
        "Mexican fighters carry a reputation for toughness and forward pressure. {name} honors that tradition every time the cage door closes.",
        "The warrior spirit that Mexican combat sports are built on runs through {name}'s approach to every fight.",
    ],
    "Swedish": [
        "The Scandinavian wrestling tradition gives {name} a grappling base that translates directly to control in the cage.",
        "{name} brings the methodical, technically sound wrestling that Swedish programs are known for developing.",
    ],
    "Nigerian": [
        "The raw athleticism and striking power that Nigerian fighters bring to the sport are on full display with {name}.",
        "{name} carries explosive speed and the kind of natural power that changes fights in a single exchange.",
    ],
    "New Zealander": [
        "{name} comes from a grappling culture influenced by rugby and ground-based martial arts that translates uniquely into the cage.",
        "New Zealand produces fighters with a blend of toughness and technical ground skills. {name} is a product of that tradition.",
    ],
    "French": [
        "French grappling has quietly produced some of the best submission artists in the sport. {name} carries that legacy forward.",
        "{name} fights with the technical sophistication that French martial arts schools have become known for developing.",
    ],
}

NATIONALITY_NICKNAMES: dict[str, list[str]] = {
    "Brazilian": ["The Brazilian", "Carioca", "Favela Born", "Jungle Cat", "Samba"],
    "Russian": ["The Russian Bear", "Siberian", "Red Machine", "Moscow Mauler", "Tsar"],
    "Dagestani": ["The Eagle", "Mountain Wolf", "Dagestani Machine", "The Wrestler"],
    "Georgian": ["The Georgian", "Tbilisi Thunder", "Caucasus King"],
    "Irish": ["Celtic Warrior", "Dublin Brawler", "The Irishman", "Green Machine"],
    "British": ["The Brit", "Bulldog", "London Calling", "The Governor"],
    "Dutch": ["Dutch Destroyer", "Windmill", "Orange Crush"],
    "Japanese": ["Samurai", "Rising Sun", "The Ronin", "Bushido"],
    "Mexican": ["El Guerrero", "Aztec Warrior", "El Diablo", "La Bestia"],
    "Swedish": ["Viking", "Nordic Thunder", "The Swede", "Ice Cold"],
    "Norwegian": ["Norse Hammer", "Viking Warrior", "Nordic Storm"],
    "South Korean": ["Korean Tiger", "Seoul Fighter", "The Dragon"],
    "Nigerian": ["African Thunder", "Lagos Lightning", "The Lion"],
    "Cameroonian": ["African Giant", "Cameroon Power", "The Panther"],
    "New Zealander": ["Kiwi Crusher", "Maori Warrior", "Southern Cross"],
    "French": ["Le Magnifique", "French Connection", "The Parisian"],
}

NATIONALITY_TONE: dict[str, str] = {
    "Brazilian": "passionate",
    "Russian": "stoic",
    "Dagestani": "intense",
    "Georgian": "fierce",
    "Irish": "brash",
    "British": "composed",
    "Dutch": "direct",
    "Japanese": "respectful",
    "Mexican": "fiery",
    "Swedish": "calm",
    "Norwegian": "calm",
    "South Korean": "focused",
    "Nigerian": "confident",
    "Cameroonian": "proud",
    "New Zealander": "relaxed",
    "French": "eloquent",
    "American": "confident",
    "Canadian": "measured",
    "Australian": "brash",
    "Polish": "determined",
    "German": "direct",
}


def _nationality_flavor(fighter: Fighter) -> str:
    """Return a nationality-themed flavor sentence if the fighter's style matches
    their nationality's stereotype. Returns empty string for Americans or mismatches."""
    nat = fighter.nationality if hasattr(fighter, "nationality") else ""
    if not nat or nat == "American" or nat not in NATIONALITY_STYLE_MAP:
        return ""
    expected_style = NATIONALITY_STYLE_MAP[nat]
    actual_style = fighter.style.value if hasattr(fighter.style, "value") else str(fighter.style)
    if actual_style != expected_style:
        return ""
    lines = _NATIONALITY_FLAVOR_LINES.get(nat, [])
    if not lines:
        return ""
    name = fighter.name
    return random.choice(lines).format(name=name)


# ---------------------------------------------------------------------------
# Nickname system
# ---------------------------------------------------------------------------

NICKNAME_POOLS: dict[str, list[str]] = {
    "Phenom": [
        "The Prodigy", "Wunderkind", "The Natural", "Young Gun", "The Future",
        "Next Level", "The Chosen One", "Gifted", "The Marvel", "Born Ready",
        "The Phenom", "Fast Track", "Lightning", "The Heir", "Showtime",
        "Prime Time", "The Kid", "Wonderboy", "The Ace", "Golden Boy",
    ],
    "GOAT Candidate": [
        "The Greatest", "All-Time", "The Legend", "Immortal", "The King",
        "Supreme", "The Standard", "Undeniable", "The One", "Final Boss",
        "The GOAT", "Untouchable", "The Master", "Colossus", "The Apex",
        "Invincible", "The Ruler", "Champion Eternal", "The Pinnacle", "The Crown",
    ],
    "Gatekeeper": [
        "The Wall", "No Shortcuts", "The Test", "Ironside", "The Guard",
        "The Gatekeeper", "Roadblock", "Fortress", "The Barrier", "Stone Cold",
        "The Sentinel", "Hard Road", "The Bouncer", "The Lock", "Checkpoint",
        "The Toll", "Full Stop", "The Blocker", "Brick Wall", "The Exam",
    ],
    "Journeyman": [
        "Tough Luck", "Hard Miles", "The Grinder", "Blue Collar", "Workhorse",
        "Iron Will", "All Heart", "The Survivor", "Steady Hand", "Never Quit",
        "The Journeyman", "Road Warrior", "The Mule", "Punchclock", "Everyman",
        "The Scrapper", "No Frills", "The Worker", "Grit", "Steel Jaw",
    ],
    "Late Bloomer": [
        "The Late Show", "Second Wind", "Better Late", "The Sleeper", "Dark Horse",
        "The Surprise", "Slow Burn", "Patient Zero", "The Awakening", "Night Shift",
        "The Bloom", "Old New Thing", "The Reveal", "Rising Tide", "Late Surge",
        "The Emergence", "Quiet Storm", "Undercooked", "The Long Game", "Afterburner",
    ],
    "Shooting Star": [
        "Supernova", "Meteor", "Flash", "Blaze", "The Comet",
        "Fireball", "Rocket", "The Spark", "Wildfire", "Stardust",
        "The Flash", "Blazing", "Sky High", "Fuse", "The Streak",
        "Nova", "The Burst", "Dynamite", "Flashpoint", "The Explosion",
    ],
}

TRAIT_NICKNAME_BOOSTS: dict[str, list[str]] = {
    "iron_chin": ["Iron Chin", "Granite", "The Tank", "Unbreakable", "Steel"],
    "knockout_artist": ["One Punch", "Lights Out", "The Hammer", "TNT", "Knockout"],
    "fast_hands": ["Quick Draw", "Lightning Hands", "The Blur", "Rapid Fire"],
    "gas_tank": ["The Machine", "Engine", "Cardio King", "Marathon Man"],
    "comeback_king": ["Comeback Kid", "The Resurrection", "Never Dead", "Lazarus"],
    "pressure_fighter": ["The Pressure", "Relentless", "The Shark", "No Mercy"],
    "ground_and_pound_specialist": ["Ground Zero", "The Smasher", "Sledgehammer"],
    "submission_magnet": ["The Escape Artist", "Slippery", "Houdini"],
    "veteran_iq": ["The Professor", "Old Wise One", "Chess Master", "The Brain"],
    "slow_starter": ["The Finisher", "Late Bloomer", "Round Three"],
    "journeyman_heart": ["All Heart", "Never Say Die", "The Warrior", "Lion Heart"],
    "media_darling": ["The Star", "Camera Ready", "Showtime", "The Draw"],
}


def suggest_nicknames(fighter: Fighter, session: Optional[Session] = None) -> list[str]:
    """Return 3 distinct nickname suggestions based on archetype, traits, and nationality."""
    archetype_val = fighter.archetype.value if hasattr(fighter.archetype, "value") else (fighter.archetype or "Journeyman")
    pool_items: list[tuple[str, float]] = []

    # Archetype pool
    archetype_pool = NICKNAME_POOLS.get(archetype_val, NICKNAME_POOLS["Journeyman"])
    for nick in archetype_pool:
        pool_items.append((nick, 1.0))

    # Trait boosts
    traits = get_traits(fighter)
    for trait in traits:
        boosts = TRAIT_NICKNAME_BOOSTS.get(trait, [])
        for nick in boosts:
            pool_items.append((nick, 2.5))

    # Nationality nicknames
    nat = fighter.nationality if hasattr(fighter, "nationality") else ""
    nat_nicks = NATIONALITY_NICKNAMES.get(nat, [])
    for nick in nat_nicks:
        pool_items.append((nick, 1.8))

    if not pool_items:
        return ["The Fighter", "Unknown", "Mystery"]

    # Deduplicate — keep highest weight for each nickname
    best_weight: dict[str, float] = {}
    for nick, weight in pool_items:
        if nick not in best_weight or weight > best_weight[nick]:
            best_weight[nick] = weight

    # Filter out already-used nicknames
    if session:
        existing = session.execute(
            select(Fighter.nickname).where(Fighter.nickname.isnot(None))
        ).scalars().all()
        used = set(existing)
        best_weight = {k: v for k, v in best_weight.items() if k not in used}

    if len(best_weight) < 3:
        # Pad with generic fallbacks
        for fallback in ["The Fighter", "The Contender", "The Challenger", "The Warrior"]:
            if fallback not in best_weight:
                best_weight[fallback] = 0.5
            if len(best_weight) >= 3:
                break

    names = list(best_weight.keys())
    weights = list(best_weight.values())

    # Pick 3 distinct
    chosen = []
    for _ in range(3):
        if not names:
            break
        picks = random.choices(names, weights=weights, k=1)
        pick = picks[0]
        chosen.append(pick)
        idx = names.index(pick)
        names.pop(idx)
        weights.pop(idx)

    return chosen


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


def _first_round_finish_count(fighter_id: int, session: Session) -> int:
    """Count wins where round_ended == 1 and method is KO/TKO or Submission."""
    return session.execute(
        select(func.count()).select_from(Fight).where(
            Fight.winner_id == fighter_id,
            Fight.round_ended == 1,
            or_(Fight.method == "KO/TKO", Fight.method == "Submission"),
        )
    ).scalar() or 0


def _decision_win_count(fighter_id: int, session: Session) -> int:
    """Count wins by any Decision method."""
    return session.execute(
        select(func.count()).select_from(Fight).where(
            Fight.winner_id == fighter_id,
            or_(
                Fight.method == "Unanimous Decision",
                Fight.method == "Split Decision",
                Fight.method == "Majority Decision",
            ),
        )
    ).scalar() or 0


def _has_been_kod(fighter_id: int, session: Session) -> bool:
    """True if fighter has ever lost by KO/TKO."""
    r = session.execute(
        select(Fight).where(
            or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
            Fight.winner_id != fighter_id,
            Fight.winner_id.isnot(None),
            Fight.method == "KO/TKO",
        )
    ).scalars().first()
    return r is not None


def _total_completed_fights(fighter_id: int, session: Session) -> int:
    """Total fights where winner_id is not None."""
    return session.execute(
        select(func.count()).select_from(Fight).where(
            or_(Fight.fighter_a_id == fighter_id, Fight.fighter_b_id == fighter_id),
            Fight.winner_id.isnot(None),
        )
    ).scalar() or 0


# ---------------------------------------------------------------------------
# apply_fight_tags
# ---------------------------------------------------------------------------

def apply_fight_tags(winner: Fighter, loser: Fighter, fight: Fight, session: Session) -> None:
    """Evaluate fight context and append narrative tags to both fighters."""

    is_finish = fight.method in ("KO/TKO", "Submission")
    is_upset = is_finish and loser.overall > winner.overall
    winner_traits = get_traits(winner)
    loser_traits  = get_traits(loser)

    # ── Tag removal logic ────────────────────────────────────────────────────
    # Winner: answered doubters — remove retirement_watch
    remove_tag(winner, "retirement_watch")
    # Loser: no longer undefeated
    remove_tag(loser, "undefeated")
    # Loser: remove rising_prospect if loss_streak >= 2
    ls_loser = _loss_streak(loser.id, session)
    if ls_loser >= 2:
        remove_tag(loser, "rising_prospect")

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

    # ── Cornerstone fall from grace ───────────────────────────────────────────
    if getattr(loser, "is_cornerstone", False) and ls >= 3:
        loser.is_cornerstone = False
        add_tag(loser, "fall_from_grace")

    # ── NEW: Method-specific winner tags ─────────────────────────────────────

    if winner.ko_wins >= 5:
        add_tag(winner, "ko_specialist")

    if winner.sub_wins >= 5:
        add_tag(winner, "submission_ace")

    if fight.round_ended == 1 and is_finish and _first_round_finish_count(winner.id, session) >= 3:
        add_tag(winner, "first_round_finisher")

    method_str_raw = fight.method.value if hasattr(fight.method, "value") else str(fight.method)
    is_decision = method_str_raw in ("Unanimous Decision", "Split Decision", "Majority Decision")
    if is_decision and _decision_win_count(winner.id, session) >= 5:
        add_tag(winner, "decision_machine")

    if method_str_raw == "KO/TKO" and fight.round_ended == 1:
        # time_ended format is "M:SS" — check if under 2:00
        try:
            parts = fight.time_ended.split(":")
            mins = int(parts[0])
            if mins < 2:
                add_tag(winner, "highlight_reel")
        except (AttributeError, ValueError, IndexError):
            pass

    if is_finish and fight.round_ended and fight.round_ended >= 3:
        add_tag(winner, "comeback_victory")

    # ── NEW: Career pattern winner tags ──────────────────────────────────────

    total_fights = _total_completed_fights(winner.id, session)
    if total_fights >= 10 and not _has_been_kod(winner.id, session):
        add_tag(winner, "iron_chin_proven")

    winner_archetype = winner.archetype.value if hasattr(winner.archetype, "value") else (winner.archetype or "")
    if winner_archetype == "Gatekeeper" and _is_ranked(loser.id, session):
        add_tag(winner, "gatekeeper_confirmed")

    if winner.age > winner.prime_end + 2:
        add_tag(winner, "veteran_presence")

    if fight.is_title_fight:
        add_tag(winner, "clutch_performer")

    if winner.age < 24 and winner.wins >= 5 and ws >= 3:
        add_tag(winner, "rising_prospect")

    if winner.losses == 0 and winner.wins >= 5:
        add_tag(winner, "undefeated")

    if total_fights >= 15:
        add_tag(winner, "road_warrior")

    if _is_ranked_top_5(winner.id, session) and ws >= 3:
        add_tag(winner, "title_contender")

    if not _is_ranked(winner.id, session) and _is_ranked(loser.id, session):
        add_tag(winner, "dark_horse")

    # ── NEW: Loser career pattern tags ───────────────────────────────────────

    if loser.age > loser.prime_end + 3 and ls >= 2 and loser.overall < 65:
        add_tag(loser, "retirement_watch")

    loser_tags = get_tags(loser)
    if "chin_concerns" in loser_tags and "ko_specialist" in loser_tags:
        add_tag(loser, "glass_cannon")

    if ls >= 3:
        has_dev = session.execute(
            select(FighterDevelopment).where(
                FighterDevelopment.fighter_id == loser.id,
                FighterDevelopment.camp_id.isnot(None),
            )
        ).scalar_one_or_none()
        if not has_dev:
            add_tag(loser, "needs_new_camp")

    # ── NEW: Fight quality tags (winner only) ────────────────────────────────

    if is_decision and winner.hype > 40 and loser.hype > 40:
        add_tag(winner, "fight_of_the_night")

    if is_decision and fight.round_ended and fight.round_ended >= 3 and winner.hype >= 30:
        add_tag(winner, "war_survivor")

    # ── Confidence shifts ────────────────────────────────────────────────────

    method = fight.method if hasattr(fight.method, "value") is False else fight.method.value if hasattr(fight.method, "value") else fight.method
    method_str = method.value if hasattr(method, "value") else str(method)

    if method_str == "KO/TKO":
        winner.confidence = min(100.0, getattr(winner, "confidence", 70.0) + 12.0)
        loser.confidence  = max(0.0,   getattr(loser, "confidence", 70.0)  - 18.0)
    elif method_str == "Submission":
        winner.confidence = min(100.0, getattr(winner, "confidence", 70.0) + 10.0)
        loser.confidence  = max(0.0,   getattr(loser, "confidence", 70.0)  - 12.0)
    else:
        # Decision
        winner.confidence = min(100.0, getattr(winner, "confidence", 70.0) + 5.0)
        loser.confidence  = max(0.0,   getattr(loser, "confidence", 70.0)  - 5.0)

    # Confidence-based narrative tags
    w_streak = _win_streak(winner.id, session)
    if w_streak >= 3 and getattr(winner, "confidence", 70.0) >= 85:
        add_tag(winner, "sky_high_confidence")
    else:
        remove_tag(winner, "sky_high_confidence")

    if method_str == "KO/TKO" and getattr(loser, "confidence", 70.0) <= 40:
        add_tag(loser, "shell_shocked")
    # Remove shell_shocked if confidence recovers
    if getattr(loser, "confidence", 70.0) > 55:
        remove_tag(loser, "shell_shocked")
    if getattr(winner, "confidence", 70.0) > 55:
        remove_tag(winner, "shell_shocked")

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
# Press Conference System
# ---------------------------------------------------------------------------

TONE_PROFILES: dict[str, str] = {
    "Phenom": "confident",
    "GOAT Candidate": "dominant",
    "Gatekeeper": "measured",
    "Journeyman": "workmanlike",
    "Late Bloomer": "hungry",
    "Shooting Star": "flashy",
}

TRAIT_TONE_MODS: dict[str, str] = {
    "knockout_artist": "menacing",
    "media_darling": "showman",
    "iron_chin": "defiant",
    "comeback_king": "resilient",
    "fast_hands": "sharp",
    "pressure_fighter": "aggressive",
    "gas_tank": "relentless",
    "veteran_iq": "cerebral",
    "journeyman_heart": "gritty",
    "slow_starter": "patient",
    "ground_and_pound_specialist": "imposing",
    "submission_magnet": "cautious",
}

_PRESS_QUOTES: dict[str, list[str]] = {
    "confident": [
        "I've been ready for this fight since day one. {opponent} is a good fighter, but I'm on another level right now.",
        "People keep asking if I'm worried. I'm not. I know what I bring to the cage.",
        "This is my moment. {opponent} is standing between me and where I'm supposed to be.",
        "I respect {opponent}, but respect doesn't stop me from finishing this fight.",
    ],
    "dominant": [
        "I've proven it over and over. {opponent} gets the same treatment everyone else has gotten.",
        "When I'm in my best form, nobody in this division can touch me. I plan on being in my best form.",
        "The record speaks. The performances speak. Saturday night, it speaks again.",
        "{opponent} is a tough fight on paper. But paper doesn't fight back.",
    ],
    "measured": [
        "I've been in this sport long enough to know that anything can happen. But I'm prepared for everything.",
        "I respect {opponent}. I've studied the tape. I have a plan. That's all I can control.",
        "Experience matters in these situations. I've been here before. That counts for something.",
        "I'm not going to make predictions. I'll let my performance do the talking.",
    ],
    "workmanlike": [
        "I'm here to work. That's what I do. {opponent} should expect a hard night.",
        "Nobody gave me this opportunity. I earned it fight by fight. I plan on keeping it.",
        "I don't do a lot of talking. I show up, I compete, and I give everything I have.",
        "They can sleep on me all they want. I'll be wide awake Saturday night.",
    ],
    "hungry": [
        "This is the fight I've been waiting for. Everything has been building to this moment.",
        "People wrote me off. That's fine. {opponent} is going to find out what happens when you underestimate me.",
        "I'm not the same fighter I was two years ago. I've evolved, and this fight is going to show it.",
        "Timing is everything. My time is now, and I intend to make the most of it.",
    ],
    "flashy": [
        "Saturday night is going to be spectacular. I promise the fans won't be disappointed.",
        "I bring the show. {opponent} brings the fight. Together we're going to give people something to remember.",
        "The highlight reel is about to get another entry. I hope {opponent} is ready for prime time.",
        "This is what the people pay to see. And I always deliver.",
    ],
    "menacing": [
        "I don't need three rounds. {opponent} knows what's coming, and there's nothing they can do about it.",
        "When I hit people, they change. {opponent} is going to find that out Saturday.",
        "I smell fear. It's fine. Most people are afraid before they fight me.",
    ],
    "showman": [
        "The cameras are here for a reason. I make fights into events. Saturday is no different.",
        "I'm the best thing that ever happened to {opponent}'s career. This is the biggest stage they'll ever stand on.",
        "Entertainment and violence — I provide both. {opponent} only provides one.",
    ],
    "defiant": [
        "You can hit me all night. I'll still be standing. Ask anyone who's tried.",
        "People keep saying I should slow down. I keep saying: make me.",
        "I've taken the best shots in this division and I'm still here. {opponent} won't change that.",
    ],
    "resilient": [
        "I've been knocked down before. I get back up. That's the story, and it's not changing Saturday.",
        "Adversity is nothing new to me. {opponent} is just the next chapter.",
    ],
    "aggressive": [
        "I'm going to push the pace from the opening bell. {opponent} better be ready for five rounds of pressure.",
        "When I start moving forward, the fight changes. Everybody knows it. {opponent} will know it soon.",
    ],
    "cerebral": [
        "I've studied {opponent} for weeks. I see patterns most people miss. Saturday, I exploit them.",
        "Fighting smart is an underrated skill. I plan on being the smartest person in the cage.",
    ],
    "gritty": [
        "I'm not the most talented fighter in the world. But I'm the hardest to beat. Ask around.",
        "Heart doesn't show up on the tale of the tape. But it shows up when it matters.",
    ],
}


def _build_fighter_tone(fighter: Fighter) -> str:
    """Combine archetype tone + first matching trait modifier + nationality tone.

    Low-confidence fighters get shifted to a more subdued tone.
    """
    conf = getattr(fighter, "confidence", 70.0) or 70.0

    # Low confidence override — fighter sounds subdued regardless of archetype
    if conf <= 40:
        return "measured"

    archetype_val = fighter.archetype.value if hasattr(fighter.archetype, "value") else (fighter.archetype or "Journeyman")
    base = TONE_PROFILES.get(archetype_val, "measured")

    traits = get_traits(fighter)
    for trait in traits:
        if trait in TRAIT_TONE_MODS:
            return TRAIT_TONE_MODS[trait]

    nat = fighter.nationality if hasattr(fighter, "nationality") else ""
    nat_tone = NATIONALITY_TONE.get(nat, "")
    if nat_tone and nat_tone in _PRESS_QUOTES:
        return nat_tone

    return base


def generate_press_conference(fighter_a: Fighter, fighter_b: Fighter,
                              is_cornerstone_a: bool = False,
                              is_cornerstone_b: bool = False) -> dict:
    """Generate pre-fight press conference dialogue between two fighters.

    Returns dict with exchanges, hype_generated, and ppv_boost.
    """
    tone_a = _build_fighter_tone(fighter_a)
    tone_b = _build_fighter_tone(fighter_b)

    exchange_count = 7 if (is_cornerstone_a or is_cornerstone_b) else 5

    exchanges = []
    for i in range(exchange_count):
        # Pick quotes for each fighter
        quotes_a = _PRESS_QUOTES.get(tone_a, _PRESS_QUOTES["measured"])
        quotes_b = _PRESS_QUOTES.get(tone_b, _PRESS_QUOTES["measured"])

        quote_a = random.choice(quotes_a).format(opponent=fighter_b.name)
        quote_b = random.choice(quotes_b).format(opponent=fighter_a.name)

        exchanges.append({
            "round": i + 1,
            "fighter_a": quote_a,
            "fighter_b": quote_b,
        })

    # Calculate hype based on tone clash diversity
    unique_tones = len({tone_a, tone_b})
    base_hype = 8.0 if unique_tones == 2 else 5.0
    # Bonus for certain dramatic combos
    dramatic_combos = [
        {"menacing", "defiant"}, {"dominant", "hungry"}, {"flashy", "workmanlike"},
        {"confident", "aggressive"}, {"showman", "gritty"},
    ]
    combo_bonus = 3.0 if {tone_a, tone_b} in dramatic_combos else 0.0
    exchange_bonus = exchange_count * 0.5
    hype_generated = min(15.0, base_hype + combo_bonus + exchange_bonus)
    ppv_boost = int(hype_generated * 50)

    return {
        "exchanges": exchanges,
        "hype_generated": round(hype_generated, 1),
        "ppv_boost": ppv_boost,
        "tone_a": tone_a,
        "tone_b": tone_b,
    }


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
# display_archetype — age-adjusted label for UI display
# ---------------------------------------------------------------------------

def display_archetype(fighter: Fighter) -> str:
    """Return the archetype label for display purposes.

    Uses _get_career_context() to compute context-aware overrides:
    - Phenom past prime → 'Former Phenom'
    - Shooting Star past prime → 'Fading Star'
    - Gatekeeper age < 27 → 'Developing'
    - Journeyman with winning record age < 28 → 'Developing'
    - Age > prime_end + 4 → 'Veteran'

    The underlying archetype in the database is never modified.
    """
    if fighter.age > fighter.prime_end + 4:
        return "Veteran"
    ctx = _get_career_context(fighter)
    return ctx["displayed_archetype"]


# ---------------------------------------------------------------------------
# generate_fighter_bio — context-aware, validated bio generation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Career context calculator
# ---------------------------------------------------------------------------

def _get_career_context(fighter) -> dict:
    """Calculate career stage, trajectory, archetype display, and key narrative tag."""
    career_fights = fighter.wins + fighter.losses + fighter.draws

    # Career stage based on age AND fight count
    if career_fights < 6 or fighter.age < 22:
        career_stage = "prospect"
    elif career_fights < 15 or fighter.age < 26:
        career_stage = "developing"
    elif career_fights < 25 or fighter.age < 30:
        career_stage = "established"
    elif fighter.age < 35:
        career_stage = "veteran"
    else:
        career_stage = "elder"

    # Career trajectory based on record and age vs prime
    past_prime = fighter.age > fighter.prime_end
    win_rate = fighter.wins / career_fights if career_fights > 0 else 0.5

    if career_fights < 6:
        trajectory = "rising"
    elif past_prime and win_rate < 0.5:
        trajectory = "declining"
    elif past_prime and win_rate >= 0.5:
        trajectory = "resilient"
    elif win_rate >= 0.65:
        trajectory = "rising"
    elif win_rate >= 0.45:
        trajectory = "steady"
    else:
        trajectory = "struggling"

    # Archetype display — override if age has passed the archetype's window
    archetype_val = (
        fighter.archetype.value
        if hasattr(fighter.archetype, "value")
        else (fighter.archetype or "Journeyman")
    )
    displayed_archetype = archetype_val
    if archetype_val == "Phenom" and fighter.age > fighter.prime_end:
        displayed_archetype = "Former Phenom"
    if archetype_val == "Shooting Star" and fighter.age > fighter.prime_end:
        displayed_archetype = "Fading Star"
    if archetype_val == "Gatekeeper" and fighter.age < 27:
        displayed_archetype = "Developing"
    if archetype_val == "Journeyman" and fighter.wins > fighter.losses and fighter.age < 28:
        displayed_archetype = "Developing"

    # Significant tags — most narratively important ones take priority
    priority_tags = [
        "goat_watch", "champion", "legendary_rivalry", "giant_killer",
        "ageless_wonder", "redemption", "comeback_king_tag", "unstoppable",
        "chin_concerns", "fading", "at_the_crossroads",
    ]
    tags = get_tags(fighter) if hasattr(fighter, "narrative_tags") else []
    significant_tag = next((t for t in priority_tags if t in tags), None)

    # Win streak from tags
    streak = 0
    if "unstoppable" in tags:
        streak = 5
    elif "on_a_tear" in tags:
        streak = 3

    return {
        "career_fights": career_fights,
        "career_stage": career_stage,
        "trajectory": trajectory,
        "displayed_archetype": displayed_archetype,
        "archetype": archetype_val,
        "significant_tag": significant_tag,
        "streak": streak,
        "win_rate": win_rate,
        "past_prime": past_prime,
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# Pluralization helper
# ---------------------------------------------------------------------------

def _plural(count, singular, plural):
    """Return count with correct singular/plural form."""
    return f"{count} {singular if count == 1 else plural}"


# ---------------------------------------------------------------------------
# Context-gated bio templates
# ---------------------------------------------------------------------------
# Each category is a tuple of (category_name, condition_fn, templates).
# The first matching category wins. Templates use {name}, {age}, {division},
# {record}, {wins}, {losses}, {career_fights}, {streak}, {ko_wins},
# {wins_word}, {losses_word}.
# RULE: never include archetype names in template text.

def _select_templates(fighter, ctx: dict) -> list[str]:
    """Return the best-matching template list based on career context."""
    archetype = ctx["archetype"]
    stage = ctx["career_stage"]
    traj = ctx["trajectory"]
    tag = ctx["significant_tag"]
    tags = ctx["tags"]
    past_prime = ctx["past_prime"]
    win_rate = ctx["win_rate"]
    fights = ctx["career_fights"]

    # ── Prospect (career_fights < 6) — all archetypes get prospect language
    if stage == "prospect":
        return [
            "The early signs are encouraging. {name} is {age} years old and {record} as a professional — too soon to draw conclusions, but the foundation looks solid.",
            "{name} is finding his footing in {division}. {career_fights_word} in, there's potential here that hasn't fully shown itself yet.",
            "Every fighter starts somewhere. At {age}, {name} is still writing the opening chapter of his story in {division}.",
        ]

    # ── Chin concerns tag (any archetype)
    if tag == "chin_concerns":
        return [
            "The chin questions started after the second stoppage. {name}'s {record} record still has value — but opponents are targeting the same spot, and it's working.",
            "Durability has become the headline for {name} in {division}. The {record} record tells part of the story. The stoppages tell the rest.",
            "At {age}, {name} has the skills to compete with anyone in {division}. Whether the chin will let him is the question that keeps getting louder.",
        ]

    # ── At the crossroads tag (any archetype)
    if tag == "at_the_crossroads":
        return [
            "Three fights. Three losses. At {age} and {record}, {name} is at the point every fighter dreads — where the next loss might be the last one that matters.",
            "{name} has been here before — competitive fights, close decisions, brutal finishes. The {record} record is what it is. What happens next defines the career.",
            "Every career has a crossroads. {name}'s is here — {record} in {division}, with the next fight carrying more weight than any that came before it.",
        ]

    # ── GOAT Candidate with goat_watch tag
    if archetype == "GOAT Candidate" and tag == "goat_watch":
        return [
            "The debate has started. {name}'s combination of finishing ability, opposition quality, and consistency is drawing comparisons to the all-time greats in {division}. At {age}, he may not be done building the case.",
            "Nobody wanted to say it first. Then everyone said it at once. {name} is in the conversation — the real one, about where he ranks when it's all over.",
            "The numbers forced the discussion. {name}'s {record} record in {division}, the quality of names on it, and the way the {wins_word} came — it all adds up to something the sport can't ignore.",
        ]

    # ── GOAT Candidate — established (wins 10-19)
    if archetype == "GOAT Candidate" and 10 <= fighter.wins <= 19:
        return [
            "The conversation is starting whether people want to have it or not. {name}'s {record} record, the names on it, and the way the {wins_word} have come are forcing comparisons nobody expected this soon.",
            "{name} doesn't talk about legacy. The {wins_word} do it for him — {ko_wins} finishes, top opposition, zero controversial decisions in the wins column.",
            "At {age} with a {record} record, {name} has moved past the point where {division} can ignore him. The question isn't whether he belongs — it's how high.",
        ]

    # ── GOAT Candidate — early (wins < 10)
    if archetype == "GOAT Candidate" and fighter.wins < 10:
        return [
            "{name} has the tools. At {age} and {record}, it's too early for the bigger conversation — but the foundation is being laid correctly.",
            "The potential is obvious. {name}'s {record} record is built on quality opposition and clean finishes. The next few years will determine how seriously to take the ceiling.",
            "Still early days for {name} in {division}. The {record} record is promising, but the sample size needs to grow before the real comparisons start.",
        ]

    # ── GOAT Candidate — 20+ wins
    if archetype == "GOAT Candidate" and fighter.wins >= 20:
        return [
            "The case is built. {name}'s {record} record in {division} speaks for itself — {wins_word}, elite opposition, and a finish rate that leaves no room for debate.",
            "At {age}, {name} has done everything that can be asked of a {division} fighter. The {record} record is the evidence. The legacy conversation is already underway.",
            "{name} in {division} is no longer a question mark. The {wins_word} against top competition have settled that. What remains is the conversation about where he fits historically.",
        ]

    # ── Developing Phenom (age 22-26, fights 6-15, trajectory rising)
    if archetype == "Phenom" and 22 <= fighter.age <= 26 and stage == "developing" and traj == "rising":
        return [
            "{name} arrived in {division} without much noise. The {wins_word} since have started making some. At {age}, the ceiling is still unclear — but it's high.",
            "The {division} division started paying attention to {name} around win number {wins}. At {age} with a {record} record, the attention is justified.",
            "Some fighters take time to develop. {name} isn't one of them. {wins_word} at {age}, and the performances are getting better each time out.",
        ]

    # ── Peak Phenom (age 23-29, trajectory rising, win_rate > 0.7)
    if archetype == "Phenom" and 23 <= fighter.age <= 29 and traj == "rising" and win_rate > 0.7:
        return [
            "If {name} isn't the best {division} fighter in the world right now, he's close. The {record} record doesn't fully capture how dominant some of these performances have been.",
            "There's a version of {name} that hasn't shown up yet — and the current version is already beating everyone in front of him. That's a problem for the {division} division.",
            "At {age} and {record}, {name} is operating at a level that the rest of {division} hasn't been able to match. The gap is real and it's growing.",
        ]

    # ── Former Phenom (age 30+, was Phenom archetype)
    if archetype == "Phenom" and fighter.age >= 30:
        return [
            "There was a time when {name} was the most talked-about fighter in {division}. At {age} and {record}, the hype has quieted — but the results haven't completely abandoned him.",
            "The prospect label faded years ago. What {name} is building now is something more durable — a career record that holds up on its own without the hype.",
            "At {age}, {name} is no longer the future of {division}. Whether he's still the present is the question he's answering one fight at a time.",
        ]

    # ── Phenom (young, doesn't match developing or peak — fallback)
    if archetype == "Phenom":
        return [
            "At {age}, {name} has already developed the kind of technical package that most {division} fighters spend years building. The results are following the tools.",
            "Youth and skill are a dangerous combination in {division}. {name}, at {age}, has both — and the composure to not waste either.",
            "The trajectory is obvious if you've watched {name} fight. The only question left for the {division} weight class is: how far does it go?",
        ]

    # ── Gatekeeper with ageless_wonder tag
    if archetype == "Gatekeeper" and tag == "ageless_wonder":
        return [
            "At {age}, {name} should be winding down. Instead he's making the {division} division uncomfortable. Some fighters don't read the script.",
            "At {age}, {name} has outlasted most of the {division} fighters he came up with. There's something to be said for durability — and for fighters who refuse to accept what they're supposed to do next.",
            "The {division} division has changed around {name}, but he's still here. At {age}, he remains exactly what he's always been: a problem that needs solving.",
        ]

    # ── Gatekeeper (age 28+, established/veteran stage)
    if archetype == "Gatekeeper" and fighter.age >= 28 and stage in ("established", "veteran", "elder"):
        return [
            "The {division} division needs fighters like {name}. His {record} record is a wall that contenders run into on their way up, and not all of them make it through.",
            "{name} has been in the {division} trenches long enough to have a PhD in the division. At {age} and {record}, he's still here. That's the credential.",
            "Every division needs a {name}. Someone who's seen everything, beaten half the ranked fighters at some point, and still shows up. He's that fighter in {division}.",
        ]

    # ── Gatekeeper fallback
    if archetype == "Gatekeeper":
        return [
            "Some fighters test champions on the way up. {name} has been that test in {division} more than once — and made them work for every second of it.",
            "The {record} record understates what {name} brings into a {division} cage. He's been in there with the best in the world. That experience isn't nothing.",
            "The {division} division is full of hungry contenders. {name} is the fighter who tells you which ones are real — a walking litmus test at the top of the division.",
        ]

    # ── Journeyman with giant_killer tag
    if archetype == "Journeyman" and tag == "giant_killer":
        return [
            "Nobody put {name} on a poster. Nobody picked him to win. That makes the upset even louder. The {division} division's top fighters have been warned.",
            "The {record} record doesn't prepare you for what {name} did to {division}'s top competition. Upsets aren't supposed to happen that cleanly.",
            "Don't let the {losses_word} fool you. {name} is capable of beating anyone in {division} on a given night — and has done exactly that when the moment arrived.",
        ]

    # ── Journeyman (age 28+, OR losses > wins)
    if archetype == "Journeyman" and (fighter.age >= 28 or fighter.losses > fighter.wins):
        return [
            "{name} has never been anyone's pick to win. The {record} record reflects a career spent competing at a level most fighters never reach, against opponents who were supposed to be too good.",
            "The {division} division is full of {name}'s {wins_word}. It's also full of his {losses_word}. At {age} and {career_fights_word} in, he's still competing — which is its own kind of statement.",
            "Comfortable in the role of underdog, {name} has made a career of being underestimated. The {record} record has more footnotes than headlines, but the footnotes are interesting.",
        ]

    # ── Journeyman fallback
    if archetype == "Journeyman":
        return [
            "Not every fight career is a title chase. {name}'s {record} record in {division} is an honest account of a fighter who showed up and competed against serious opposition.",
            "Some fighters exist to test the contenders. {name} has served that role in {division} and done it with more ability than the record suggests.",
            "Nobody put {name} on a poster. He kept fighting anyway. The {division} division is better for it.",
        ]

    # ── Late Bloomer (in prime, age 29-33)
    if archetype == "Late Bloomer" and 29 <= fighter.age <= 33:
        return [
            "{name} spent his twenties being overlooked. At {age}, he's running out of patience for that. The recent fights suggest the division was wrong about him.",
            "Late development doesn't announce itself. {name}'s {record} record in {division} has been building slowly, and then quickly. At {age} he's arrived — just not where anyone expected.",
            "The {division} weight class didn't see {name} coming. At {age} and {record}, the conversation has shifted from whether he belongs to how far he can go.",
        ]

    # ── Late Bloomer (before prime, age < 29)
    if archetype == "Late Bloomer" and fighter.age < 29:
        return [
            "{name} isn't there yet — and at {age} with a {record} record, that's fine. The attributes are developing on a slower curve. The fighters who peak late often peak highest.",
            "Quiet fighter. {record} record. {age} years old. The {division} division hasn't noticed {name} yet. That window is closing.",
            "Development is non-linear. {name}'s {division} career has taken the long route — and is arriving exactly where it was always going, just on a different timeline.",
        ]

    # ── Late Bloomer fallback (past 33)
    if archetype == "Late Bloomer":
        return [
            "The best fighters sometimes need time. {name} has spent a career in {division} building something. The {record} record is starting to show what it is.",
            "At {age}, {name} is in the middle of the career that scouts thought was years away. The {division} weight class is adjusting its expectations accordingly.",
            "Second acts are underrated. {name} in {division} is on one — and the current version of this fighter is more dangerous than the early record suggested.",
        ]

    # ── Shooting Star (before prime_end)
    if archetype == "Shooting Star" and not past_prime:
        return [
            "Everything about {name}'s game is built for highlight reels. The {record} record at {age} is the start of something — the question is how long the rocket burns.",
            "{name} at {age} is the most exciting fighter in {division} on his best nights. The challenge is making best nights the standard.",
            "Brilliant, athletic, and capable of finishing anyone in {division} on a given night. The ceiling is visible. The consistency question will define the career.",
        ]

    # ── Shooting Star (past prime_end, fading)
    if archetype == "Shooting Star" and past_prime:
        return [
            "High peak, steep decline — that's the {name} story so far. At {age}, the tools are still there. The consistency that turns tools into titles has been harder to find.",
            "The burst that announced {name} in {division} may not be sustainable — recent results have raised questions about whether the peak was the starting line or the finish line.",
            "Every fighter runs at a different pace. {name} ran fast and made {division} pay attention. Whether there's fuel for another run is genuinely unclear.",
        ]

    # ── Resilient veteran (past prime, winning record, age 33+)
    if past_prime and win_rate >= 0.5 and fighter.age >= 33:
        return [
            "At {age}, {name} has outlasted the fighters who were supposed to replace him. The {record} record at this stage of a career is either stubbornness or greatness — possibly both.",
            "{name} is still winning fights in {division} at {age}. The division keeps sending new challengers. He keeps sending them back.",
            "Most fighters slow down by {age}. {name} in {division} hasn't received that message. The {record} record at this point speaks louder than any scouting report.",
        ]

    # ── Safe generic fallback
    return [
        "{name} is a {division} fighter with a {record} record at {age} years old.",
        "At {age}, {name} competes in the {division} division with a professional record of {record}.",
        "{name} carries a {record} record into every {division} fight. At {age}, the story is still being written.",
    ]


# ---------------------------------------------------------------------------
# Bio validation
# ---------------------------------------------------------------------------

def _validate_bio(bio: str, fighter, ctx: dict) -> tuple[bool, list[str]]:
    """Check bio for age/career-inappropriate language. Returns (passed, red_flags)."""
    import re
    red_flags = []

    if ctx["career_fights"] < 10 and any(w in bio for w in ["decade", "years of competition", "long career", "veteran"]):
        red_flags.append("veteran language for low fight count")

    if fighter.age < 28 and any(w in bio for w in ["decades", "seen it all", "been around"]):
        red_flags.append("elder language for young fighter")

    if ctx["career_stage"] == "prospect" and any(w in bio for w in ["arrived", "proven", "established"]):
        red_flags.append("established language for prospect")

    # Check pluralization
    if re.search(r'\b1 (wins|losses|draws)\b', bio):
        red_flags.append("pluralization error")

    return len(red_flags) == 0, red_flags


# ---------------------------------------------------------------------------
# Main bio generation entry point
# ---------------------------------------------------------------------------

def generate_fighter_bio(fighter: Fighter) -> str:
    """Return a context-appropriate bio paragraph.

    Uses career context (age, fight count, trajectory, archetype, tags) to
    select the most appropriate template category, then validates the output
    to prevent age/career-inappropriate language.

    NEVER references archetype names in output text.
    """
    ctx = _get_career_context(fighter)

    division = (
        fighter.weight_class.value
        if hasattr(fighter.weight_class, "value")
        else str(fighter.weight_class)
    ).lower()

    # Select templates based on context
    templates = _select_templates(fighter, ctx)
    template = random.choice(templates)

    # Build format values with proper pluralization
    fmt = {
        "name": fighter.name,
        "age": fighter.age,
        "division": division,
        "record": fighter.record,
        "wins": fighter.wins,
        "losses": fighter.losses,
        "ko_wins": fighter.ko_wins,
        "career_fights": ctx["career_fights"],
        "streak": ctx["streak"],
        "wins_word": _plural(fighter.wins, "win", "wins"),
        "losses_word": _plural(fighter.losses, "loss", "losses"),
        "career_fights_word": _plural(ctx["career_fights"], "fight", "fights"),
    }

    bio = template.format(**fmt)

    # Validate — fall back to safe generic if checks fail
    passed, red_flags = _validate_bio(bio, fighter, ctx)
    if not passed:
        bio = f"{fighter.name} is a {division} fighter with a {fighter.record} record at {fighter.age} years old."

    # Append nationality flavor if applicable
    nat_flavor = _nationality_flavor(fighter)
    if nat_flavor:
        bio = bio + " " + nat_flavor

    # Append trait-based sentences
    trait_bio = _build_bio_from_traits(fighter, division)
    if trait_bio:
        bio = bio + " " + trait_bio

    # Confidence-based flavor
    conf = getattr(fighter, "confidence", 70.0) or 70.0
    if conf >= 85:
        bio += f" There's a visible swagger to {fighter.name} right now — a fighter who believes the next win is already his."
    elif conf <= 35:
        bio += f" Something has shifted in {fighter.name}'s demeanor. The hesitation is subtle, but it's there — and at this level, opponents notice."

    # Cornerstone bio paragraph for established cornerstone fighters
    if getattr(fighter, "is_cornerstone", False) and ctx["career_fights"] >= 5:
        bio = bio + f" As a cornerstone of the organization, {fighter.name} carries the weight of the franchise on their shoulders and headlines the biggest events."

    return bio


# ---------------------------------------------------------------------------
# News Headline System
# ---------------------------------------------------------------------------

HEADLINE_TEMPLATES: dict[str, list[str]] = {
    "ko_finish": [
        "{winner} DESTROYS {loser} in R{round} — another devastating knockout",
        "LIGHTS OUT! {winner} flattens {loser} with a vicious R{round} stoppage",
        "{winner} adds another highlight to the reel with R{round} KO of {loser}",
    ],
    "sub_finish": [
        "{winner} taps out {loser} in R{round} — submission artistry on display",
        "SUBMITTED! {loser} had no answer for {winner}'s ground game in R{round}",
    ],
    "upset": [
        "UPSET! {winner} stuns {loser} in a shocking finish nobody saw coming",
        "The betting lines were wrong — {winner} pulls off a massive upset over {loser}",
    ],
    "decision": [
        "{winner} edges out {loser} in a competitive decision",
        "Close fight goes to {winner} over {loser} on the scorecards",
    ],
    "title_fight": [
        "CHAMPION: {winner} claims {division} gold with a dominant performance over {loser}",
        "Title fight delivers — {winner} defeats {loser} for the {division} championship",
    ],
    "streak": [
        "{name} extends win streak to {streak} — who can stop this run?",
        "UNSTOPPABLE: {name} makes it {streak} in a row and the division is on notice",
    ],
    "signing": [
        "BREAKING: {org} signs {name} — a major addition to the roster",
        "Free agent {name} finds a new home with {org}",
    ],
    "retirement_concern": [
        "Is it over? {name} drops {streak}th straight loss as decline continues",
        "Father Time catches up — {name} suffers another defeat, retirement talk grows louder",
    ],
}


def generate_fight_headline(
    winner: Fighter, loser: Fighter, fight: Fight, session: Session
) -> Optional[str]:
    """Generate a news headline for a completed fight. Returns None for mundane fights."""
    method = fight.method.value if hasattr(fight.method, "value") else str(fight.method) if fight.method else ""
    division = winner.weight_class.value if hasattr(winner.weight_class, "value") else str(winner.weight_class)

    # 1. Title fight — always generate
    if fight.is_title_fight:
        template = random.choice(HEADLINE_TEMPLATES["title_fight"])
        return template.format(winner=winner.name, loser=loser.name, division=division)

    # 2. KO/Sub in R1-2
    if method == "KO/TKO" and fight.round_ended and fight.round_ended <= 2:
        template = random.choice(HEADLINE_TEMPLATES["ko_finish"])
        return template.format(winner=winner.name, loser=loser.name, round=fight.round_ended)

    if method == "Submission" and fight.round_ended and fight.round_ended <= 2:
        template = random.choice(HEADLINE_TEMPLATES["sub_finish"])
        return template.format(winner=winner.name, loser=loser.name, round=fight.round_ended)

    # 3. Upset — lower OVR beats higher by 10+
    if loser.overall - winner.overall >= 10:
        template = random.choice(HEADLINE_TEMPLATES["upset"])
        return template.format(winner=winner.name, loser=loser.name)

    # 4. Win streak >= 5
    ws = _win_streak(winner.id, session)
    if ws >= 5:
        template = random.choice(HEADLINE_TEMPLATES["streak"])
        return template.format(name=winner.name, streak=ws)

    # 5. Loss streak >= 3, age > prime_end
    ls = _loss_streak(loser.id, session)
    if ls >= 3 and loser.age > loser.prime_end:
        template = random.choice(HEADLINE_TEMPLATES["retirement_concern"])
        return template.format(name=loser.name, streak=ls)

    # 6. Decision — 50% chance
    if method in ("Unanimous Decision", "Split Decision", "Majority Decision"):
        if random.random() < 0.50:
            template = random.choice(HEADLINE_TEMPLATES["decision"])
            return template.format(winner=winner.name, loser=loser.name)

    return None


def generate_signing_headline(fighter: Fighter, org: Organization) -> Optional[str]:
    """Generate headline for significant AI signings (OVR >= 70)."""
    if fighter.overall < 70:
        return None
    template = random.choice(HEADLINE_TEMPLATES["signing"])
    return template.format(name=fighter.name, org=org.name)
