#!/usr/bin/env python3
"""Aggregate GitHub language usage across a user's repos and emit a compact SVG.

Runs in GitHub Actions with the built-in GITHUB_TOKEN (no third-party service,
no rate-limit risk). Output: generated/languages.svg
"""
import os
import json
import urllib.request
from collections import defaultdict

USER = "redtidev1918"
OUT = "generated/languages.svg"
TOPN = 8

# GitHub language color palette (most common ones)
COLORS = {
    "TypeScript": "#3178C6", "Python": "#3776AB", "Dart": "#0175C2",
    "JavaScript": "#F1E05A", "C++": "#F34B7D", "Go": "#00ADD8",
    "HTML": "#E34C26", "CSS": "#563D7C", "SCSS": "#C6538C", "Shell": "#89E051",
    "Dockerfile": "#384D54", "Makefile": "#427819", "Rust": "#DEA584",
    "Vue": "#41B883", "Kotlin": "#A97BFF", "Java": "#B07219", "C": "#555555",
    "C#": "#178600", "Ruby": "#701516", "PHP": "#4F5D95", "Swift": "#F05138",
    "Lua": "#000080", "Zig": "#EC915C",
}
FALLBACK = ["#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3",
            "#FDB462", "#B3DE69", "#FCCDE5"]


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "Bearer " + os.environ.get("GITHUB_TOKEN", ""),
            "Accept": "application/vnd.github+json",
            "User-Agent": "lang-stats-action",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        page += 1

    totals = defaultdict(int)
    for repo in repos:
        if repo.get("fork"):
            continue
        langs = api(f"/repos/{USER}/{repo['name']}/languages")
        for lang, bytes_ in langs.items():
            totals[lang] += bytes_

    if not totals:
        raise SystemExit("no language data")

    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = items[:TOPN]
    rest = sum(b for _, b in items[TOPN:])
    if rest:
        top.append(("Other", rest))

    grand = sum(b for _, b in top)

    # ---- build SVG ----
    W, PAD = 495, 20
    bar_x, bar_y, bar_w, bar_h = PAD, 46, W - 2 * PAD, 10
    rows = []
    y = bar_y + bar_h + 18
    for i, (lang, bytes_) in enumerate(top):
        pct = bytes_ / grand * 100
        color = COLORS.get(lang, FALLBACK[i % len(FALLBACK)])
        rows.append((lang, pct, color))

    bar_parts = []
    cursor = bar_x
    for lang, pct, color in rows:
        seg = bar_w * pct / 100
        bar_parts.append(
            f'<rect x="{cursor:.1f}" y="{bar_y}" width="{seg:.1f}" height="{bar_h}" fill="{color}"/>'
        )
        cursor += seg

    legend = []
    col_w = (W - 2 * PAD) / 2
    for i, (lang, pct, color) in enumerate(rows):
        col = i % 2
        row = i // 2
        lx = PAD + col * col_w
        ly = y + row * 22
        legend.append(
            f'<circle cx="{lx+6}" cy="{ly-4}" r="5" fill="{color}"/>'
            f'<text x="{lx+18}" y="{ly}" class="txt">{lang}</text>'
            f'<text x="{lx+col_w-10}" y="{ly}" class="pct" text-anchor="end">{pct:.1f}%</text>'
        )

    height = y + ((len(rows) + 1) // 2) * 22 + 10
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height:.0f}" viewBox="0 0 {W} {height:.0f}" font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">
<rect x="0.5" y="0.5" width="{W-1}" height="{height-1}" rx="6" fill="#0d1117" stroke="#30363d"/>
<text x="{PAD}" y="28" class="title">Languages</text>
<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="3" fill="#21262d"/>
{''.join(bar_parts)}
{''.join(legend)}
<style>
.title{{font-size:15px;font-weight:700;fill:#e6edf3}}
.txt{{font-size:12.5px;fill:#c9d1d9}}
.pct{{font-size:12.5px;fill:#8b949e}}
</style>
</svg>'''

    os.makedirs("generated", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT, "| languages:", ", ".join(f"{l} {p:.1f}%" for l, p, _ in rows))


if __name__ == "__main__":
    main()
