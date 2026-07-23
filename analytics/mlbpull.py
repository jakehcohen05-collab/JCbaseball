"""MLB Stats API data puller.

Pulls a full season of hitting, pitching, and standings from the free public
MLB Stats API (statsapi.mlb.com — no key, no login) and writes tidy CSVs the
projection / valuation / backtest layers consume.

    # one season of everything → data/2026/
    python -m analytics.mlbpull --season 2026 --out data

    # a range of seasons for the backtest (2019 through 2026)
    python -m analytics.mlbpull --seasons 2019-2026 --out data

Run it on a machine with open internet. (This can't run inside a locked-down
sandbox — the API host has to be reachable.) Standard library only.

The flatten/merge functions are pure and unit-tested against sample payloads,
so the parsing is trustworthy even though the live fetch happens on your side.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://statsapi.mlb.com/api/v1"
UA = "Mozilla/5.0 (JCBaseballLab data pull)"

HITTING_FIELDS = [
    "player_id", "name", "team", "age", "position", "season",
    "gamesPlayed", "plateAppearances", "atBats", "runs", "hits", "doubles",
    "triples", "homeRuns", "rbi", "baseOnBalls", "intentionalWalks",
    "hitByPitch", "sacFlies", "strikeOuts", "stolenBases", "caughtStealing",
    "avg", "obp", "slg", "ops", "babip",
]
PITCHING_FIELDS = [
    "player_id", "name", "team", "age", "season", "role",
    "gamesPlayed", "gamesStarted", "inningsPitched", "battersFaced",
    "hits", "runs", "earnedRuns", "homeRuns", "baseOnBalls", "hitBatsmen",
    "strikeOuts", "wins", "losses", "saves", "era", "whip",
    "strikeoutsPer9Inn", "walksPer9Inn", "strikeoutWalkRatio",
]
STANDINGS_FIELDS = [
    "season", "league", "division", "team", "wins", "losses",
    "winningPercentage", "runsScored", "runsAllowed", "runDifferential",
    "divisionRank", "leagueRank",
]

DIVISIONS = {
    200: "AL West", 201: "AL East", 202: "AL Central",
    203: "NL West", 204: "NL East", 205: "NL Central",
}


# ---- HTTP ---------------------------------------------------------------- #

def fetch(url: str, retries: int = 4, timeout: int = 30) -> dict:
    """GET JSON with retries + exponential backoff."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            wait = 2 ** attempt
            print(f"  fetch failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}: {last}")


# ---- Player master (ages, positions) ------------------------------------ #

def build_player_index(season: int) -> dict[int, dict]:
    """Map player_id → {age, position, team} for a season's players."""
    data = fetch(f"{API}/sports/1/players?season={season}")
    idx = {}
    for p in data.get("people", []):
        idx[p["id"]] = {
            "age": p.get("currentAge"),
            "position": (p.get("primaryPosition") or {}).get("abbreviation"),
            "team": (p.get("currentTeam") or {}).get("name"),
        }
    return idx


# ---- Flatten (pure, testable) ------------------------------------------- #

def flatten_hitting(splits: list, players: dict, season: int) -> list[dict]:
    rows = []
    for s in splits:
        st = s.get("stat", {})
        pid = (s.get("player") or {}).get("id")
        meta = players.get(pid, {})
        rows.append({
            "player_id": pid,
            "name": (s.get("player") or {}).get("fullName"),
            "team": (s.get("team") or {}).get("name") or meta.get("team"),
            "age": meta.get("age"),
            "position": (s.get("position") or {}).get("abbreviation") or meta.get("position"),
            "season": season,
            **{f: st.get(f) for f in HITTING_FIELDS[6:]},
        })
    return rows


