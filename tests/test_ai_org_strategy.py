from models.models import Fighter, FighterStyle, Organization, WeightClass
from simulation.org_strategy import (
    derive_org_identity,
    candidate_strategy_score,
    event_pairing_strategy_score,
)


def _make_fighter(
    name: str,
    *,
    weight_class=WeightClass.LIGHTWEIGHT,
    age: int = 28,
    overall_bias: int = 0,
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
):
    base = 70 + overall_bias
    return Fighter(
        name=name,
        age=age,
        nationality="American",
        weight_class=weight_class,
        style=style,
        striking=base,
        grappling=base,
        wrestling=base,
        cardio=base,
        chin=base,
        speed=base,
        wins=10,
        losses=3,
        draws=0,
        ko_wins=5,
        sub_wins=1,
        prime_start=25,
        prime_end=31,
        confidence=70.0,
        hype=hype,
        popularity=popularity,
    )


def test_prestige_hunter_prefers_established_stars():
    org = Organization(
        name="Elite Org", prestige=90.0, bank_balance=50_000_000, is_player=False
    )
    roster = [_make_fighter("Top Champ", overall_bias=9, hype=80, popularity=78)]
    identity = derive_org_identity(org, roster)

    star = _make_fighter("Star", age=29, overall_bias=7, hype=74, popularity=70)
    prospect = _make_fighter("Prospect", age=22, overall_bias=6, hype=42, popularity=30)

    assert identity["label"] == "Prestige Hunter"
    assert candidate_strategy_score(
        star, identity, market_signals={}
    ) > candidate_strategy_score(prospect, identity, market_signals={})


def test_talent_factory_prefers_young_upside():
    org = Organization(
        name="Factory Org", prestige=58.0, bank_balance=12_000_000, is_player=False
    )
    roster = [
        _make_fighter("Young One", age=23, overall_bias=2, hype=30, popularity=24),
        _make_fighter("Young Two", age=24, overall_bias=3, hype=34, popularity=28),
    ]
    identity = derive_org_identity(org, roster)

    prospect = _make_fighter("Prospect", age=21, overall_bias=4, hype=32, popularity=26)
    vet = _make_fighter("Veteran", age=33, overall_bias=6, hype=58, popularity=52)

    assert identity["label"] == "Talent Factory"
    assert candidate_strategy_score(
        prospect, identity, market_signals={}
    ) > candidate_strategy_score(vet, identity, market_signals={})


def test_division_sniper_prefers_its_focus_weight_class_and_marquee_pairing():
    org = Organization(
        name="Sniper Org", prestige=63.0, bank_balance=18_000_000, is_player=False
    )
    roster = [
        _make_fighter(
            "WW A",
            weight_class=WeightClass.WELTERWEIGHT,
            overall_bias=4,
            hype=50,
            popularity=45,
        ),
        _make_fighter(
            "WW B",
            weight_class=WeightClass.WELTERWEIGHT,
            overall_bias=3,
            hype=48,
            popularity=42,
        ),
        _make_fighter(
            "WW C",
            weight_class=WeightClass.WELTERWEIGHT,
            overall_bias=2,
            hype=44,
            popularity=39,
        ),
        _make_fighter(
            "LW One",
            weight_class=WeightClass.LIGHTWEIGHT,
            overall_bias=5,
            hype=55,
            popularity=50,
        ),
    ]
    identity = derive_org_identity(org, roster)

    ww_target = _make_fighter(
        "WW Target",
        weight_class=WeightClass.WELTERWEIGHT,
        overall_bias=5,
        hype=52,
        popularity=47,
    )
    lw_target = _make_fighter(
        "LW Target",
        weight_class=WeightClass.LIGHTWEIGHT,
        overall_bias=6,
        hype=58,
        popularity=55,
    )

    assert identity["label"] == "Division Sniper"
    assert candidate_strategy_score(
        ww_target, identity, market_signals={}
    ) > candidate_strategy_score(lw_target, identity, market_signals={})

    main_event_pair = event_pairing_strategy_score(
        roster[0],
        ww_target,
        {
            "booking_value": "Strong Main Event",
            "combined_draw": 72.0,
            "prospect_risk": "Low",
        },
        identity,
    )
    lower_pair = event_pairing_strategy_score(
        roster[3],
        lw_target,
        {
            "booking_value": "Risky Development Fight",
            "combined_draw": 50.0,
            "prospect_risk": "Medium",
        },
        identity,
    )
    assert main_event_pair > lower_pair
