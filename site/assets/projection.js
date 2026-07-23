/*
 * Projection + valuation engine (client-side port of analytics/*.py).
 *
 * Turns multiple seasons of index history into a projected next-season index,
 * then into projected WAR. Mirrors the Python engine so the site and the
 * offline tools agree.
 */

import { woba, fip, ipToOuts, outsToIp } from "./sabermetrics.js";

// --- Aging curve (index points relative to peak). ---
export const AGING = {
  19: -9.0, 20: -7.5, 21: -6.0, 22: -4.5, 23: -3.0, 24: -1.6, 25: -0.7,
  26: -0.1, 27: 0.0, 28: -0.2, 29: -0.8, 30: -1.7, 31: -2.8, 32: -4.1,
  33: -5.6, 34: -7.3, 35: -9.2, 36: -11.3, 37: -13.6, 38: -16.1, 39: -18.8, 40: -21.7,
};

export function agingValue(age) {
  const ages = Object.keys(AGING).map(Number);
  const lo = Math.min(...ages), hi = Math.max(...ages);
  if (age <= lo) return AGING[lo];
  if (age >= hi) return AGING[hi];
  const a0 = Math.floor(age), a1 = a0 + 1;
  if (AGING[a1] === undefined) return AGING[a0];
  const f = age - a0;
  return AGING[a0] * (1 - f) + AGING[a1] * f;
}
const agingDelta = (from, to) => agingValue(to) - agingValue(from);

// --- Within-season z-score → 100-scaled index. ---
export function toIndex(rawById, { invert = false, mean = 100, sd = 15, refIds = null } = {}) {
  const ids = Object.keys(rawById);
  const ref = (refIds && refIds.length ? refIds : ids).map((i) => rawById[i]);
  const n = ref.length || 1;
  const mu = ref.reduce((a, b) => a + b, 0) / n;
  const varr = ref.reduce((a, b) => a + (b - mu) ** 2, 0) / n;
  const sdev = varr > 0 ? Math.sqrt(varr) : 1;
  const sign = invert ? -1 : 1;
  const out = {};
  for (const i of ids) out[i] = +(mean + sd * sign * (rawById[i] - mu) / sdev).toFixed(1);
  return out;
}

// --- Marcel-style projection of one index. ---
export function projectIndex(history, projAge, {
  weights = [5, 4, 3], regressionSample = 200, basePlayingTime = 200, leagueAvg = 100,
} = {}) {
  const seasons = [...history].sort((a, b) => b.age - a.age).slice(0, weights.length);
  let num = leagueAvg * regressionSample, den = regressionSample, ageNum = 0, ageDen = 0;
  seasons.forEach((s, i) => {
    const w = weights[i] * s.sample;
    num += w * s.value; den += w; ageNum += w * s.age; ageDen += w;
  });
  const regressed = den ? num / den : leagueAvg;
  const weightedAge = ageDen ? ageNum / ageDen : projAge;
  const projected = regressed + agingDelta(weightedAge, projAge);
  const recent = seasons[0]?.sample || 0, second = seasons[1]?.sample || 0;
  return {
    value: +projected.toFixed(1),
    sample: Math.round(0.5 * recent + 0.1 * second + basePlayingTime),
    projAge,
  };
}

// --- Valuation constants (mirror valuation.py). ---
const RUNS_PER_WIN = 10, SD = 15;
const RUNS_PER_SD_BAT_600 = 20, RUNS_PER_SD_PITCH_180 = 22;
const REPL_BAT_600 = 20, REPL_SP_180 = 20, REPL_RP_60 = 4;
export const POSITION_ADJ = {
  C: 12.5, SS: 7.5, "2B": 2.5, "3B": 2.5, CF: 2.5,
  LF: -7.5, RF: -7.5, "1B": -12.5, DH: -17.5, OF: -2.5,
};

export function hitterWar(hvi, pa, pos = "DH") {
  const z = (hvi - 100) / SD, scale = pa / 600;
  const batting = z * RUNS_PER_SD_BAT_600 * scale;
  const position = (POSITION_ADJ[pos] ?? 0) * scale;
  const repl = REPL_BAT_600 * scale;
  return +((batting + position + repl) / RUNS_PER_WIN).toFixed(1);
}

export function pitcherWar(pvi, ip, role = "SP") {
  const z = (pvi - 100) / SD, scale = ip / 180;
  const pitching = z * RUNS_PER_SD_PITCH_180 * scale;
  const repl = role === "RP" ? REPL_RP_60 * (ip / 60) : REPL_SP_180 * scale;
  return +((pitching + repl) / RUNS_PER_WIN).toFixed(1);
}

// --- Helpers to turn raw API stat lines into provisional indices. ---
export const wobaRaw = (st) => {
  const pa = (+st.atBats || 0) + (+st.baseOnBalls || 0) + (+st.hitByPitch || 0) + (+st.sacFlies || 0);
  return pa > 0 ? woba(st) : null;
};
export const fipRaw = (st) => (ipToOuts(st.inningsPitched) > 0 ? fip(st) : null);
export const ipOf = (st) => outsToIp(ipToOuts(st.inningsPitched));
