"""Validation tests for the refactored seed pipeline.

Tests cover: roster scale, weight class distribution, archetype quotas,
career stage distribution, organization distribution, nicknames, and determinism.
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.database import Base
from models.models import (
    Fighter,
    WeightClass,
    Archetype,
    Contract,
    Organization,
    ContractStatus,
)
from simulation.seed import seed_organizations, seed_fighters


@pytest.fixture(scope="module")
def seeded_session():
    """Create in-memory DB, seed orgs + 450 fighters, return session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        orgs = seed_organizations(session)
        fighters = seed_fighters(session, orgs, seed=42)
        session.commit()
        yield session


# ---------------------------------------------------------------------------
# FGEN-02: Scale (400-500 fighters across 5 weight classes)
# ---------------------------------------------------------------------------


class TestScale:
    def test_total_fighter_count(self, seeded_session):
        """Roster should have 400-500 fighters total."""
        count = seeded_session.execute(select(Fighter)).scalars().all()
        assert 400 <= len(count) <= 500, f"Expected 400-500, got {len(count)}"

    def test_weight_class_distribution(self, seeded_session):
        """Each weight class should have 80-100 fighters."""
        for wc in WeightClass:
            fighters = (
                seeded_session.execute(
                    select(Fighter).where(Fighter.weight_class == wc)
                )
                .scalars()
                .all()
            )
            assert 80 <= len(fighters) <= 100, (
                f"{wc.value}: expected 80-100, got {len(fighters)}"
            )


# ---------------------------------------------------------------------------
# FGEN-01: Names (unique, Latin-script, nationality-appropriate)
# ---------------------------------------------------------------------------


class TestNames:
    def test_all_names_unique(self, seeded_session):
        """No duplicate fighter names."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        names = [f.name for f in fighters]
        assert len(names) == len(set(names)), "Duplicate names found"

    def test_nationality_name_correlation(self, seeded_session):
        """Spot-check that nationality-appropriate names are generated.

        Brazilian fighters should have Portuguese-sounding names,
        Russian fighters should have Slavic-sounding names, etc.
        """
        fighters = seeded_session.execute(select(Fighter)).scalars().all()

        # Known name fragments by nationality
        brazilian_fragments = {
            "Silva",
            "Santos",
            "Costa",
            "Souza",
            "Lima",
            "Ferreira",
            "Alves",
            "Pereira",
            "Oliveira",
        }
        russian_fragments = {"ov", "ev", "in", "ko"}  # common surname endings
        dagestani_fragments = {"ov", "ev", "aev"}

        # Check that at least some Brazilian fighters have Portuguese-sounding names
        brazilians = [f for f in fighters if f.nationality == "Brazilian"]
        if brazilians:
            has_match = any(
                any(frag.lower() in f.name.lower() for frag in brazilian_fragments)
                for f in brazilians
            )
            assert has_match, (
                "No Brazilian fighters have Portuguese-sounding last names"
            )

        # Check that Russian fighters have Slavic-sounding names
        russians = [f for f in fighters if f.nationality == "Russian"]
        if russians:
            has_match = any(
                any(frag in f.name.lower() for frag in russian_fragments)
                for f in russians
            )
            assert has_match, "No Russian fighters have Slavic-sounding names"

    def test_names_are_latin_script(self, seeded_session):
        """All names should be ASCII Latin characters."""
        import re

        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        pattern = re.compile(r"^[A-Za-z\s\-\'.]+$")
        for f in fighters:
            assert pattern.match(f.name), (
                f"Non-Latin name: '{f.name}' (nationality={f.nationality})"
            )


class TestPortraits:
    def test_all_seeded_fighters_get_portrait_keys(self, seeded_session):
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        assert fighters
        assert all(getattr(f, "portrait_key", None) for f in fighters)

    def test_portrait_assignment_is_deterministic_for_same_seed(self):
        snapshots = []
        for _ in range(2):
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(engine)
            with Session(engine) as session:
                orgs = seed_organizations(session)
                fighters = seed_fighters(session, orgs, seed=42)
                session.commit()
                snapshots.append(sorted((f.name, f.portrait_key) for f in fighters))
        assert snapshots[0] == snapshots[1]


# ---------------------------------------------------------------------------
# FGEN-03: Archetype distribution (pyramid with quotas)
# ---------------------------------------------------------------------------


class TestArchetypeDistribution:
    def test_no_archetype_exceeds_25_percent(self, seeded_session):
        """No single archetype should exceed 25% of total roster."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        total = len(fighters)
        from collections import Counter

        counts = Counter(
            f.archetype.value if hasattr(f.archetype, "value") else f.archetype
            for f in fighters
        )
        for archetype, count in counts.items():
            pct = count / total * 100
            assert pct <= 25.0, (
                f"{archetype}: {pct:.1f}% exceeds 25% cap ({count}/{total})"
            )

    def test_archetype_pyramid_per_weight_class(self, seeded_session):
        """Per weight class: Journeyman > Gatekeeper > Phenom > Late Bloomer > Shooting Star > GOAT Candidate (with tolerance)."""
        from collections import Counter

        for wc in WeightClass:
            fighters = (
                seeded_session.execute(
                    select(Fighter).where(Fighter.weight_class == wc)
                )
                .scalars()
                .all()
            )
            counts = Counter(
                f.archetype.value if hasattr(f.archetype, "value") else f.archetype
                for f in fighters
            )
            # Verify rough ordering with tolerance (+/-3)
            j = counts.get("Journeyman", 0)
            gk = counts.get("Gatekeeper", 0)
            ph = counts.get("Phenom", 0)
            lb = counts.get("Late Bloomer", 0)
            ss = counts.get("Shooting Star", 0)
            gc = counts.get("GOAT Candidate", 0)
            # Journeyman should be most common
            assert j >= gk - 3, (
                f"{wc.value}: Journeyman ({j}) should be >= Gatekeeper ({gk}) -3"
            )
            assert gk >= ph - 3, (
                f"{wc.value}: Gatekeeper ({gk}) should be >= Phenom ({ph}) -3"
            )
            assert ph >= lb - 3, (
                f"{wc.value}: Phenom ({ph}) should be >= Late Bloomer ({lb}) -3"
            )
            # GOAT Candidate should be rarest
            assert gc <= ss + 3, (
                f"{wc.value}: GOAT Candidate ({gc}) should be <= Shooting Star ({ss}) +3"
            )

    def test_goat_candidates_per_weight_class(self, seeded_session):
        """Each weight class should have 3-7 GOAT Candidates."""
        for wc in WeightClass:
            fighters = (
                seeded_session.execute(
                    select(Fighter).where(
                        Fighter.weight_class == wc,
                        Fighter.archetype == Archetype.GOAT_CANDIDATE,
                    )
                )
                .scalars()
                .all()
            )
            assert 3 <= len(fighters) <= 7, (
                f"{wc.value}: expected 3-7 GOAT Candidates, got {len(fighters)}"
            )


