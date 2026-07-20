"""Sabermetric statistics.

Pure functions that turn raw counting stats into rate stats. Every function
guards against division by zero and returns ``0.0`` for empty inputs so they
are safe to call on partial data. Rates are returned as floats; format them
for display at the call site.
"""

from __future__ import annotations

from dataclasses import dataclass

# League-average weights for the linear weights / wOBA formulas below.
# These approximate a modern run environment; swap them out per season if you
# load real historical data and want era-accurate values.
WOBA_WEIGHTS = {
    "bb": 0.690,
    "hbp": 0.722,
    "single": 0.888,
    "double": 1.271,
    "triple": 1.616,
    "hr": 2.101,
}
WOBA_SCALE = 1.157
LEAGUE_WOBA = 0.320       # league average wOBA the scale is anchored to
LEAGUE_OBP = 0.320
LEAGUE_SLG = 0.400


def _safe_div(numerator: float, denominator: float) -> float:
    """Return ``numerator / denominator`` or 0.0 when the denominator is 0."""
    return numerator / denominator if denominator else 0.0


# ---------------------------------------------------------------------------
# Batting
# ---------------------------------------------------------------------------

def batting_average(h: int, ab: int) -> float:
    """Hits per at-bat (AVG)."""
    return _safe_div(h, ab)


def on_base_percentage(h: int, bb: int, hbp: int, ab: int, sf: int) -> float:
    """On-base percentage (OBP): times on base / plate appearances."""
    return _safe_div(h + bb + hbp, ab + bb + hbp + sf)


def slugging(h: int, doubles: int, triples: int, hr: int, ab: int) -> float:
    """Slugging percentage (SLG): total bases per at-bat."""
    singles = h - doubles - triples - hr
    total_bases = singles + 2 * doubles + 3 * triples + 4 * hr
    return _safe_div(total_bases, ab)


def ops(obp: float, slg: float) -> float:
    """On-base plus slugging (OPS)."""
    return obp + slg


def iso(slg: float, avg: float) -> float:
    """Isolated power (ISO): extra bases per at-bat, SLG minus AVG."""
    return slg - avg


def babip(h: int, hr: int, ab: int, so: int, sf: int) -> float:
    """Batting average on balls in play (BABIP)."""
    return _safe_div(h - hr, ab - so - hr + sf)


def woba(
    bb: int, hbp: int, h: int, doubles: int, triples: int, hr: int,
    ab: int, sf: int,
) -> float:
    """Weighted on-base average (wOBA) using the linear weights above."""
    singles = h - doubles - triples - hr
    w = WOBA_WEIGHTS
    numerator = (
        w["bb"] * bb
        + w["hbp"] * hbp
        + w["single"] * singles
        + w["double"] * doubles
        + w["triple"] * triples
        + w["hr"] * hr
    )
    pa = ab + bb + hbp + sf
    return _safe_div(numerator, pa)


def wraa(woba_value: float, pa: int) -> float:
    """Weighted runs above average (wRAA) — runs vs. a league-average hitter."""
    return ((woba_value - LEAGUE_WOBA) / WOBA_SCALE) * pa


def ops_plus(obp: float, slg: float,
             league_obp: float = LEAGUE_OBP,
             league_slg: float = LEAGUE_SLG) -> float:
    """OPS+ — 100 is league average, park factor omitted."""
    if not league_obp or not league_slg:
        return 0.0
    return 100 * (obp / league_obp + slg / league_slg - 1)


# ---------------------------------------------------------------------------
# Pitching. Innings are stored as whole ``outs`` to avoid the 0.1/0.2 fraction
# trap; convert here.
# ---------------------------------------------------------------------------

def innings_pitched(outs: int) -> float:
    """Convert recorded outs to innings pitched (as a true decimal)."""
    return outs / 3.0


def era(er: int, outs: int) -> float:
    """Earned run average (ERA): earned runs per nine innings."""
    return _safe_div(er * 9.0, innings_pitched(outs)) if outs else 0.0


def whip(bb: int, h: int, outs: int) -> float:
    """Walks and hits per inning pitched (WHIP)."""
    return _safe_div(bb + h, innings_pitched(outs)) if outs else 0.0


def k_per_9(so: int, outs: int) -> float:
    """Strikeouts per nine innings (K/9)."""
    return _safe_div(so * 9.0, innings_pitched(outs)) if outs else 0.0


def bb_per_9(bb: int, outs: int) -> float:
    """Walks per nine innings (BB/9)."""
    return _safe_div(bb * 9.0, innings_pitched(outs)) if outs else 0.0


def k_bb_ratio(so: int, bb: int) -> float:
    """Strikeout-to-walk ratio (K/BB)."""
    return _safe_div(so, bb)


def fip(hr: int, bb: int, hbp: int, so: int, outs: int,
        constant: float = 3.10) -> float:
    """Fielding independent pitching (FIP).

    Isolates outcomes a pitcher controls directly. The constant scales FIP to
    the league ERA; 3.10 is a reasonable modern default.
    """
    ip = innings_pitched(outs)
    if not ip:
        return 0.0
    return (13 * hr + 3 * (bb + hbp) - 2 * so) / ip + constant


# ---------------------------------------------------------------------------
# Bundled rate-stat computation for whole stat lines.
# ---------------------------------------------------------------------------

@dataclass
class BattingRates:
    avg: float
    obp: float
    slg: float
    ops: float
    iso: float
    babip: float
    woba: float
    wraa: float
    ops_plus: float


def batting_rates(row: dict) -> BattingRates:
    """Compute the full batting rate-stat suite from a totals ``dict``.

    ``row`` uses the column names from the ``batting_totals`` view.
    """
    avg = batting_average(row["h"], row["ab"])
    obp = on_base_percentage(row["h"], row["bb"], row["hbp"], row["ab"], row["sf"])
    slg = slugging(row["h"], row["doubles"], row["triples"], row["hr"], row["ab"])
    wv = woba(row["bb"], row["hbp"], row["h"], row["doubles"], row["triples"],
              row["hr"], row["ab"], row["sf"])
    pa = row["ab"] + row["bb"] + row["hbp"] + row["sf"]
    return BattingRates(
        avg=avg,
        obp=obp,
        slg=slg,
        ops=ops(obp, slg),
        iso=iso(slg, avg),
        babip=babip(row["h"], row["hr"], row["ab"], row["so"], row["sf"]),
        woba=wv,
        wraa=wraa(wv, pa),
        ops_plus=ops_plus(obp, slg),
    )


@dataclass
class PitchingRates:
    ip: float
    era: float
    whip: float
    k9: float
    bb9: float
    k_bb: float
    fip: float


def pitching_rates(row: dict) -> PitchingRates:
    """Compute the full pitching rate-stat suite from a totals ``dict``.

    ``row`` uses the column names from the ``pitching_totals`` view.
    """
    return PitchingRates(
        ip=innings_pitched(row["outs"]),
        era=era(row["er"], row["outs"]),
        whip=whip(row["bb"], row["h"], row["outs"]),
        k9=k_per_9(row["so"], row["outs"]),
        bb9=bb_per_9(row["bb"], row["outs"]),
        k_bb=k_bb_ratio(row["so"], row["bb"]),
        fip=fip(row["hr"], row["bb"], 0, row["so"], row["outs"]),
    )
