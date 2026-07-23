/*
 * JC Baseball Lab — application logic.
 *
 * Fetches live 2026 data from the free public MLB Stats API and renders
 * standings + advanced leaderboards + player cards. Advanced metrics the API
 * doesn't return (wOBA, FIP, ISO) are computed client-side (sabermetrics.js).
 *
 * If the API can't be reached, it falls back to clearly-labeled sample data so
 * the page still renders — and shows a banner saying so.
 */

import * as sm from "./sabermetrics.js";
import { SAMPLE } from "./sample-data.js";

const SEASON = 2026;
const API = "https://statsapi.mlb.com/api/v1";
const LEADER_LIMIT = 30;

const DIVISIONS = {
  200: "AL West", 201: "AL East", 202: "AL Central",
  203: "NL West", 204: "NL East", 205: "NL Central",
};

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};

async function fetchJSON(url, timeoutMs = 12000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(t);
  }
}

/* ======================================================================= */
/*  Standings                                                              */
/* ======================================================================= */

async function loadStandings() {
  const grid = $("#standings-grid");
  try {
    const data = await fetchJSON(
      `${API}/standings?leagueId=103,104&season=${SEASON}&standingsTypes=regularSeason`
    );
    const rows = [];
    for (const rec of data.records || []) {
      const divName = DIVISIONS[rec.division?.id] || "Division";
      for (const tr of rec.teamRecords || []) {
        rows.push({
          team: { name: tr.team?.name },
          abbrev: abbrevFromName(tr.team?.name),
          division: divName,
          wins: tr.wins, losses: tr.losses,
          runsScored: tr.runsScored, runsAllowed: tr.runsAllowed,
        });
      }
    }
    renderStandings(rows);
    $("#hs-teams").textContent = rows.length || "—";
    return rows.length;
  } catch (err) {
    renderStandings(SAMPLE.standings);
    $("#hs-teams").textContent = SAMPLE.standings.length;
    throw err;
  }
}

// The standings API gives full team names; abbreviations aren't always present,
// so map the common ones for the compact display.
const ABBR = {
  "New York Yankees": "NYY", "Baltimore Orioles": "BAL", "Toronto Blue Jays": "TOR",
  "Boston Red Sox": "BOS", "Tampa Bay Rays": "TB", "Cleveland Guardians": "CLE",
  "Kansas City Royals": "KC", "Detroit Tigers": "DET", "Minnesota Twins": "MIN",
  "Chicago White Sox": "CWS", "Houston Astros": "HOU", "Seattle Mariners": "SEA",
  "Texas Rangers": "TEX", "Los Angeles Angels": "LAA", "Oakland Athletics": "ATH",
  "Athletics": "ATH", "Philadelphia Phillies": "PHI", "Atlanta Braves": "ATL",
  "New York Mets": "NYM", "Washington Nationals": "WSH", "Miami Marlins": "MIA",
  "Chicago Cubs": "CHC", "Milwaukee Brewers": "MIL", "St. Louis Cardinals": "STL",
  "Cincinnati Reds": "CIN", "Pittsburgh Pirates": "PIT", "Los Angeles Dodgers": "LAD",
  "San Diego Padres": "SD", "Arizona Diamondbacks": "ARI",
  "San Francisco Giants": "SF", "Colorado Rockies": "COL",
};
const abbrevFromName = (name) => ABBR[name] || (name || "").slice(0, 3).toUpperCase();

const DIV_ORDER = ["AL East", "AL Central", "AL West", "NL East", "NL Central", "NL West"];

