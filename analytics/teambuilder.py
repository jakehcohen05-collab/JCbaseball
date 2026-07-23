"""Team construction.

The payoff layer: given a roster of projected WARs, what record does that
project to, where are the holes, and which available players add the most value
per dollar? This is where projection + valuation become "build a winning team."
"""

from __future__ import annotations

from dataclasses import dataclass

from .valuation import DOLLARS_PER_WIN, war_to_dollars

# A replacement-level team wins about 47-48 games over 162. Marginal wins stack
# on top of that via total roster WAR.
REPLACEMENT_WINS = 47.7


@dataclass
class TeamProjection:
    total_war: float
    projected_wins: float
    projected_losses: float
    payroll: float
    dollars_per_marginal_win: float


def project_team(war_values: list[float], payroll: float = 0.0,
                 *, replacement_wins: float = REPLACEMENT_WINS) -> TeamProjection:
    """Roster WAR → projected win total (and payroll efficiency)."""
    total = sum(war_values)
    wins = replacement_wins + total
    marginal = payroll / total if total > 0 else 0.0
    return TeamProjection(
        total_war=round(total, 1),
        projected_wins=round(wins, 1),
        projected_losses=round(162 - wins, 1),
        payroll=round(payroll, 1),
        dollars_per_marginal_win=round(marginal, 2),
    )


def roster_needs(war_by_position: dict[str, float],
                 replacement: dict[str, float] | None = None) -> list[dict]:
    """Rank positions by how far below a target they project.

    ``war_by_position`` maps a slot (e.g. 'SS', 'CF', 'SP1') to its projected
    WAR. ``replacement`` optionally sets a per-slot target (default: 2.0 WAR, a
    league-average regular). Returns slots sorted worst-first — your shopping
    list.
    """
    needs = []
    for slot, war in war_by_position.items():
        target = (replacement or {}).get(slot, 2.0)
        needs.append({
            "slot": slot, "projected_war": round(war, 1),
            "target_war": target, "gap": round(target - war, 1),
        })
    needs.sort(key=lambda r: r["gap"], reverse=True)
    return needs


@dataclass
class Target:
    name: str
    war: float
    salary: float
    market_value: float
    surplus: float


def rank_targets(candidates, *, dollars_per_win: float = DOLLARS_PER_WIN) -> list[Target]:
    """Rank acquisition targets by surplus value (market value − asking salary).

    ``candidates`` = iterable of (name, projected_war, salary_$M). The best
    signings aren't the biggest names — they're the biggest surplus.
    """
    out = []
    for name, war, salary in candidates:
        mv = war_to_dollars(war, dollars_per_win)
        out.append(Target(name=name, war=round(war, 1), salary=round(salary, 1),
                          market_value=mv, surplus=round(mv - salary, 1)))
    out.sort(key=lambda t: t.surplus, reverse=True)
    return out
