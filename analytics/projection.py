"""Projection engine.

Turns a player's *descriptive* index history (PVI/HVI/DVI) into a *predictive*
projection for a target season. This is the piece your own notes flagged as
missing: "they measure what happened, not what will happen." Now they can.

Method (a Marcel-style baseline — deliberately transparent, hard to beat, and a
fair yardstick for anything fancier you build later):

  1. Weight recent seasons more (default 5/4/3 for the last three years) and by
     playing time — a 600-PA season says more than a 150-PA one.
  2. Regress toward league average (index 100) by adding a chunk of
     league-average PA/IP. Small samples get pulled harder toward the mean.
  3. Age-adjust from the weighted mean age of the sample to the target age using
     the aging curve (default or your data-derived one).

Everything is a documented knob, and the whole thing is unit-tested so you can
trust the arithmetic while you refine the constants against your data.
"""

from __future__ import annotations

from dataclasses import dataclass

from .aging import DEFAULT_AGING, aging_delta

LEAGUE_AVG = 100.0


@dataclass
class ProjInput:
    """One historical season for projection: the index value, workload, age."""
    value: float
    sample: float   # PA (hitters/defense) or IP (pitchers)
    age: float


@dataclass
class Projection:
    value: float          # projected index (100 = league avg)
    sample: float         # projected workload (PA or IP)
    proj_age: float
    components: dict       # transparency: intermediate numbers


def project_index(
    history: list[ProjInput],
    proj_age: float,
    *,
    weights: tuple[float, ...] = (5, 4, 3),
    regression_sample: float = 200.0,
    base_playing_time: float = 200.0,
    aging_curve: dict[int, float] = DEFAULT_AGING,
    league_avg: float = LEAGUE_AVG,
) -> Projection:
    """Project one index (HVI, PVI, or DVI) forward to ``proj_age``.

    ``history`` may hold any number of seasons; only the most recent
    ``len(weights)`` are used, most-recent weighted highest.
    """
    seasons = sorted(history, key=lambda s: s.age, reverse=True)[: len(weights)]

    # --- 1 + 2: playing-time-weighted, recency-weighted mean, regressed. ---
    num = league_avg * regression_sample     # regression prior
    den = regression_sample
    age_num = 0.0
    age_den = 0.0
    for w, s in zip(weights, seasons):
        pt_weight = w * s.sample
        num += pt_weight * s.value
        den += pt_weight
        age_num += pt_weight * s.age
        age_den += pt_weight

    regressed = num / den if den else league_avg
    weighted_age = age_num / age_den if age_den else proj_age

    # --- 3: age adjustment. ---
    shift = aging_delta(weighted_age, proj_age, aging_curve)
    projected = regressed + shift

    # --- projected workload (Marcel-style playing-time forecast). ---
    recent = seasons[0].sample if len(seasons) >= 1 else 0.0
    second = seasons[1].sample if len(seasons) >= 2 else 0.0
    proj_pt = 0.5 * recent + 0.1 * second + base_playing_time

    return Projection(
        value=round(projected, 1),
        sample=round(proj_pt, 0),
        proj_age=proj_age,
        components={
            "regressed_mean": round(regressed, 2),
            "weighted_age": round(weighted_age, 2),
            "aging_shift": round(shift, 2),
            "seasons_used": len(seasons),
        },
    )


def project_player(player, proj_season: int, *, index: str = "auto", **kw) -> Projection:
    """Convenience wrapper: project a :class:`~analytics.player.Player`.

    ``index`` is 'hvi', 'pvi', 'dvi', or 'auto' (pvi for pitchers else hvi).
    Age for the projection season is inferred from the latest known season.
    """
    seasons = player.seasons_desc()
    if not seasons:
        raise ValueError(f"{player.name} has no history to project from")

    if index == "auto":
        index = "pvi" if player.is_pitcher else "hvi"

    latest = seasons[0]
    proj_age = latest.age + (proj_season - latest.season)

    hist = []
    for s in seasons:
        val = getattr(s, index)
        if val is None:
            continue
        sample = s.ip if index == "pvi" else s.pa
        if sample <= 0:
            continue
        hist.append(ProjInput(value=val, sample=sample, age=s.age))

    if not hist:
        raise ValueError(f"{player.name} has no {index.upper()} history")

    # Pitchers accrue innings, not PA — smaller base playing time default.
    if index == "pvi":
        kw.setdefault("base_playing_time", 40.0)
        kw.setdefault("regression_sample", 60.0)

    return project_index(hist, proj_age, aging_curve=kw.pop("aging_curve", DEFAULT_AGING), **kw)
