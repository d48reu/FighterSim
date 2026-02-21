#!/usr/bin/env python3
"""Start the FighterSim server with a fresh seeded database."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

DB_FILE = ROOT / "mma_game.db"
DB_URL = f"sqlite:///{DB_FILE}"

# Remove old DB for a fresh start
if DB_FILE.exists():
    os.remove(DB_FILE)

from api.app import create_app
import api.services as svc
from simulation.seed import seed_organizations, seed_fighters

# Create app (this calls init_db, creating tables + session factory)
app = create_app(DB_URL)

# Seed using the app's session factory
with svc._SessionFactory() as session:
    orgs = seed_organizations(session)
    fighters = seed_fighters(session, orgs, seed=42)
    print(f"Seeded {len(orgs)} orgs and {len(fighters)} fighters")

# Verify
camps = svc.get_training_camps()
print(f"Training camps: {len(camps)}")

print("\nStarting server at http://127.0.0.1:5000")
app.run(host="127.0.0.1", port=5000, debug=False)
