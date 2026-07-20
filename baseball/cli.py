"""Command-line interface for the baseball analysis database.

Usage examples::

    python -m baseball.cli init                       # build + seed the database
    python -m baseball.cli standings                  # team standings
    python -m baseball.cli bat-leaders --stat ops     # batting leaderboard
    python -m baseball.cli pitch-leaders --stat era   # pitching leaderboard
    python -m baseball.cli player "Marco Reyes"       # one player's stat card
"""

from __future__ import annotations

import argparse
import sqlite3
import sys

from . import analysis, db, seed
from .seed import SEASON


def _resolve_player(conn: sqlite3.Connection, needle: str) -> int | None:
    """Find a player_id by 'First Last', last name, or numeric id."""
    if needle.isdigit():
        return int(needle)
    rows = conn.execute("SELECT player_id, first_name, last_name FROM players").fetchall()
    needle_l = needle.strip().lower()
    for r in rows:
        full = f"{r['first_name']} {r['last_name']}".lower()
        if needle_l in (full, r["last_name"].lower()):
            return r["player_id"]
    return None


def _fmt3(x: float) -> str:
    """Format a rate stat like .317 (baseball drops the leading zero)."""
    s = f"{x:.3f}"
    return s[1:] if s.startswith("0.") else s


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_init(args) -> int:
    seed.build(args.db, verbose=True)
    return 0


def cmd_standings(args) -> int:
    conn = db.connect(args.db)
    table = analysis.team_standings(conn, args.season)
    print(f"\n{SEASON if args.season == SEASON else args.season} Standings")
    print(f"{'Team':<26} {'W':>3} {'L':>3} {'PCT':>5} {'RS':>4} {'RA':>4} "
          f"{'DIFF':>5} {'PYTH':>5}")
    print("-" * 68)
    for t in table:
        print(f"{t['name']:<26} {t['w']:>3} {t['l']:>3} {_fmt3(t['pct']):>5} "
              f"{t['rs']:>4} {t['ra']:>4} {t['run_diff']:>+5} "
              f"{_fmt3(t['pyth_pct']):>5}")
    conn.close()
    return 0


def cmd_bat_leaders(args) -> int:
    conn = db.connect(args.db)
    rows = analysis.batting_leaderboard(conn, args.season, stat=args.stat,
                                        limit=args.limit)
    print(f"\nBatting leaders — {args.stat.upper()}")
    print(f"{'#':>2} {'Player':<18} {'G':>3} {'PA':>4} {'AVG':>5} {'OBP':>5} "
          f"{'SLG':>5} {'OPS':>5} {'HR':>3} {'wOBA':>5}")
    print("-" * 66)
    for i, r in enumerate(rows, 1):
        print(f"{i:>2} {r['name']:<18} {r['g']:>3} {r['pa']:>4} "
              f"{_fmt3(r['avg']):>5} {_fmt3(r['obp']):>5} {_fmt3(r['slg']):>5} "
              f"{_fmt3(r['ops']):>5} {r['hr']:>3} {_fmt3(r['woba']):>5}")
    conn.close()
    return 0


def cmd_pitch_leaders(args) -> int:
    conn = db.connect(args.db)
    rows = analysis.pitching_leaderboard(conn, args.season, stat=args.stat,
                                         limit=args.limit)
    print(f"\nPitching leaders — {args.stat.upper()}")
    print(f"{'#':>2} {'Player':<18} {'IP':>5} {'ERA':>5} {'WHIP':>5} "
          f"{'K/9':>5} {'BB/9':>5} {'FIP':>5} {'W':>2} {'L':>2}")
    print("-" * 64)
    for i, r in enumerate(rows, 1):
        print(f"{i:>2} {r['name']:<18} {r['ip']:>5.1f} {r['era']:>5.2f} "
              f"{r['whip']:>5.2f} {r['k9']:>5.2f} {r['bb9']:>5.2f} "
              f"{r['fip']:>5.2f} {r['w']:>2} {r['l']:>2}")
    conn.close()
    return 0


def cmd_player(args) -> int:
    conn = db.connect(args.db)
    pid = _resolve_player(conn, args.name)
    if pid is None:
        print(f"No player matching {args.name!r}", file=sys.stderr)
        return 1

    bat = analysis.player_batting(conn, pid, args.season)
    pit = analysis.player_pitching(conn, pid, args.season)
    name = (bat or pit).get("name", args.name) if (bat or pit) else args.name

    print(f"\n{name} — {args.season}")
    if bat:
        print("  Batting")
        print(f"    G {bat['g']}  AB {bat['ab']}  H {bat['h']}  HR {bat['hr']}  "
              f"RBI {bat['rbi']}  BB {bat['bb']}  SO {bat['so']}  SB {bat['sb']}")
        print(f"    AVG {_fmt3(bat['avg'])}  OBP {_fmt3(bat['obp'])}  "
              f"SLG {_fmt3(bat['slg'])}  OPS {_fmt3(bat['ops'])}  "
              f"ISO {_fmt3(bat['iso'])}")
        print(f"    wOBA {_fmt3(bat['woba'])}  wRAA {bat['wraa']:+.1f}  "
              f"OPS+ {bat['ops_plus']:.0f}  BABIP {_fmt3(bat['babip'])}")
    if pit:
        print("  Pitching")
        print(f"    G {pit['g']}  GS {pit['gs']}  IP {pit['ip']:.1f}  "
              f"W {pit['w']}  L {pit['l']}  SO {pit['so']}  BB {pit['bb']}")
        print(f"    ERA {pit['era']:.2f}  WHIP {pit['whip']:.2f}  "
              f"K/9 {pit['k9']:.2f}  BB/9 {pit['bb9']:.2f}  FIP {pit['fip']:.2f}")
    if not bat and not pit:
        print(f"  No {args.season} stats on record.")
    conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="baseball", description="Baseball analysis database CLI")
    parser.add_argument("--db", default=str(db.DEFAULT_DB_PATH),
                        help="path to the SQLite database file")
    parser.add_argument("--season", type=int, default=SEASON,
                        help="season year to analyze")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create and seed the database").set_defaults(
        func=cmd_init)

    p = sub.add_parser("standings", help="team standings")
    p.set_defaults(func=cmd_standings)

    p = sub.add_parser("bat-leaders", help="batting leaderboard")
    p.add_argument("--stat", default="ops",
                   help="stat to rank by (avg, obp, slg, ops, hr, woba, iso...)")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_bat_leaders)

    p = sub.add_parser("pitch-leaders", help="pitching leaderboard")
    p.add_argument("--stat", default="era",
                   help="stat to rank by (era, whip, k9, fip, so, w...)")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_pitch_leaders)

    p = sub.add_parser("player", help="single player stat card")
    p.add_argument("name", help="player name, last name, or id")
    p.set_defaults(func=cmd_player)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
