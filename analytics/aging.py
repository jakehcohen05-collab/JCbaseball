"""Aging curves.

Two pieces:

1. A sensible DEFAULT aging curve, expressed in index points relative to a
   player's peak. It's only a starting point.
2. ``estimate_aging_curve`` — the delta method, so you can derive your OWN aging
   curve from your 2019-2025 dataset and replace the default. That's the whole
   point of owning the data: your curve, from your players, not a borrowed one.

The curve is stored as {age: value}, where ``value`` is the expected index level
at that age relative to peak (peak == 0.0, everything else <= 0). Projecting a
player from a weighted mean age to a target age shifts their number by the
difference of the two curve values.
"""

from __future__ import annotations

from collections import defaultdict

# Default curve: gains through the early 20s, a peak plateau at 26-28, gentle
# decline through the early 30s, steeper after. Values are index points below
# peak. Tune per index — hitters and pitchers age differently.
DEFAULT_AGING = {
    19: -9.0, 20: -7.5, 21: -6.0, 22: -4.5, 23: -3.0, 24: -1.6,
    25: -0.7, 26: -0.1, 27: 0.0, 28: -0.2, 29: -0.8, 30: -1.7,
    31: -2.8, 32: -4.1, 33: -5.6, 34: -7.3, 35: -9.2, 36: -11.3,
    37: -13.6, 38: -16.1, 39: -18.8, 40: -21.7,
}


def aging_value(age: float, curve: dict[int, float] = DEFAULT_AGING) -> float:
    """Curve value at an (interpolated) age, clamped to the curve's range."""
    lo, hi = min(curve), max(curve)
    if age <= lo:
        return curve[lo]
    if age >= hi:
        return curve[hi]
    a0 = int(age)
    a1 = a0 + 1
    if a1 not in curve:
        return curve[a0]
    frac = age - a0
    return curve[a0] * (1 - frac) + curve[a1] * frac


def aging_delta(from_age: float, to_age: float,
                curve: dict[int, float] = DEFAULT_AGING) -> float:
    """Index points to add when moving a player from one age to another."""
    return aging_value(to_age, curve) - aging_value(from_age, curve)


def estimate_aging_curve(pairs, min_sample: float = 200.0,
                         weight_by_sample: bool = True) -> dict[int, float]:
    """Derive an aging curve from your data via the delta method.

    ``pairs`` is an iterable of consecutive same-player season pairs:
        (age_year1, index_year1, index_year2, sample_year2)
    i.e. a player who was ``age_year1`` and posted ``index_year1``, then the
    next season posted ``index_year2`` over ``sample_year2`` PA/IP.

    We average the year-over-year *change* at each age, then integrate those
    deltas into a curve anchored so the peak age = 0.

    Caveat worth remembering: the delta method has survivorship bias — players
    who collapse get benched and drop out, so raw curves understate late-career
    decline. Treat the tail with the same caution your About page already gives
    the 2020 season.
    """
    changes: dict[int, list] = defaultdict(list)
    for age1, idx1, idx2, samp2 in pairs:
        if idx1 is None or idx2 is None or samp2 < min_sample:
            continue
        changes[int(age1)].append((idx2 - idx1, samp2))

    # Average delta per age transition (age -> age+1).
    avg_delta: dict[int, float] = {}
    for age, obs in changes.items():
        if weight_by_sample:
            wsum = sum(w for _, w in obs)
            avg_delta[age] = sum(d * w for d, w in obs) / wsum if wsum else 0.0
        else:
            avg_delta[age] = sum(d for d, _ in obs) / len(obs)

    if not avg_delta:
        return dict(DEFAULT_AGING)

    # Integrate deltas into a cumulative curve, then anchor peak (max) to 0.
    ages = range(min(avg_delta), max(avg_delta) + 2)
    curve: dict[int, float] = {}
    running = 0.0
    curve[min(avg_delta)] = 0.0
    for age in list(ages)[:-1]:
        running += avg_delta.get(age, 0.0)
        curve[age + 1] = running
    peak = max(curve.values())
    return {age: val - peak for age, val in curve.items()}
