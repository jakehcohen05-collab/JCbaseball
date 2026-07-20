"""Unit tests for the pure sabermetric functions.

Expected values are hand-computed from textbook formulas so a regression in the
math is caught immediately.
"""

import math

from baseball import sabermetrics as sm


def approx(a, b, tol=1e-4):
    return math.isclose(a, b, abs_tol=tol)


def test_batting_average():
    assert approx(sm.batting_average(150, 500), 0.300)
    assert sm.batting_average(0, 0) == 0.0            # no divide-by-zero


def test_on_base_percentage():
    # 150 H, 50 BB, 5 HBP, 500 AB, 5 SF -> (205)/(560)
    assert approx(sm.on_base_percentage(150, 50, 5, 500, 5), 205 / 560)


def test_slugging_and_ops():
    # 150 H incl 30 2B, 5 3B, 25 HR -> singles 90
    # TB = 90 + 60 + 15 + 100 = 265 over 500 AB
    slg = sm.slugging(150, 30, 5, 25, 500)
    assert approx(slg, 265 / 500)
    obp = sm.on_base_percentage(150, 50, 5, 500, 5)
    assert approx(sm.ops(obp, slg), obp + slg)


def test_iso():
    assert approx(sm.iso(0.530, 0.300), 0.230)


def test_babip():
    # (H - HR) / (AB - SO - HR + SF)
    assert approx(sm.babip(150, 25, 500, 100, 5), (150 - 25) / (500 - 100 - 25 + 5))


def test_era_and_whip():
    # 90 outs = 30 IP, 10 ER -> 3.00 ERA
    assert approx(sm.era(10, 90), 3.00)
    # 30 BB+H over 30 IP -> 1.00 WHIP... use 30 walks+hits
    assert approx(sm.whip(10, 20, 90), 30 / 30)
    assert sm.era(5, 0) == 0.0                        # no outs -> guard


def test_innings_pitched():
    assert approx(sm.innings_pitched(20), 20 / 3)     # 6.2 IP == 6.667


def test_k_and_bb_per_9():
    assert approx(sm.k_per_9(30, 90), 9.0)            # 30 K in 30 IP
    assert approx(sm.bb_per_9(10, 90), 3.0)
    assert approx(sm.k_bb_ratio(30, 10), 3.0)
    assert sm.k_bb_ratio(30, 0) == 0.0


def test_fip_is_finite_and_scaled():
    val = sm.fip(hr=5, bb=20, hbp=2, so=60, outs=180)  # 60 IP
    assert 1.0 < val < 6.0
    assert sm.fip(0, 0, 0, 0, 0) == 0.0


def test_woba_reasonable_range():
    # A strong line should land in the .350-.450 wOBA band.
    val = sm.woba(bb=50, hbp=5, h=150, doubles=30, triples=5, hr=25,
                  ab=500, sf=5)
    assert 0.35 < val < 0.50


def test_batting_rates_bundle():
    row = {"h": 150, "ab": 500, "bb": 50, "hbp": 5, "sf": 5, "doubles": 30,
           "triples": 5, "hr": 25, "so": 100}
    rates = sm.batting_rates(row)
    assert approx(rates.avg, 0.300)
    assert approx(rates.ops, rates.obp + rates.slg)


def test_pitching_rates_bundle():
    row = {"outs": 180, "h": 50, "er": 20, "bb": 15, "so": 60, "hr": 5}
    rates = sm.pitching_rates(row)
    assert approx(rates.ip, 60.0)
    assert approx(rates.era, 20 * 9 / 60)
