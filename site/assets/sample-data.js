/*
 * SAMPLE fallback data — illustrative only.
 *
 * This is NOT real 2026 performance. It exists solely so the page renders a
 * complete design when the live MLB Stats API can't be reached (e.g. offline,
 * blocked network, or a preview build). When the site runs on a normal
 * network, app.js fetches real, current 2026 data and this file is never used.
 *
 * Team names and divisions are real; win/loss and stat lines are placeholders.
 */

export const SAMPLE = { isSample: true, season: 2026 };

// --- Standings (real teams, placeholder records) -------------------------
const S = (name, abbr, div, w, l, rs, ra) => ({
  team: { name }, abbrev: abbr, division: div,
  wins: w, losses: l, runsScored: rs, runsAllowed: ra,
});

SAMPLE.standings = [
  // AL East
  S("New York Yankees", "NYY", "AL East", 61, 40, 512, 420),
  S("Baltimore Orioles", "BAL", "AL East", 57, 44, 489, 441),
  S("Toronto Blue Jays", "TOR", "AL East", 52, 49, 455, 452),
  S("Boston Red Sox", "BOS", "AL East", 50, 51, 470, 478),
  S("Tampa Bay Rays", "TB", "AL East", 46, 55, 421, 466),
  // AL Central
  S("Cleveland Guardians", "CLE", "AL Central", 58, 43, 478, 419),
  S("Kansas City Royals", "KC", "AL Central", 54, 47, 461, 448),
  S("Detroit Tigers", "DET", "AL Central", 53, 48, 449, 440),
  S("Minnesota Twins", "MIN", "AL Central", 49, 52, 452, 463),
  S("Chicago White Sox", "CWS", "AL Central", 38, 63, 388, 512),
  // AL West
  S("Houston Astros", "HOU", "AL West", 59, 42, 501, 428),
  S("Seattle Mariners", "SEA", "AL West", 56, 45, 470, 431),
  S("Texas Rangers", "TEX", "AL West", 51, 50, 463, 461),
  S("Los Angeles Angels", "LAA", "AL West", 45, 56, 432, 489),
  S("Athletics", "ATH", "AL West", 41, 60, 401, 505),
  // NL East
  S("Philadelphia Phillies", "PHI", "NL East", 60, 41, 505, 421),
  S("Atlanta Braves", "ATL", "NL East", 57, 44, 498, 430),
  S("New York Mets", "NYM", "NL East", 55, 46, 481, 444),
  S("Washington Nationals", "WSH", "NL East", 47, 54, 438, 470),
  S("Miami Marlins", "MIA", "NL East", 42, 59, 405, 498),
  // NL Central
  S("Chicago Cubs", "CHC", "NL Central", 56, 45, 479, 433),
  S("Milwaukee Brewers", "MIL", "NL Central", 55, 46, 466, 431),
  S("St. Louis Cardinals", "STL", "NL Central", 51, 50, 458, 455),
  S("Cincinnati Reds", "CIN", "NL Central", 49, 52, 461, 470),
  S("Pittsburgh Pirates", "PIT", "NL Central", 44, 57, 410, 481),
  // NL West
  S("Los Angeles Dodgers", "LAD", "NL West", 64, 37, 540, 401),
  S("San Diego Padres", "SD", "NL West", 58, 43, 489, 424),
  S("Arizona Diamondbacks", "ARI", "NL West", 53, 48, 495, 470),
  S("San Francisco Giants", "SF", "NL West", 50, 51, 447, 452),
  S("Colorado Rockies", "COL", "NL West", 39, 62, 430, 560),
];

// --- Batting leaders (placeholder lines) ---------------------------------
const B = (name, team, g, pa, ab, h, d, t, hr, bb, hbp, sf, so, rbi, sb) => ({
  player: { fullName: name }, team: { abbreviation: team },
  stat: {
    gamesPlayed: g, plateAppearances: pa, atBats: ab, hits: h, doubles: d,
    triples: t, homeRuns: hr, baseOnBalls: bb, hitByPitch: hbp, sacFlies: sf,
    strikeOuts: so, rbi, stolenBases: sb,
  },
});

