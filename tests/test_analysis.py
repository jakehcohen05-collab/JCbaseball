"""Integration tests: seed an in-memory database and exercise the queries."""

import pytest

from baseball import analysis, db, seed
from baseball.seed import SEASON


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_schema(c)
    seed.seed(c)
    yield c
    c.close()


def test_seed_populates_tables(conn):
    for table in ("teams", "players", "games", "batting_lines", "pitching_lines"):
        n = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        assert n > 0, f"{table} should not be empty"


def test_standings_sum_to_games(conn):
    table = analysis.team_standings(conn, SEASON)
    assert len(table) == 4
    total_games = conn.execute(
        "SELECT COUNT(*) AS n FROM games WHERE season = ?", (SEASON,)
    ).fetchone()["n"]
    # Each game contributes exactly one win and one loss across the league.
    assert sum(t["w"] for t in table) == total_games
    assert sum(t["l"] for t in table) == total_games
    for t in table:
        assert t["w"] + t["l"] == t["gp"]


def test_standings_pct_matches_record(conn):
    for t in analysis.team_standings(conn, SEASON):
        if t["gp"]:
            # pct is rounded to 3 decimals for display, so allow that tolerance.
            assert abs(t["pct"] - t["w"] / t["gp"]) < 5e-4


def test_batting_leaderboard_sorted(conn):
    board = analysis.batting_leaderboard(conn, SEASON, stat="ops", limit=5)
    assert board, "leaderboard should not be empty"
    ops_values = [r["ops"] for r in board]
    assert ops_values == sorted(ops_values, reverse=True)
    assert len(board) <= 5


def test_pitching_leaderboard_era_ascending(conn):
    board = analysis.pitching_leaderboard(conn, SEASON, stat="era", limit=5)
    assert board
    era_values = [r["era"] for r in board]
    assert era_values == sorted(era_values)   # lower ERA is better


def test_unknown_stat_raises(conn):
    with pytest.raises(ValueError):
        analysis.batting_leaderboard(conn, SEASON, stat="not_a_stat")


def test_player_batting_card(conn):
    # Marco Reyes is the highest-skill batter and should have real totals.
    card = analysis.player_batting(conn, 101, SEASON)
    assert card["name"] == "Marco Reyes"
    assert card["ab"] > 0
    assert 0.0 <= card["avg"] <= 1.0


def test_seed_is_deterministic():
    def fingerprint():
        c = db.connect(":memory:")
        db.init_schema(c)
        seed.seed(c)
        row = c.execute("SELECT SUM(h) AS h, SUM(hr) AS hr, SUM(ab) AS ab "
                        "FROM batting_lines").fetchone()
        c.close()
        return (row["h"], row["hr"], row["ab"])

    assert fingerprint() == fingerprint()
