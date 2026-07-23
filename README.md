# JC Baseball Lab

Two complementary pieces:

1. **[`site/`](site/) — the front-office analytics web app.** A static site that
   pulls **live 2026 MLB data** from the public MLB Stats API and shows
   standings, advanced batting/pitching leaderboards, and searchable player
   cards (wOBA, FIP, ISO, K/BB, Pythagorean win%, …). This is the deployable
   asset — see [`site/README.md`](site/README.md).
2. **`baseball/` — the offline analysis engine.** A dependency-free Python
   toolkit that stores box-score data in SQLite and computes the same
   sabermetric suite. Useful for loading your own datasets and running analysis
   without a browser. Documented below.

The two share identical stat formulas, so the web leaderboards and the Python
engine agree to the last decimal.

3. **[`analytics/`](analytics/) — the evaluation engine (projection → valuation
   → team-building).** The forward-looking layer that turns the descriptive
   PVI/HVI/DVI composites into decisions: it projects next season, converts a
   projection to WAR / dollars / contract surplus, and ranks roster needs and
   acquisition targets. Standard-library only, 37 tests, fully documented in
   [`analytics/METHODOLOGY.md`](analytics/METHODOLOGY.md). Run the end-to-end
   demo:

   ```bash
   python -m analytics.demo
   ```

   Feed it your own data, calibrate the documented constants, and the model
   stays entirely yours.

   **Getting data in:** [`analytics/mlbpull.py`](analytics/mlbpull.py) pulls a
   full season (hitters, pitchers, standings) from the free MLB Stats API to
   CSV, and [`analytics/backtest.py`](analytics/backtest.py) validates the
   projections out-of-sample against naive baselines. See
   [`data/README.md`](data/README.md).

   ```bash
   python -m analytics.mlbpull --seasons 2019-2026 --out data   # run where you have internet
   python -m analytics.backtest --csv "data/*/hitting.csv" --value ops --sample plateAppearances
   ```

   **The payoff:** [`analytics/report.py`](analytics/report.py) turns the pulled
   CSVs into ranked **projected-WAR** leaderboards (hitters + pitchers) for a
   target season, as CSV and Markdown — the artifact a GM or scout reads. It
   derives a provisional index from wOBA/FIP (z-scored within season) so you get
   real projected-WAR boards immediately; point it at your HVI/PVI/DVI columns to
   finalize.

   ```bash
   python -m analytics.report --data data --season 2026 --out data/reports
   ```

---

## `baseball/` — Baseball Analysis Database (Python)

A small, dependency-free toolkit for storing baseball box-score data in SQLite
and computing sabermetric statistics on top of it. It ships with a deterministic
sample season so every command works the moment you clone the repo — no data
feed, no API keys, no third-party packages (runtime uses only the Python
standard library).

## What's inside

| Area | Description |
|------|-------------|
| **Schema** (`baseball/schema.sql`) | Normalized tables for teams, players, games, and per-game batting/pitching lines, plus season-total views. |
| **Sabermetrics** (`baseball/sabermetrics.py`) | Pure functions for AVG, OBP, SLG, OPS, ISO, BABIP, wOBA, wRAA, OPS+, ERA, WHIP, K/9, BB/9, K/BB, and FIP. |
| **Analysis** (`baseball/analysis.py`) | Leaderboards, player stat cards, and team standings with Pythagorean expected win %. |
| **Seed** (`baseball/seed.py`) | Generates a reproducible fictional season (4 teams, 20 players, 72 games). |
| **CLI** (`baseball/cli.py`) | `init`, `standings`, `bat-leaders`, `pitch-leaders`, `player`. |
| **Tests** (`tests/`) | 20 unit + integration tests. |

## Quick start

```bash
# 1. Build and seed the database (writes data/baseball.db)
python -m baseball.cli init

# 2. Look at the standings
python -m baseball.cli standings

# 3. Batting leaderboards — rank by any stat
python -m baseball.cli bat-leaders --stat ops
python -m baseball.cli bat-leaders --stat hr --limit 5

# 4. Pitching leaderboards (ERA/WHIP/FIP sort ascending automatically)
python -m baseball.cli pitch-leaders --stat era
python -m baseball.cli pitch-leaders --stat k9

# 5. A single player's stat card
python -m baseball.cli player "Marco Reyes"
```

Example output:

```
2024 Standings
Team                         W   L   PCT   RS   RA  DIFF  PYTH
--------------------------------------------------------------------
Oakland Athletics           21  15  .583   41   38    +3  .535
Chicago Windies             19  17  .528   42   34    +8  .595
...
```

## Data model

```
teams ──< players
  │           │
  │           └──< batting_lines >── games
  └──< games        pitching_lines >──┘
```

Everything is stored as **raw per-game box-score lines**. Season totals are
never duplicated — they come from the `batting_totals` and `pitching_totals`
SQL views, so the database has a single source of truth. Innings pitched are
stored as whole `outs` to avoid the classic `6.1/6.2` fractional-inning bug.

## Loading your own data

The database is plain SQLite, so you can load real data any way you like:

```python
from baseball import db, analysis

conn = db.connect("data/baseball.db")
db.init_schema(conn)

conn.execute("INSERT INTO teams VALUES (10, 'LAD', 'Los Angeles Dodgers', 'NL', 'West')")
# ... insert players, games, batting_lines, pitching_lines ...
conn.commit()

# Then analyze:
for row in analysis.batting_leaderboard(conn, season=2024, stat="woba"):
    print(row["name"], round(row["woba"], 3))
```

To rebuild the sample database from scratch at any time:

```bash
python -m baseball.cli init      # or: python -m baseball.seed
```

## Sabermetrics reference

The formulas implemented (see `baseball/sabermetrics.py`):

- **AVG** = H / AB
- **OBP** = (H + BB + HBP) / (AB + BB + HBP + SF)
- **SLG** = total bases / AB   ·   **OPS** = OBP + SLG   ·   **ISO** = SLG − AVG
- **BABIP** = (H − HR) / (AB − SO − HR + SF)
- **wOBA** — linear weights; **wRAA** — runs above average; **OPS+** — 100 = league avg
- **ERA** = 9·ER / IP   ·   **WHIP** = (BB + H) / IP
- **K/9**, **BB/9**, **K/BB**
- **FIP** = (13·HR + 3·(BB+HBP) − 2·SO) / IP + constant

Rate stats are league-relative where noted; the weights and league baselines
live at the top of the module and can be tuned per era.

## Development

```bash
pip install -r requirements.txt   # installs pytest
python -m pytest                   # run the 20 tests
```

The sample data generator is seeded with a fixed RNG value, so the same
database — and the same test fingerprints — are produced on every run.
