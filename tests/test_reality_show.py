from datetime import date
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.database import Base
from models.models import (
    Fighter,
    FighterStyle,
    GameState,
    Organization,
    RealityShow,
    ShowContestant,
    ShowEpisode,
    ShowStatus,
    WeightClass,
)
from simulation.monthly_sim import _process_reality_show


def _make_fighter(name: str) -> Fighter:
    return Fighter(
        name=name,
        age=28,
        nationality="American",
        weight_class=WeightClass.WELTERWEIGHT,
        style=FighterStyle.STRIKER,
        striking=70,
        grappling=65,
        wrestling=60,
        cardio=72,
        chin=68,
        speed=73,
        wins=8,
        losses=3,
        draws=0,
        ko_wins=4,
        sub_wins=1,
        prime_start=25,
        prime_end=31,
        confidence=70.0,
        hype=30.0,
        popularity=35.0,
    )


def test_finale_still_resolves_when_both_finalists_are_unavailable():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        org = Organization(
            name="Player Org",
            prestige=60.0,
            bank_balance=5_000_000,
            is_player=True,
        )
        fighters = [_make_fighter(f"Fighter {idx}") for idx in range(1, 9)]
        session.add(org)
        session.add_all(fighters)
        session.flush()

        session.add(
            GameState(id=1, current_date=date(2026, 4, 1), player_org_id=org.id)
        )

        show = RealityShow(
            name="Ultimate Fighter: Welterweight",
            organization_id=org.id,
            weight_class=WeightClass.WELTERWEIGHT,
            status=ShowStatus.IN_PROGRESS,
            format_size=8,
            start_date=date(2026, 1, 1),
            current_round=2,
            episodes_aired=3,
            production_cost_per_episode=75_000.0,
            total_production_spend=225_000.0,
            total_revenue=0.0,
            show_hype=55.0,
        )
        session.add(show)
        session.flush()

        contestants = []
        for seed, fighter in enumerate(fighters, start=1):
            status = "eliminated" if seed not in (1, 2) else "active"
            eliminated_round = 1 if seed not in (1, 2) else None
            eliminated_by = "loss" if seed not in (1, 2) else None
            contestants.append(
                ShowContestant(
                    show_id=show.id,
                    fighter_id=fighter.id,
                    seed=seed,
                    status=status,
                    eliminated_round=eliminated_round,
                    eliminated_by=eliminated_by,
                    show_wins=1 if seed in (1, 2) else 0,
                    show_losses=0 if seed in (1, 2) else 1,
                    show_hype_earned=12.0 if seed == 1 else 10.0 if seed == 2 else 3.0,
                )
            )
        session.add_all(contestants)
        session.flush()

        finalists = {1: fighters[0], 2: fighters[1]}
        for seed, fighter in finalists.items():
            sc = contestants[seed - 1]
            sc.status = "eliminated"
            sc.eliminated_round = 2
            sc.eliminated_by = "injury" if seed == 1 else "quit"
            fighter.injury_months = 1

        semifinal_results = [
            {
                "fighter_a_id": fighters[0].id,
                "fighter_a": fighters[0].name,
                "fighter_b_id": fighters[3].id,
                "fighter_b": fighters[3].name,
                "winner_id": fighters[0].id,
                "winner": fighters[0].name,
                "loser": fighters[3].name,
                "is_walkover": False,
                "method": "Unanimous Decision",
                "round": 3,
                "time": "5:00",
                "narrative": "Semifinal one.",
            },
            {
                "fighter_a_id": fighters[1].id,
                "fighter_a": fighters[1].name,
                "fighter_b_id": fighters[2].id,
                "fighter_b": fighters[2].name,
                "winner_id": fighters[1].id,
                "winner": fighters[1].name,
                "loser": fighters[2].name,
                "is_walkover": False,
                "method": "KO/TKO",
                "round": 2,
                "time": "3:10",
                "narrative": "Semifinal two.",
            },
        ]
        session.add(
            ShowEpisode(
                show_id=show.id,
                episode_number=3,
                episode_type="semifinal",
                air_date=date(2026, 3, 1),
                fight_results=json.dumps(semifinal_results),
                shenanigans=None,
                episode_narrative="Semifinals",
                episode_rating=7.5,
                hype_generated=10.0,
            )
        )
        session.commit()

        notifications = _process_reality_show(
            session, date(2026, 4, 1), org, __import__("random").Random(7)
        )

        finale = session.execute(
            select(ShowEpisode).where(
                ShowEpisode.show_id == show.id,
                ShowEpisode.episode_type == "finale",
            )
        ).scalar_one()
        finale_results = json.loads(finale.fight_results)

        assert notifications
        assert "concluded" in notifications[-1].lower()
        assert finale_results
        assert finale_results[0]["winner_id"] is not None

        session.flush()
        assert show.winner_id is not None
        assert show.runner_up_id is not None
        assert show.status == ShowStatus.COMPLETED
