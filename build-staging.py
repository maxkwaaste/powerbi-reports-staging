#!/usr/bin/env python3
"""Build GitHub Pages directory structure from Power BI report HTML files."""

import os
import re
import shutil
from pathlib import Path
from html import escape

SRC = Path.home() / "ClaudeCode" / "powerbi-reports"
DST = Path.home() / "ClaudeCode" / "powerbi-reports-staging"

EN_SRC = SRC / "en"
NL_SRC = SRC / "nl"
EN_PATH = "powerbi/insights"
NL_PATH = "nl-powerbi/ai-gegenereerde-rapporten"

NOINDEX = '<meta name="robots" content="noindex, nofollow">'

LINK_REPLACEMENTS = [
    ('https://proxuma.io/powerbi/insights/', '/powerbi/insights/'),
    ('https://proxuma.io/nl-powerbi/ai-gegenereerde-rapporten/', '/nl-powerbi/ai-gegenereerde-rapporten/'),
]

SKIP_PATTERNS = re.compile(r'rel="canonical"|hreflang=|"mainEntityOfPage"|"@type":\s*"ListItem"|"url":|"image":|og:|schema\.org')


def extract_slug(filename: str) -> str:
    return filename.removeprefix("proxuma-io-").removesuffix("-post.html")


def extract_title(html: str) -> str:
    m = re.search(r'id="prx-hero-h1"[^>]*>([^<]+)', html)
    if m:
        return m.group(1).strip()
    m = re.search(r'<title>([^<]+)', html)
    if m:
        return m.group(1).strip()
    return "Untitled"


def process_html(html: str) -> str:
    if NOINDEX not in html:
        html = html.replace('<head>', f'<head>\n{NOINDEX}', 1)

    lines = html.split('\n')
    result = []
    for line in lines:
        if SKIP_PATTERNS.search(line):
            result.append(line)
            continue
        for old, new in LINK_REPLACEMENTS:
            line = line.replace(old, new)
        result.append(line)
    return '\n'.join(result)


def build_reports(src_dir: Path, base_path: str) -> list[dict]:
    reports = []
    if not src_dir.exists():
        return reports
    for f in sorted(src_dir.iterdir()):
        if not f.name.endswith("-post.html"):
            continue
        slug = extract_slug(f.name)
        html = f.read_text(encoding="utf-8")
        title = extract_title(html)
        processed = process_html(html)

        out_dir = DST / base_path / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(processed, encoding="utf-8")

        reports.append({"slug": slug, "title": title, "lang": "en" if "insights" in base_path else "nl"})
    return reports


