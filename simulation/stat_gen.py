"""Archetype/style/career-stage-driven stat generation using numpy distributions.

Generates the 6 core fighter attributes (striking, grappling, wrestling,
cardio, chin, speed) as integers 1-100 using normal distributions
parameterized by archetype profile, style emphasis, and career stage.

All randomness uses numpy.random.Generator for reproducibility.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Core attributes (must match Fighter model)
# ---------------------------------------------------------------------------

ATTRIBUTES: list[str] = [
    "striking", "grappling", "wrestling", "cardio", "chin", "speed",
]

# ---------------------------------------------------------------------------
# Archetype profiles: center/spread define the normal distribution,
# floor/ceiling define the archetype's stat range.
# ---------------------------------------------------------------------------

ARCHETYPE_PROFILES: dict[str, dict[str, int | float]] = {
    "GOAT Candidate": {"center": 85, "spread": 5, "floor": 75, "ceiling": 95},
    "Phenom":         {"center": 72, "spread": 8, "floor": 60, "ceiling": 90},
    "Gatekeeper":     {"center": 62, "spread": 5, "floor": 52, "ceiling": 72},
    "Journeyman":     {"center": 55, "spread": 6, "floor": 40, "ceiling": 68},
    "Late Bloomer":   {"center": 58, "spread": 7, "floor": 45, "ceiling": 75},
    "Shooting Star":  {"center": 70, "spread": 7, "floor": 58, "ceiling": 85},
}

# ---------------------------------------------------------------------------
# Style emphasis: multiplier applied to relevant stats.
# Attributes not listed default to 1.0 (no bias).
# ---------------------------------------------------------------------------

STYLE_EMPHASIS: dict[str, dict[str, float]] = {
    "Striker":      {"striking": 1.15, "speed": 1.10, "grappling": 0.90},
    "Grappler":     {"grappling": 1.15, "wrestling": 1.05, "striking": 0.90},
    "Wrestler":     {"wrestling": 1.15, "cardio": 1.05, "striking": 0.92},
    "Well-Rounded": {},  # no bias
}

# ---------------------------------------------------------------------------
# Career stage modifiers: scale factor range applied to archetype center.
# Each stage defines (low, high) multiplier bounds -- the actual factor
# is sampled uniformly from this range for each stat independently.
# ---------------------------------------------------------------------------

CAREER_STAGE_MODIFIERS: dict[str, tuple[float, float]] = {
    "prospect":      (0.60, 0.75),   # room to grow: 60-75% of center
    "prime":         (0.95, 1.05),   # near peak: 95-105% of center
    "veteran":       (0.85, 0.95),   # slightly declining from peak
    "transitional":  (0.80, 0.90),   # mid-transition
}

# ---------------------------------------------------------------------------
# Overall rating weights (must match Fighter.overall property in models.py)
# ---------------------------------------------------------------------------

_OVERALL_WEIGHTS: dict[str, float] = {
    "striking":  0.20,
    "grappling": 0.20,
    "wrestling": 0.15,
    "cardio":    0.15,
    "chin":      0.15,
    "speed":     0.15,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_stats(
    archetype: str,
    style: str,
    career_stage: str,
    rng: np.random.Generator,
) -> dict[str, int]:
    """Generate the 6 core fighter attributes based on archetype, style, and career stage.

    Args:
        archetype: One of the keys in ARCHETYPE_PROFILES (e.g. "GOAT Candidate").
        style: One of the keys in STYLE_EMPHASIS (e.g. "Striker", "Well-Rounded").
        career_stage: One of the keys in CAREER_STAGE_MODIFIERS.
        rng: Seeded numpy random Generator for reproducibility.

    Returns:
        Dict with keys "striking", "grappling", "wrestling", "cardio", "chin", "speed",
        each an integer in [1, 100].
    """
    profile = ARCHETYPE_PROFILES[archetype]
    emphasis = STYLE_EMPHASIS.get(style, {})
    stage_low, stage_high = CAREER_STAGE_MODIFIERS[career_stage]

    stats: dict[str, int] = {}
    for attr in ATTRIBUTES:
        # Draw base value from normal distribution centered on archetype
        base = rng.normal(loc=profile["center"], scale=profile["spread"])

        # Apply career stage modifier (uniform within stage range)
        stage_factor = rng.uniform(stage_low, stage_high)
        base = base * stage_factor

        # Apply style emphasis multiplier
        multiplier = emphasis.get(attr, 1.0)
        val = base * multiplier

        # Clip to valid range and round to int
        val = int(round(float(np.clip(val, 1, 100))))
        stats[attr] = val

    return stats


def compute_overall(stats: dict[str, int]) -> int:
    """Compute weighted overall rating matching Fighter.overall property.

    Args:
        stats: Dict with the 6 core attribute values.

    Returns:
        Integer overall rating in [1, 100].
    """
    total = sum(stats[attr] * weight for attr, weight in _OVERALL_WEIGHTS.items())
    return int(round(total))
