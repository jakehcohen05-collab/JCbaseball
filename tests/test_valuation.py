"""Tests for the valuation and team-building layers."""

import pytest

from analytics.valuation import (
    hitter_war, pitcher_war, war_to_dollars, surplus_value, calibrate_runs_per_sd,
)
from analytics.teambuilder import project_team, roster_needs, rank_targets, REPLACEMENT_WINS


def test_league_average_hitter_is_about_two_war():
    # Average bat + average glove at a roughly neutral position ≈ 2 WAR.
    w = hitter_war(100, 600, "2B", dvi=100)
    assert 1.8 <= w.war <= 2.6
    # A league-average DH, by contrast, is barely above replacement — the
    # -17.5 positional penalty and zero defense are correct baseball.
    dh = hitter_war(100, 600, "DH", dvi=100)
    assert dh.war < 0.6


def test_war_increases_with_index():
    lo = hitter_war(100, 600, "SS", dvi=100).war
    hi = hitter_war(140, 600, "SS", dvi=100).war
    assert hi > lo


def test_position_scarcity_rewarded():
    ss = hitter_war(120, 600, "SS", dvi=100).war
    firstb = hitter_war(120, 600, "1B", dvi=100).war
    assert ss > firstb                      # SS worth more than 1B, same bat


def test_pitcher_war_scales_with_innings_and_quality():
    small = pitcher_war(130, 60, "SP").war
    big = pitcher_war(130, 200, "SP").war
    assert big > small
    assert pitcher_war(140, 180).war > pitcher_war(110, 180).war


def test_reliever_replacement_is_lower_bar():
    # Same rate over same innings, RP clears a lower replacement level -> less WAR
    sp = pitcher_war(120, 60, "SP").war
    rp = pitcher_war(120, 60, "RP").war
    assert sp > rp


def test_dollars_and_surplus_signs():
    assert war_to_dollars(4.0, 8.0) == 32.0
    # 4 WAR/yr for 3 yrs at $12M/yr should be big positive surplus.
    good = surplus_value([4, 4, 4], [12, 12, 12], inflation=0.0)
    assert good.surplus > 0
    # 1 WAR/yr at $25M/yr is underwater.
    bad = surplus_value([1, 1], [25, 25], inflation=0.0)
    assert bad.surplus < 0


def test_surplus_inflation_raises_value():
    flat = surplus_value([3, 3, 3], [10, 10, 10], inflation=0.0).market_value
    infl = surplus_value([3, 3, 3], [10, 10, 10], inflation=0.08).market_value
    assert infl > flat


def test_team_wins_stack_on_replacement():
    tp = project_team([2.0, 2.0, 2.0], payroll=60)
    assert tp.projected_wins == pytest.approx(REPLACEMENT_WINS + 6.0, abs=0.1)
    assert tp.projected_wins + tp.projected_losses == pytest.approx(162, abs=0.1)


def test_roster_needs_sorted_worst_first():
    needs = roster_needs({"SS": 4.0, "CF": 0.5, "3B": 1.5})
    assert needs[0]["slot"] == "CF"         # biggest gap first
    assert needs[0]["gap"] >= needs[-1]["gap"]


def test_rank_targets_by_surplus():
    targets = rank_targets([
        ("Cheap Star", 4.0, 8.0),
        ("Fair Deal", 4.0, 32.0),
        ("Overpaid", 1.0, 30.0),
    ], dollars_per_win=8.0)
    assert targets[0].name == "Cheap Star"
    assert targets[-1].name == "Overpaid"
    assert targets[-1].surplus < 0


def test_calibrate_runs_per_sd():
    # Perfectly linear data: 1 SD * full workload -> 20 runs.
    pairs = [(1.0, 1.0, 20.0), (2.0, 1.0, 40.0), (0.5, 1.0, 10.0)]
    assert calibrate_runs_per_sd(pairs) == pytest.approx(20.0, abs=0.1)