# ---------------------------------------------------------------------------
# FGEN-04: Career stages
# ---------------------------------------------------------------------------


class TestCareerStages:
    def test_career_stage_mix(self, seeded_session):
        """Roster should have roughly 20/35/25/20 split across career stages."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        total = len(fighters)

        prospects = [f for f in fighters if f.age <= 24]
        prime = [f for f in fighters if 25 <= f.age <= 31]
        veterans = [f for f in fighters if f.age >= 32]

        # Allow +/-10% tolerance -- career stage ages overlap (transitional 27-33
        # spans both prime and veteran buckets), so measured percentages have
        # natural variance beyond the target weights
        prospect_pct = len(prospects) / total * 100
        prime_pct = len(prime) / total * 100
        veteran_pct = len(veterans) / total * 100

        assert 10 <= prospect_pct <= 30, (
            f"Prospects: {prospect_pct:.1f}% (expected ~20%)"
        )
        assert 25 <= prime_pct <= 50, f"Prime: {prime_pct:.1f}% (expected ~35%)"
        # Veterans (32+) includes some transitional fighters
        assert 15 <= veteran_pct <= 50, (
            f"Veterans (32+): {veteran_pct:.1f}% (expected ~25-45%)"
        )

    def test_no_contradictions(self, seeded_session):
        """No GOAT Candidate under 25, no Late Bloomer under 25."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        for f in fighters:
            arch = f.archetype.value if hasattr(f.archetype, "value") else f.archetype
            if arch == "GOAT Candidate":
                assert f.age >= 25, f"GOAT Candidate {f.name} is only {f.age}"
            if arch == "Late Bloomer":
                assert f.age >= 25, f"Late Bloomer {f.name} is only {f.age}"


# ---------------------------------------------------------------------------
# FGEN-05: Stat correlation
# ---------------------------------------------------------------------------


