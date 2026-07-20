"""Seed the database with a small, self-contained sample season.

The data is fictional but statistically plausible: four teams, a handful of
hitters and pitchers each, and a round-robin of games with generated box-score
lines. It exists so the tools work end-to-end immediately after install,
without needing an external data feed.

The generator is fully deterministic (fixed RNG seed) so the same database is
produced every run — useful for tests and reproducible demos.
"""

from __future__ import annotations

import random
import sqlite3

from . import db

SEASON = 2024
_RNG_SEED = 8675309

TEAMS = [
    # (team_id, abbrev, name, league, division)
    (1, "BOS", "Boston Bay Staters", "AL", "East"),
    (2, "NYM", "New York Metropolitans", "NL", "East"),
    (3, "CHI", "Chicago Windies", "NL", "Central"),
    (4, "OAK", "Oakland Athletics", "AL", "West"),
]

# (player_id, first, last, bats, throws, pos, team_id, skill)
# `skill` (0.0-1.0) nudges the box-score generator so stars out-hit scrubs.
BATTERS = [
    (101, "Marco", "Reyes",   "R", "R", "SS", 1, 0.90),
    (102, "Dell",  "Hoyt",    "L", "L", "1B", 1, 0.72),
    (103, "Sam",   "Okafor",  "S", "R", "CF", 1, 0.60),
    (104, "Tomas", "Vidal",   "R", "R", "3B", 2, 0.85),
    (105, "Ike",   "Brennan", "L", "L", "RF", 2, 0.55),
    (106, "Rudy",  "Chen",    "R", "R", "2B", 2, 0.48),
    (107, "Gene",  "Falk",    "L", "R", "LF", 3, 0.80),
    (108, "Ozzie", "Kane",    "R", "R", "C",  3, 0.50),
    (109, "Pete",  "Marsh",   "S", "R", "DH", 3, 0.65),
    (110, "Luis",  "Arroyo",  "R", "R", "SS", 4, 0.78),
    (111, "Cal",   "Diggs",   "L", "L", "1B", 4, 0.58),
    (112, "Ford",  "Nakai",   "R", "R", "CF", 4, 0.44),
]

# (player_id, first, last, throws, team_id, skill)
PITCHERS = [
    (201, "Jose",  "Medina",  "R", 1, 0.88),
    (202, "Walt",  "Cobb",    "L", 1, 0.62),
    (203, "Rhys",  "Palmer",  "R", 2, 0.83),
    (204, "Ari",   "Stern",   "L", 2, 0.55),
    (205, "Kip",   "Novak",   "R", 3, 0.79),
    (206, "Dane",  "Ellis",   "R", 3, 0.50),
    (207, "Yuki",  "Sato",    "L", 4, 0.86),
    (208, "Bo",    "Trent",   "R", 4, 0.58),
]


def _insert_reference(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO teams (team_id, abbrev, name, league, division) "
        "VALUES (?, ?, ?, ?, ?)", TEAMS,
    )
    conn.executemany(
        "INSERT INTO players (player_id, first_name, last_name, bats, throws, "
        "primary_pos, team_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(p[0], p[1], p[2], p[3], p[4], p[5], p[6]) for p in BATTERS],
    )
    conn.executemany(
        "INSERT INTO players (player_id, first_name, last_name, throws, "
        "primary_pos, team_id) VALUES (?, ?, ?, ?, 'SP', ?)",
        [(p[0], p[1], p[2], p[3], p[4]) for p in PITCHERS],
    )


def _gen_batting_line(rng: random.Random, skill: float) -> dict:
    """Generate one plausible batting line weighted by a player's skill."""
    ab = rng.randint(3, 5)
    line = {k: 0 for k in ("ab", "r", "h", "doubles", "triples", "hr", "rbi",
                           "bb", "so", "hbp", "sf", "sb", "cs")}
    line["ab"] = ab
    hit_prob = 0.20 + 0.14 * skill          # ~.200 to ~.340 true talent
    for _ in range(ab):
        if rng.random() < hit_prob:
            line["h"] += 1
            roll = rng.random()
            if roll < 0.62:
                pass                          # single
            elif roll < 0.82:
                line["doubles"] += 1
            elif roll < 0.87:
                line["triples"] += 1
            else:
                line["hr"] += 1
        elif rng.random() < 0.22:
            line["so"] += 1
    if rng.random() < 0.10 + 0.10 * skill:
        line["bb"] += 1
    if rng.random() < 0.02:
        line["hbp"] += 1
    line["rbi"] = line["h"] + (1 if rng.random() < 0.3 else 0)
    line["r"] = min(line["h"], 1 if rng.random() < 0.4 else 0)
    if rng.random() < 0.08 * (skill + 0.3):
        line["sb"] += 1
    return line


