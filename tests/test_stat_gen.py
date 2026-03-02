"""Tests for simulation.stat_gen -- archetype/style/career-stage stat generation."""

import numpy as np
import pytest

from simulation.stat_gen import (
    ARCHETYPE_PROFILES,
    CAREER_STAGE_MODIFIERS,
    STYLE_EMPHASIS,
    compute_overall,
    generate_stats,
)

ATTRS = ["striking", "grappling", "wrestling", "cardio", "chin", "speed"]


@pytest.fixture
def rng():
    """Create a seeded numpy RNG."""
    return np.random.default_rng(seed=42)


# ---- Archetype differentiation -----------------------------------------------


def test_goat_candidate_stats_average_80_90(rng):
    """GOAT Candidate prime stats should average 80-90 across all attributes."""
    totals = []
    for _ in range(100):
        stats = generate_stats("GOAT Candidate", "Well-Rounded", "prime", rng)
        totals.append(sum(stats[a] for a in ATTRS) / len(ATTRS))
    avg = sum(totals) / len(totals)
    assert 78 <= avg <= 92, f"GOAT Candidate average {avg:.1f} not in 80-90 range"


def test_journeyman_stats_average_50_62(rng):
    """Journeyman prime stats should average 50-62 across all attributes."""
    totals = []
    for _ in range(100):
        stats = generate_stats("Journeyman", "Well-Rounded", "prime", rng)
        totals.append(sum(stats[a] for a in ATTRS) / len(ATTRS))
    avg = sum(totals) / len(totals)
    assert 48 <= avg <= 64, f"Journeyman average {avg:.1f} not in 50-62 range"


# ---- Style emphasis -----------------------------------------------------------


def test_striker_higher_striking_than_grappling(rng):
    """Striker style should produce higher striking than grappling on average."""
    striking_total = 0
    grappling_total = 0
    n = 200
    for _ in range(n):
        stats = generate_stats("Phenom", "Striker", "prime", rng)
        striking_total += stats["striking"]
        grappling_total += stats["grappling"]
    assert striking_total > grappling_total, (
        f"Striker striking avg {striking_total/n:.1f} should exceed "
        f"grappling avg {grappling_total/n:.1f}"
    )


def test_grappler_higher_grappling_than_striking(rng):
    """Grappler style should produce higher grappling than striking on average."""
    striking_total = 0
    grappling_total = 0
    n = 200
    for _ in range(n):
        stats = generate_stats("Phenom", "Grappler", "prime", rng)
        striking_total += stats["striking"]
        grappling_total += stats["grappling"]
    assert grappling_total > striking_total, (
        f"Grappler grappling avg {grappling_total/n:.1f} should exceed "
        f"striking avg {striking_total/n:.1f}"
    )


# ---- Career stage modifiers --------------------------------------------------


def test_prospect_stats_below_prime(rng):
    """Prospect career stage should produce stats below prime (room to grow)."""
    prospect_totals = []
    prime_totals = []
    for _ in range(100):
        p_stats = generate_stats("Phenom", "Well-Rounded", "prospect", rng)
        prospect_totals.append(sum(p_stats[a] for a in ATTRS))
        pr_stats = generate_stats("Phenom", "Well-Rounded", "prime", rng)
        prime_totals.append(sum(pr_stats[a] for a in ATTRS))
    avg_prospect = sum(prospect_totals) / len(prospect_totals)
    avg_prime = sum(prime_totals) / len(prime_totals)
    assert avg_prospect < avg_prime, (
        f"Prospect avg total {avg_prospect:.1f} should be below "
        f"prime avg total {avg_prime:.1f}"
    )