function renderStandings(rows) {
  const grid = $("#standings-grid");
  grid.innerHTML = "";
  const byDiv = {};
  for (const r of rows) (byDiv[r.division] ||= []).push(r);

  for (const div of DIV_ORDER) {
    const teams = byDiv[div];
    if (!teams) continue;
    teams.forEach((t) => {
      const gp = (t.wins || 0) + (t.losses || 0);
      t._pct = gp ? t.wins / gp : 0;
      t._diff = (t.runsScored || 0) - (t.runsAllowed || 0);
      const rs = t.runsScored || 0, ra = t.runsAllowed || 0;
      t._pyth = rs || ra ? Math.pow(rs, 1.83) / (Math.pow(rs, 1.83) + Math.pow(ra, 1.83)) : 0;
    });
    teams.sort((a, b) => b._pct - a._pct || b._diff - a._diff);

    const card = el("div", "division-card");
    card.appendChild(el("div", "division-title", div));
    teams.forEach((t, i) => {
      const row = el("div", "div-row" + (i === 0 ? " leader" : ""));
      const diffCls = t._diff > 0 ? "pos" : t._diff < 0 ? "neg" : "";
      row.innerHTML = `
        <span class="div-team">${t.team.name}<span class="abbr">${t.abbrev}</span></span>
        <span class="div-rec">${t.wins}-${t.losses}</span>
        <span class="div-pct">${sm.fmtRate(t._pct)}</span>
        <span class="div-diff ${diffCls}">${sm.fmtSigned(t._diff)}</span>`;
      row.title = `Pythagorean win%: ${sm.fmtRate(t._pyth)}`;
      card.appendChild(row);
    });
    grid.appendChild(card);
  }
}

/* ======================================================================= */
/*  Leaderboards (generic sortable table)                                  */
/* ======================================================================= */