def _gen_pitching_line(rng: random.Random, skill: float, starter: bool) -> dict:
    """Generate one plausible pitching line weighted by skill."""
    outs = rng.randint(15, 21) if starter else rng.randint(2, 6)
    bf = outs + rng.randint(1, 6)
    line = {k: 0 for k in ("outs", "bf", "h", "r", "er", "bb", "so", "hr",
                           "win", "loss", "save", "started")}
    line["outs"] = outs
    line["bf"] = bf
    line["started"] = 1 if starter else 0
    hit_rate = 0.30 - 0.10 * skill
    for _ in range(bf - outs if bf > outs else 0):
        r = rng.random()
        if r < hit_rate:
            line["h"] += 1
            if rng.random() < 0.12:
                line["hr"] += 1
        else:
            line["bb"] += 1
    line["so"] = int(outs * (0.25 + 0.25 * skill))
    # Each baserunner has a chance to come around; better pitchers strand more.
    score_prob = 0.34 - 0.12 * skill
    runners = line["h"] - line["hr"] + line["bb"]
    scored = sum(1 for _ in range(max(runners, 0)) if rng.random() < score_prob)
    line["r"] = line["hr"] + scored
    # A small share of runs are unearned (errors).
    line["er"] = line["r"] - (1 if line["r"] and rng.random() < 0.08 else 0)
    return line


def seed(conn: sqlite3.Connection, verbose: bool = False) -> None:
    """Populate an initialized (empty) database with the sample season."""
    rng = random.Random(_RNG_SEED)
    _insert_reference(conn)

    batters_by_team: dict[int, list] = {}
    pitchers_by_team: dict[int, list] = {}
    for p in BATTERS:
        batters_by_team.setdefault(p[6], []).append(p)
    for p in PITCHERS:
        pitchers_by_team.setdefault(p[4], []).append(p)

    team_ids = [t[0] for t in TEAMS]
    game_id = 1
    line_id = 1
    pline_id = 1
    day = 1

    # Triple round-robin: every ordered pair of teams plays several times.
    for _round in range(6):
        for home in team_ids:
            for away in team_ids:
                if home == away:
                    continue
                home_score = 0
                away_score = 0
                batting_rows = []
                pitching_rows = []

                for team_id, is_home in ((home, True), (away, False)):
                    for b in batters_by_team[team_id]:
                        line = _gen_batting_line(rng, b[7])
                        batting_rows.append((line_id, game_id, b[0], team_id,
                                             line["ab"], line["r"], line["h"],
                                             line["doubles"], line["triples"],
                                             line["hr"], line["rbi"], line["bb"],
                                             line["so"], line["hbp"], line["sf"],
                                             line["sb"], line["cs"]))
                        line_id += 1
                        if is_home:
                            home_score += line["r"]
                        else:
                            away_score += line["r"]

                    staff = pitchers_by_team[team_id]
                    starter = staff[0]
                    sline = _gen_pitching_line(rng, starter[5], True)
                    pitching_rows.append((pline_id, game_id, starter[0], team_id, sline))
                    pline_id += 1
                    if len(staff) > 1:
                        rp = staff[1]
                        rline = _gen_pitching_line(rng, rp[5], False)
                        pitching_rows.append((pline_id, game_id, rp[0], team_id, rline))
                        pline_id += 1

                # Ensure a decisive game.
                if home_score == away_score:
                    home_score += 1

                conn.execute(
                    "INSERT INTO games (game_id, game_date, season, home_team_id, "
                    "away_team_id, home_score, away_score) VALUES (?,?,?,?,?,?,?)",
                    (game_id, f"{SEASON}-04-{day:02d}", SEASON, home, away,
                     home_score, away_score),
                )

                conn.executemany(
                    "INSERT INTO batting_lines (id, game_id, player_id, team_id, "
                    "ab, r, h, doubles, triples, hr, rbi, bb, so, hbp, sf, sb, cs) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batting_rows,
                )

                # Assign decision + save, then insert pitching lines.
                home_won = home_score > away_score
                for pid, gid, player_id, team_id, sline in pitching_rows:
                    won = (team_id == home) == home_won
                    sline["win"] = 1 if (won and sline["started"]) else 0
                    sline["loss"] = 1 if (not won and sline["started"]) else 0
                    conn.execute(
                        "INSERT INTO pitching_lines (id, game_id, player_id, team_id, "
                        "outs, bf, h, r, er, bb, so, hr, win, loss, save, started) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (pid, gid, player_id, team_id, sline["outs"], sline["bf"],
                         sline["h"], sline["r"], sline["er"], sline["bb"],
                         sline["so"], sline["hr"], sline["win"], sline["loss"],
                         sline["save"], sline["started"]),
                    )

                game_id += 1
                day = day % 28 + 1

    conn.commit()
    if verbose:
        print(f"Seeded {game_id - 1} games, {line_id - 1} batting lines, "
              f"{pline_id - 1} pitching lines for the {SEASON} season.")


def build(db_path=db.DEFAULT_DB_PATH, verbose: bool = True) -> None:
    """Create a fresh database file and seed it (drops any existing file)."""
    from pathlib import Path
    path = Path(db_path)
    if path.exists():
        path.unlink()
    conn = db.connect(db_path)
    db.init_schema(conn)
    seed(conn, verbose=verbose)
    conn.close()
    if verbose:
        print(f"Database ready at {db_path}")


if __name__ == "__main__":
    build()
