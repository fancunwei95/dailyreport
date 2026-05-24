#!/usr/bin/env python3
"""Build static site for Daily Big News.

Scans reports/ for daily_big_news_YYYY-MM-DD[_zh].html files, wraps each in a
shared chrome (header + history strip + language toggle), and emits a docs/
tree that GitHub Pages can serve.

Output layout (relative to docs/):
    index.html              latest EN report + chrome
    zh/index.html           latest ZH report + chrome
    YYYY-MM-DD/index.html   that day's EN report + chrome
    YYYY-MM-DD/zh/index.html that day's ZH report + chrome
    archive/index.html      full date list
    manifest.json           PWA manifest
    icon-192.png            PWA icon (small)
    icon-512.png            PWA icon (large)
"""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
DOCS_DIR = ROOT / "docs"
ASSETS_DIR = ROOT / "assets"

REPORT_RE = re.compile(r"^daily_big_news_(\d{4}-\d{2}-\d{2})(_zh)?\.html$")
BODY_RE = re.compile(r"<body[^>]*>(.*?)</body>", re.DOTALL | re.IGNORECASE)
STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
LANG_TOGGLE_RE = re.compile(r'<div class="lang-toggle">.*?</div>', re.DOTALL)
HISTORY_WINDOW = 30


def find_reports() -> dict[str, dict[str, Path | None]]:
    """Return {date: {'en': Path|None, 'zh': Path|None}} sorted by date desc later."""
    out: dict[str, dict[str, Path | None]] = {}
    for f in REPORTS_DIR.glob("daily_big_news_*.html"):
        m = REPORT_RE.match(f.name)
        if not m:
            continue
        date, zh_suffix = m.group(1), m.group(2)
        lang = "zh" if zh_suffix else "en"
        out.setdefault(date, {"en": None, "zh": None})[lang] = f
    return out


def extract_style_and_body(html: str) -> tuple[str, str]:
    """Pull the first <style> block and the inner <body> content out of a report."""
    style = ""
    sm = STYLE_RE.search(html)
    if sm:
        style = sm.group(1)
    body = ""
    bm = BODY_RE.search(html)
    if bm:
        body = bm.group(1)
    # The original report links its sibling language file with a relative path
    # that won't resolve under our new URL layout — strip it, chrome has its own.
    body = LANG_TOGGLE_RE.sub("", body)
    return style, body


CHROME_CSS = """
.dbn-chrome{position:sticky;top:0;z-index:10;background:rgba(15,20,25,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--border);margin:-24px -24px 18px -24px;padding:10px 24px}
.dbn-bar{max-width:1100px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.dbn-brand{font-weight:700;font-size:16px;color:var(--text);text-decoration:none;letter-spacing:.2px}
.dbn-brand .dbn-dot{color:var(--accent)}
.dbn-tag{font-size:11px;color:var(--muted);margin-left:8px}
.dbn-lang a{color:var(--accent);text-decoration:none;font-size:12px;border:1px solid var(--border);padding:4px 10px;border-radius:999px}
.dbn-history{max-width:1100px;margin:8px auto 0 auto;display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;scrollbar-width:thin}
.dbn-history::-webkit-scrollbar{height:6px}
.dbn-history::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.dbn-history a{flex:0 0 auto;font-size:12px;color:var(--muted);text-decoration:none;border:1px solid var(--border);padding:4px 10px;border-radius:6px;white-space:nowrap;background:var(--card)}
.dbn-history a.dbn-current{color:var(--accent);border-color:var(--accent);font-weight:600}
.dbn-history a.dbn-latest{color:var(--text);border-color:var(--text)}
.dbn-history a.dbn-more{color:var(--muted);background:transparent;border-style:dashed}
@media (max-width:600px){
  .dbn-chrome{margin:-24px -16px 14px -16px;padding:8px 16px}
  body{padding:16px !important}
}
"""


