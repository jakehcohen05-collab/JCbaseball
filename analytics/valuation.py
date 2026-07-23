"""Valuation: from index → runs → wins (WAR) → dollars → surplus value.

This is the bridge from "how good" to "what's it worth" — the language GMs
actually make decisions in. A projected HVI/PVI/DVI becomes a projected WAR,
WAR becomes a market dollar value, and value-minus-salary becomes surplus, the
single number that says whether a contract, trade, or signing is a win.

The conversion leans on the fact that your indices are z-scored within season:
z = (index - 100) / SD. We value in "runs per standard deviation of talent,"
which is a clean, defensible abstraction — but the SD-to-runs constants below
MUST be calibrated to your indices' real spread. Defaults are league-plausible
placeholders; ``calibrate_runs_per_sd`` helps you set them from your data.
"""

from __future__ import annotations

from dataclasses import dataclass

from .player import POSITION_ADJ

# --- Core constants (all overridable; calibrate the starred ones). ---
RUNS_PER_WIN = 10.0                 # ~standard; ~9.5-10.5 depending on run env

# SD of each index in "index points." Your tiers (Elite 145+, ~+3 SD) imply
# roughly SD ≈ 15. Confirm against your actual distributions.
HVI_SD = 15.0
PVI_SD = 15.0
DVI_SD = 15.0

# ★ Runs of value per +1 SD of talent, at a full workload. CALIBRATE THESE.
RUNS_PER_SD_BAT_600 = 20.0          # +1 SD hitter over 600 PA ≈ +20 batting runs
RUNS_PER_SD_DEF_600 = 10.0          # defense has a smaller spread than offense
RUNS_PER_SD_PITCH_180 = 22.0        # +1 SD pitcher over 180 IP

# Replacement level: how many runs a league-average full-timer sits above a
# freely-available replacement. A league-average regular ≈ 2 WAR.
REPL_RUNS_BAT_600 = 20.0
REPL_RUNS_PITCH_180_SP = 20.0
REPL_RUNS_PITCH_60_RP = 4.0         # relievers clear a lower replacement bar

DOLLARS_PER_WIN = 8.0               # $M per marginal win (free-agent market)


def _z(index: float, sd: float) -> float:
    return (index - 100.0) / sd


@dataclass
class WARBreakdown:
    war: float
    batting_runs: float = 0.0
    defense_runs: float = 0.0
    position_runs: float = 0.0
    replacement_runs: float = 0.0
    pitching_runs: float = 0.0

    def as_dict(self) -> dict:
        return {k: round(v, 1) for k, v in self.__dict__.items()}


def hitter_war(
    hvi: float, pa: float, position: str = "DH",
    dvi: float | None = None,
    *, hvi_sd=HVI_SD, dvi_sd=DVI_SD,
    runs_per_sd_bat=RUNS_PER_SD_BAT_600, runs_per_sd_def=RUNS_PER_SD_DEF_600,
    repl_runs=REPL_RUNS_BAT_600, runs_per_win=RUNS_PER_WIN,
    dvi_includes_position=False,
) -> WARBreakdown:
    """Position-player WAR from HVI (offense) + DVI (defense) + position + repl.

    Set ``dvi_includes_position=True`` if your DVI already folds in the position
    adjustment, to avoid double-counting scarcity.
    """
    scale = pa / 600.0
    batting = _z(hvi, hvi_sd) * runs_per_sd_bat * scale
    defense = _z(dvi, dvi_sd) * runs_per_sd_def * scale if dvi is not None else 0.0
    position = 0.0 if dvi_includes_position else POSITION_ADJ.get(position, 0.0) * scale
    replacement = repl_runs * scale
    war = (batting + defense + position + replacement) / runs_per_win
    return WARBreakdown(
        war=round(war, 1), batting_runs=batting, defense_runs=defense,
        position_runs=position, replacement_runs=replacement,
    )


def pitcher_war(
    pvi: float, ip: float, role: str = "SP",
    *, pvi_sd=PVI_SD, runs_per_sd_pitch=RUNS_PER_SD_PITCH_180,
    runs_per_win=RUNS_PER_WIN,
) -> WARBreakdown:
    """Pitcher WAR from PVI over a projected innings workload."""
    scale = ip / 180.0
    pitching = _z(pvi, pvi_sd) * runs_per_sd_pitch * scale
    if role == "RP":
        replacement = REPL_RUNS_PITCH_60_RP * (ip / 60.0)
    else:
        replacement = REPL_RUNS_PITCH_180_SP * scale
    war = (pitching + replacement) / runs_per_win
    return WARBreakdown(
        war=round(war, 1), pitching_runs=pitching, replacement_runs=replacement,
    )


# --- Dollars & surplus --------------------------------------------------- #

def war_to_dollars(war: float, dollars_per_win: float = DOLLARS_PER_WIN) -> float:
    """Market $ value ($M) of a WAR total."""
    return round(war * dollars_per_win, 1)


@dataclass
class SurplusResult:
    total_war: float
    market_value: float      # $M the production is worth on the open market
    salary: float            # $M actually paid
    surplus: float           # market_value - salary  (positive = good deal)
    by_year: list[dict]


def surplus_value(
    war_by_year: list[float],
    salary_by_year: list[float],
    *,
    dollars_per_win: float = DOLLARS_PER_WIN,
    inflation: float = 0.05,   # $/win grows ~5%/yr
) -> SurplusResult:
    """Surplus value of a contract: projected market value minus salary, summed
    over its years, with $/win inflating and (via projected WAR) aging baked in.

    Feed ``war_by_year`` from year-by-year projections (age the player each
    season) and ``salary_by_year`` from the contract. Team-control years, where
    salary is set by rule below market, light up here as large surplus.
    """
    rows = []
    tot_war = tot_val = tot_sal = 0.0
    for i, war in enumerate(war_by_year):
        dpw = dollars_per_win * ((1 + inflation) ** i)
        val = war * dpw
        sal = salary_by_year[i] if i < len(salary_by_year) else 0.0
        rows.append({
            "year": i + 1, "war": round(war, 1),
            "dollars_per_win": round(dpw, 2),
            "market_value": round(val, 1), "salary": round(sal, 1),
            "surplus": round(val - sal, 1),
        })
        tot_war += war; tot_val += val; tot_sal += sal
    return SurplusResult(
        total_war=round(tot_war, 1), market_value=round(tot_val, 1),
        salary=round(tot_sal, 1), surplus=round(tot_val - tot_sal, 1),
        by_year=rows,
    )


def calibrate_runs_per_sd(known_pairs) -> float:
    """Fit RUNS_PER_SD from players whose WAR you already trust.

    ``known_pairs`` = iterable of (z_score, workload_fraction, known_runs_above
    _replacement_minus_replacement...) — practically: (z, scale, runs_above_avg)
    where runs_above_avg is that player's non-replacement runs at that workload.
    Returns the runs-per-SD that best maps your z-scores onto those runs (simple
    least-squares through the origin).
    """
    sxy = sxx = 0.0
    for z, scale, runs in known_pairs:
        x = z * scale
        sxy += x * runs
        sxx += x * x
    return round(sxy / sxx, 2) if sxx else 0.0
