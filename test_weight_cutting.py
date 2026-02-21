"""
Dedicated tests for the Weight Cutting feature.

Tests:
1. Seeded fighters get valid natural_weight/fighting_weight per weight class
2. get_cut_severity() classifies correctly at all thresholds
3. Fight engine applies stamina/chin penalties for each severity level
4. Missed weight probability tiers are wired correctly
5. Fighter dict includes cut_severity in API output
"""

from __future__ import annotations

import json
import random
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import (
    Fighter, Organization, Contract, GameState,
    WeightClass, FighterStyle, ContractStatus,
)
from simulation.seed import (
    seed_fighters, WEIGHT_CLASS_LIMITS, NATURAL_WEIGHT_RANGES,
)
from simulation.fight_engine import (
    FighterStats, simulate_fight, CUT_PENALTIES,
)
from api.services import get_cut_severity, MISS_WEIGHT_PROB

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" -- {detail}"
        print(msg)


# -------------------------------------------------------------------------
# Setup: create a test DB and seed fighters
# -------------------------------------------------------------------------
print("=" * 60)
print("WEIGHT CUTTING FEATURE TESTS")
print("=" * 60)

engine = create_engine("sqlite:///wc_test.db", echo=False,
                        connect_args={"check_same_thread": False})
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Seed orgs and fighters
player_org = Organization(name="Player FC", bank_balance=5_000_000, prestige=50, is_player=True)
ai_org = Organization(name="AI FC", bank_balance=5_000_000, prestige=50, is_player=False)
session.add_all([player_org, ai_org])
session.flush()
gs = GameState(id=1, current_date=__import__("datetime").date(2026, 1, 1), player_org_id=player_org.id)
session.add(gs)
session.commit()

seed_fighters(session, orgs=[player_org, ai_org], count=80, seed=42)
session.commit()

fighters = session.execute(select(Fighter)).scalars().all()
print(f"\nSeeded {len(fighters)} fighters\n")

# =========================================================================
# TEST 1: Seeded fighters have valid natural/fighting weights
# =========================================================================
print("--- Test 1: Natural/Fighting Weight Validity ---")

fighters_missing_weight = [f for f in fighters if f.natural_weight is None or f.fighting_weight is None]
check("All fighters have natural_weight set", len(fighters_missing_weight) == 0,
      f"{len(fighters_missing_weight)} fighters missing weights")

fighters_missing_fw = [f for f in fighters if f.fighting_weight is None]
check("All fighters have fighting_weight set", len(fighters_missing_fw) == 0)

# Check that fighting_weight matches the weight class limit
wrong_limit = []
for f in fighters:
    wc_val = f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class
    expected_limit = WEIGHT_CLASS_LIMITS.get(wc_val)
    if expected_limit and f.fighting_weight != float(expected_limit):
        wrong_limit.append(f"{f.name}: {wc_val} limit={expected_limit}, fighting_weight={f.fighting_weight}")

check("Fighting weight matches weight class limit", len(wrong_limit) == 0,
      f"{len(wrong_limit)} mismatches: {wrong_limit[:3]}")

# Check natural weight falls within expected range
out_of_range = []
for f in fighters:
    wc_val = f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class
    nat_lo, nat_hi = NATURAL_WEIGHT_RANGES.get(wc_val, (0, 999))
    if not (nat_lo <= f.natural_weight <= nat_hi):
        out_of_range.append(f"{f.name}: {wc_val} nat={f.natural_weight} range=({nat_lo},{nat_hi})")

check("Natural weight within expected range", len(out_of_range) == 0,
      f"{len(out_of_range)} out of range: {out_of_range[:3]}")

# Natural weight should always be >= fighting weight (you cut DOWN)
wrong_direction = [f for f in fighters if f.natural_weight < f.fighting_weight]
# Heavyweights can be at or below limit, so filter them
non_hw_wrong = [f for f in wrong_direction
                if (f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class) != "Heavyweight"]
check("Natural weight >= fighting weight (non-HW)", len(non_hw_wrong) == 0,
      f"{len(non_hw_wrong)} fighters with natural < fighting")

print()

# =========================================================================
# TEST 2: get_cut_severity() classification thresholds
# =========================================================================
print("--- Test 2: Cut Severity Classification ---")

# Create mock fighters with specific weights to test each threshold
class MockFighter:
    def __init__(self, natural_weight, fighting_weight):
        self.natural_weight = natural_weight
        self.fighting_weight = fighting_weight

# Easy: cut_pct < 5%
# 155 fighting, 160 natural => cut_pct = (160-155)/160*100 = 3.125%
check("Easy cut (3.1%)", get_cut_severity(MockFighter(160, 155)) == "easy",
      f"got {get_cut_severity(MockFighter(160, 155))}")

