"""Backtest harness — does the projection actually beat naive baselines?

A leaderboard nobody has validated is a guess with good typography. This harness
answers the question a front office will ask before trusting a number: *out of
sample, does your projection predict next season better than just using last
year's stat?*

For each player-season it can "predict" (has prior history), it compares the
projection against two honest baselines:

  - naive-last : just use the most recent prior season (surprisingly tough)
  - league-mean: everyone reverts fully to average

and reports RMSE, MAE, correlation, and a **skill score** vs. naive-last
(``1 - RMSE_proj / RMSE_naive``; positive = the model adds value).

It's index-agnostic: run it on OPS from the raw MLB pull today, or on your HVI /
PVI / DVI once those are wired in — same code.

    python -m analytics.backtest --csv "data/*/hitting.csv" \
        --value ops --sample plateAppearances --scale 1000
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
from collections import defaultdict
from dataclasses import dataclass

from .aging import DEFAULT_AGING
from .projection import ProjInput, project_index


@dataclass
class Record:
    player_id: str
    season: int
    age: float
    value: float
    sample: float


# ---- metrics ------------------------------------------------------------- #

def rmse(pairs):
    return math.sqrt(sum((a - p) ** 2 for a, p in pairs) / len(pairs)) if pairs else float("nan")

def mae(pairs):
    return sum(abs(a - p) for a, p in pairs) / len(pairs) if pairs else float("nan")

def corr(pairs):
    n = len(pairs)
    if n < 2:
        return float("nan")
    ax = sum(a for a, _ in pairs) / n
    px = sum(p for _, p in pairs) / n
    sa = sum((a - ax) ** 2 for a, _ in pairs)
    sp = sum((p - px) ** 2 for _, p in pairs)
    if sa == 0 or sp == 0:
        return float("nan")
    cov = sum((a - ax) * (p - px) for a, p in pairs)
    return cov / math.sqrt(sa * sp)


# ---- core ---------------------------------------------------------------- #

def run_backtest(
    records: list[Record],
    *,
    min_prior: int = 1,
    min_sample: float = 200.0,
    league_avg: float | None = None,
    regression_sample: float = 200.0,
    weights=(5, 4, 3),
    aging_curve=DEFAULT_AGING,
) -> dict:
    """Walk-forward backtest. Returns a report dict of per-method metrics.

    ``league_avg`` anchors regression; if None it's the sample-weighted mean of
    ``value`` per target season (so the harness works on any stat scale).
    """
    by_player: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        by_player[r.player_id].append(r)

    # Per-season league mean (sample-weighted) when not supplied.
    season_vals: dict[int, list[Record]] = defaultdict(list)
    for r in records:
        season_vals[r.season].append(r)
    season_mean = {}
    for yr, rs in season_vals.items():
        wsum = sum(r.sample for r in rs)
        season_mean[yr] = (sum(r.value * r.sample for r in rs) / wsum) if wsum else 0.0

    methods = {"projection": [], "naive_last": [], "league_mean": []}
    for pid, seasons in by_player.items():
        seasons.sort(key=lambda s: s.season)
        for i, tgt in enumerate(seasons):
            prior = seasons[:i]
            if len(prior) < min_prior or tgt.sample < min_sample:
                continue
            la = league_avg if league_avg is not None else season_mean.get(tgt.season, 0.0)
            proj = project_index(
                [ProjInput(s.value, s.sample, s.age) for s in prior],
                tgt.age, weights=weights, regression_sample=regression_sample,
                aging_curve=aging_curve, league_avg=la,
            )
            methods["projection"].append((tgt.value, proj.value))
            methods["naive_last"].append((tgt.value, prior[-1].value))
            methods["league_mean"].append((tgt.value, la))

    report = {"n": len(methods["projection"]), "methods": {}}
    for name, pairs in methods.items():
        report["methods"][name] = {
            "rmse": round(rmse(pairs), 4),
            "mae": round(mae(pairs), 4),
            "corr": round(corr(pairs), 4),
        }
    base = report["methods"]["naive_last"]["rmse"]
    proj = report["methods"]["projection"]["rmse"]
    report["skill_vs_naive"] = round(1 - proj / base, 4) if base else float("nan")
    return report


def print_report(report: dict) -> None:
    print(f"\nBacktest — {report['n']} player-seasons predicted\n")
    print(f"{'method':<14}{'RMSE':>10}{'MAE':>10}{'corr':>10}")
    print("-" * 44)
    for name, m in report["methods"].items():
        print(f"{name:<14}{m['rmse']:>10}{m['mae']:>10}{m['corr']:>10}")
    skill = report["skill_vs_naive"]
    verdict = ("projection beats naive-last ✅" if skill > 0
               else "projection does NOT beat naive-last ❌")
    print(f"\nSkill vs naive-last: {skill:+.1%}  →  {verdict}")


# ---- CSV loading + CLI --------------------------------------------------- #

def load_records(paths, value_col, sample_col, age_col="age",
                 id_col="player_id", season_col="season", scale=1.0) -> list[Record]:
    """Load Records from pulled CSVs. ``scale`` multiplies value (e.g. OPS×1000
    to put it on a friendlier integer scale — doesn't change the skill score)."""
    out = []
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    val, samp = row.get(value_col), row.get(sample_col)
                    age = row.get(age_col)
                    if not val or not samp or not age:
                        continue
                    out.append(Record(
                        player_id=row[id_col], season=int(row[season_col]),
                        age=float(age), value=float(val) * scale,
                        sample=float(samp)))
                except (ValueError, KeyError):
                    continue
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Backtest projections against baselines.")
    ap.add_argument("--csv", required=True, help="glob of season CSVs, e.g. 'data/*/hitting.csv'")
    ap.add_argument("--value", default="ops", help="value column to project")
    ap.add_argument("--sample", default="plateAppearances", help="workload column")
    ap.add_argument("--scale", type=float, default=1000.0, help="multiply value (readability)")
    ap.add_argument("--min-sample", type=float, default=200.0)
    ap.add_argument("--min-prior", type=int, default=1)
    args = ap.parse_args(argv)

    paths = sorted(glob.glob(args.csv))
    if not paths:
        raise SystemExit(f"no CSVs matched {args.csv!r} — run analytics.mlbpull first")
    records = load_records(paths, args.value, args.sample, scale=args.scale)
    print(f"Loaded {len(records)} player-seasons from {len(paths)} files.")
    report = run_backtest(records, min_prior=args.min_prior, min_sample=args.min_sample)
    print_report(report)


if __name__ == "__main__":
    main()