def history_strip_html(dates: list[str], current_date: str | None, lang: str, depth: int) -> str:
    """Build the horizontal history strip.

    depth = number of `../` segments needed to reach the docs root from this page.
    """
    up = "../" * depth
    parts: list[str] = []
    # "Latest" link only on per-date pages (depth > 1 for EN, depth > 2 for ZH).
    on_latest = (current_date is None)
    latest_href = up if lang == "en" else (up + "zh/")
    if not on_latest:
        parts.append(f'<a href="{latest_href}" class="dbn-latest">↑ Latest</a>')
    visible = dates[:HISTORY_WINDOW]
    for d in visible:
        href = url_for(d, lang, depth)
        classes = ["dbn-date"]
        if d == current_date:
            classes.append("dbn-current")
        if d == dates[0] and on_latest:
            classes.append("dbn-current")
        parts.append(f'<a href="{href}" class="{" ".join(classes)}">{d}</a>')
    if len(dates) > HISTORY_WINDOW:
        archive_href = f"{up}archive/"
        parts.append(f'<a href="{archive_href}" class="dbn-more">Full archive →</a>')
    return '<div class="dbn-history">' + "".join(parts) + "</div>"


def url_for(date: str, lang: str, depth: int) -> str:
    """Relative URL from a page at the given depth to that date's report in the given lang."""
    up = "../" * depth
    if lang == "en":
        return f"{up}{date}/"
    return f"{up}{date}/zh/"


def chrome_bar_html(lang: str, depth: int, other_lang_exists: bool) -> str:
    up = "../" * depth
    home = (up or "./") if lang == "en" else (up + "zh/")
    # toggle target: same date's other language, computed by caller via attribute
    if lang == "en":
        toggle_label = "中文"
    else:
        toggle_label = "English"
    if not other_lang_exists:
        toggle = ""
    else:
        toggle = f'<div class="dbn-lang"><a href="__OTHER_LANG__">{toggle_label}</a></div>'
    return f'''<nav class="dbn-chrome">
  <div class="dbn-bar">
    <a class="dbn-brand" href="{home}">Daily Big News<span class="dbn-dot">.</span><span class="dbn-tag">pre-market view</span></a>
    {toggle}
  </div>
  __HISTORY__
</nav>'''


def page_html(*, date: str, lang: str, depth: int, dates: list[str], style: str, body: str,
              other_lang_href: str | None, is_latest_page: bool) -> str:
    """Assemble the final HTML for a single page."""
    up = "../" * depth
    html_lang = "en" if lang == "en" else "zh-CN"
    title = f"Daily Big News — {date}"
    description = "Daily pre-market read of major U.S. equity-impacting news. Updated each morning."
    manifest_href = f"{up}manifest.json"
    icon_href = f"{up}icon-192.png"
    icon512 = f"{up}icon-512.png"
    current_for_strip = None if is_latest_page else date

    chrome = chrome_bar_html(lang, depth, other_lang_href is not None)
    chrome = chrome.replace("__HISTORY__", history_strip_html(dates, current_for_strip, lang, depth))
    if other_lang_href is not None:
        chrome = chrome.replace("__OTHER_LANG__", other_lang_href)

    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{description}">
<meta name="theme-color" content="#0f1419">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Daily Big News">
<link rel="manifest" href="{manifest_href}">
<link rel="apple-touch-icon" href="{icon_href}">
<link rel="icon" type="image/png" sizes="512x512" href="{icon512}">
<style>{style}
{CHROME_CSS}</style>
</head>
<body>
{chrome}
{body}
</body>
</html>
"""


def empty_page_html() -> str:
    """Shown when there are no reports yet."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Daily Big News</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0f1419">
