from models.models import Fighter, FighterStyle, WeightClass
from simulation.matchmaking import assess_matchup


def make_fighter(
    name: str,
    overall_bias: int = 0,
    age: int = 28,
    prime_start: int = 25,
    prime_end: int = 31,
    hype: float = 40.0,
    popularity: float = 40.0,
    style=FighterStyle.STRIKER,
) -> Fighter:
    base = 70 + overall_bias
    return Fighter(
        name=name,
        age=age,
        nationality="American",
        weight_class=WeightClass.LIGHTWEIGHT,
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
        prime_start=prime_start,
        prime_end=prime_end,
        hype=hype,
        popularity=popularity,
    )


def test_main_event_signal_for_close_high_draw_matchup():
    a = make_fighter("A", overall_bias=6, hype=72, popularity=65)
    b = make_fighter(
        "B", overall_bias=5, hype=68, popularity=62, style=FighterStyle.WRESTLER
    )
    result = assess_matchup(a, b)
    assert result["competitiveness"] in {"Toss-Up", "Competitive"}
    assert result["star_power"] == "High"
    assert result["booking_value"] in {"Strong Main Event", "Strong Co-Main"}


def test_prospect_risk_signal_for_young_fighter_vs_tougher_vet():
    prospect = make_fighter(
        "Prospect",
        overall_bias=-2,
        age=22,
        prime_start=25,
        prime_end=30,
        hype=28,
        popularity=22,
    )
    veteran = make_fighter(
        "Veteran",
        overall_bias=8,
        age=34,
        prime_start=25,
        prime_end=31,
        hype=35,
        popularity=38,
        style=FighterStyle.WRESTLER,
    )
    result = assess_matchup(prospect, veteran)
    assert result["prospect_risk"] in {"Medium", "High"}
    assert result["reasons"]