# Moderate: 5% <= cut_pct < 10%
# 155 fighting, 170 natural => cut_pct = (170-155)/170*100 = 8.82%
check("Moderate cut (8.8%)", get_cut_severity(MockFighter(170, 155)) == "moderate",
      f"got {get_cut_severity(MockFighter(170, 155))}")

# Severe: 10% <= cut_pct < 15%
# 155 fighting, 175 natural => cut_pct = (175-155)/175*100 = 11.43%
check("Severe cut (11.4%)", get_cut_severity(MockFighter(175, 155)) == "severe",
      f"got {get_cut_severity(MockFighter(175, 155))}")

# Extreme: cut_pct >= 15%
# 155 fighting, 185 natural => cut_pct = (185-155)/185*100 = 16.2%
check("Extreme cut (16.2%)", get_cut_severity(MockFighter(185, 155)) == "extreme",
      f"got {get_cut_severity(MockFighter(185, 155))}")

# Edge cases
check("No natural weight => easy", get_cut_severity(MockFighter(None, 155)) == "easy")
check("No fighting weight => easy", get_cut_severity(MockFighter(170, None)) == "easy")
check("Natural <= fighting => easy", get_cut_severity(MockFighter(150, 155)) == "easy")

# Boundary: exactly 5%
# natural=200, fighting=190 => cut_pct = 10/200*100 = 5.0% => moderate
check("Boundary 5.0% => moderate", get_cut_severity(MockFighter(200, 190)) == "moderate",
      f"got {get_cut_severity(MockFighter(200, 190))}")

# Boundary: exactly 10%
# natural=200, fighting=180 => cut_pct = 20/200*100 = 10.0% => severe
check("Boundary 10.0% => severe", get_cut_severity(MockFighter(200, 180)) == "severe",
      f"got {get_cut_severity(MockFighter(200, 180))}")

# Boundary: exactly 15%
# natural=200, fighting=170 => cut_pct = 30/200*100 = 15.0% => extreme
check("Boundary 15.0% => extreme", get_cut_severity(MockFighter(200, 170)) == "extreme",
      f"got {get_cut_severity(MockFighter(200, 170))}")

print()

# =========================================================================
# TEST 3: Fight engine applies stamina/chin penalties correctly
# =========================================================================
print("--- Test 3: Fight Engine Penalty Application ---")

def make_stats(id=1, name="A", chin=80, cardio=80):
    return FighterStats(
        id=id, name=name,
        striking=70, grappling=70, wrestling=70,
        cardio=cardio, chin=chin, speed=70,
        confidence=70.0,
    )

# Test: "easy" cut should not reduce stats
a_easy = make_stats(1, "A_easy")
b_easy = make_stats(2, "B_easy")
result_easy = simulate_fight(a_easy, b_easy, seed=100, cut_severity_a="easy", cut_severity_b="easy")
# After fight, stamina was set to 100 (no penalty), chin stays 80
# We can't inspect mid-fight, but we can verify the penalty dict
check("Easy penalties are zero",
      CUT_PENALTIES["easy"]["stamina"] == 0 and CUT_PENALTIES["easy"]["chin"] == 0)

check("Moderate penalties: stamina=-3, chin=-2",
      CUT_PENALTIES["moderate"]["stamina"] == -3 and CUT_PENALTIES["moderate"]["chin"] == -2)

check("Severe penalties: stamina=-7, chin=-5",
      CUT_PENALTIES["severe"]["stamina"] == -7 and CUT_PENALTIES["severe"]["chin"] == -5)

check("Extreme penalties: stamina=-12, chin=-8",
      CUT_PENALTIES["extreme"]["stamina"] == -12 and CUT_PENALTIES["extreme"]["chin"] == -8)

# Functional test: extreme cut fighters should lose more often to easy cut fighters
# Run 200 fights: same stats, but A has extreme cut and B has easy cut
extreme_wins = 0
N = 200
for i in range(N):
    a = make_stats(1, "Extreme_Cutter")
    b = make_stats(2, "Easy_Cutter")
    r = simulate_fight(a, b, seed=i * 7, cut_severity_a="extreme", cut_severity_b="easy")
    if r.winner_id == 1:
        extreme_wins += 1

extreme_win_pct = extreme_wins / N * 100
# With -12 stamina and -8 chin, the extreme cutter should win less than 50%
check(f"Extreme cut fighter wins less often ({extreme_win_pct:.1f}% < 50%)",
      extreme_win_pct < 50,
      f"extreme cutter won {extreme_wins}/{N} = {extreme_win_pct:.1f}%")

# More granular: severe vs easy
severe_wins = 0
for i in range(N):
    a = make_stats(1, "Severe_Cutter")
    b = make_stats(2, "Easy_Cutter")
    r = simulate_fight(a, b, seed=i * 13, cut_severity_a="severe", cut_severity_b="easy")
    if r.winner_id == 1:
        severe_wins += 1

