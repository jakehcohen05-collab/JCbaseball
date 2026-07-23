"""Turn raw stats into 100-scaled, within-season z-scored indices.

This lets the projection/valuation engine run on raw MLB pulls *today*, before
your own PVI/HVI/DVI are wired in. We derive a provisional value from a solid
public estimator — wOBA for hitters, FIP for pitchers — then z-score it within
each season to the same 100 = average, SD = 15 shape your composites use.

When your real composites are ready, skip this and index on those columns
instead. Same downstream code.
"""

from __future__ import annotations

import math

# wOBA linear weights (shared with the JS engine and baseball/sabermetrics.py).
WOBA_W = {"bb": 0.69, "hbp": 0.722, "1b": 0.888, "2b": 1.271, "3b": 1.616, "hr": 2.101}


def _f(row, key):
    v = row.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def ip_to_outs(ip) -> int:
    """'130.1' (130 ⅓ innings) → 391 outs."""
    if ip in (None, ""):
        return 0
    whole, _, frac = str(ip).partition(".")
    return int(_num(whole)) * 3 + (int(frac[0]) if frac[:1].isdigit() else 0)


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def woba_of(row) -> float | None:
    """wOBA from a hitting CSV row; None if no plate appearances."""
    ab = _f(row, "atBats"); bb = _f(row, "baseOnBalls"); hbp = _f(row, "hitByPitch")
    sf = _f(row, "sacFlies"); h = _f(row, "hits")
    d = _f(row, "doubles"); t = _f(row, "triples"); hr = _f(row, "homeRuns")
    pa = ab + bb + hbp + sf
    if pa <= 0:
        return None
    singles = max(h - d - t - hr, 0)
    w = WOBA_W
    num = (w["bb"] * bb + w["hbp"] * hbp + w["1b"] * singles +
           w["2b"] * d + w["3b"] * t + w["hr"] * hr)
    return num / pa


def fip_of(row, constant: float = 3.10) -> float | None:
    """FIP from a pitching CSV row; None if no innings. Lower is better."""
    outs = ip_to_outs(row.get("inningsPitched"))
    if outs <= 0:
        return None
    ip = outs / 3.0
    hr = _f(row, "homeRuns"); bb = _f(row, "baseOnBalls")
    hbp = _f(row, "hitBatsmen"); so = _f(row, "strikeOuts")
    return (13 * hr + 3 * (bb + hbp) - 2 * so) / ip + constant


def to_index(raw_by_id: dict, *, invert: bool = False,
             mean: float = 100.0, sd: float = 15.0,
             min_for_moments=None) -> dict:
    """Z-score a {id: raw_value} map to a {id: index} map (100 = avg, SD = 15).

    ``invert=True`` flips the sign so that lower-is-better stats (FIP, ERA) map
    to higher-is-better indices. ``min_for_moments`` optionally restricts which
    ids define the mean/SD (e.g. only qualified players), while still indexing
    everyone against that reference.
    """
    ids = list(raw_by_id)
    ref_ids = [i for i in ids if (min_for_moments is None or i in min_for_moments)]
    ref = [raw_by_id[i] for i in ref_ids] or [raw_by_id[i] for i in ids]
    n = len(ref)
    mu = sum(ref) / n
    var = sum((v - mu) ** 2 for v in ref) / n
    sdev = math.sqrt(var) if var > 0 else 1.0
    sign = -1.0 if invert else 1.0
    return {i: round(mean + sd * sign * (raw_by_id[i] - mu) / sdev, 1) for i in ids}
