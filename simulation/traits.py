"""Fighter trait definitions for FighterSim.

Traits are permanent attributes assigned at creation that affect simulation
behaviour, narrative generation, and hype dynamics. Each fighter has 1-3 traits.
"""

from __future__ import annotations

TRAITS: dict[str, dict] = {
    "iron_chin": {
        "label": "Iron Chin",
        "description": "Absorbs punishment that would stop others.",
        "effect": {"chin_bonus": 8, "ko_resistance": 0.15},
    },
    "gas_tank": {
        "label": "Gas Tank",
        "description": "Cardio barely decays. Dangerous in championship rounds.",
        "effect": {"cardio_decay_multiplier": 0.4},
    },
    "slow_starter": {
        "label": "Slow Starter",
        "description": "Needs time to warm up. Round 1 output is reduced.",
        "effect": {"round1_penalty": 0.15, "late_round_bonus": 0.10},
    },
    "pressure_fighter": {
        "label": "Pressure Fighter",
        "description": "Performs better when opponent is hurt or tired.",
        "effect": {"damage_bonus_vs_hurt": 0.20},
    },
    "submission_magnet": {
        "label": "Submission Magnet",
        "description": "Something about their base leaves them vulnerable on the ground.",
        "effect": {"sub_vulnerability": 0.20},
    },
    "knockout_artist": {
        "label": "Knockout Artist",
        "description": "One punch can end it at any moment.",
        "effect": {"one_punch_ko_chance": 0.05},
    },
    "media_darling": {
        "label": "Media Darling",
        "description": "The cameras love them. Hype decays slower.",
        "effect": {"hype_decay_multiplier": 0.40, "popularity_gain_multiplier": 1.30},
    },
    "journeyman_heart": {
        "label": "Journeyman Heart",
        "description": "Never stops competing. Never gets counted out.",
        "effect": {"prevent_fading_tag": True, "chin_bonus": 4},
    },
    "fast_hands": {
        "label": "Fast Hands",
        "description": "Striking speed that makes up for power deficits.",
        "effect": {"speed_bonus": 6, "first_strike_advantage": 0.10},
    },
    "ground_and_pound_specialist": {
        "label": "Ground & Pound",
        "description": "Devastating once the fight hits the mat.",
        "effect": {"gnp_damage_bonus": 0.25},
    },
    "comeback_king": {
        "label": "Comeback King",
        "description": "Fights back hardest when hurt. Never truly out of it.",
        "effect": {"hurt_resistance": 0.15, "comeback_damage_bonus": 0.20},
    },
    "veteran_iq": {
        "label": "Veteran IQ",
        "description": "Reads opponents better with experience. Gets smarter with age.",
        "effect": {"age_decline_delay": 2, "late_career_bonus": 0.10},
    },
}

# Traits that cannot coexist on the same fighter
CONTRADICTIONS: dict[str, set[str]] = {
    "slow_starter": {"fast_hands"},
    "fast_hands": {"slow_starter"},
}


def contradicts(trait: str, existing: list[str]) -> bool:
    """Return True if adding trait conflicts with an already-assigned trait."""
    blocked = CONTRADICTIONS.get(trait, set())
    return bool(blocked & set(existing))
