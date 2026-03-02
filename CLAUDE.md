# FighterSim

Desktop MMA promotion management simulator. Player manages an MMA organization — sign fighters, book events, manage finances, build prestige.

**Repo:** https://github.com/d48reu/FighterSim.git
**Status:** Feature-rich prototype, not yet deployed

## Architecture

```
api/app.py          → Flask routes (thin controller)
api/services.py     → Business logic (3700 lines)
models/models.py    → 25 SQLAlchemy models
simulation/
  fight_engine.py   → Tick-based fight sim (ZERO Flask dependencies)
  monthly_sim.py    → Monthly advancement (aging, injuries, contracts, AI orgs)
  narrative.py      → Bios, tags, hype, GOAT scores
  rankings.py       → Cached rankings with dirty flag optimization
  seed.py           → 100-fighter + 4-org seed data
  traits.py         → 12 trait definitions + contradictions
frontend/           → Single-page vanilla JS app
```

**Critical rule:** Fight engine (`simulation/`) has NO Flask dependencies — keep it decoupled for testing and future desktop packaging.

## Tech Stack

**Backend:** Python 3, Flask 3.0+, SQLAlchemy 2.0+, SQLite
**Frontend:** Vanilla HTML/CSS/JS (single-page app, Rajdhani + Inter fonts, CSS design tokens)
**No external API keys needed** — fully self-contained simulation

## Key Commands

```bash
pip install -r requirements.txt
python run.py                    # Fresh start: delete DB, reseed 100 fighters, start server
python main.py                   # Start server with existing DB
python -X utf8 test_cli.py       # Full validation: seed → event sim → 3 months → rankings
python test_show.py              # Test reality show system
python test_weight_cutting.py    # Test weight cutting mechanics
```

## Database (25 SQLAlchemy Models)

**Core:** Fighter (attributes 1-100, styles, archetypes, traits), Organization, Contract, Event, Fight, Ranking, GameState
**Extended:** BroadcastDeal, TrainingCamp, FighterDevelopment, Sponsorship, RealityShow, ShowContestant, ShowEpisode, NewsHeadline, LegendCoach, Notification

**Enums:** WeightClass (5), FightMethod (6), FighterStyle (4), Archetype (6), ContractStatus (3), EventStatus (3)

**Database file:** `sqlite:///mma_game.db` (run.py) or `sqlite:///mma_test.db` (test_cli.py)

## Game Systems

- **Fight Engine:** 30-second tick simulation, zones (striking/clinch/ground), momentum, knockdowns, style matchups, judge bias
- **Monthly Sim:** Aging/prime windows, injury recovery, contract expiry, AI org booking, free agency
- **Finance:** Payroll, gate/PPV/broadcast revenue, fight costs, bankruptcy mechanics
- **Narrative:** AI-generated bios, press conferences, news headlines, career timeline
- **Training:** 15 camps across 3 tiers for fighter development
- **TV/Sponsorships:** Broadcast deals (prestige-gated), per-fighter sponsorship tiers
- **Reality Show:** Ultimate Fighter-style system with shenanigans
- **Rankings:** Dirty flag caching per weight class

## Roadmap

See `ROADMAP.md` for completed features and remaining work (fighter portraits, fight visualization, sound design, save/load, tutorial, Steam prep).
