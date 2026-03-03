"""TDD tests for fight-history paragraph generator and career highlights extractor.

Tests for Phase 03-01: generate_fight_history_paragraph() and extract_career_highlights()
in simulation/narrative.py.
"""
import os
import sys
import unittest
from datetime import date

from sqlalchemy import create_engine, select, or_
from sqlalchemy.orm import Session

from models.models import (
    Base, Fighter, Fight, Event, Ranking, Organization,
    WeightClass, FightMethod, FighterStyle, Archetype, EventStatus,
)


DB_PATH = "mma_test_narrative.db"
DB_URL = f"sqlite:///{DB_PATH}"


def _make_fighter(session, name, age=28, wins=10, losses=2, draws=0,
                  ko_wins=5, sub_wins=2, weight_class=WeightClass.WELTERWEIGHT,
                  archetype=Archetype.JOURNEYMAN, rivalry_with=None,
                  prime_start=25, prime_end=32, **kwargs):
    """Helper to create a Fighter with sane defaults."""
    f = Fighter(
        name=name, age=age, nationality="American",
        weight_class=weight_class, style=FighterStyle.STRIKER,
        striking=70, grappling=65, wrestling=60, cardio=70, chin=70, speed=65,
        wins=wins, losses=losses, draws=draws, ko_wins=ko_wins, sub_wins=sub_wins,
        prime_start=prime_start, prime_end=prime_end,
        archetype=archetype, rivalry_with=rivalry_with,
        confidence=70.0, popularity=50.0, hype=50.0,
        **kwargs,
    )
    session.add(f)
    session.flush()
    return f


def _make_event(session, name="Test Event 1", event_date=None, org_id=1):
    """Helper to create an Event."""
    e = Event(
        name=name,
        event_date=event_date or date(2024, 6, 15),
        venue="Test Arena",
        organization_id=org_id,
        status=EventStatus.COMPLETED,
    )
    session.add(e)
    session.flush()
    return e


def _make_fight(session, event, fighter_a, fighter_b, winner,
                method=FightMethod.KO_TKO, round_ended=2,
                is_title_fight=False, card_position=1):
    """Helper to create a Fight result."""
    f = Fight(
        event_id=event.id,
        fighter_a_id=fighter_a.id,
        fighter_b_id=fighter_b.id,
        weight_class=fighter_a.weight_class,
        winner_id=winner.id if winner else None,
        method=method,
        round_ended=round_ended,
        time_ended="2:30",
        is_title_fight=is_title_fight,
        card_position=card_position,
    )
    session.add(f)
    session.flush()
    return f


