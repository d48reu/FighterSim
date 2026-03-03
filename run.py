#!/usr/bin/env python3
"""Start the FighterSim server with a fresh database (seeding deferred to origin selection)."""

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

# Create app (creates tables, no seeding -- origin selection triggers seed)
app = create_app(DB_URL)

print("\nStarting server at http://127.0.0.1:5000")
print("Select your origin to begin a new game.")
app.run(host="127.0.0.1", port=5000, debug=False)
