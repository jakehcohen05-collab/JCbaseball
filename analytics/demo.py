"""End-to-end demo of the evaluation engine.

Runs the full pipeline on a few illustrative players (fabricated index lines —
NOT real data) so you can see projection → valuation → team-building work
together. Swap in real PVI/HVI/DVI from your build pipeline and the same code
produces real evaluations.

    python -m analytics.demo
"""

from __future__ import annotations

from .player import Player, SeasonLine, Contract
from .projection import project_player
from .valuation import hitter_war, pitcher_war, surplus_value
from .teambuilder import project_team, roster_needs, rank_targets

PROJ_SEASON = 2026


def _hitter(name, pos, lines, contract=None):
    p = Player(name=name, primary_pos=pos, is_pitcher=False, contract=contract)
    p.history = [SeasonLine(season=s, age=a, position=pos, pa=pa, hvi=hvi, dvi=dvi)
                 for s, a, pa, hvi, dvi in lines]
    return p


def _pitcher(name, lines, role="SP", contract=None):
    p = Player(name=name, primary_pos="SP", is_pitcher=True, contract=contract)
    p.history = [SeasonLine(season=s, age=a, ip=ip, pvi=pvi, role=role)
                 for s, a, ip, pvi in lines]
    return p


def bar(label):
    print("\n" + "=" * 72 + f"\n  {label}\n" + "=" * 72)


def main():
    # (season, age, PA, HVI, DVI)
    young_ss = _hitter("Rookie Reyes", "SS", [
        (2023, 22, 210, 104, 103),
        (2024, 23, 540, 118, 108),
        (2025, 24, 610, 126, 110),
    ], Contract(salaries=[0.8, 0.9, 5.0, 9.0], team_control=True))

    vet_1b = _hitter("Vet Hoyt", "1B", [
        (2023, 32, 640, 138, 96),
        (2024, 33, 600, 131, 94),
        (2025, 34, 520, 122, 92),
    ], Contract(salaries=[24.0, 24.0, 24.0]))

    ace = _pitcher("Ace Medina", [
        (2023, 27, 190, 132),
        (2024, 28, 175, 128),
        (2025, 29, 185, 135),
    ], contract=Contract(salaries=[30.0, 30.0, 30.0, 30.0]))

    bar("1 · PROJECTION  (descriptive history → 2026 forecast)")
    for pl, idx in [(young_ss, "hvi"), (vet_1b, "hvi"), (ace, "pvi")]:
        pr = project_player(pl, PROJ_SEASON, index=idx)
        print(f"\n{pl.name} ({'SP' if pl.is_pitcher else pl.primary_pos}) → 2026 "
              f"{idx.upper()} {pr.value}  (age {pr.proj_age:.0f}, "
              f"proj {'IP' if idx=='pvi' else 'PA'} {pr.sample:.0f})")
        c = pr.components
        print(f"   regressed mean {c['regressed_mean']}, "
              f"aging shift {c['aging_shift']:+.1f} from age {c['weighted_age']}")

    bar("2 · VALUATION  (2026 projection → WAR → $ → surplus)")
    ss_proj = project_player(young_ss, PROJ_SEASON, index="hvi")
    ss_def = project_player(young_ss, PROJ_SEASON, index="dvi")
    w = hitter_war(ss_proj.value, ss_proj.sample, "SS", dvi=ss_def.value)
    print(f"\n{young_ss.name}: {w.war} WAR  {w.as_dict()}")

    ace_proj = project_player(ace, PROJ_SEASON, index="pvi")
    wp = pitcher_war(ace_proj.value, ace_proj.sample, "SP")
    print(f"{ace.name}: {wp.war} WAR  {wp.as_dict()}")

    bar("3 · CONTRACT SURPLUS  (young control vs. aging vet)")
    # Age each player forward year by year for a multi-year contract view.
    def multiyear_war_hitter(pl, pos, years):
        out = []
        for k in range(years):
            hv = project_player(pl, PROJ_SEASON + k, index="hvi").value
            dv = project_player(pl, PROJ_SEASON + k, index="dvi").value
            pa = project_player(pl, PROJ_SEASON + k, index="hvi").sample
            out.append(hitter_war(hv, pa, pos, dvi=dv).war)
        return out

    ss_wars = multiyear_war_hitter(young_ss, "SS", 4)
    ss_sv = surplus_value(ss_wars, young_ss.contract.salaries)
    print(f"\n{young_ss.name} (team control): {ss_sv.total_war} WAR, "
          f"${ss_sv.market_value}M value vs ${ss_sv.salary}M salary "
          f"→ SURPLUS ${ss_sv.surplus}M")

    vet_wars = multiyear_war_hitter(vet_1b, "1B", 3)
    vet_sv = surplus_value(vet_wars, vet_1b.contract.salaries)
    print(f"{vet_1b.name} (market deal): {vet_sv.total_war} WAR, "
          f"${vet_sv.market_value}M value vs ${vet_sv.salary}M salary "
          f"→ SURPLUS ${vet_sv.surplus}M")

    bar("4 · TEAM BUILD  (roster → wins, needs, best targets)")
    roster_war = ss_wars[0:1] + [w.war for w in [wp]] + [1.8, 2.4, 3.1, 0.9, 2.0, 1.2, 4.1]
    tp = project_team(roster_war, payroll=142.0)
    print(f"\nRoster WAR {tp.total_war} → projected {tp.projected_wins}-"
          f"{tp.projected_losses}, ${tp.payroll}M payroll "
          f"(${tp.dollars_per_marginal_win}M / marginal win)")

    print("\nBiggest needs:")
    needs = roster_needs({"SS": ss_wars[0], "CF": 0.6, "3B": 1.1, "SP2": 1.4, "RP": 0.3})
    for n in needs[:3]:
        print(f"   {n['slot']:<4} projects {n['projected_war']} WAR "
              f"(gap {n['gap']:+.1f} vs {n['target_war']})")

    print("\nBest available targets by surplus:")
    targets = rank_targets([
        ("Bounceback Brennan", 2.8, 9.0),
        ("Star Falk", 5.1, 40.0),
        ("Underrated Kane", 3.4, 12.0),
        ("Overpaid Diggs", 1.5, 22.0),
    ])
    for t in targets:
        flag = "✅" if t.surplus > 0 else "❌"
        print(f"   {flag} {t.name:<20} {t.war} WAR  ${t.market_value}M value "
              f"− ${t.salary}M → surplus ${t.surplus}M")

    print("\n(Illustrative data — wire in real PVI/HVI/DVI and calibrate the "
          "valuation constants to make it real.)")


if __name__ == "__main__":
    main()
