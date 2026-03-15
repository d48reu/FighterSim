from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.database import Base
from models.models import Contract, Fighter, Organization
from simulation.seed import seed_fighters


def test_seed_fighters_supports_custom_org_counts_without_crashing():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        player_org = Organization(
            name="Player FC",
            bank_balance=5_000_000,
            prestige=50,
            is_player=True,
        )
        ai_org = Organization(
            name="AI FC",
            bank_balance=5_000_000,
            prestige=65,
            is_player=False,
        )
        session.add_all([player_org, ai_org])
        session.flush()

        fighters = seed_fighters(session, orgs=[player_org, ai_org], count=80, seed=42)

        assert len(fighters) == 80

        seeded_fighters = session.execute(select(Fighter)).scalars().all()
        contracts = session.execute(select(Contract)).scalars().all()
        org_ids = {player_org.id, ai_org.id}

        assert len(seeded_fighters) == 80
        assert all(contract.organization_id in org_ids for contract in contracts)
