# Evaluation Engine — Methodology

This is the forward-looking layer for JCBaseballLab. Your PVI/HVI/DVI composites
answer *what happened*. This engine answers the three questions a front office
actually decides on:

1. **Projection** — what will a player do next season?
2. **Valuation** — what is that worth, in wins and dollars?
3. **Team-building** — which moves add the most wins per dollar?

Everything here is transparent, tested, and built on your indices' existing
design (100 = league average, z-scored within season).

---

## 1. Projection (`projection.py`)

A **Marcel-style** baseline: simple, transparent, and famously hard to beat by
much. It's the right yardstick to build against.

```
projected_index = regressed_weighted_mean + aging_shift
```

- **Recency + playing-time weighting.** The last 3 seasons are weighted 5/4/3
  (most recent highest) and by sample size — a 600-PA season carries more signal
  than a 150-PA one.
- **Regression to the mean.** We add `regression_sample` PA (default 200) of
  league-average (index 100) production. Small samples get pulled toward 100
  harder — that's reliability shrinkage, and it's why a 20-PA hot streak doesn't
  project as a star.
- **Aging.** The weighted-mean age of the sample is shifted to the projection
  age along an aging curve.

**Reliability / stabilization.** The `regression_sample` constant *is* the
stabilization knob — larger = more skepticism of small samples. Different inputs
stabilize at different rates (K% fast, BABIP slow); when you calibrate, set it
per index from your data.

## 2. Aging curves (`aging.py`)

Ships with a sensible default (peak 26–28, gentle decline into the early 30s,
steeper after). But the point of owning 2019–2025 is to build **your own** curve:

```python
from analytics.aging import estimate_aging_curve
curve = estimate_aging_curve(pairs)   # pairs = (age1, index1, index2, sample2)
```

This uses the **delta method** — averaging every player's year-over-year change
at each age. Known caveat: **survivorship bias**. Players who fall off get
benched and leave the sample, so raw delta curves *understate* late-career
decline. Handle the tail with care (the same caution your About page gives 2020).

## 3. Valuation (`valuation.py`)

The chain: **index → runs → wins (WAR) → dollars → surplus.**

Because your indices are z-scored, we convert to `z = (index − 100) / SD` and
value talent in **runs per standard deviation**:

```
batting_runs   = z_HVI · RUNS_PER_SD_BAT · (PA / 600)
defense_runs   = z_DVI · RUNS_PER_SD_DEF · (PA / 600)
position_runs  = positional_adjustment · (PA / 600)
replacement    = REPL_RUNS · (PA / 600)
WAR            = (batting + defense + position + replacement) / RUNS_PER_WIN
```

- **Positional adjustments** are the standard FanGraphs scarcity values (C
  +12.5 … DH −17.5 runs/600). This is *scarcity*, distinct from fielding skill —
  which is why a league-average-hitting DH is ~0.2 WAR while the same bat at SS
  is a star. If your DVI already folds in position, set
  `dvi_includes_position=True` to avoid double-counting.
- **Replacement level** sets a league-average regular at ~2 WAR.
- **Dollars.** `WAR × $/win` (default $8M, inflating ~5%/yr). **Surplus value** =
  market value − salary, summed over a contract with the player aged each year.
  Cost-controlled young stars light up here — exactly the inefficiency a smart
  front office exploits.

### ⚠️ Calibrate before you trust the dollar figures

The starred constants (`RUNS_PER_SD_*`, the `*_SD` spreads, `DOLLARS_PER_WIN`)
are league-plausible **placeholders**. The WAR *ordering* is sound out of the
box; the absolute scale needs fitting to your indices' real distributions.
`calibrate_runs_per_sd()` fits the runs-per-SD from players whose WAR you already
trust. Do this once per index and the dollar values become real.

## 4. Team-building (`teambuilder.py`)

- **`project_team`** — roster WAR → wins (`47.7 replacement + Σ WAR`), record,
  and $/marginal-win efficiency.
- **`roster_needs`** — rank slots by gap below a target (your shopping list).
- **`rank_targets`** — rank acquisitions by **surplus**, not by name. The best
  signing is the biggest value-over-cost, not the biggest star.

---

## What makes this an asset (and honest limits)

- **Descriptive → predictive.** This is the gap your own notes named. Projection
  closes it.
- **Validate it.** Before leaning on any metric, check it **out of sample**: does
  projected-2025 predict actual-2025 better than the raw stat? That test — not a
  leaderboard — is what earns a scout's trust. (A backtest harness is the natural
  next module.)
- **Not yet included** (good next steps): wRC+-style park/league adjustments
  inside the indices, minor-league equivalencies (MLEs) so prospects value on the
  same scale, injury/playing-time risk, and a similarity/comps engine.
- **Everything is a knob.** No black boxes. Every constant is documented and
  overridable, so the model stays *yours*.