class TestStatCorrelation:
    def test_goat_stats_higher_than_journeyman(self, seeded_session):
        """Average overall for GOAT Candidates > average for Journeymen."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        goats = [
            f.overall
            for f in fighters
            if (f.archetype.value if hasattr(f.archetype, "value") else f.archetype)
            == "GOAT Candidate"
        ]
        journeymen = [
            f.overall
            for f in fighters
            if (f.archetype.value if hasattr(f.archetype, "value") else f.archetype)
            == "Journeyman"
        ]
        assert goats and journeymen, "Need both GOAT Candidates and Journeymen"
        avg_goat = sum(goats) / len(goats)
        avg_journeyman = sum(journeymen) / len(journeymen)
        assert avg_goat > avg_journeyman, (
            f"GOAT avg ({avg_goat:.1f}) should be > Journeyman avg ({avg_journeyman:.1f})"
        )

    def test_prospect_stats_lower_than_prime(self, seeded_session):
        """Average overall for prospects (20-24) < average for prime (25-31)."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        prospect_ovr = [f.overall for f in fighters if f.age <= 24]
        prime_ovr = [f.overall for f in fighters if 25 <= f.age <= 31]
        assert prospect_ovr and prime_ovr, "Need both prospects and prime fighters"
        avg_prospect = sum(prospect_ovr) / len(prospect_ovr)
        avg_prime = sum(prime_ovr) / len(prime_ovr)
        assert avg_prospect < avg_prime, (
            f"Prospect avg ({avg_prospect:.1f}) should be < Prime avg ({avg_prime:.1f})"
        )


# ---------------------------------------------------------------------------
# Organization distribution
# ---------------------------------------------------------------------------


class TestOrganizationDistribution:
    def test_free_agent_count(self, seeded_session):
        """10-15% of fighters should have no active contract."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        total = len(fighters)

        # Get fighters with active contracts
        signed_ids = set(
            seeded_session.execute(
                select(Contract.fighter_id).where(
                    Contract.status == ContractStatus.ACTIVE
                )
            )
            .scalars()
            .all()
        )
        unsigned = [f for f in fighters if f.id not in signed_ids]
        pct = len(unsigned) / total * 100
        assert 10 <= pct <= 15, f"Free agents: {pct:.1f}% (expected 10-15%)"

    def test_ucc_talent_quality(self, seeded_session):
        """UCC's average overall should be higher than player org's."""
        orgs = seeded_session.execute(select(Organization)).scalars().all()
        ucc = next(o for o in orgs if "Ultimate" in o.name)
        player = next(o for o in orgs if o.is_player)

        ucc_contracts = (
            seeded_session.execute(
                select(Contract).where(
                    Contract.organization_id == ucc.id,
                    Contract.status == ContractStatus.ACTIVE,
                )
            )
            .scalars()
            .all()
        )
        player_contracts = (
            seeded_session.execute(
                select(Contract).where(
                    Contract.organization_id == player.id,
                    Contract.status == ContractStatus.ACTIVE,
                )
            )
            .scalars()
            .all()
        )

        ucc_fighter_ids = {c.fighter_id for c in ucc_contracts}
        player_fighter_ids = {c.fighter_id for c in player_contracts}

        all_fighters = seeded_session.execute(select(Fighter)).scalars().all()
        fighter_map = {f.id: f for f in all_fighters}

        ucc_avg = sum(fighter_map[fid].overall for fid in ucc_fighter_ids) / len(
            ucc_fighter_ids
        )
        player_avg = sum(fighter_map[fid].overall for fid in player_fighter_ids) / len(
            player_fighter_ids
        )

        assert ucc_avg > player_avg, (
            f"UCC avg ({ucc_avg:.1f}) should be > Player avg ({player_avg:.1f})"
        )


# ---------------------------------------------------------------------------
# Nicknames
# ---------------------------------------------------------------------------


class TestNicknames:
    def test_all_fighters_have_nicknames(self, seeded_session):
        """Every fighter should have a nickname assigned."""
        fighters = seeded_session.execute(select(Fighter)).scalars().all()
        for f in fighters:
            assert f.nickname is not None, f"Fighter {f.name} has no nickname"
            assert len(f.nickname.strip()) > 0, f"Fighter {f.name} has empty nickname"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_deterministic_seeding(self):
        """Running seed_fighters twice with seed=42 should produce same roster."""
        results = []
        for _ in range(2):
            engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(engine)
            with Session(engine) as session:
                orgs = seed_organizations(session)
                fighters = seed_fighters(session, orgs, seed=42)
                session.commit()
                names = sorted([f.name for f in fighters])
                results.append(names)

        assert results[0] == results[1], (
            "Two seed runs with seed=42 produced different rosters"
        )