SAMPLE.batting = [
  B("Aaron Judge", "NYY", 99, 430, 355, 118, 21, 1, 34, 66, 4, 5, 92, 88, 8),
  B("Bobby Witt Jr.", "KC", 101, 448, 402, 132, 28, 6, 24, 38, 3, 5, 68, 79, 31),
  B("Shohei Ohtani", "LAD", 100, 445, 388, 120, 22, 3, 33, 51, 3, 3, 96, 82, 19),
  B("Juan Soto", "NYM", 98, 441, 350, 108, 19, 1, 29, 84, 2, 5, 78, 74, 6),
  B("Gunnar Henderson", "BAL", 100, 442, 390, 118, 26, 4, 26, 47, 4, 1, 99, 71, 17),
  B("Yordan Alvarez", "HOU", 96, 421, 360, 114, 24, 0, 30, 55, 2, 4, 86, 90, 2),
  B("Freddie Freeman", "LAD", 99, 435, 372, 122, 30, 2, 19, 56, 2, 5, 70, 77, 9),
  B("Corey Seager", "TEX", 94, 408, 360, 115, 25, 1, 27, 42, 3, 3, 74, 73, 3),
  B("Mookie Betts", "LAD", 97, 430, 372, 116, 27, 2, 22, 52, 3, 3, 62, 70, 14),
  B("Vladimir Guerrero Jr.", "TOR", 100, 440, 388, 121, 26, 1, 23, 48, 2, 2, 71, 76, 3),
  B("Ronald Acuña Jr.", "ATL", 95, 425, 368, 112, 20, 3, 21, 52, 2, 3, 82, 60, 34),
  B("Kyle Tucker", "CHC", 98, 432, 372, 111, 23, 2, 24, 54, 2, 4, 68, 72, 20),
  B("Rafael Devers", "BOS", 99, 436, 384, 115, 28, 1, 25, 47, 3, 2, 95, 78, 4),
  B("José Ramírez", "CLE", 100, 438, 390, 116, 27, 2, 26, 44, 2, 2, 58, 80, 28),
  B("Marcell Ozuna", "ATL", 98, 428, 378, 108, 21, 0, 28, 46, 2, 2, 90, 81, 1),
];

// --- Pitching leaders (placeholder lines) --------------------------------
const P = (name, team, w, l, sv, gs, ip, so, bb, hbp, hr, era, whip) => ({
  player: { fullName: name }, team: { abbreviation: team },
  stat: {
    wins: w, losses: l, saves: sv, gamesStarted: gs, inningsPitched: ip,
    strikeOuts: so, baseOnBalls: bb, hitBatsmen: hbp, homeRuns: hr,
    era: String(era), whip: String(whip),
  },
});

SAMPLE.pitching = [
  P("Tarik Skubal", "DET", 12, 3, 0, 20, "132.1", 168, 22, 3, 9, "2.31", "0.88"),
  P("Paul Skenes", "PIT", 10, 5, 0, 20, "128.0", 172, 30, 4, 8, "2.44", "0.96"),
  P("Zack Wheeler", "PHI", 11, 4, 0, 20, "130.2", 155, 28, 2, 11, "2.58", "0.98"),
  P("Chris Sale", "ATL", 12, 3, 0, 20, "129.1", 176, 33, 3, 10, "2.61", "1.01"),
  P("Logan Gilbert", "SEA", 9, 6, 0, 20, "127.0", 158, 24, 4, 12, "2.79", "0.94"),
  P("Corbin Burnes", "ARI", 10, 5, 0, 20, "131.0", 149, 31, 2, 9, "2.83", "1.02"),
  P("Garrett Crochet", "BOS", 9, 6, 0, 20, "128.2", 178, 34, 5, 11, "2.88", "1.05"),
  P("Framber Valdez", "HOU", 11, 4, 0, 20, "126.1", 141, 36, 6, 8, "2.91", "1.09"),
  P("Cole Ragans", "KC", 10, 5, 0, 20, "125.0", 165, 40, 3, 10, "2.96", "1.08"),
  P("Dylan Cease", "SD", 9, 6, 0, 20, "127.2", 170, 44, 4, 12, "3.05", "1.11"),
  P("Emmanuel Clase", "CLE", 3, 2, 31, 0, "48.1", 62, 9, 1, 2, "1.49", "0.79"),
  P("Mason Miller", "ATH", 2, 3, 28, 0, "46.0", 78, 15, 2, 3, "1.96", "0.85"),
];
