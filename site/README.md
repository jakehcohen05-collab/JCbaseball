# JC Baseball Lab — front-office analytics site

A static, dependency-free web app that presents **live 2026 MLB analytics**:
division standings, advanced batting and pitching leaderboards, and a searchable
player stat card. Built to be usable in a front-office setting.

## How the data works

The site fetches directly from the **free public [MLB Stats API](https://statsapi.mlb.com)**
in the browser at view time. Nothing is baked in, so the numbers are always the
current 2026 season figures — not a stale snapshot.

Advanced metrics the API does *not* return are computed client-side in
[`assets/sabermetrics.js`](assets/sabermetrics.js), matching the formulas in the
repo's Python engine (`baseball/sabermetrics.py`):

| Metric | Where it comes from |
|--------|--------------------|
| AVG, OBP, SLG, OPS, ISO | computed from component stats |
| **wOBA** | linear weights, computed client-side |
| **FIP** | computed from HR/BB/HBP/SO/IP |
| K/9, BB/9, K/BB | computed from component stats |
| Pythagorean win% | computed in the standings (exp 1.83) |
| ERA, WHIP | from the API |

If the API can't be reached (offline, or a locked-down network), the page
renders a **clearly-labeled sample dataset** and shows a banner saying so, so the
layout is never blank. Real team names are used with placeholder records — no
fabricated stat is ever presented as real.

## Run it locally

It's plain static files — serve the `site/` directory with any static server:

```bash
cd site
python3 -m http.server 8799
# open http://127.0.0.1:8799
```

(A static server is needed rather than opening the file directly, because the
app uses native ES modules.)

## Deploy

`netlify.toml` at the repo root sets `publish = "site"` with no build step.
Point Netlify at the repo and it deploys as-is. Any static host works (Netlify,
Vercel, GitHub Pages, S3+CloudFront) — there is no server component.

## Files

```
site/
  index.html              # page structure
  assets/
    styles.css            # dark front-office theme
    sabermetrics.js       # advanced-metric engine (wOBA, FIP, ISO, …)
    app.js                # MLB Stats API integration + sortable tables + search
    sample-data.js        # labeled offline fallback
```

## Customizing

- **Season** — change `SEASON` at the top of `assets/app.js`.
- **Leaderboard depth** — change `LEADER_LIMIT` in `assets/app.js`.
- **wOBA weights / league baselines** — edit the constants at the top of
  `assets/sabermetrics.js` to match a specific run environment.
- **Branding / colors** — the palette lives in the `:root` block of
  `assets/styles.css`.