def build_gallery(reports: list[dict], base_path: str, lang: str, title: str):
    rows = ""
    for r in reports:
        slug = escape(r["slug"])
        name = escape(r["title"])
        rows += f'<tr><td>{name}</td><td><code>{slug}</code></td><td><a href="/{base_path}/{slug}/">View</a></td></tr>\n'

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{NOINDEX}
<title>{title} - dev.proxuma.io</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Open Sans',system-ui,sans-serif;background:#f8fafc;color:#2c3e50}}
header{{background:#1e293b;color:#fff;padding:24px 32px}}
header h1{{font-size:1.4rem;font-weight:800}}
header p{{opacity:.7;margin-top:4px;font-size:.9rem}}
.wrap{{max-width:1200px;margin:0 auto;padding:24px}}
.search{{width:100%;padding:12px 16px;border:1px solid #e2e8f0;border-radius:8px;font-size:1rem;margin-bottom:16px}}
.count{{font-size:.9rem;color:#64748b;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
th{{background:#f1f5f9;text-align:left;padding:12px 16px;font-weight:700;font-size:.85rem;text-transform:uppercase;color:#64748b}}
td{{padding:12px 16px;border-top:1px solid #f1f5f9;font-size:.9rem}}
tr:hover td{{background:#f8fafc}}
a{{color:#0f766e;text-decoration:none;font-weight:600}}
a:hover{{text-decoration:underline}}
code{{background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:.8rem}}
.back{{display:inline-block;margin-bottom:16px;font-size:.9rem}}
</style>
</head>
<body>
<header>
<h1>{title}</h1>
<p>{len(reports)} reports - Staging preview at dev.proxuma.io</p>
</header>
<div class="wrap">
<a class="back" href="/">Back to overview</a>
<input class="search" type="text" placeholder="Filter reports..." id="q">
<div class="count" id="count">{len(reports)} reports</div>
<table>
<thead><tr><th>Report</th><th>Slug</th><th>Link</th></tr></thead>
<tbody id="tbody">
{rows}
</tbody>
</table>
</div>
<script>
const q=document.getElementById('q'),tbody=document.getElementById('tbody'),count=document.getElementById('count'),rows=[...tbody.querySelectorAll('tr')];
q.addEventListener('input',()=>{{const v=q.value.toLowerCase();let n=0;rows.forEach(r=>{{const m=r.textContent.toLowerCase().includes(v);r.style.display=m?'':'none';if(m)n++}});count.textContent=n+' reports'}});
</script>
</body>
</html>"""
    out_dir = DST / base_path
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def build_root(en_reports: list[dict], nl_reports: list[dict]):
    slug_map = {}
    for r in en_reports:
        slug_map.setdefault(r["slug"], {})["en"] = r
    for r in nl_reports:
        slug_map.setdefault(r["slug"], {})["nl"] = r

    rows = ""
    for slug in sorted(slug_map.keys()):
        info = slug_map[slug]
        name = escape(info.get("en", info.get("nl", {})).get("title", slug))
        en_link = f'<a href="/{EN_PATH}/{slug}/">EN</a>' if "en" in info else "-"
        nl_link = f'<a href="/{NL_PATH}/{slug}/">NL</a>' if "nl" in info else "-"
        rows += f'<tr><td>{name}</td><td><code>{escape(slug)}</code></td><td>{en_link}</td><td>{nl_link}</td></tr>\n'

    total = len(en_reports) + len(nl_reports)
    unique = len(slug_map)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{NOINDEX}
<title>Power BI Reports Staging - dev.proxuma.io</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Open Sans',system-ui,sans-serif;background:#f8fafc;color:#2c3e50}}
header{{background:#1e293b;color:#fff;padding:32px}}
header h1{{font-size:1.6rem;font-weight:800}}
header p{{opacity:.7;margin-top:6px;font-size:.95rem}}
.wrap{{max-width:1200px;margin:0 auto;padding:24px}}
.stats{{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}}
.stat{{background:#fff;padding:16px 24px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.stat-n{{font-size:1.8rem;font-weight:800;color:#0f766e}}
.stat-l{{font-size:.8rem;color:#64748b;text-transform:uppercase;font-weight:700;margin-top:2px}}
.links{{display:flex;gap:12px;margin-bottom:24px}}
.links a{{background:#0f766e;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:700;font-size:.9rem}}
.links a:hover{{background:#115e58}}
.search{{width:100%;padding:12px 16px;border:1px solid #e2e8f0;border-radius:8px;font-size:1rem;margin-bottom:16px}}
.count{{font-size:.9rem;color:#64748b;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
th{{background:#f1f5f9;text-align:left;padding:12px 16px;font-weight:700;font-size:.85rem;text-transform:uppercase;color:#64748b}}
td{{padding:12px 16px;border-top:1px solid #f1f5f9;font-size:.9rem}}
tr:hover td{{background:#f8fafc}}
a{{color:#0f766e;text-decoration:none;font-weight:600}}
a:hover{{text-decoration:underline}}
code{{background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:.8rem}}
.note{{background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;padding:12px 16px;margin-bottom:24px;font-size:.9rem;color:#92400e}}
</style>
</head>
<body>
<header>
<h1>Proxuma Power BI Reports</h1>
<p>Staging preview -- dev.proxuma.io -- not indexed</p>
</header>
<div class="wrap">
<div class="note">This is a staging preview. Reports are not indexed by search engines. Production site: proxuma.io</div>
<div class="stats">
<div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total pages</div></div>
<div class="stat"><div class="stat-n">{len(en_reports)}</div><div class="stat-l">English</div></div>
<div class="stat"><div class="stat-n">{len(nl_reports)}</div><div class="stat-l">Dutch</div></div>
<div class="stat"><div class="stat-n">{unique}</div><div class="stat-l">Unique slugs</div></div>
</div>
<div class="links">
<a href="/{EN_PATH}/">EN Gallery ({len(en_reports)} reports)</a>
<a href="/{NL_PATH}/">NL Gallery ({len(nl_reports)} reports)</a>
</div>
<input class="search" type="text" placeholder="Filter reports..." id="q">
<div class="count" id="count">{unique} reports</div>
<table>
<thead><tr><th>Report</th><th>Slug</th><th>EN</th><th>NL</th></tr></thead>
<tbody id="tbody">
{rows}
</tbody>
</table>
</div>
<script>
const q=document.getElementById('q'),tbody=document.getElementById('tbody'),count=document.getElementById('count'),rows=[...tbody.querySelectorAll('tr')];
q.addEventListener('input',()=>{{const v=q.value.toLowerCase();let n=0;rows.forEach(r=>{{const m=r.textContent.toLowerCase().includes(v);r.style.display=m?'':'none';if(m)n++}});count.textContent=n+' reports'}});
</script>
</body>
</html>"""
    # Write to staging-table.html instead of index.html (gallery is the index now)
    (DST / "staging-table.html").write_text(html, encoding="utf-8")


def main():
    for d in (DST / EN_PATH, DST / NL_PATH):
        if d.exists():
            shutil.rmtree(d)

    # Don't delete root index.html -- it's the gallery page (gallery-en.html), managed separately
    # root_index = DST / "index.html"

    print(f"Source EN: {EN_SRC} ({len(list(EN_SRC.glob('*-post.html')))} files)")
    print(f"Source NL: {NL_SRC} ({len(list(NL_SRC.glob('*-post.html')))} files)")

    en_reports = build_reports(EN_SRC, EN_PATH)
    print(f"Built {len(en_reports)} EN report pages")

    nl_reports = build_reports(NL_SRC, NL_PATH)
    print(f"Built {len(nl_reports)} NL report pages")

    build_gallery(en_reports, EN_PATH, "en", "AI-Powered Power BI Reports (EN)")
    build_gallery(nl_reports, NL_PATH, "nl", "AI-Gegenereerde Power BI Rapporten (NL)")
    print("Built gallery pages")

    build_root(en_reports, nl_reports)
    print("Built root index")

    print(f"\nTotal: {len(en_reports) + len(nl_reports)} pages in {DST}")


if __name__ == "__main__":
    main()