function makeSortableTable(tableEl, columns, rows, defaultSort) {
  let sortKey = defaultSort.key;
  let sortDir = defaultSort.dir; // 1 asc, -1 desc

  const thead = $("thead", tableEl);
  const tbody = $("tbody", tableEl);

  function draw() {
    const col = columns.find((c) => c.key === sortKey);
    const sorted = [...rows].sort((a, b) => {
      const av = col.sortVal ? col.sortVal(a) : a[sortKey];
      const bv = col.sortVal ? col.sortVal(b) : b[sortKey];
      if (typeof av === "string") return sortDir * av.localeCompare(bv);
      return sortDir * ((av ?? -Infinity) - (bv ?? -Infinity));
    });

    thead.innerHTML = "";
    const htr = el("tr");
    columns.forEach((c) => {
      const th = el("th", c.cls || "");
      if (c.key === sortKey) th.classList.add("sorted");
      th.innerHTML = c.label + (c.key === sortKey
        ? `<span class="arrow">${sortDir === 1 ? "▲" : "▼"}</span>` : "");
      th.title = c.title || c.label;
      th.onclick = () => {
        if (sortKey === c.key) sortDir *= -1;
        else { sortKey = c.key; sortDir = c.defaultDir || -1; }
        draw();
      };
      htr.appendChild(th);
    });
    thead.appendChild(htr);

    tbody.innerHTML = "";
    sorted.forEach((r, i) => {
      const tr = el("tr");
      columns.forEach((c) => {
        const td = el("td", c.cls || "");
        if (c.key === "rank") td.textContent = i + 1;
        else td.innerHTML = c.render(r);
        if (c.key === sortKey && c.key !== "rank" && c.key !== "name") td.classList.add("lead");
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }
  draw();
}

function decorateBatting(rows) {
  return rows.map((s) => {
    const st = s.stat;
    const pa = sm.plateAppearances(st);
    const avg = sm.avg(st);
    const obp = sm.obp(st);
    const slg = sm.slg(st);
    return {
      name: s.player.fullName,
      team: s.team?.abbreviation || abbrevFromName(s.team?.name),
      g: +st.gamesPlayed || 0, pa,
      avg, obp, slg,
      ops: obp + slg,
      iso: sm.iso(slg, avg),
      woba: sm.woba(st),
      hr: +st.homeRuns || 0, rbi: +st.rbi || 0, sb: +st.stolenBases || 0,
    };
  });
}

function decoratePitching(rows) {
  return rows.map((s) => {
    const st = s.stat;
    const outs = sm.ipToOuts(st.inningsPitched);
    const ip = sm.outsToIp(outs);
    return {
      name: s.player.fullName,
      team: s.team?.abbreviation || abbrevFromName(s.team?.name),
      w: +st.wins || 0, l: +st.losses || 0, sv: +st.saves || 0,
      ip, ipStr: st.inningsPitched ?? "0.0",
      era: +st.era || 0, whip: +st.whip || 0,
      k9: ip ? (+st.strikeOuts || 0) * 9 / ip : 0,
      bb9: ip ? (+st.baseOnBalls || 0) * 9 / ip : 0,
      kbb: +st.baseOnBalls ? (+st.strikeOuts || 0) / (+st.baseOnBalls) : (+st.strikeOuts || 0),
      fip: sm.fip(st),
      so: +st.strikeOuts || 0,
    };
  });
}

const nameCell = (r) => `${r.name}<span class="team-tag">${r.team}</span>`;

const BATTING_COLS = [
  { key: "rank", label: "#", cls: "col-rank" },
  { key: "name", label: "Player", cls: "col-name", render: nameCell,
    sortVal: (r) => r.name, defaultDir: 1 },
  { key: "g", label: "G", render: (r) => sm.fmtInt(r.g) },
  { key: "pa", label: "PA", render: (r) => sm.fmtInt(r.pa) },
  { key: "avg", label: "AVG", render: (r) => sm.fmtRate(r.avg) },
  { key: "obp", label: "OBP", render: (r) => sm.fmtRate(r.obp) },
  { key: "slg", label: "SLG", render: (r) => sm.fmtRate(r.slg) },
  { key: "ops", label: "OPS", render: (r) => sm.fmtRate(r.ops) },
  { key: "iso", label: "ISO", title: "Isolated power", render: (r) => sm.fmtRate(r.iso) },
  { key: "woba", label: "wOBA", title: "Weighted on-base avg", render: (r) => sm.fmtRate(r.woba) },
  { key: "hr", label: "HR", render: (r) => sm.fmtInt(r.hr) },
  { key: "rbi", label: "RBI", render: (r) => sm.fmtInt(r.rbi) },
  { key: "sb", label: "SB", render: (r) => sm.fmtInt(r.sb) },
];

const PITCHING_COLS = [
  { key: "rank", label: "#", cls: "col-rank" },
  { key: "name", label: "Player", cls: "col-name", render: nameCell,
    sortVal: (r) => r.name, defaultDir: 1 },
  { key: "wl", label: "W-L", render: (r) => `${r.w}-${r.l}`, sortVal: (r) => r.w - r.l },
  { key: "sv", label: "SV", render: (r) => sm.fmtInt(r.sv) },
  { key: "ip", label: "IP", render: (r) => r.ipStr, sortVal: (r) => r.ip },
  { key: "era", label: "ERA", defaultDir: 1, render: (r) => sm.fmt2(r.era) },
  { key: "whip", label: "WHIP", defaultDir: 1, render: (r) => sm.fmt2(r.whip) },
  { key: "k9", label: "K/9", render: (r) => sm.fmt2(r.k9) },
  { key: "bb9", label: "BB/9", defaultDir: 1, render: (r) => sm.fmt2(r.bb9) },
  { key: "kbb", label: "K/BB", render: (r) => sm.fmt2(r.kbb) },
  { key: "fip", label: "FIP", title: "Fielding independent pitching",
    defaultDir: 1, render: (r) => sm.fmt2(r.fip) },
  { key: "so", label: "SO", render: (r) => sm.fmtInt(r.so) },
];

async function loadBatting() {
  try {
    const data = await fetchJSON(
      `${API}/stats?stats=season&group=hitting&season=${SEASON}&sportId=1` +
      `&playerPool=qualified&limit=${LEADER_LIMIT}&sortStat=onBasePlusSlugging`
    );
    const splits = data.stats?.[0]?.splits || [];
    if (!splits.length) throw new Error("no data");
    const rows = decorateBatting(splits);
    makeSortableTable($("#batting-table"), BATTING_COLS, rows, { key: "ops", dir: -1 });
    $("#hs-hitters").textContent = rows.length;
  } catch (err) {
    const rows = decorateBatting(SAMPLE.batting);
    makeSortableTable($("#batting-table"), BATTING_COLS, rows, { key: "ops", dir: -1 });
    $("#hs-hitters").textContent = rows.length;
    throw err;
  }
}

async function loadPitching() {
  try {
    const data = await fetchJSON(
      `${API}/stats?stats=season&group=pitching&season=${SEASON}&sportId=1` +
      `&playerPool=qualified&limit=${LEADER_LIMIT}&sortStat=earnedRunAverage`
    );
    const splits = data.stats?.[0]?.splits || [];
    if (!splits.length) throw new Error("no data");
    const rows = decoratePitching(splits);
    makeSortableTable($("#pitching-table"), PITCHING_COLS, rows, { key: "era", dir: 1 });
    $("#hs-pitchers").textContent = rows.length;
  } catch (err) {
    const rows = decoratePitching(SAMPLE.pitching);
    makeSortableTable($("#pitching-table"), PITCHING_COLS, rows, { key: "era", dir: 1 });
    $("#hs-pitchers").textContent = rows.length;
    throw err;
  }
}

/* ======================================================================= */
/*  Player search                                                          */
/* ======================================================================= */

let playerIndex = null;

async function ensurePlayerIndex() {
  if (playerIndex) return playerIndex;
  try {
    const data = await fetchJSON(`${API}/sports/1/players?season=${SEASON}`);
    playerIndex = (data.people || []).map((p) => ({
      id: p.id, name: p.fullName,
      team: p.currentTeam?.name ? abbrevFromName(p.currentTeam.name) : "",
      pos: p.primaryPosition?.abbreviation || "",
    }));
  } catch {
    // Fallback: build a tiny index from the sample leaders.
    playerIndex = [...SAMPLE.batting, ...SAMPLE.pitching].map((s, i) => ({
      id: `sample-${i}`, name: s.player.fullName,
      team: s.team.abbreviation, pos: "", _sample: s,
    }));
  }
  return playerIndex;
}

function setupPlayerSearch() {
  const input = $("#player-search");
  const results = $("#search-results");
  const hint = $("#players-hint");
  let items = [], active = -1;

  const close = () => { results.classList.add("hidden"); active = -1; };

  input.addEventListener("input", async () => {
    const q = input.value.trim().toLowerCase();
    if (q.length < 2) { close(); return; }
    const idx = await ensurePlayerIndex();
    items = idx.filter((p) => p.name.toLowerCase().includes(q)).slice(0, 12);
    if (!items.length) { results.innerHTML = `<div class="search-item">No match</div>`;
      results.classList.remove("hidden"); return; }
    results.innerHTML = items.map((p, i) =>
      `<div class="search-item" data-i="${i}">
         <span>${p.name}</span>
         <span class="si-team">${[p.team, p.pos].filter(Boolean).join(" · ")}</span>
       </div>`).join("");
    results.classList.remove("hidden");
    results.querySelectorAll(".search-item").forEach((n) => {
      n.onclick = () => selectPlayer(items[+n.dataset.i]);
    });
  });

  input.addEventListener("keydown", (e) => {
    const nodes = results.querySelectorAll(".search-item");
    if (e.key === "ArrowDown") { active = Math.min(active + 1, nodes.length - 1); }
    else if (e.key === "ArrowUp") { active = Math.max(active - 1, 0); }
    else if (e.key === "Enter" && items[active]) { selectPlayer(items[active]); return; }
    else if (e.key === "Escape") { close(); return; }
    else return;
    nodes.forEach((n, i) => n.classList.toggle("active", i === active));
    e.preventDefault();
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-box")) close();
  });

  async function selectPlayer(p) {
    close();
    input.value = p.name;
    hint.textContent = "Loading card…";
    const card = $("#player-card");
    try {
      let bat = null, pit = null, meta = { team: p.team, pos: p.pos };
      if (p._sample) {
        // Sample fallback: render whatever line we have.
        if (p._sample.stat.atBats != null) bat = p._sample.stat;
        else pit = p._sample.stat;
      } else {
        const data = await fetchJSON(
          `${API}/people/${p.id}?hydrate=stats(group=[hitting,pitching],type=[season],season=${SEASON})`
        );
        const person = data.people?.[0] || {};
        meta = { team: abbrevFromName(person.currentTeam?.name) || p.team,
                 pos: person.primaryPosition?.abbreviation || p.pos };
        for (const grp of person.stats || []) {
          const st = grp.splits?.[0]?.stat;
          if (!st) continue;
          if (grp.group?.displayName === "hitting") bat = st;
          if (grp.group?.displayName === "pitching") pit = st;
        }
      }
      renderPlayerCard(p.name, meta, bat, pit);
      hint.textContent = "";
    } catch (err) {
      card.classList.add("hidden");
      hint.textContent = "Couldn't load that player's 2026 stats.";
    }
  }
}

function statTile(k, v, hl) {
  return `<div class="pc-stat ${hl ? "hl" : ""}"><div class="v">${v}</div><div class="k">${k}</div></div>`;
}

function renderPlayerCard(name, meta, bat, pit) {
  const card = $("#player-card");
  const groups = [];

  if (bat && (+bat.atBats || +bat.plateAppearances)) {
    const pa = sm.plateAppearances(bat);
    const avg = sm.avg(bat);
    const obp = sm.obp(bat);
    const slg = sm.slg(bat);
    const tiles = [
      statTile("AVG", sm.fmtRate(avg)),
      statTile("OBP", sm.fmtRate(obp)),
      statTile("SLG", sm.fmtRate(slg)),
      statTile("OPS", sm.fmtRate(obp + slg), true),
      statTile("wOBA", sm.fmtRate(sm.woba(bat)), true),
      statTile("ISO", sm.fmtRate(sm.iso(slg, avg))),
      statTile("HR", sm.fmtInt(bat.homeRuns)),
      statTile("RBI", sm.fmtInt(bat.rbi)),
      statTile("SB", sm.fmtInt(bat.stolenBases)),
      statTile("PA", sm.fmtInt(pa)),
    ].join("");
    groups.push(`<div class="pc-group"><h4>Batting · ${SEASON}</h4><div class="pc-stats">${tiles}</div></div>`);
  }

  if (pit && sm.ipToOuts(pit.inningsPitched)) {
    const ip = sm.outsToIp(sm.ipToOuts(pit.inningsPitched));
    const tiles = [
      statTile("W-L", `${pit.wins || 0}-${pit.losses || 0}`),
      statTile("ERA", sm.fmt2(+pit.era || 0), true),
      statTile("FIP", sm.fmt2(sm.fip(pit)), true),
      statTile("WHIP", sm.fmt2(+pit.whip || 0)),
      statTile("IP", pit.inningsPitched),
      statTile("SO", sm.fmtInt(pit.strikeOuts)),
      statTile("K/9", sm.fmt2(ip ? (+pit.strikeOuts || 0) * 9 / ip : 0)),
      statTile("BB/9", sm.fmt2(ip ? (+pit.baseOnBalls || 0) * 9 / ip : 0)),
      statTile("SV", sm.fmtInt(pit.saves)),
    ].join("");
    groups.push(`<div class="pc-group"><h4>Pitching · ${SEASON}</h4><div class="pc-stats">${tiles}</div></div>`);
  }

  if (!groups.length) {
    groups.push(`<div class="pc-group"><p class="hint">No 2026 stats on record for this player yet.</p></div>`);
  }

  card.innerHTML = `
    <div class="pc-head">
      <span class="pc-name">${name}</span>
      <span class="pc-meta">${[meta.team, meta.pos].filter(Boolean).join(" · ")}</span>
    </div>
    <div class="pc-body">${groups.join("")}</div>`;
  card.classList.remove("hidden");
}

/* ======================================================================= */
/*  Boot                                                                   */
/* ======================================================================= */

function showSampleBanner() {
  const b = $("#data-banner");
  b.innerHTML =
    "⚠️ Showing <strong>sample data</strong> — couldn't reach the live MLB Stats API " +
    "from this network. Deployed on a normal connection, this page loads real, " +
    "current 2026 stats.";
  b.classList.remove("hidden");
}

async function boot() {
  $("#updated").textContent = `· Loaded ${new Date().toLocaleString()}`;
  setupPlayerSearch();

  const results = await Promise.allSettled([
    loadStandings(), loadBatting(), loadPitching(),
  ]);
  // If everything fell back to sample data, tell the user plainly.
  if (results.every((r) => r.status === "rejected")) showSampleBanner();
}

boot();