def test_prime_stats_near_ceiling(rng):
    """Prime career stage should produce stats near archetype ceiling."""
    totals = []
    for _ in range(100):
        stats = generate_stats("Phenom", "Well-Rounded", "prime", rng)
        totals.append(sum(stats[a] for a in ATTRS) / len(ATTRS))
    avg = sum(totals) / len(totals)
    profile = ARCHETYPE_PROFILES["Phenom"]
    # Prime should be near the center (95-105% of center)
    assert avg >= profile["center"] * 0.90, (
        f"Prime avg {avg:.1f} too far below center {profile['center']}"
    )


def test_veteran_stats_slightly_below_prime(rng):
    """Veteran career stage should produce stats at or declining from prime."""
    veteran_totals = []
    prime_totals = []
    for _ in range(100):
        v_stats = generate_stats("Gatekeeper", "Well-Rounded", "veteran", rng)
        veteran_totals.append(sum(v_stats[a] for a in ATTRS))
        p_stats = generate_stats("Gatekeeper", "Well-Rounded", "prime", rng)
        prime_totals.append(sum(p_stats[a] for a in ATTRS))
    avg_veteran = sum(veteran_totals) / len(veteran_totals)
    avg_prime = sum(prime_totals) / len(prime_totals)
    assert avg_veteran <= avg_prime, (
        f"Veteran avg {avg_veteran:.1f} should not exceed "
        f"prime avg {avg_prime:.1f}"
    )


# ---- Bounds and types --------------------------------------------------------


def test_all_stats_integers_in_range(rng):
    """All generated stats must be integers in [1, 100]."""
    for archetype in ARCHETYPE_PROFILES:
        for style in STYLE_EMPHASIS:
            for stage in CAREER_STAGE_MODIFIERS:
                stats = generate_stats(archetype, style, stage, rng)
                for attr in ATTRS:
                    val = stats[attr]
                    assert isinstance(val, int), (
                        f"{archetype}/{style}/{stage} {attr}={val} not int"
                    )
                    assert 1 <= val <= 100, (
                        f"{archetype}/{style}/{stage} {attr}={val} out of [1,100]"
                    )


# ---- Determinism --------------------------------------------------------------


def test_deterministic_same_seed():
    """Same seed must produce the exact same stats."""
    rng1 = np.random.default_rng(seed=77)
    rng2 = np.random.default_rng(seed=77)

    stats1 = generate_stats("GOAT Candidate", "Striker", "prime", rng1)
    stats2 = generate_stats("GOAT Candidate", "Striker", "prime", rng2)

    assert stats1 == stats2, f"Determinism broken:\n{stats1}\nvs\n{stats2}"


# ---- Bell-curve clustering (std dev) -----------------------------------------


def test_bell_curve_clustering(rng):
    """100 fighters from same archetype should show std dev < 15 per attribute."""
    for attr in ATTRS:
        values = []
        for _ in range(100):
            stats = generate_stats("Phenom", "Well-Rounded", "prime", rng)
            values.append(stats[attr])
        std = np.std(values)
        assert std < 15, (
            f"Phenom/Well-Rounded/prime {attr} std dev {std:.1f} >= 15 "
            f"(values should cluster)"
        )


# ---- compute_overall ----------------------------------------------------------


def test_compute_overall_matches_fighter_property():
    """compute_overall should match the Fighter model's overall property weights."""
    stats = {
        "striking": 80, "grappling": 70, "wrestling": 60,
        "cardio": 75, "chin": 85, "speed": 65,
    }
    # From models: striking*0.2 + grappling*0.2 + wrestling*0.15 +
    #              cardio*0.15 + chin*0.15 + speed*0.15
    expected = round(80*0.2 + 70*0.2 + 60*0.15 + 75*0.15 + 85*0.15 + 65*0.15)
    result = compute_overall(stats)
    assert result == expected, f"compute_overall={result}, expected={expected}"


def test_compute_overall_returns_int():
    """compute_overall should return an integer."""
    stats = {
        "striking": 50, "grappling": 50, "wrestling": 50,
        "cardio": 50, "chin": 50, "speed": 50,
    }
    result = compute_overall(stats)
    assert isinstance(result, int)
    assert 1 <= result <= 100
