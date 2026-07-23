# Data

CSVs pulled from the MLB Stats API live here, one folder per season:

```
data/
  2026/
    hitting.csv       # every hitter: PA, AB, H, 2B, 3B, HR, BB, HBP, SF, SO, AVG/OBP/SLG/OPS, …
    pitching.csv      # every pitcher: IP, BF, H, ER, BB, HBP, SO, HR, ERA, WHIP, K/9, BB/9, role
    standings.csv     # W-L, run diff, ranks by division
  2025/ …
```

## Pull the data (run where you have internet)

The pull can't run inside the locked-down build sandbox — the MLB API host has
to be reachable. Run it locally or on your build box:

```bash
# the current season, everything
python -m analytics.mlbpull --season 2026 --out data

# a range, for the backtest (2019 through 2026)
python -m analytics.mlbpull --seasons 2019-2026 --out data
```

No API key, no login — it's the free public MLB Stats API. Standard library
only, so no `pip install` needed.

## Validate the projections

Once a few seasons are pulled:

```bash
python -m analytics.backtest --csv "data/*/hitting.csv" \
    --value ops --sample plateAppearances --scale 1000
```

That reports whether the projection beats naive baselines out of sample — swap
`--value ops` for your own HVI/PVI/DVI columns once those are in the CSVs.

## Note on committing data

Raw pulls can be large and change daily. `data/*.csv` and `data/*/` are
gitignored by default — treat the CSVs as a rebuildable cache, not source. If
you *want* a season snapshot in git (e.g. a frozen final 2025), add it
explicitly with `git add -f data/2025/`.
