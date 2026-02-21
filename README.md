# MMA Management Simulator

A desktop MMA promotion management game built with Python, SQLite, Flask, and vanilla JS.

## Setup

```bash
pip install -r requirements.txt

# Run the CLI test (validates everything works before touching the UI)
PYTHONPATH=. python tests/test_cli.py

# Start the web interface
PYTHONPATH=. python main.py
# → http://127.0.0.1:5000
```

## Project Structure

```
mma_sim/
├── models/
│   ├── database.py       # Engine, session factory
│   └── models.py         # SQLAlchemy ORM models
├── simulation/
│   ├── fight_engine.py   # Core fight simulation (Flask-free)
│   ├── monthly_sim.py    # sim_month() — aging, contracts, AI events
│   ├── rankings.py       # Cached rankings system
│   └── seed.py           # 100-fighter seed data
├── api/
│   ├── app.py            # Flask routes (no business logic)
│   └── services.py       # All business logic
├── frontend/
│   ├── templates/index.html
│   └── static/{css,js}
├── tests/
│   └── test_cli.py       # Full validation script
├── main.py               # Entry point
└── requirements.txt
```

## Key Design Decisions

- **Fight engine** is 100% decoupled from Flask — pure Python, testable standalone
- **Rankings** are cached in a `rankings` table with a `dirty` flag; never recomputed on page load
- **All simulation runs async** via background threads; Flask returns a `task_id` immediately, frontend polls `/api/tasks/<id>`
- **All DB queries use indexed lookups** — indexes on weight_class, age, contract expiry, fight date, fighter IDs
- **sim_month()** completes in ~120ms average for 100 fighters

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/fighters` | GET | List fighters (`?weight_class=`, `?limit=`, `?offset=`) |
| `/api/fighters/<id>` | GET | Single fighter |
| `/api/organization` | GET | Player org info |
| `/api/events/<id>` | GET | Event results |
| `/api/events/simulate` | POST | Simulate event card (async) |
| `/api/rankings/<wc>` | GET | Weight class rankings |
| `/api/sim/month` | POST | Advance one month (async) |
| `/api/tasks/<id>` | GET | Poll async task result |

## Fight Engine

The engine simulates round-by-round in 30-second ticks. Each tick:
1. Determines fight zone (striking / clinch / ground) based on wrestling stats
2. Applies damage with stamina-adjusted attributes
3. Checks for finish (KO threshold based on chin; sub threshold based on grappling)
4. Drains stamina (cardio governs drain rate)

Between rounds, partial stamina recovery occurs — but the ceiling drops each round for low-cardio fighters, causing meaningful late-round fatigue.
