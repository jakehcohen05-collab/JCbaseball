"""Data model for the evaluation engine.

The engine is built to consume JCBaseballLab's own composite scores — PVI, HVI,
DVI — which are already calibrated to 100 = league average and z-scored within
each season. Because they're z-scored, we can convert any of them to a standard
normal z (``(index - 100) / sd``) and reason about value in a principled way.

Nothing here needs live data: you populate ``SeasonLine`` rows from your build
pipeline, and the projection / valuation layers take it from there.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# FanGraphs-style positional adjustments, runs per 600 PA (full season).
# These reflect position *scarcity*, which is distinct from fielding skill.
POSITION_ADJ = {
    "C": 12.5, "SS": 7.5, "2B": 2.5, "3B": 2.5, "CF": 2.5,
    "LF": -7.5, "RF": -7.5, "1B": -12.5, "DH": -17.5,
    "OF": -2.5,  # generic corner/utility outfield fallback
}

HITTER_POSITIONS = set(POSITION_ADJ) - {"DH"} | {"DH"}


@dataclass
class SeasonLine:
    """One player-season of composite scores plus workload.

    Populate whichever indices apply: HVI/DVI for hitters, PVI for pitchers.
    ``pa`` drives hitter workload/reliability; ``ip`` drives pitcher workload.
    """
    season: int
    age: float
    position: str | None = None
    pa: float = 0.0
    ip: float = 0.0
    hvi: float | None = None   # Hitter Value Index (100 = avg)
    pvi: float | None = None   # Pitcher Value Index (100 = avg)
    dvi: float | None = None   # Defensive Value Index (100 = avg)
    role: str = "SP"           # 'SP' or 'RP' for pitchers


@dataclass
class Contract:
    """A player's contract: salary (in $M) for each upcoming season."""
    salaries: list[float] = field(default_factory=list)   # $M per year, in order
    team_control: bool = False   # pre-arb / arb years (below-market by rule)


@dataclass
class Player:
    """A player: identity, position, season history, and (optional) contract."""
    name: str
    primary_pos: str | None = None
    is_pitcher: bool = False
    history: list[SeasonLine] = field(default_factory=list)
    contract: Contract | None = None

    def seasons_desc(self) -> list[SeasonLine]:
        """History sorted most-recent first."""
        return sorted(self.history, key=lambda s: s.season, reverse=True)

    def latest_age(self) -> float | None:
        s = self.seasons_desc()
        return s[0].age if s else None
