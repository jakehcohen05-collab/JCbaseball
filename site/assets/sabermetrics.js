/*
 * Sabermetrics — client-side advanced-stat engine.
 *
 * The MLB Stats API returns raw counting stats and the common rate stats
 * (AVG/OBP/SLG/OPS/ERA/WHIP), but NOT wOBA, FIP, or ISO. We compute those here
 * from the component stats so the leaderboards carry real analytical value.
 *
 * Formulas mirror baseball/sabermetrics.py so the site and the Python engine
 * agree to the last decimal.
 */

// Linear weights for wOBA (modern run environment). Tune per season for
// era-accurate values.
export const WOBA_WEIGHTS = {
  bb: 0.69, hbp: 0.722, single: 0.888, double: 1.271, triple: 1.616, hr: 2.101,
};
export const LEAGUE_OBP = 0.320;
export const LEAGUE_SLG = 0.400;

const num = (v) => {
  const n = typeof v === "string" ? parseFloat(v) : v;
  return Number.isFinite(n) ? n : 0;
};
const safeDiv = (a, b) => (b ? a / b : 0);

/** Innings-pitched string ("120.1" = 120 ⅓) → whole outs. */
export function ipToOuts(ip) {
  if (ip == null) return 0;
  const s = String(ip);
  const [whole, frac = "0"] = s.split(".");
  return num(whole) * 3 + num(frac[0] ?? "0");
}

/** Outs → true decimal innings (361 outs → 120.33). */
export const outsToIp = (outs) => outs / 3;

export function iso(slg, avg) {
  return num(slg) - num(avg);
}

/* Rate stats computed from raw components, so they work identically on live
   API data and on component-only data. Each prefers an explicit value if the
   caller already has an authoritative one. */

export function avg(stat) {
  return safeDiv(num(stat.hits), num(stat.atBats));
}

export function obp(stat) {
  const h = num(stat.hits), bb = num(stat.baseOnBalls), hbp = num(stat.hitByPitch);
  const ab = num(stat.atBats), sf = num(stat.sacFlies);
  return safeDiv(h + bb + hbp, ab + bb + hbp + sf);
}

export function slg(stat) {
  const h = num(stat.hits), d = num(stat.doubles), t = num(stat.triples);
  const hr = num(stat.homeRuns), ab = num(stat.atBats);
  const singles = Math.max(h - d - t - hr, 0);
  return safeDiv(singles + 2 * d + 3 * t + 4 * hr, ab);
}

/**
 * wOBA from a hitting stat line (MLB Stats API field names).
 * Falls back gracefully when a component is missing.
 */
export function woba(stat) {
  const h = num(stat.hits);
  const d = num(stat.doubles);
  const t = num(stat.triples);
  const hr = num(stat.homeRuns);
  const bb = num(stat.baseOnBalls);
  const hbp = num(stat.hitByPitch);
  const ab = num(stat.atBats);
  const sf = num(stat.sacFlies);
  const singles = Math.max(h - d - t - hr, 0);
  const w = WOBA_WEIGHTS;
  const numer =
    w.bb * bb + w.hbp * hbp + w.single * singles +
    w.double * d + w.triple * t + w.hr * hr;
  const pa = ab + bb + hbp + sf;
  return safeDiv(numer, pa);
}

/**
 * FIP from a pitching stat line. constant scales FIP to league ERA (~3.10).
 */
export function fip(stat, constant = 3.1) {
  const hr = num(stat.homeRuns);
  const bb = num(stat.baseOnBalls);
  const hbp = num(stat.hitBatsmen ?? stat.hitByPitch);
  const so = num(stat.strikeOuts);
  const outs = ipToOuts(stat.inningsPitched);
  const ip = outsToIp(outs);
  if (!ip) return 0;
  return (13 * hr + 3 * (bb + hbp) - 2 * so) / ip + constant;
}

/** K/9 and BB/9 straight from components (API usually supplies these too). */
export function per9(count, ip) {
  const outs = ipToOuts(ip);
  return outs ? safeDiv(num(count) * 9, outsToIp(outs)) : 0;
}

/** Plate appearances, deriving from components if the API omits the field. */
export function plateAppearances(stat) {
  if (stat.plateAppearances != null) return num(stat.plateAppearances);
  return (
    num(stat.atBats) + num(stat.baseOnBalls) + num(stat.hitByPitch) +
    num(stat.sacFlies) + num(stat.sacBunts)
  );
}

/* ---- display formatting ------------------------------------------------ */

/** Rate stat like .316 — baseball drops the leading zero. */
export function fmtRate(x, digits = 3) {
  if (x == null || !Number.isFinite(+x)) return "—";
  const s = (+x).toFixed(digits);
  return s.startsWith("0.") ? s.slice(1) : s.startsWith("-0.") ? "-" + s.slice(2) : s;
}

/** Two-decimal stat like ERA 3.24 / FIP 3.10. */
export function fmt2(x) {
  return x == null || !Number.isFinite(+x) ? "—" : (+x).toFixed(2);
}

export function fmtInt(x) {
  return x == null || !Number.isFinite(+x) ? "—" : String(Math.round(+x));
}

export function fmtSigned(x, digits = 0) {
  if (x == null || !Number.isFinite(+x)) return "—";
  const v = +x;
  return (v >= 0 ? "+" : "") + v.toFixed(digits);
}