def flatten_pitching(splits: list, players: dict, season: int) -> list[dict]:
    rows = []
    for s in splits:
        st = s.get("stat", {})
        pid = (s.get("player") or {}).get("id")
        meta = players.get(pid, {})
        gs = st.get("gamesStarted") or 0
        gp = st.get("gamesPlayed") or 0
        rows.append({
            "player_id": pid,
            "name": (s.get("player") or {}).get("fullName"),
            "team": (s.get("team") or {}).get("name") or meta.get("team"),
            "age": meta.get("age"),
            "season": season,
            "role": "SP" if gs and gs >= gp * 0.5 else "RP",
            **{f: st.get(f) for f in PITCHING_FIELDS[6:]},
        })
    return rows


def flatten_standings(records: list, season: int) -> list[dict]:
    rows = []
    for rec in records:
        div = DIVISIONS.get((rec.get("division") or {}).get("id"), "")
        league = "AL" if (rec.get("league") or {}).get("id") == 103 else "NL"
        for tr in rec.get("teamRecords", []):
            rows.append({
                "season": season, "league": league, "division": div,
                "team": (tr.get("team") or {}).get("name"),
                "wins": tr.get("wins"), "losses": tr.get("losses"),
                "winningPercentage": tr.get("winningPercentage"),
                "runsScored": tr.get("runsScored"),
                "runsAllowed": tr.get("runsAllowed"),
                "runDifferential": tr.get("runDifferential"),
                "divisionRank": tr.get("divisionRank"),
                "leagueRank": tr.get("leagueRank"),
            })
    return rows


# ---- Paginated stat pulls ----------------------------------------------- #

def _pull_stats(group: str, season: int, pool: str, page: int = 250) -> list:
    """Pull all splits for a stat group, paging through the API."""
    splits, offset = [], 0
    while True:
        url = (f"{API}/stats?stats=season&group={group}&season={season}"
               f"&sportId=1&playerPool={pool}&limit={page}&offset={offset}")
        data = fetch(url)
        chunk = (data.get("stats") or [{}])[0].get("splits", [])
        splits.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    return splits


def pull_season(season: int, out_dir: Path, pool: str = "all") -> dict:
    """Pull hitting, pitching, and standings for one season → CSVs."""
    print(f"[{season}] building player index…")
    players = build_player_index(season)

    print(f"[{season}] hitting…")
    hitting = flatten_hitting(_pull_stats("hitting", season, pool), players, season)
    print(f"[{season}] pitching…")
    pitching = flatten_pitching(_pull_stats("pitching", season, pool), players, season)
    print(f"[{season}] standings…")
    standings = flatten_standings(
        fetch(f"{API}/standings?leagueId=103,104&season={season}"
              f"&standingsTypes=regularSeason").get("records", []), season)

    season_dir = out_dir / str(season)
    season_dir.mkdir(parents=True, exist_ok=True)
    write_csv(hitting, HITTING_FIELDS, season_dir / "hitting.csv")
    write_csv(pitching, PITCHING_FIELDS, season_dir / "pitching.csv")
    write_csv(standings, STANDINGS_FIELDS, season_dir / "standings.csv")
    print(f"[{season}] wrote {len(hitting)} hitters, {len(pitching)} pitchers, "
          f"{len(standings)} teams → {season_dir}/")
    return {"hitting": len(hitting), "pitching": len(pitching),
            "standings": len(standings)}


def write_csv(rows: list[dict], fields: list[str], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---- CLI ----------------------------------------------------------------- #

def _parse_seasons(arg: str) -> list[int]:
    if "-" in arg:
        a, b = arg.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(arg)]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pull MLB Stats API season data to CSV.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--season", type=int, help="single season, e.g. 2026")
    g.add_argument("--seasons", type=str, help="range, e.g. 2019-2026")
    ap.add_argument("--out", type=str, default="data", help="output directory")
    ap.add_argument("--pool", default="all",
                    choices=["all", "qualified", "rookies"],
                    help="player pool (default: all)")
    args = ap.parse_args(argv)

    seasons = [args.season] if args.season else _parse_seasons(args.seasons)
    out = Path(args.out)
    for yr in seasons:
        pull_season(yr, out, pool=args.pool)
    print(f"\nDone. Data in {out}/  —  feed it to analytics.backtest or the engine.")


if __name__ == "__main__":
    main()
