#!/usr/bin/env python3
"""Aggregate GitHub language usage across a user's repos and emit a donut SVG.

Runs in GitHub Actions with the built-in GITHUB_TOKEN (no third-party service,
no rate-limit risk). Output: generated/languages.svg
"""
import os
import json
import math
import urllib.request
from collections import defaultdict

USER = "redtidev1918"
OUT = "generated/languages.svg"
MIN_PCT = 1.2  # 小于该比例的并入 Other

COLORS = {
    "TypeScript": "#3178C6", "Python": "#3776AB", "Dart": "#0175C2",
    "JavaScript": "#F1E05A", "C++": "#F34B7D", "Go": "#00ADD8",
    "HTML": "#E34C26", "CSS": "#563D7C", "SCSS": "#C6538C", "Shell": "#89E051",
    "Dockerfile": "#384D54", "Makefile": "#427819", "Rust": "#DEA584",
    "Vue": "#41B883", "Kotlin": "#A97BFF", "Java": "#B07219", "C": "#555555",
    "C#": "#178600", "Ruby": "#701516", "PHP": "#4F5D95", "Swift": "#F05138",
    "Lua": "#000080", "Zig": "#EC915C", "Other": "#8B949E",
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


def polar(cx, cy, radius, ang):
    """ang: radians clockwise from 12 o'clock."""
    return (cx + radius * math.sin(ang), cy - radius * math.cos(ang))


def donut_segment(cx, cy, r_out, r_in, a0, a1):
    large = 1 if (a1 - a0) > math.pi else 0
    x0o, y0o = polar(cx, cy, r_out, a0)
    x1o, y1o = polar(cx, cy, r_out, a1)
    x1i, y1i = polar(cx, cy, r_in, a1)
    x0i, y0i = polar(cx, cy, r_in, a0)
    return (
        f'<path d="M {x0o:.2f} {y0o:.2f} '
        f'A {r_out} {r_out} 0 {large} 1 {x1o:.2f} {y1o:.2f} '
        f'L {x1i:.2f} {y1i:.2f} '
        f'A {r_in} {r_in} 0 {large} 0 {x0i:.2f} {y0i:.2f} Z"/>'
    )


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
        for lang, bytes_ in api(f"/repos/{USER}/{repo['name']}/languages").items():
            totals[lang] += bytes_

    if not totals:
        raise SystemExit("no language data")

    grand_all = sum(totals.values())
    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top, rest_bytes = [], 0
    for lang, bytes_ in items:
        if bytes_ / grand_all * 100 >= MIN_PCT and len(top) < 8:
            top.append((lang, bytes_))
        else:
            rest_bytes += bytes_
    if rest_bytes:
        top.append(("Other", rest_bytes))

    grand = sum(b for _, b in top)
    rows = []
    for i, (lang, bytes_) in enumerate(top):
        pct = bytes_ / grand * 100
        color = COLORS.get(lang, FALLBACK[i % len(FALLBACK)])
        rows.append((lang, pct, color))

    # ---- donut geometry ----
    W = 495
    cx, cy, r_out, r_in = 118, 118, 80, 50
    gap = 0.012  # 扇区之间的小间隙（弧度）
    segs = []
    ang = gap / 2
    for lang, pct, color in rows:
        sweep = pct / 100 * 2 * math.pi
        segs.append(
            f'<g fill="{color}" stroke="#0d1117" stroke-width="2">'
            f'{donut_segment(cx, cy, r_out, r_in, ang, ang + sweep - gap)}</g>'
        )
        ang += sweep

    # ---- legend (right side, vertically centered) ----
    row_h = 24
    leg_x = 230
    leg_y0 = cy - (len(rows) * row_h) / 2 + 8
    legend = []
    for i, (lang, pct, color) in enumerate(rows):
        ly = leg_y0 + i * row_h
        legend.append(
            f'<circle cx="{leg_x}" cy="{ly-5}" r="5.5" fill="{color}"/>'
            f'<text x="{leg_x+15}" y="{ly}" class="txt">{lang}</text>'
            f'<text x="{W-24}" y="{ly}" class="pct" text-anchor="end">{pct:.1f}%</text>'
        )

    height = max(cy + r_out, leg_y0 + len(rows) * row_h) + 22
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height:.0f}" viewBox="0 0 {W} {height:.0f}" font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">
<rect x="0.5" y="0.5" width="{W-1}" height="{height-1}" rx="8" fill="#0d1117" stroke="#30363d"/>
<text x="22" y="30" class="title">Languages</text>
{''.join(segs)}
{''.join(legend)}
<style>
.title{{font-size:15px;font-weight:700;fill:#e6edf3}}
.txt{{font-size:13px;fill:#c9d1d9}}
.pct{{font-size:13px;font-weight:600;fill:#8b949e}}
</style>
</svg>'''

    os.makedirs("generated", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", OUT, "|", ", ".join(f"{l} {p:.1f}%" for l, p, _ in rows))


if __name__ == "__main__":
    main()
