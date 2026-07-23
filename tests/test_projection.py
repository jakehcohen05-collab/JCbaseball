"""Tests for the projection engine and aging curves."""

import pytest

from analytics.aging import aging_delta, aging_value, estimate_aging_curve, DEFAULT_AGING
from analytics.projection import ProjInput, project_index


def test_regression_pulls_small_samples_toward_league_avg():
    # A tiny 20-PA sample at 160 should regress hard toward 100.
    small = project_index([ProjInput(160, 20, 27)], proj_age=27,
                          regression_sample=200, base_playing_time=200)
    big = project_index([ProjInput(160, 600, 27)], proj_age=27,
                        regression_sample=200, base_playing_time=200)
    assert small.value < big.value          # small sample regressed more
    assert 100 < small.value < 160
    assert big.value > 130                  # large sample keeps most of its signal


def test_recency_weighting_favors_recent_seasons():
    # Same samples; a rising player should project above a falling one.
    rising = project_index(
        [ProjInput(110, 500, 26), ProjInput(120, 500, 27), ProjInput(130, 500, 28)][::-1],
        proj_age=29)
    falling = project_index(
        [ProjInput(130, 500, 26), ProjInput(120, 500, 27), ProjInput(110, 500, 28)][::-1],
        proj_age=29)
    # Both regress + age the same way; recency is the only difference.
    assert rising.value > falling.value


def test_aging_curve_peaks_and_declines():
    assert aging_value(27) == max(aging_value(a) for a in range(19, 41))
    assert aging_delta(24, 27) > 0          # improving toward peak
    assert aging_delta(30, 34) < 0          # declining past peak


def test_aging_shift_applied_in_projection():
    # A 24-year-old projected to 27 should get an age bump vs. flat.
    young = project_index([ProjInput(120, 600, 24)], proj_age=27)
    assert young.components["aging_shift"] > 0
    old = project_index([ProjInput(120, 600, 33)], proj_age=36)
    assert old.components["aging_shift"] < 0


def test_projected_playing_time_reasonable():
    pr = project_index([ProjInput(120, 600, 27), ProjInput(120, 550, 26)],
                       proj_age=28, base_playing_time=200)
    # 0.5*600 + 0.1*550 + 200 = 555
    assert pr.sample == pytest.approx(555, abs=1)


def test_estimate_aging_curve_recovers_shape():
    # Synthesize pairs from the default curve; the estimator should recover a
    # curve that also peaks in the mid-to-late 20s.
    pairs = []
    for age in range(21, 38):
        delta = DEFAULT_AGING[age + 1] - DEFAULT_AGING[age]
        # 30 fake players per age, each with a 500-PA follow-up season.
        for _ in range(30):
            pairs.append((age, 100.0, 100.0 + delta, 500))
    curve = estimate_aging_curve(pairs)
    peak_age = max(curve, key=curve.get)
    assert 25 <= peak_age <= 29