class TestFightHistoryParagraph(unittest.TestCase):
    """Tests for generate_fight_history_paragraph()."""

    @classmethod
    def setUpClass(cls):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        cls.engine = create_engine(DB_URL)
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

    def setUp(self):
        self.session = Session(self.engine)
        # Create a default org
        org = Organization(name="Test Org", prestige=80.0, bank_balance=1_000_000)
        self.session.add(org)
        self.session.flush()
        self.org = org

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_zero_fights_returns_empty_string(self):
        """Fighter with 0 fights returns empty string."""
        from simulation.narrative import generate_fight_history_paragraph
        f = _make_fighter(self.session, "Zero Fights Guy", wins=0, losses=0, draws=0, ko_wins=0, sub_wins=0)
        result = generate_fight_history_paragraph(f, self.session)
        self.assertEqual(result, "")

    def test_one_fight_debut_win(self):
        """Fighter with 1 fight (debut win) returns single-sentence paragraph mentioning opponent name and method."""
        from simulation.narrative import generate_fight_history_paragraph
        fighter = _make_fighter(self.session, "Debut Winner", wins=1, losses=0, draws=0,
                               ko_wins=1, sub_wins=0, age=22,
                               archetype=Archetype.PHENOM)
        opponent = _make_fighter(self.session, "Opponent Jones", wins=5, losses=3)
        event = _make_event(self.session, "UCC 1", date(2024, 1, 15), self.org.id)
        _make_fight(self.session, event, fighter, opponent, winner=fighter,
                    method=FightMethod.KO_TKO, round_ended=1)
        self.session.flush()

        result = generate_fight_history_paragraph(fighter, self.session)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0, "Should produce some text for a debut win")
        # Should mention the opponent by name
        self.assertIn("Jones", result, "Paragraph should mention opponent's last name")

    def test_veteran_with_many_fights(self):
        """Fighter with 10+ fights returns paragraph with 3-4 fight references."""
        from simulation.narrative import generate_fight_history_paragraph
        fighter = _make_fighter(self.session, "Veteran Vic", wins=15, losses=5, draws=0,
                               ko_wins=8, sub_wins=3, age=34,
                               archetype=Archetype.GATEKEEPER,
                               prime_start=26, prime_end=33)
        # Create 15+ opponents and fights
        opponents = []
        for i in range(20):
            opp = _make_fighter(self.session, f"Opp_{i} Fighter{i}", wins=5+i, losses=3)
            opponents.append(opp)

        for i in range(20):
            event = _make_event(self.session, f"UCC {i+1}",
                               date(2022, 1, 1 + i) if i < 28 else date(2022, 2, i - 27),
                               self.org.id)
            winner = fighter if i < 15 else opponents[i]
            method = FightMethod.KO_TKO if i % 3 == 0 else FightMethod.UNANIMOUS_DECISION
            _make_fight(self.session, event, fighter, opponents[i],
                        winner=winner, method=method, round_ended=2)
        self.session.flush()

        result = generate_fight_history_paragraph(fighter, self.session)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 50, "Veteran paragraph should be substantial")

    def test_rivalry_with_shared_fights(self):
        """Fighter with rivalry_with set and shared fights produces paragraph mentioning the rival."""
        from simulation.narrative import generate_fight_history_paragraph
        rival = _make_fighter(self.session, "Rival Rodriguez", wins=12, losses=4)
        fighter = _make_fighter(self.session, "Rivalry Rex", wins=10, losses=3, draws=0,
                               ko_wins=5, sub_wins=2, age=30,
                               archetype=Archetype.PHENOM,
                               rivalry_with=rival.id)
        # Create some fights, including shared fights with the rival
        opponents = [rival]
        for i in range(8):
            opp = _make_fighter(self.session, f"Other_{i} Opp{i}", wins=5+i, losses=2)
            opponents.append(opp)

        for i, opp in enumerate(opponents):
            event = _make_event(self.session, f"Event {i+100}",
                               date(2023, 1 + (i % 12), 15), self.org.id)
            _make_fight(self.session, event, fighter, opp, winner=fighter,
                        method=FightMethod.KO_TKO, round_ended=2)

        # Add a second fight with the rival
        event2 = _make_event(self.session, "Rematch Night", date(2024, 6, 1), self.org.id)
        _make_fight(self.session, event2, fighter, rival, winner=rival,
                    method=FightMethod.SPLIT_DECISION, round_ended=3)
        self.session.flush()

        result = generate_fight_history_paragraph(fighter, self.session)
        self.assertIn("Rodriguez", result,
                      "Paragraph should mention rivalry opponent by name")

    def test_rivalry_without_shared_fights(self):
        """Fighter with rivalry_with set but NO shared fights mentions rivalry without citing specific bout."""
        from simulation.narrative import generate_fight_history_paragraph
        rival = _make_fighter(self.session, "Distant Rival Davis", wins=8, losses=2)
        fighter = _make_fighter(self.session, "Rivalry Without Fights", wins=6, losses=2,
                               ko_wins=3, sub_wins=1, age=27,
                               archetype=Archetype.PHENOM,
                               rivalry_with=rival.id)
        # Create fights but NONE with the rival
        for i in range(6):
            opp = _make_fighter(self.session, f"NonRival_{i} Person{i}", wins=4, losses=2)
            event = _make_event(self.session, f"Solo Event {i+200}",
                               date(2023, 3 + i, 10), self.org.id)
            _make_fight(self.session, event, fighter, opp, winner=fighter,
                        method=FightMethod.UNANIMOUS_DECISION, round_ended=3)
        self.session.flush()

        result = generate_fight_history_paragraph(fighter, self.session)
        self.assertIn("Davis", result,
                      "Should mention the rival by name even without shared fights")

    def test_current_champion_language(self):
        """Current champion (rank 1 in Ranking table) gets champion language."""
        from simulation.narrative import generate_fight_history_paragraph
        fighter = _make_fighter(self.session, "Champ McChampface", wins=15, losses=1,
                               ko_wins=10, sub_wins=3, age=29,
                               archetype=Archetype.GOAT_CANDIDATE)
        # Create ranking entry: rank 1
        r = Ranking(
            weight_class=WeightClass.WELTERWEIGHT,
            fighter_id=fighter.id,
            rank=1,
            score=100.0,
        )
        self.session.add(r)

        # Create enough fights
        for i in range(15):
            opp = _make_fighter(self.session, f"ChampOpp_{i} X{i}", wins=5, losses=3)
            event = _make_event(self.session, f"Champ Event {i+300}",
                               date(2023, 1 + (i % 12), 10), self.org.id)
            _make_fight(self.session, event, fighter, opp, winner=fighter,
                        method=FightMethod.KO_TKO, round_ended=2,
                        is_title_fight=(i >= 12))
        self.session.flush()

        result = generate_fight_history_paragraph(fighter, self.session)
        # Should contain champion-related language
        champion_words = ["champion", "championship", "crown", "belt", "title", "gold"]
        has_champion_language = any(w in result.lower() for w in champion_words)
        self.assertTrue(has_champion_language,
                        f"Champion should get champion language. Got: {result[:200]}")

    def test_former_champion_language(self):
        """Former champion (title fight wins but not rank 1) gets former champion language."""
        from simulation.narrative import generate_fight_history_paragraph
        fighter = _make_fighter(self.session, "Former Champ Fernando", wins=12, losses=4,
                               ko_wins=7, sub_wins=2, age=33,
                               archetype=Archetype.GATEKEEPER,
                               prime_start=26, prime_end=32)
        # Create ranking entry: NOT rank 1
        r = Ranking(
            weight_class=WeightClass.WELTERWEIGHT,
            fighter_id=fighter.id,
            rank=5,
            score=70.0,
        )
        self.session.add(r)

        # Create fights, some as title fights won
        for i in range(12):
            opp = _make_fighter(self.session, f"FormerOpp_{i} Y{i}", wins=5, losses=3)
            event = _make_event(self.session, f"Former Event {i+400}",
                               date(2022, 1 + (i % 12), 10), self.org.id)
            _make_fight(self.session, event, fighter, opp,
                        winner=fighter if i < 10 else opp,
                        method=FightMethod.KO_TKO, round_ended=2,
                        is_title_fight=(i in [8, 9, 10, 11]))
        self.session.flush()

        result = generate_fight_history_paragraph(fighter, self.session)
        former_words = ["former", "once held", "once wore", "previously held", "belt", "title", "champion"]
        has_former_language = any(w in result.lower() for w in former_words)
        self.assertTrue(has_former_language,
                        f"Former champion should get former champion language. Got: {result[:200]}")

    def test_different_archetypes_produce_different_word_choices(self):
        """Different archetypes produce different word choices for the same method."""
        from simulation.narrative import generate_fight_history_paragraph
        # Create two fighters with same stats but different archetypes
        goat = _make_fighter(self.session, "GOAT Guy Alpha", wins=15, losses=1,
                             ko_wins=10, sub_wins=3, age=29,
                             archetype=Archetype.GOAT_CANDIDATE)
        journeyman = _make_fighter(self.session, "Journey John Beta", wins=15, losses=8,
                                   ko_wins=5, sub_wins=2, age=30,
                                   archetype=Archetype.JOURNEYMAN)

        # Give both the same fight history
        for fighter in [goat, journeyman]:
            for i in range(15):
                opp = _make_fighter(self.session, f"Arch_{fighter.id}_{i} Opp{i}", wins=5, losses=3)
                event = _make_event(self.session, f"Arch Event {fighter.id}_{i}",
                                   date(2023, 1 + (i % 12), 10), self.org.id)
                _make_fight(self.session, event, fighter, opp,
                            winner=fighter,
                            method=FightMethod.KO_TKO, round_ended=2)
        self.session.flush()

        goat_para = generate_fight_history_paragraph(goat, self.session)
        journeyman_para = generate_fight_history_paragraph(journeyman, self.session)

        # The paragraphs should be different (different tone/word choices)
        self.assertNotEqual(goat_para, journeyman_para,
                           "GOAT Candidate and Journeyman should produce different paragraphs")

    def test_different_stages_produce_different_structure(self):
        """Prospect and veteran produce noticeably different narrative structure."""
        from simulation.narrative import generate_fight_history_paragraph
        prospect = _make_fighter(self.session, "Young Prospect Pete", wins=2, losses=0,
                                 ko_wins=1, sub_wins=1, age=21,
                                 archetype=Archetype.PHENOM,
                                 prime_start=24, prime_end=32)
        veteran = _make_fighter(self.session, "Old Vet Victor", wins=20, losses=8,
                                ko_wins=12, sub_wins=4, age=36,
                                archetype=Archetype.GATEKEEPER,
                                prime_start=26, prime_end=33)

        # Give prospect 2 fights
        for i in range(2):
            opp = _make_fighter(self.session, f"ProspOpp_{i} X{i}", wins=3, losses=2)
            event = _make_event(self.session, f"Prospect Event {i+500}",
                               date(2024, 6 + i, 10), self.org.id)
            _make_fight(self.session, event, prospect, opp, winner=prospect,
                        method=FightMethod.KO_TKO, round_ended=1)

        # Give veteran 20 fights
        for i in range(20):
            opp = _make_fighter(self.session, f"VetOpp_{i} Y{i}", wins=5+i, losses=3)
            event = _make_event(self.session, f"Vet Event {i+600}",
                               date(2020 + (i // 12), 1 + (i % 12), 10), self.org.id)
            winner = veteran if i < 16 else opp
            _make_fight(self.session, event, veteran, opp, winner=winner,
                        method=FightMethod.KO_TKO if i % 2 == 0 else FightMethod.UNANIMOUS_DECISION,
                        round_ended=2)
        self.session.flush()

        prospect_para = generate_fight_history_paragraph(prospect, self.session)
        veteran_para = generate_fight_history_paragraph(veteran, self.session)

        self.assertNotEqual(prospect_para, veteran_para,
                           "Prospect and veteran should have different paragraphs")
        # Prospect should be shorter (1 fight ref vs 3-4)
        if prospect_para and veteran_para:
            self.assertLess(len(prospect_para), len(veteran_para),
                           "Prospect paragraph should be shorter than veteran's")


class TestCareerHighlights(unittest.TestCase):
    """Tests for extract_career_highlights()."""

    @classmethod
    def setUpClass(cls):
        # Reuse existing DB from above tests
        cls.engine = create_engine(DB_URL)
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.session = Session(self.engine)
        org = Organization(name="Highlights Org", prestige=80.0, bank_balance=1_000_000)
        self.session.add(org)
        self.session.flush()
        self.org = org

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_zero_fights_returns_empty_list(self):
        """Fighter with 0 fights returns empty list."""
        from simulation.narrative import extract_career_highlights
        f = _make_fighter(self.session, "No Fights Nancy", wins=0, losses=0, draws=0,
                          ko_wins=0, sub_wins=0)
        result = extract_career_highlights(f, self.session)
        self.assertEqual(result, [])

    def test_highlights_capped_at_six(self):
        """Highlights never exceed 6 entries regardless of career length."""
        from simulation.narrative import extract_career_highlights
        fighter = _make_fighter(self.session, "Long Career Larry", wins=25, losses=5,
                               ko_wins=15, sub_wins=5, age=35,
                               archetype=Archetype.GOAT_CANDIDATE)
        for i in range(30):
            opp = _make_fighter(self.session, f"HLOpp_{i} Z{i}", wins=5, losses=3)
            event = _make_event(self.session, f"HL Event {i+700}",
                               date(2020 + (i // 12), 1 + (i % 12), 10), self.org.id)
            _make_fight(self.session, event, fighter, opp,
                        winner=fighter if i < 25 else opp,
                        method=FightMethod.KO_TKO, round_ended=1,
                        is_title_fight=(i % 5 == 0))
        self.session.flush()

        result = extract_career_highlights(fighter, self.session)
        self.assertLessEqual(len(result), 6, f"Highlights should be capped at 6, got {len(result)}")

    def test_highlight_dict_structure(self):
        """Each highlight has required keys: fight_id, text, score, event_name, event_date."""
        from simulation.narrative import extract_career_highlights
        fighter = _make_fighter(self.session, "Structure Test Sally", wins=5, losses=1,
                               ko_wins=3, sub_wins=1, age=27)
        for i in range(5):
            opp = _make_fighter(self.session, f"StructOpp_{i} A{i}", wins=4, losses=2)
            event = _make_event(self.session, f"Struct Event {i+800}",
                               date(2024, 1 + i, 10), self.org.id)
            _make_fight(self.session, event, fighter, opp, winner=fighter,
                        method=FightMethod.KO_TKO, round_ended=2)
        self.session.flush()

        result = extract_career_highlights(fighter, self.session)
        self.assertGreater(len(result), 0, "Should have at least one highlight")
        for h in result:
            self.assertIn("fight_id", h, "Highlight missing 'fight_id'")
            self.assertIn("text", h, "Highlight missing 'text'")
            self.assertIn("score", h, "Highlight missing 'score'")
            self.assertIn("event_name", h, "Highlight missing 'event_name'")
            self.assertIn("event_date", h, "Highlight missing 'event_date'")
            self.assertIsInstance(h["text"], str)
            self.assertIsInstance(h["score"], int)


class TestHelpers(unittest.TestCase):
    """Tests for helper functions."""

    def test_humanize_method(self):
        """_humanize_method maps FightMethod values to natural language."""
        from simulation.narrative import _humanize_method
        self.assertEqual(_humanize_method("KO/TKO"), "knocked out")
        self.assertEqual(_humanize_method("Submission"), "submitted")
        self.assertEqual(_humanize_method("Unanimous Decision"), "outpointed")
        self.assertEqual(_humanize_method("Split Decision"), "edged out")
        self.assertEqual(_humanize_method("Majority Decision"), "outworked")

    def test_ordinal_round(self):
        """_ordinal_round maps round numbers to words."""
        from simulation.narrative import _ordinal_round
        self.assertEqual(_ordinal_round(1), "first")
        self.assertEqual(_ordinal_round(2), "second")
        self.assertEqual(_ordinal_round(3), "third")
        self.assertEqual(_ordinal_round(4), "fourth")
        self.assertEqual(_ordinal_round(5), "fifth")
        # Unexpected round number
        result = _ordinal_round(6)
        self.assertIn("6", result)

    def test_jinja2_env_exists(self):
        """Module-level _jinja_env Environment exists."""
        from simulation.narrative import _jinja_env
        from jinja2 import Environment
        self.assertIsInstance(_jinja_env, Environment)


if __name__ == "__main__":
    unittest.main()
