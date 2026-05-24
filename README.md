# Daily Big News

Daily pre-market commentary on major U.S. equity-impacting news, generated
by an automated Claude routine and published as a static site via GitHub
Pages.

**Live site:** https://fancunwei95.github.io/dailyreport/

## How it works

```
reports/ ──▶ build.py ──▶ docs/ ──▶ git push ──▶ GitHub Pages
```

1. A Claude routine writes the day's HTML reports into `reports/`:
   - `daily_big_news_YYYY-MM-DD.html` (English)
   - `daily_big_news_YYYY-MM-DD_zh.html` (中文)
2. `build.py` wraps each report in a shared chrome (header, language toggle,
   horizontal history strip) and emits the full static tree under `docs/`.
3. `docs/` is served by GitHub Pages.

The landing page shows the latest report inline, with the most recent 30
dates accessible from a strip at the top. The full archive lives at
`/archive/`.

## Layout

```
reports/                    raw HTML reports (one per day, EN + ZH)
build.py                    static-site generator
assets/
  manifest.json             PWA manifest
  icon-192.png, icon-512.png app icons
  make_icons.py             regenerate icons (rarely needed)
docs/                       generated output — what GitHub Pages serves
```

## Running the build

```sh
python3 build.py
```

Reads `reports/`, regenerates `docs/`. Idempotent — safe to re-run.

## Daily routine integration

The Claude routine that writes new reports should, after writing, run:

```sh
cd /path/to/dailyreport
python3 build.py
git add -A
git commit -m "Daily report $(date +%F)"
git push
```

If `git push` fails (no network), reports stay local. The next run catches up.

## PWA

The site ships a `manifest.json` and apple-touch-icon meta tags, so on iPhone
you can tap **Share → Add to Home Screen** in Safari and it installs as a
full-screen app with its own icon. No App Store required.

## Disclaimer

The reports are informational research, not investment advice. Position
sizing and risk management remain the reader's responsibility.