severe_win_pct = severe_wins / N * 100
check(f"Severe cut fighter wins less often ({severe_win_pct:.1f}% < 50%)",
      severe_win_pct < 50,
      f"severe cutter won {severe_wins}/{N} = {severe_win_pct:.1f}%")

# Ordering: extreme cutters should win LESS than severe cutters
check(f"Extreme ({extreme_win_pct:.1f}%) < Severe ({severe_win_pct:.1f}%) win rate",
      extreme_win_pct < severe_win_pct,
      f"extreme={extreme_win_pct:.1f}%, severe={severe_win_pct:.1f}%")

print()

# =========================================================================
# TEST 4: Missed Weight Probability Tiers
# =========================================================================
print("--- Test 4: Missed Weight Probability ---")

check("Easy: 0% miss chance", MISS_WEIGHT_PROB["easy"] == 0.0)
check("Moderate: 2% miss chance", MISS_WEIGHT_PROB["moderate"] == 0.02)
check("Severe: 8% miss chance", MISS_WEIGHT_PROB["severe"] == 0.08)
check("Extreme: 20% miss chance", MISS_WEIGHT_PROB["extreme"] == 0.20)

# Statistical test: run 10000 rolls for extreme, should be ~2000 misses
rng = random.Random(99)
misses = sum(1 for _ in range(10000) if rng.random() < MISS_WEIGHT_PROB["extreme"])
miss_pct = misses / 10000 * 100
check(f"Extreme miss rate ~20% (got {miss_pct:.1f}%)",
      15 < miss_pct < 25,
      f"expected ~20%, got {miss_pct:.1f}%")

# Easy should never miss
easy_misses = sum(1 for _ in range(10000) if rng.random() < MISS_WEIGHT_PROB["easy"])
check("Easy never misses weight", easy_misses == 0)

print()

# =========================================================================
# TEST 5: Distribution of cut severities across seeded fighters
# =========================================================================
print("--- Test 5: Cut Severity Distribution ---")

severity_counts = {"easy": 0, "moderate": 0, "severe": 0, "extreme": 0}
for f in fighters:
    sev = get_cut_severity(f)
    severity_counts[sev] = severity_counts.get(sev, 0) + 1

print(f"  Distribution: {severity_counts}")
total = len(fighters)
for sev, count in severity_counts.items():
    pct = count / total * 100
    print(f"    {sev}: {count} ({pct:.1f}%)")

# We should have a mix — at least 2 different severities among 80 fighters
unique_severities = sum(1 for v in severity_counts.values() if v > 0)
check(f"Multiple severity levels present ({unique_severities} levels)",
      unique_severities >= 2)

# Heavyweights can have easy cuts (natural <= limit)
hw_fighters = [f for f in fighters
               if (f.weight_class.value if hasattr(f.weight_class, "value") else f.weight_class) == "Heavyweight"]
if hw_fighters:
    hw_easy = sum(1 for f in hw_fighters if get_cut_severity(f) == "easy")
    print(f"  Heavyweights: {len(hw_fighters)} total, {hw_easy} easy cuts")
    check("Some heavyweights have easy cuts", hw_easy > 0 or len(hw_fighters) == 0)

print()

# =========================================================================
# TEST 6: KO rate increases with extreme weight cuts
# =========================================================================
print("--- Test 6: Extreme Cut Increases KO Rate ---")

ko_count_easy = 0
ko_count_extreme = 0
N2 = 300

for i in range(N2):
    a = make_stats(1, "A")
    b = make_stats(2, "B")
    r = simulate_fight(a, b, seed=i, cut_severity_a="easy", cut_severity_b="easy")
    if r.method == "KO/TKO":
        ko_count_easy += 1

for i in range(N2):
    a = make_stats(1, "A")
    b = make_stats(2, "B")
    r = simulate_fight(a, b, seed=i, cut_severity_a="extreme", cut_severity_b="extreme")
    if r.method == "KO/TKO":
        ko_count_extreme += 1

ko_easy_pct = ko_count_easy / N2 * 100
ko_extreme_pct = ko_count_extreme / N2 * 100
print(f"  KO rate (both easy): {ko_easy_pct:.1f}%")
print(f"  KO rate (both extreme): {ko_extreme_pct:.1f}%")
check(f"Extreme cut increases KO rate ({ko_extreme_pct:.1f}% > {ko_easy_pct:.1f}%)",
      ko_extreme_pct > ko_easy_pct,
      f"easy={ko_easy_pct:.1f}%, extreme={ko_extreme_pct:.1f}%")

print()

# =========================================================================
# SUMMARY
# =========================================================================
print("=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 60)

# Cleanup
session.close()
import os
try:
    os.remove("wc_test.db")
except:
    pass

sys.exit(0 if FAIL == 0 else 1)
