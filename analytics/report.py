"""Projection report generator — the capstone.

    pull CSVs  →  within-season index  →  project to target season  →  WAR
             →  ranked leaderboards + team value totals (CSV + Markdown)

This is the artifact a GM or scout actually reads: "here are 2026's players
ranked by *projected* value, not last year's stats." Run it right after the
pull and you get real projected-WAR boards from raw MLB data; swap the index
columns for your HVI/PVI/DVI when they're ready.

    python -m analytics.report --data data --season 2026 --out data/reports

Standard library only. Fully testable offline.
"""

from __future__ import annotations

import argparse
import csv
import glob
from collections import defaultdict
from pathlib import Path

from .indexing import woba_of, fip_of, to_index, ip_to_outs
from .player import Player, SeasonLine
from .projection import project_player
from .valuation import hitter_war, pitcher_war

HIT_MIN_PA = 100      # min PA in a season to define the index reference
PIT_MIN_OUTS = 60     # 20 IP


def _read(paths):
    rows = []
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def _int(v, d=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


# ---- build indexed player histories ------------------------------------- #

def build_hitters(rows) -> dict[str, Player]:
    by_season = defaultdict(list)
    for r in rows:
        by_season[_int(r.get("season"))].append(r)

    players: dict[str, Player] = {}
    for season, srows in by_season.items():
        raw = {}
        qualified = set()
        for r in srows:
            pid = r.get("player_id")
            w = woba_of(r)
            if w is None or not pid:
                continue
            raw[pid] = w
            if _f(r.get("plateAppearances")) >= HIT_MIN_PA:
                qualified.add(pid)
        idx = to_index(raw, min_for_moments=qualified)
        rmap = {r.get("player_id"): r for r in srows}
        for pid, hvi in idx.items():
            r = rmap[pid]
            pl = players.setdefault(pid, Player(
                name=r.get("name", pid), primary_pos=r.get("position"),
                is_pitcher=False))
            pl.history.append(SeasonLine(
                season=season, age=_f(r.get("age")), position=r.get("position"),
                pa=_f(r.get("plateAppearances")), hvi=hvi))
    return players


def build_pitchers(rows) -> dict[str, Player]:
    by_season = defaultdict(list)
    for r in rows:
        by_season[_int(r.get("season"))].append(r)

    players: dict[str, Player] = {}
    for season, srows in by_season.items():
        raw = {}
        qualified = set()
        for r in srows:
            pid = r.get("player_id")
            fip = fip_of(r)
            if fip is None or not pid:
                continue
            raw[pid] = fip
            if ip_to_outs(r.get("inningsPitched")) >= PIT_MIN_OUTS:
                qualified.add(pid)
        idx = to_index(raw, invert=True, min_for_moments=qualified)  # low FIP → high index
        rmap = {r.get("player_id"): r for r in srows}
        for pid, pvi in idx.items():
            r = rmap[pid]
            pl = players.setdefault(pid, Player(
                name=r.get("name", pid), primary_pos="SP", is_pitcher=True))
            pl.history.append(SeasonLine(
                season=season, age=_f(r.get("age")),
                ip=ip_to_outs(r.get("inningsPitched")) / 3.0,
                pvi=pvi, role=r.get("role", "SP")))
    return players


# ---- project + value ---------------------------------------------------- #

def project_hitters(players, season, min_history_pa=200):
    out = []
    for pl in players.values():
        prior_pa = sum(s.pa for s in pl.history if s.season < season)
        if prior_pa < min_history_pa and not any(s.season < season for s in pl.history):
            continue
        try:
            hvi = project_player(pl, season, index="hvi")
        except ValueError:
            continue
        pos = pl.primary_pos or "DH"
        war = hitter_war(hvi.value, hvi.sample, pos)
        latest = pl.seasons_desc()[0]
        out.append({
            "name": pl.name, "team_last": latest_team(pl), "pos": pos,
            "proj_age": round(hvi.proj_age, 0), "proj_pa": int(hvi.sample),
            "proj_index": hvi.value, "proj_war": war.war,
        })
    out.sort(key=lambda r: r["proj_war"], reverse=True)
    return out


def project_pitchers(players, season, min_history_ip=40):
    out = []
    for pl in players.values():
        prior_ip = sum(s.ip for s in pl.history if s.season < season)
        if prior_ip < min_history_ip and not any(s.season < season for s in pl.history):
            continue
        try:
            pvi = project_player(pl, season, index="pvi")
        except ValueError:
            continue
        latest = pl.seasons_desc()[0]
        war = pitcher_war(pvi.value, pvi.sample, latest.role)
        out.append({
            "name": pl.name, "team_last": latest_team(pl), "role": latest.role,
            "proj_age": round(pvi.proj_age, 0), "proj_ip": int(pvi.sample),
            "proj_index": pvi.value, "proj_war": war.war,
        })
    out.sort(key=lambda r: r["proj_war"], reverse=True)
    return out


def latest_team(pl):
    for s in pl.seasons_desc():
        if getattr(s, "team", None):
            return s.team
    return ""


# ---- output ------------------------------------------------------------- #

def write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def markdown(hitters, pitchers, season, top=25):
    lines = [f"# {season} Projections — JCBaseballLab\n",
             "_Provisional index from wOBA/FIP (z-scored within season). "
             "Swap in HVI/PVI/DVI to finalize._\n",
             f"\n## Top {top} hitters by projected WAR\n",
             "| # | Player | Pos | Age | PA | Index | proj WAR |",
             "|--:|--------|-----|--:|--:|--:|--:|"]
    for i, r in enumerate(hitters[:top], 1):
        lines.append(f"| {i} | {r['name']} | {r['pos']} | {r['proj_age']:.0f} "
                     f"| {r['proj_pa']} | {r['proj_index']} | {r['proj_war']} |")
    lines += [f"\n## Top {top} pitchers by projected WAR\n",
              "| # | Player | Role | Age | IP | Index | proj WAR |",
              "|--:|--------|------|--:|--:|--:|--:|"]
    for i, r in enumerate(pitchers[:top], 1):
        lines.append(f"| {i} | {r['name']} | {r['role']} | {r['proj_age']:.0f} "
                     f"| {r['proj_ip']} | {r['proj_index']} | {r['proj_war']} |")
    return "\n".join(lines) + "\n"


def generate(data_dir="data", season=2026, out_dir="data/reports"):
    hit_rows = _read(sorted(glob.glob(f"{data_dir}/*/hitting.csv")))
    pit_rows = _read(sorted(glob.glob(f"{data_dir}/*/pitching.csv")))
    if not hit_rows and not pit_rows:
        raise SystemExit(f"no CSVs under {data_dir}/*/ — run analytics.mlbpull first")

    hitters = project_hitters(build_hitters(hit_rows), season)
    pitchers = project_pitchers(build_pitchers(pit_rows), season)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(hitters, out / f"{season}_hitters_proj.csv")
    write_csv(pitchers, out / f"{season}_pitchers_proj.csv")
    (out / f"{season}_projections.md").write_text(markdown(hitters, pitchers, season))
    return hitters, pitchers, out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate projection report from pulled CSVs.")
    ap.add_argument("--data", default="data", help="dir containing <season>/hitting.csv etc.")
    ap.add_argument("--season", type=int, default=2026, help="season to project")
    ap.add_argument("--out", default="data/reports", help="output dir")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args(argv)

    hitters, pitchers, out = generate(args.data, args.season, args.out)
    print(f"Projected {len(hitters)} hitters, {len(pitchers)} pitchers → {out}/\n")
    print(f"Top {args.top} hitters by projected WAR:")
    for i, r in enumerate(hitters[:args.top], 1):
        print(f"  {i:>2} {r['name']:<24} {r['pos']:<3} age {r['proj_age']:.0f}  "
              f"idx {r['proj_index']:>5}  {r['proj_war']:>4} WAR")
    print(f"\nTop {args.top} pitchers by projected WAR:")
    for i, r in enumerate(pitchers[:args.top], 1):
        print(f"  {i:>2} {r['name']:<24} {r['role']:<3} age {r['proj_age']:.0f}  "
              f"idx {r['proj_index']:>5}  {r['proj_war']:>4} WAR")


if __name__ == "__main__":
    main()
