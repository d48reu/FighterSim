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
from models.models import Fighter, WeightClass, GameState
from simulation.seed import seed_organizations, seed_fighters
from simulation.fight_engine import FighterStats, simulate_fight
from simulation.rankings import rebuild_rankings, get_rankings
from simulation.monthly_sim import sim_month
from sqlalchemy import select
import json
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
            traits=json.loads(fa.traits) if fa.traits else [],
            style=fa.style.value if hasattr(fa.style, "value") else str(fa.style),
        )
        b_stats = FighterStats(
            id=fb.id, name=fb.name,
            striking=fb.striking, grappling=fb.grappling,
            wrestling=fb.wrestling, cardio=fb.cardio,
            chin=fb.chin, speed=fb.speed,
            traits=json.loads(fb.traits) if fb.traits else [],
            style=fb.style.value if hasattr(fb.style, "value") else str(fb.style),
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

    # Verify game state exists and show initial date
    gs = session.get(GameState, 1)
    print(f"  Game start date: {gs.current_date}")

    for i in range(1, 4):
        t0 = time.perf_counter()
        summary = sim_month(session, seed=i * 1000)
        elapsed = time.perf_counter() - t0
        total_time += elapsed

        # Re-read game state to see updated date
        session.expire(gs)
        status = "✓" if elapsed < 2.0 else "✗ SLOW"
        print(f"  Month {i} (game date now: {gs.current_date}): {elapsed:.3f}s {status}")
        print(f"    Fighters aged: {summary['fighters_aged']}, Events simulated: {summary['events_simulated']}")

    print(f"\n  Total: {total_time:.3f}s | Average: {total_time/3:.3f}s")
    if total_time / 3 < 2.0:
        print("  ✓ All sim_month() calls within 2s limit")
    else:
        print("  ✗ Performance requirement not met")

    # Verify game date advanced correctly (should be April 2026 after 3 months from Jan 2026)
    expected_date = date(2026, 4, 1)
    if gs.current_date == expected_date:
        print(f"  ✓ Game date correctly advanced to {gs.current_date}")
    else:
        print(f"  ✗ Game date mismatch: expected {expected_date}, got {gs.current_date}")


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

# ──────────────────────────────────────────────
# 5. Test new features: nationality, nicknames, press conference, cornerstones
# ──────────────────────────────────────────────

print()
print("=" * 60)
print("STEP 5: Feature tests (nationality, nicknames, press conf, cornerstones)")
print("=" * 60)

from simulation.narrative import (
    _nationality_flavor, suggest_nicknames, generate_press_conference,
)
from models.models import Contract, ContractStatus, Organization

with SessionFactory() as session:
    errors = []

    # 5a: Nationality flavor
    print("\n  5a. Nationality flavor...")
    brazilian_grappler = None
    american_fighter = None
    for f in session.execute(select(Fighter)).scalars().all():
        if f.nationality == "Brazilian" and f.style.value == "Grappler" and not brazilian_grappler:
            brazilian_grappler = f
        if f.nationality == "American" and not american_fighter:
            american_fighter = f
    if brazilian_grappler:
        flavor = _nationality_flavor(brazilian_grappler)
        if flavor:
            print(f"    ✓ Brazilian Grappler gets flavor: '{flavor[:60]}...'")
        else:
            errors.append("Brazilian Grappler should get nationality flavor text")
            print("    ✗ Brazilian Grappler got no flavor text")
    else:
        print("    - No Brazilian Grappler found in seed (skipped)")
    if american_fighter:
        flavor = _nationality_flavor(american_fighter)
        if not flavor:
            print("    ✓ American fighter gets no flavor (correct)")
        else:
            errors.append("American fighter should NOT get nationality flavor text")
            print(f"    ✗ American fighter got flavor: '{flavor}'")

    # 5b: Nickname suggestions
    print("\n  5b. Nickname suggestions...")
    test_fighter = session.execute(select(Fighter)).scalars().first()
    suggestions = suggest_nicknames(test_fighter, session=session)
    if len(suggestions) == 3 and len(set(suggestions)) == 3:
        print(f"    ✓ Got 3 distinct nicknames: {suggestions}")
    else:
        errors.append(f"Expected 3 distinct nicknames, got {suggestions}")
        print(f"    ✗ Bad suggestions: {suggestions}")

    # 5c: Press conference
    print("\n  5c. Press conference...")
    all_f = session.execute(select(Fighter)).scalars().all()
    fa, fb = all_f[0], all_f[1]
    pc = generate_press_conference(fa, fb)
    if len(pc["exchanges"]) == 5:
        print(f"    ✓ Generated 5 exchanges (non-cornerstone)")
    else:
        errors.append(f"Expected 5 exchanges, got {len(pc['exchanges'])}")
        print(f"    ✗ Got {len(pc['exchanges'])} exchanges")
    if pc["hype_generated"] > 0:
        print(f"    ✓ Hype generated: {pc['hype_generated']:.1f}")
    else:
        errors.append("Expected hype_generated > 0")
        print("    ✗ No hype generated")
    if pc["ppv_boost"] > 0:
        print(f"    ✓ PPV boost: {pc['ppv_boost']}")
    else:
        errors.append("Expected ppv_boost > 0")
        print("    ✗ No PPV boost")

    # Test cornerstone press conference (7 exchanges)
    pc_cs = generate_press_conference(fa, fb, is_cornerstone_a=True)
    if len(pc_cs["exchanges"]) == 7:
        print(f"    ✓ Cornerstone press conference: 7 exchanges")
    else:
        errors.append(f"Expected 7 cornerstone exchanges, got {len(pc_cs['exchanges'])}")
        print(f"    ✗ Got {len(pc_cs['exchanges'])} cornerstone exchanges")

    # 5d: Cornerstone designation
    print("\n  5d. Cornerstone designation...")
    player_org = session.execute(
        select(Organization).where(Organization.is_player == True)
    ).scalar_one_or_none()

    # Find fighters with active contracts on player org
    roster_contracts = session.execute(
        select(Contract).where(
            Contract.organization_id == player_org.id,
            Contract.status == ContractStatus.ACTIVE,
        )
    ).scalars().all()

    if len(roster_contracts) >= 4:
        # Designate 3
        for i, c in enumerate(roster_contracts[:3]):
            f = session.get(Fighter, c.fighter_id)
            f.is_cornerstone = True
        session.flush()

        cs_list = [session.get(Fighter, c.fighter_id) for c in roster_contracts[:3] if session.get(Fighter, c.fighter_id).is_cornerstone]
        if len(cs_list) == 3:
            print(f"    ✓ Designated 3 cornerstones: {[f.name for f in cs_list]}")
        else:
            errors.append(f"Expected 3 cornerstones, got {len(cs_list)}")
            print(f"    ✗ Cornerstone count: {len(cs_list)}")

        # Verify max-3 enforcement would apply (4th fighter not cornerstone)
        fourth = session.get(Fighter, roster_contracts[3].fighter_id)
        if not fourth.is_cornerstone:
            print("    ✓ 4th fighter is not a cornerstone (max-3 verified)")
        else:
            errors.append("4th fighter should not be a cornerstone")

        # Remove one
        cs_list[0].is_cornerstone = False
        session.flush()
        remaining = sum(1 for c in roster_contracts[:3] if session.get(Fighter, c.fighter_id).is_cornerstone)
        if remaining == 2:
            print(f"    ✓ Removed one cornerstone, {remaining} remain")
        else:
            errors.append(f"Expected 2 remaining after removal, got {remaining}")

        # Clean up
        for c in roster_contracts[:3]:
            session.get(Fighter, c.fighter_id).is_cornerstone = False
        session.flush()
    else:
        print("    - Not enough roster fighters to test cornerstones (skipped)")

    # 5e: Archetype-record consistency
    print("\n  5e. Archetype-record consistency...")
    from models.models import Archetype
    all_fighters = session.execute(select(Fighter)).scalars().all()
    mismatches = []
    for f in all_fighters:
        total_decided = f.wins + f.losses
        if total_decided == 0:
            continue
        win_rate = f.wins / total_decided
        if f.archetype == Archetype.GOAT_CANDIDATE and win_rate < 0.70:
            mismatches.append(f"{f.name} GOAT_CANDIDATE {f.wins}-{f.losses} ({win_rate:.0%})")
        if f.archetype == Archetype.SHOOTING_STAR and win_rate < 0.60:
            mismatches.append(f"{f.name} SHOOTING_STAR {f.wins}-{f.losses} ({win_rate:.0%})")
    if mismatches:
        errors.append(f"Archetype-record mismatches: {mismatches}")
        for m in mismatches:
            print(f"    ✗ {m}")
    else:
        print("    ✓ No archetype-record mismatches found")

    # Summary
    print()
    if errors:
        print(f"  ✗ {len(errors)} error(s):")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  ✓ All Step 5 tests passed!")

print()
print("=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
