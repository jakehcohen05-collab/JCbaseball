"""Analysis queries.

Higher-level functions that pull season totals out of the database and layer
the sabermetric rate stats on top. These are the functions the CLI calls and
the natural entry point for notebooks or scripts.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict

from . import sabermetrics as sm

# Minimum plate appearances / innings to qualify for a rate-stat leaderboard,
# so a 1-for-1 pinch hitter doesn't top the AVG list.
DEFAULT_MIN_PA = 20
DEFAULT_MIN_OUTS = 30   # 10 innings


def _player_name(conn: sqlite3.Connection, player_id: int) -> str:
    row = conn.execute(
        "SELECT first_name, last_name FROM players WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    if not row:
        return f"#{player_id}"
    return f"{row['first_name']} {row['last_name']}"


def player_batting(conn: sqlite3.Connection, player_id: int, season: int) -> dict:
    """Return one player's season batting totals plus computed rate stats."""
    row = conn.execute(
        "SELECT * FROM batting_totals WHERE player_id = ? AND season = ?",
        (player_id, season),
    ).fetchone()
    if not row:
        return {}
    rates = sm.batting_rates(row)
    return {"name": _player_name(conn, player_id), **row, **asdict(rates)}


def player_pitching(conn: sqlite3.Connection, player_id: int, season: int) -> dict:
    """Return one player's season pitching totals plus computed rate stats."""
    row = conn.execute(
        "SELECT * FROM pitching_totals WHERE player_id = ? AND season = ?",
        (player_id, season),
    ).fetchone()
    if not row:
        return {}
    rates = sm.pitching_rates(row)
    return {"name": _player_name(conn, player_id), **row, **asdict(rates)}


def batting_leaderboard(
    conn: sqlite3.Connection,
    season: int,
    stat: str = "ops",
    min_pa: int = DEFAULT_MIN_PA,
    limit: int = 10,
    descending: bool = True,
) -> list[dict]:
    """Rank qualified batters for a season by any computed batting stat."""
    rows = conn.execute(
        "SELECT * FROM batting_totals WHERE season = ?", (season,)
    ).fetchall()
    out = []
    for row in rows:
        pa = row["ab"] + row["bb"] + row["hbp"] + row["sf"]
        if pa < min_pa:
            continue
        rates = sm.batting_rates(row)
        record = {"name": _player_name(conn, row["player_id"]),
                  "pa": pa, **row, **asdict(rates)}
        if stat not in record:
            raise ValueError(f"unknown batting stat: {stat!r}")
        out.append(record)
    out.sort(key=lambda r: r[stat], reverse=descending)
    return out[:limit]


def pitching_leaderboard(
    conn: sqlite3.Connection,
    season: int,
    stat: str = "era",
    min_outs: int = DEFAULT_MIN_OUTS,
    limit: int = 10,
    descending: bool | None = None,
) -> list[dict]:
    """Rank qualified pitchers for a season by any computed pitching stat.

    For ERA/WHIP/FIP/BB9 lower is better, so those default to ascending.
    """
    if descending is None:
        descending = stat not in ("era", "whip", "fip", "bb9")
    rows = conn.execute(
        "SELECT * FROM pitching_totals WHERE season = ?", (season,)
    ).fetchall()
    out = []
    for row in rows:
        if row["outs"] < min_outs:
            continue
        rates = sm.pitching_rates(row)
        record = {"name": _player_name(conn, row["player_id"]), **row, **asdict(rates)}
        if stat not in record:
            raise ValueError(f"unknown pitching stat: {stat!r}")
        out.append(record)
    out.sort(key=lambda r: r[stat], reverse=descending)
    return out[:limit]


def team_standings(conn: sqlite3.Connection, season: int) -> list[dict]:
    """Compute win/loss records and run differential from played games."""
    teams = conn.execute("SELECT team_id, abbrev, name, league, division "
                         "FROM teams").fetchall()
    stats = {t["team_id"]: {"w": 0, "l": 0, "rs": 0, "ra": 0, **t} for t in teams}

    games = conn.execute(
        "SELECT * FROM games WHERE season = ? AND home_score IS NOT NULL",
        (season,),
    ).fetchall()
    for g in games:
        home, away = stats[g["home_team_id"]], stats[g["away_team_id"]]
        home["rs"] += g["home_score"]; home["ra"] += g["away_score"]
        away["rs"] += g["away_score"]; away["ra"] += g["home_score"]
        if g["home_score"] > g["away_score"]:
            home["w"] += 1; away["l"] += 1
        else:
            away["w"] += 1; home["l"] += 1

    table = []
    for t in stats.values():
        gp = t["w"] + t["l"]
        t["gp"] = gp
        t["pct"] = round(t["w"] / gp, 3) if gp else 0.0
        t["run_diff"] = t["rs"] - t["ra"]
        # Pythagorean expected win% (exponent 1.83, Bill James refinement).
        rs, ra = t["rs"], t["ra"]
        t["pyth_pct"] = round(rs ** 1.83 / (rs ** 1.83 + ra ** 1.83), 3) if (rs or ra) else 0.0
        table.append(t)
    table.sort(key=lambda r: (r["pct"], r["run_diff"]), reverse=True)
    return table
