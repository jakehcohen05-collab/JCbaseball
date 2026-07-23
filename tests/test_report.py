"""End-to-end test of the report generator on synthetic pulled CSVs."""

import csv
from pathlib import Path

import pytest

from analytics.indexing import woba_of, fip_of, to_index
from analytics import report


def _write(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


HIT_COLS = ["player_id", "name", "team", "age", "position", "season",
            "plateAppearances", "atBats", "hits", "doubles", "triples",
            "homeRuns", "baseOnBalls", "hitByPitch", "sacFlies", "strikeOuts"]
PIT_COLS = ["player_id", "name", "team", "age", "season", "role",
            "inningsPitched", "homeRuns", "baseOnBalls", "hitBatsmen", "strikeOuts"]


def _hit(pid, name, age, season, pa, h, hr, bb):
    ab = pa - bb
    return {"player_id": pid, "name": name, "team": "TST", "age": age,
            "position": "SS", "season": season, "plateAppearances": pa,
            "atBats": ab, "hits": h, "doubles": int(h * 0.2), "triples": 1,
            "homeRuns": hr, "baseOnBalls": bb, "hitByPitch": 2, "sacFlies": 3,
            "strikeOuts": int(pa * 0.2)}


def _pit(pid, name, age, season, ip, so, bb, hr):
    return {"player_id": pid, "name": name, "team": "TST", "age": age,
            "season": season, "role": "SP", "inningsPitched": ip,
            "homeRuns": hr, "baseOnBalls": bb, "hitBatsmen": 2, "strikeOuts": so}


@pytest.fixture
def data_dir(tmp_path):
    # Three seasons; "Star" clearly out-hits "Scrub"; ace out-pitches filler.
    for season, age in [(2024, 25), (2025, 26), (2026, 27)]:
        _write(tmp_path / str(season) / "hitting.csv", HIT_COLS, [
            _hit("1", "Star Hitter", age, season, 650, 200, 40, 90),
            _hit("2", "Mid Hitter", age, season, 600, 150, 20, 50),
            _hit("3", "Scrub Hitter", age, season, 550, 120, 8, 30),
            _hit("4", "Filler A", age, season, 500, 125, 12, 35),
            _hit("5", "Filler B", age, season, 520, 130, 15, 40),
        ])
        _write(tmp_path / str(season) / "pitching.csv", PIT_COLS, [
            _pit("11", "Ace Arm", age, season, "190.0", 250, 35, 12),
            _pit("12", "Mid Arm", age, season, "170.0", 150, 55, 22),
            _pit("13", "Filler Arm", age, season, "160.0", 120, 70, 28),
            _pit("14", "Filler Arm2", age, season, "150.0", 110, 65, 25),
        ])
    return tmp_path


def test_indexing_orders_talent():
    rows = {"a": 0.400, "b": 0.320, "c": 0.280}
    idx = to_index(rows)
    assert idx["a"] > idx["b"] > idx["c"]
    # FIP inverted: lower raw → higher index.
    fip = to_index({"a": 2.5, "b": 4.0, "c": 5.5}, invert=True)
    assert fip["a"] > fip["b"] > fip["c"]


def test_report_generates_ranked_output(data_dir):
    hitters, pitchers, out = report.generate(str(data_dir), season=2026,
                                             out_dir=str(data_dir / "reports"))
    assert hitters and pitchers
    # Sorted by projected WAR, descending.
    assert [h["proj_war"] for h in hitters] == sorted(
        [h["proj_war"] for h in hitters], reverse=True)
    # The star should top the hitter board.
    assert hitters[0]["name"] == "Star Hitter"
    assert pitchers[0]["name"] == "Ace Arm"
    # Files written.
    assert (out / "2026_hitters_proj.csv").exists()
    assert (out / "2026_pitchers_proj.csv").exists()
    assert (out / "2026_projections.md").exists()
    # Markdown has a table row for the star.
    assert "Star Hitter" in (out / "2026_projections.md").read_text()


def test_star_projects_above_scrub(data_dir):
    hitters, _, _ = report.generate(str(data_dir), season=2026,
                                    out_dir=str(data_dir / "reports"))
    by_name = {h["name"]: h for h in hitters}
    assert by_name["Star Hitter"]["proj_war"] > by_name["Scrub Hitter"]["proj_war"]
    assert by_name["Star Hitter"]["proj_index"] > by_name["Scrub Hitter"]["proj_index"]
