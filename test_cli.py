#!/usr/bin/env python3
"""
CLI test script for MMA Management Simulator.

Tests:
1. Database initialization and 100-fighter seed
2. 10-fight event card simulation with printed results
3. sim_month() run 3x with timing
4. Rankings display for one weight class
"""

from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Ensure project root is on the path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from models.database import create_db_engine, create_session_factory, Base
from models.models import Fighter, WeightClass
from simulation.seed import seed_organizations, seed_fighters
from simulation.fight_engine import FighterStats, simulate_fight
from simulation.rankings import rebuild_rankings, get_rankings
from simulation.monthly_sim import sim_month
from sqlalchemy import select
import random

DB_URL = "sqlite:///mma_test.db"

# ──────────────────────────────────────────────
# 1. Initialize DB and seed
# ──────────────────────────────────────────────

print("=" * 60)
print("STEP 1: Initializing database and seeding fighters")
print("=" * 60)

engine = create_db_engine(DB_URL)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
SessionFactory = create_session_factory(engine)

with SessionFactory() as session:
    orgs = seed_organizations(session)
    fighters = seed_fighters(session, orgs, seed=42)
    print(f"✓ Created {len(orgs)} organizations")
    print(f"✓ Seeded {len(fighters)} fighters")
    
    # Show breakdown by weight class
    for wc in WeightClass:
        count = session.execute(
            select(Fighter).where(Fighter.weight_class == wc)
        ).scalars().all()
        print(f"  {wc.value}: {len(count)} fighters")


# ──────────────────────────────────────────────
# 2. Simulate a 10-fight event card
# ──────────────────────────────────────────────

print()
print("=" * 60)
print("STEP 2: Simulating 10-fight event card")
print("=" * 60)

with SessionFactory() as session:
    rng = random.Random(99)
    
    # Pick 20 fighters across all weight classes for 10 bouts
    all_fighters = session.execute(select(Fighter)).scalars().all()
    rng.shuffle(all_fighters)
    
    matchups = []
    used = set()
    
    for fa in all_fighters:
        if fa.id in used:
            continue
        for fb in all_fighters:
            if fb.id in used or fb.id == fa.id:
                continue
            if fb.weight_class == fa.weight_class:
                matchups.append((fa, fb))
                used.add(fa.id)
                used.add(fb.id)
                break
        if len(matchups) == 10:
            break

    print(f"\n{'POS':<4} {'FIGHTER A':<22} {'FIGHTER B':<22} {'WINNER':<22} {'METHOD':<22} {'RD':<3} {'TIME'}")
    print("-" * 105)

    method_counts: dict[str, int] = {}
    
    for i, (fa, fb) in enumerate(matchups, 1):
        a_stats = FighterStats(
            id=fa.id, name=fa.name,
            striking=fa.striking, grappling=fa.grappling,
            wrestling=fa.wrestling, cardio=fa.cardio,
            chin=fa.chin, speed=fa.speed,
        )
        b_stats = FighterStats(
            id=fb.id, name=fb.name,
            striking=fb.striking, grappling=fb.grappling,
            wrestling=fb.wrestling, cardio=fb.cardio,
            chin=fb.chin, speed=fb.speed,
        )
        
        result = simulate_fight(a_stats, b_stats, seed=rng.randint(0, 99999))
        winner_name = a_stats.name if result.winner_id == a_stats.id else b_stats.name
        
        method_counts[result.method] = method_counts.get(result.method, 0) + 1
        
        print(
            f"{i:<4} {fa.name:<22} {fb.name:<22} {winner_name:<22} "
            f"{result.method:<22} {result.round_ended:<3} {result.time_ended}"
        )
        print(f"      → {result.narrative}")
        print()

    print("\nMethod breakdown:")
    for method, count in sorted(method_counts.items()):
        print(f"  {method}: {count}")


# ──────────────────────────────────────────────
# 3. Run sim_month() 3x with timing
# ──────────────────────────────────────────────

print()
print("=" * 60)
print("STEP 3: Running sim_month() three times")
print("=" * 60)

with SessionFactory() as session:
    total_time = 0.0
    base_date = date.today()
    
    for i in range(1, 4):
        sim_date = base_date + timedelta(days=30 * i)
        t0 = time.perf_counter()
        summary = sim_month(session, sim_date, seed=i * 1000)
        elapsed = time.perf_counter() - t0
        total_time += elapsed
        
        status = "✓" if elapsed < 2.0 else "✗ SLOW"
        print(f"  Month {i} ({sim_date}): {elapsed:.3f}s {status}")
        print(f"    Fighters aged: {summary['fighters_aged']}, Events simulated: {summary['events_simulated']}")
    
    print(f"\n  Total: {total_time:.3f}s | Average: {total_time/3:.3f}s")
    if total_time / 3 < 2.0:
        print("  ✓ All sim_month() calls within 2s limit")
    else:
        print("  ✗ Performance requirement not met")


# ──────────────────────────────────────────────
# 4. Print rankings for Middleweight
# ──────────────────────────────────────────────

print()
print("=" * 60)
print("STEP 4: Middleweight Rankings")
print("=" * 60)

with SessionFactory() as session:
    rebuild_rankings(session, WeightClass.MIDDLEWEIGHT)
    rankings = get_rankings(session, WeightClass.MIDDLEWEIGHT, top_n=10)

print(f"\n{'RK':<4} {'FIGHTER':<25} {'RECORD':<12} {'OVERALL':<8} {'SCORE'}")
print("-" * 60)
for entry in rankings:
    print(
        f"{entry['rank']:<4} {entry['name']:<25} {entry['record']:<12} "
        f"{entry['overall']:<8} {entry['score']}"
    )

print()
print("=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
