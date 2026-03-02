"""Tests for simulation.name_gen -- nationality-appropriate name generation."""

import random
import re

import pytest

from simulation.name_gen import (
    NATIONALITY_LOCALE_MAP,
    NATIONALITY_WEIGHTS,
    ROMANIZED_NAMES,
    create_faker_instances,
    generate_name,
    pick_nationality,
)

# Regex: Latin script only (letters, spaces, hyphens, apostrophes, periods)
LATIN_RE = re.compile(r"^[A-Za-z\s\-\'.]+$")


@pytest.fixture
def faker_instances():
    """Create seeded Faker instances for all locales."""
    return create_faker_instances(seed=42)


@pytest.fixture
def rng():
    """Create a seeded stdlib RNG."""
    return random.Random(42)


# ---- Basic nationality tests ------------------------------------------------


def test_american_name(faker_instances, rng):
    """American names should be Latin-script with first and last parts."""
    name = generate_name("American", faker_instances, rng, set())
    assert " " in name, f"Name should have first and last: {name}"
    assert LATIN_RE.match(name), f"Non-Latin characters in: {name}"


def test_brazilian_name(faker_instances, rng):
    """Brazilian names should be Portuguese-appropriate."""
    name = generate_name("Brazilian", faker_instances, rng, set())
    assert " " in name, f"Name should have first and last: {name}"
    assert LATIN_RE.match(name), f"Non-Latin characters in: {name}"


def test_russian_name(faker_instances, rng):
    """Russian names should be romanized (no Cyrillic)."""
    name = generate_name("Russian", faker_instances, rng, set())
    assert " " in name, f"Name should have first and last: {name}"
    assert LATIN_RE.match(name), f"Cyrillic detected in: {name}"
    # Verify it comes from romanized pool
    first = name.split()[0]
    assert first in ROMANIZED_NAMES["Russian"]["first"], (
        f"First name '{first}' not in romanized Russian pool"
    )


def test_dagestani_name(faker_instances, rng):
    """Dagestani names should come from hardcoded romanized list."""
    name = generate_name("Dagestani", faker_instances, rng, set())
    assert " " in name, f"Name should have first and last: {name}"
    assert LATIN_RE.match(name), f"Non-Latin characters in: {name}"
    first = name.split()[0]
    assert first in ROMANIZED_NAMES["Dagestani"]["first"], (
        f"First name '{first}' not in romanized Dagestani pool"
    )


def test_japanese_name(faker_instances, rng):
    """Japanese names should be romanized Latin-script."""
    name = generate_name("Japanese", faker_instances, rng, set())
    assert " " in name, f"Name should have first and last: {name}"
    assert LATIN_RE.match(name), f"Non-Latin characters in: {name}"


def test_south_korean_name(faker_instances, rng):
    """South Korean names should be romanized (no Hangul)."""
    name = generate_name("South Korean", faker_instances, rng, set())
    assert " " in name, f"Name should have first and last: {name}"
    assert LATIN_RE.match(name), f"Hangul detected in: {name}"
    last = name.split()[-1]
    assert last in ROMANIZED_NAMES["South Korean"]["last"], (
        f"Last name '{last}' not in romanized Korean pool"
    )


def test_georgian_name(faker_instances, rng):
    """Georgian names should be romanized (no Georgian script)."""
    name = generate_name("Georgian", faker_instances, rng, set())
    assert " " in name, f"Name should have first and last: {name}"
    assert LATIN_RE.match(name), f"Georgian script detected in: {name}"
    first = name.split()[0]
    assert first in ROMANIZED_NAMES["Georgian"]["first"], (
        f"First name '{first}' not in romanized Georgian pool"
    )


# ---- Uniqueness test --------------------------------------------------------


def test_500_unique_names(faker_instances, rng):
    """500 names generated with unique name tracking should have no duplicates."""
    used_names = set()
    all_nationalities = (
        list(NATIONALITY_LOCALE_MAP.keys())
        + list(ROMANIZED_NAMES.keys())
        + ["Japanese"]
    )
    # Remove dupes from combined list
    all_nationalities = list(dict.fromkeys(all_nationalities))

    names = []
    for i in range(500):
        nat = all_nationalities[i % len(all_nationalities)]
        name = generate_name(nat, faker_instances, rng, used_names)
        names.append(name)

    assert len(names) == 500
    assert len(set(names)) == 500, (
        f"Found duplicates: {len(names) - len(set(names))} collisions"
    )


# ---- Latin-script-only test -------------------------------------------------


def test_all_names_latin_script(faker_instances, rng):
    """Every nationality must produce Latin-script-only names."""
    all_nationalities = (
        list(NATIONALITY_LOCALE_MAP.keys())
        + list(ROMANIZED_NAMES.keys())
        + ["Japanese"]
    )
    all_nationalities = list(dict.fromkeys(all_nationalities))

    used = set()
    for nat in all_nationalities:
        for _ in range(10):
            name = generate_name(nat, faker_instances, rng, used)
            assert LATIN_RE.match(name), (
                f"Non-Latin characters for {nat}: {name}"
            )


# ---- Determinism test -------------------------------------------------------


def test_deterministic_same_seed():
    """Same seed must produce the exact same name sequence.

    Faker.seed() is global, so we must generate each run fully before
    re-seeding and generating the comparison run.
    """
    nationalities = ["American", "Brazilian", "Russian", "Japanese", "Dagestani",
                     "South Korean", "Georgian", "British", "Mexican", "Polish"]

    # Run 1
    instances1 = create_faker_instances(seed=99)
    rng1 = random.Random(99)
    used1 = set()
    names1 = [generate_name(nat, instances1, rng1, used1) for nat in nationalities]

    # Run 2 (re-seeds Faker globally)
    instances2 = create_faker_instances(seed=99)
    rng2 = random.Random(99)
    used2 = set()
    names2 = [generate_name(nat, instances2, rng2, used2) for nat in nationalities]

    assert names1 == names2, f"Determinism broken:\n{names1}\nvs\n{names2}"


# ---- pick_nationality test ---------------------------------------------------


def test_pick_nationality_returns_valid():
    """pick_nationality must return a nationality in our mapping."""
    rng = random.Random(42)
    valid = set(NATIONALITY_LOCALE_MAP.keys()) | set(ROMANIZED_NAMES.keys()) | {"Japanese"}
    for _ in range(100):
        nat = pick_nationality(rng)
        assert nat in valid, f"Unknown nationality: {nat}"


def test_nationality_weights_sum():
    """All nationality weights should be defined and positive."""
    all_nats = set(NATIONALITY_LOCALE_MAP.keys()) | set(ROMANIZED_NAMES.keys()) | {"Japanese"}
    for nat in all_nats:
        assert nat in NATIONALITY_WEIGHTS, f"Missing weight for {nat}"
        assert NATIONALITY_WEIGHTS[nat] > 0, f"Non-positive weight for {nat}"