<style>
body{margin:0;padding:60px 24px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f1419;color:#e2e8f0;text-align:center}
h1{font-size:24px;margin-bottom:8px}
p{color:#94a3b8}
</style>
</head>
<body>
<h1>Daily Big News</h1>
<p>No reports yet — check back tomorrow.</p>
</body>
</html>
"""


def archive_html(dates: list[str]) -> str:
    """A simple full archive of all dates, EN + ZH side-by-side."""
    rows = []
    for d in dates:
        rows.append(
            f'<li><span class="d">{d}</span> '
            f'<a href="../{d}/">English</a> '
            f'<a href="../{d}/zh/">中文</a></li>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Daily Big News — Archive</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0f1419">
<link rel="manifest" href="../manifest.json">
<link rel="apple-touch-icon" href="../icon-192.png">
<style>
body{{margin:0;padding:24px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f1419;color:#e2e8f0;line-height:1.5}}
.wrap{{max-width:720px;margin:0 auto}}
h1{{font-size:22px;margin:0 0 16px}}
ul{{list-style:none;padding:0;margin:0}}
li{{display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid #2d3748}}
.d{{flex:1;color:#cbd5e1;font-variant-numeric:tabular-nums}}
a{{color:#60a5fa;text-decoration:none;font-size:13px;border:1px solid #2d3748;padding:3px 10px;border-radius:6px}}
.back{{display:inline-block;margin-bottom:14px;color:#60a5fa;text-decoration:none;font-size:13px}}
</style>
</head>
<body>
<div class="wrap">
<a class="back" href="../">← Latest</a>
<h1>Archive · {len(dates)} reports</h1>
<ul>
{chr(10).join(rows)}
</ul>
</div>
</body>
</html>
"""


def build() -> None:
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    reports = find_reports()
    dates = sorted(reports.keys(), reverse=True)

    if not dates:
        (DOCS_DIR / "index.html").write_text(empty_page_html(), encoding="utf-8")
        write_pwa_assets(DOCS_DIR)
        print("No reports found — wrote empty placeholder.")
        return

    for date in dates:
        for lang in ("en", "zh"):
            src = reports[date][lang]
            if src is None:
                continue
            style, body = extract_style_and_body(src.read_text(encoding="utf-8"))
            other = "zh" if lang == "en" else "en"
            other_exists = reports[date][other] is not None

            # Per-date page: docs/<date>/index.html (en) or docs/<date>/zh/index.html
            if lang == "en":
                out_dir = DOCS_DIR / date
                depth = 1
                other_href = "zh/" if other_exists else None
            else:
                out_dir = DOCS_DIR / date / "zh"
                depth = 2
                other_href = "../" if other_exists else None
            out_dir.mkdir(parents=True, exist_ok=True)
            html = page_html(
                date=date, lang=lang, depth=depth, dates=dates,
                style=style, body=body, other_lang_href=other_href,
                is_latest_page=False,
            )
            (out_dir / "index.html").write_text(html, encoding="utf-8")

    # Root index.html + zh/index.html — derived from latest available report.
    latest = dates[0]
    for lang in ("en", "zh"):
        src = reports[latest][lang]
        if src is None:
            continue
        style, body = extract_style_and_body(src.read_text(encoding="utf-8"))
        other = "zh" if lang == "en" else "en"
        other_exists = reports[latest][other] is not None
        if lang == "en":
            out_dir = DOCS_DIR
            depth = 0
            other_href = "zh/" if other_exists else None
        else:
            out_dir = DOCS_DIR / "zh"
            depth = 1
            other_href = "../" if other_exists else None
        out_dir.mkdir(parents=True, exist_ok=True)
        html = page_html(
            date=latest, lang=lang, depth=depth, dates=dates,
            style=style, body=body, other_lang_href=other_href,
            is_latest_page=True,
        )
        (out_dir / "index.html").write_text(html, encoding="utf-8")

    # Archive
    archive_dir = DOCS_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(archive_html(dates), encoding="utf-8")

    write_pwa_assets(DOCS_DIR)
    write_404(DOCS_DIR)

    print(f"Built {len(dates)} report dates → docs/  (latest: {latest})")


def write_pwa_assets(out: Path) -> None:
    """Copy manifest + icons from assets/ into docs/."""
    for name in ("manifest.json", "icon-192.png", "icon-512.png", "favicon.svg"):
        src = ASSETS_DIR / name
        if src.exists():
            shutil.copy(src, out / name)


def write_404(out: Path) -> None:
    """A friendly 404 that links back to latest."""
    (out / "404.html").write_text("""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Not found</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;padding:60px 24px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f1419;color:#e2e8f0;text-align:center}h1{font-size:24px}a{color:#60a5fa}</style>
</head><body><h1>404</h1><p>That page doesn't exist. <a href="/">Go to latest →</a></p></body></html>
""", encoding="utf-8")


if __name__ == "__main__":
    build()
