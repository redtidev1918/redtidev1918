#!/usr/bin/env python3
"""Aggregate profile stats (stars / lines of code / repos / forks) and emit a stat-card SVG.

Runs in GitHub Actions. Lines of code come from tokei over shallow clones of each
non-fork repo; stars/repos/forks come from the GitHub API using the built-in
GITHUB_TOKEN. No third-party service, no per-repo API calls beyond the repo list.
Output: generated/stats.svg
"""
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request

USER = "redtidev1918"
OUT = "generated/stats.svg"

# ---- card theme (matches generated/languages.svg) ----
BG = "#161b22"
BORDER = "#30363d"
TITLE_COLOR = "#8b949e"
NUM_COLOR = "#e6edf3"


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "Bearer " + os.environ.get("GITHUB_TOKEN", ""),
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-stats-action",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def list_repos():
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def count_loc(repos):
    workdir = tempfile.mkdtemp(prefix="profile-loc-")
    try:
        for repo in repos:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet",
                 f"https://github.com/{USER}/{repo['name']}.git", repo["name"]],
                cwd=workdir, check=True, capture_output=True,
            )
        out = subprocess.run(
            ["tokei", "--output", "json", workdir],
            capture_output=True, check=True,
        )
        data = json.loads(out.stdout)
        return data["Total"]["code"]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def fmt(n):
    return f"{n:,}"


def render(rows):
    n = len(rows)
    pad, cw, ch, gap = 16, 156, 84, 12
    width = pad * 2 + cw * n + gap * (n - 1)
    height = pad * 2 + ch

    cards = []
    for i, (title, value, color) in enumerate(rows):
        x = pad + i * (cw + gap)
        y = pad
        num = fmt(value)
        size = 26 if len(num) <= 7 else 22
        cards.append(
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="8" '
            f'fill="{BG}" stroke="{BORDER}"/>'
            f'<text x="{x+14}" y="{y+26}" class="title">{title}</text>'
            f'<text x="{x+14}" y="{y+56}" class="num" fill="{color}" '
            f'font-size="{size}">{num}</text>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">
{''.join(cards)}
<style>
.title{{font-size:11px;font-weight:600;letter-spacing:0.5px;fill:{TITLE_COLOR}}}
.num{{font-weight:700;fill:{NUM_COLOR}}}
</style>
</svg>'''
    return svg


def main():
    repos = list_repos()
    mine = [r for r in repos if not r.get("fork")]

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    loc = count_loc(mine)

    rows = [
        ("Total Stars", stars, "#F1E05A"),
        ("Lines of Code", loc, "#58A6FF"),
        ("Repositories", len(mine), "#3FB950"),
        ("Forks", forks, "#F0883E"),
    ]

    os.makedirs("generated", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(rows))
    print("wrote", OUT, "|", ", ".join(f"{t}={v}" for t, v, _ in rows))


if __name__ == "__main__":
    main()
