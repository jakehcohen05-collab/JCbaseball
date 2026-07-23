# Deploying JC Baseball Lab

The site (`site/`) is fully static and fetches live 2026 data from the MLB Stats
API in the browser, so there's **no build step** — any static host works. Two
easy paths below. Both take a couple of minutes.

Once it's live on a normal network, the "sample data" banner disappears and the
standings, leaderboards, and projections load real, current 2026 numbers.

---

## Option A — GitHub Pages (automated, already wired up)

A workflow (`.github/workflows/deploy-pages.yml`) is committed. It deploys
`site/` on every push. You just have to turn Pages on **once**:

1. In the repo on GitHub: **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Push anything to the branch (or **Actions tab → "Deploy site to GitHub
   Pages" → Run workflow**). The workflow builds and gives you a live URL like
   `https://<you>.github.io/JCbaseball/`.

> If you see *"Branch is not allowed to deploy to github-pages"*, the repo's
> `github-pages` environment is restricted to the default branch. Either merge
> this branch to `main` (the workflow also triggers on `main`), or in
> **Settings → Environments → github-pages** add this branch to the allowed
> deployment branches.

## Option B — Netlify (matches your current host)

Your existing site is already on Netlify, so this fits your setup. `netlify.toml`
is committed with `publish = "site"`, so there's nothing to configure.

**Fastest (drag-and-drop):**
1. Go to <https://app.netlify.com/drop>.
2. Drag the `site/` folder onto the page. Live instantly at a Netlify URL.

**Connected to the repo (auto-deploys on every push):**
1. Netlify → **Add new site → Import an existing project → GitHub**.
2. Pick `jakehcohen05-collab/JCbaseball`, and this branch
   (`claude/baseball-analysis-database-c13ij9`) — or `main` after you merge.
3. Netlify reads `netlify.toml` (publish dir `site`, no build command). Deploy.
4. Every push to that branch redeploys automatically.

---

## After it's live

- The page calls `https://statsapi.mlb.com` directly from the browser. That's a
  free public API (no key), and it's CORS-open, so it works from any deployed
  origin.
- Custom domain: both Pages and Netlify let you attach one in their settings.
- Nothing here logs, tracks, or needs secrets — it's a static front end.
