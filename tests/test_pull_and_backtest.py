"""Tests for the MLB pull parsing and the backtest harness.

The live fetch can't run here (no network), so we test the pure functions:
payload flattening (against realistic sample JSON) and the backtest math
(against synthetic data whose answer we know).
"""

import random

from analytics.mlbpull import flatten_hitting, flatten_pitching, flatten_standings
from analytics.backtest import Record, run_backtest, rmse, corr


# ---- pull parsing -------------------------------------------------------- #

SAMPLE_HIT_SPLITS = [
    {"player": {"id": 1, "fullName": "Test Judge"},
     "team": {"name": "New York Yankees"},
     "stat": {"gamesPlayed": 99, "plateAppearances": 430, "atBats": 355,
              "hits": 118, "doubles": 21, "triples": 1, "homeRuns": 34,
              "baseOnBalls": 66, "hitByPitch": 4, "sacFlies": 5,
              "strikeOuts": 92, "avg": ".332", "obp": ".440", "slg": ".685",
              "ops": "1.125", "rbi": 88, "stolenBases": 8}},
]
SAMPLE_PLAYERS = {1: {"age": 33, "position": "RF", "team": "New York Yankees"}}


def test_flatten_hitting_maps_fields_and_age():
    rows = flatten_hitting(SAMPLE_HIT_SPLITS, SAMPLE_PLAYERS, 2026)
    r = rows[0]
    assert r["name"] == "Test Judge"
    assert r["age"] == 33                      # merged from player index
    assert r["position"] == "RF"
    assert r["homeRuns"] == 34
    assert r["ops"] == "1.125"
    assert r["season"] == 2026


def test_flatten_pitching_infers_role():
    splits = [
        {"player": {"id": 2, "fullName": "Test Starter"}, "team": {"name": "X"},
         "stat": {"gamesPlayed": 20, "gamesStarted": 20, "inningsPitched": "130.1",
                  "strikeOuts": 168, "baseOnBalls": 22, "era": "2.31"}},
        {"player": {"id": 3, "fullName": "Test Closer"}, "team": {"name": "X"},
         "stat": {"gamesPlayed": 60, "gamesStarted": 0, "inningsPitched": "60.0",
                  "saves": 40, "strikeOuts": 90, "era": "1.90"}},
    ]
    rows = flatten_pitching(splits, {}, 2026)
    assert rows[0]["role"] == "SP"
    assert rows[1]["role"] == "RP"


def test_flatten_standings():
    records = [{
        "league": {"id": 103}, "division": {"id": 201},
        "teamRecords": [{"team": {"name": "New York Yankees"}, "wins": 61,
                         "losses": 40, "winningPercentage": ".604",
                         "runsScored": 512, "runsAllowed": 420,
                         "runDifferential": 92, "divisionRank": "1"}],
    }]
    rows = flatten_standings(records, 2026)
    assert rows[0]["league"] == "AL"
    assert rows[0]["division"] == "AL East"
    assert rows[0]["wins"] == 61


# ---- backtest math ------------------------------------------------------- #

def test_metrics_basic():
    assert rmse([(1, 1), (2, 2)]) == 0.0
    assert abs(corr([(1, 1), (2, 2), (3, 3)]) - 1.0) < 1e-9


def test_projection_beats_naive_on_mean_reverting_data():
    """Synthesize a world where true talent is stable but single seasons are
    noisy. Projection (which regresses noise out) should beat naive-last, which
    chases the noise."""
    rng = random.Random(42)
    records = []
    for pid in range(200):
        talent = rng.gauss(100, 15)            # stable underlying talent
        for season in range(2019, 2027):
            age = 27 + (season - 2023)          # flat-ish age band
            noise = rng.gauss(0, 18)            # big single-season swing
            observed = talent + noise
            records.append(Record(str(pid), season, age, observed, sample=500))

    report = run_backtest(records, min_prior=2, min_sample=200,
                          league_avg=100, regression_sample=200)
    # With heavy noise, regressing beats chasing last year's number.
    assert report["skill_vs_naive"] > 0
    assert report["methods"]["projection"]["rmse"] < report["methods"]["naive_last"]["rmse"]
    assert report["n"] > 500


def test_backtest_respects_min_sample_and_prior():
    records = [
        Record("a", 2024, 27, 120, 50),   # small sample
        Record("a", 2025, 28, 118, 600),
        Record("a", 2026, 29, 121, 600),
    ]
    # min_prior=1, min_sample=200: 2026 qualifies (prior 2025 ok), 2025's target
    # sample ok but its only prior (2024) is fine for prior-count; 2024 has no prior.
    report = run_backtest(records, min_prior=1, min_sample=200, league_avg=100)
    assert report["n"] == 2      # 2025 and 2026 are predictable targets
