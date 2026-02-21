# FighterSim

A Python-based MMA promotion management simulator. Models fighters, organizations, contracts, events, and fight cards with a tick-based fight engine and monthly simulation cycle.

## Setup

```bash
pip install -r requirements.txt

# Validate everything works
python -X utf8 test_cli.py
```

## Project Structure

```
FighterSim/
├── models/
│   ├── database.py       # Engine, session factory, declarative Base
│   └── models.py         # SQLAlchemy ORM models
├── simulation/
│   ├── fight_engine.py   # Core fight simulation (no framework dependencies)
│   ├── monthly_sim.py    # sim_month() — aging, contracts, AI org events
│   ├── rankings.py       # Cached rankings with dirty-flag invalidation
│   └── seed.py           # 100-fighter + 4-org seed data
├── test_cli.py           # Full validation script (4 steps)
└── requirements.txt
```

## How It Works

### Fight Engine

Simulates fights round-by-round in 30-second ticks. Each tick:

1. Determines fight zone (striking / clinch / ground) based on wrestling stats
2. Applies damage with stamina-adjusted attributes
3. Checks for finish — KO threshold scales with chin; submission threshold scales with grappling
4. Drains stamina at a rate governed by cardio

Between rounds, fighters partially recover stamina — but the ceiling drops each round for low-cardio fighters, causing meaningful late-round fatigue.

### Monthly Simulation (`sim_month`)

Each call advances the world one month:
- Ages all fighters and applies attribute drift (pre-prime growth, peak stability, post-prime decline)
- Recovers injured fighters
- Expires and auto-renews AI org contracts
- Randomly generates and simulates AI org events (~40% chance per org)

Runs in ~25ms average for a 100-fighter roster.

### Rankings

Rankings are cached in a `rankings` table with a `dirty` flag. They are only recomputed when `rebuild_rankings()` is called explicitly — never on reads. Scores weight win rate, finish rate, and overall fighter rating.

## Models

| Model | Description |
|---|---|
| `Fighter` | Core athlete — attributes (1–100), record, age, prime range, condition |
| `Organization` | MMA promotion — prestige, bank balance, player flag |
| `Contract` | Fighter ↔ org relationship — salary, fights remaining, expiry |
| `Event` | Fight card — venue, date, gate revenue, PPV buys |
| `Fight` | Single bout result — method, round, time, narrative |
| `Ranking` | Cached rank entry per weight class |

## Weight Classes

Flyweight · Lightweight · Welterweight · Middleweight · Heavyweight
