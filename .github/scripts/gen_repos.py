#!/usr/bin/env python3
"""Auto-generate the project index in README.md from the GitHub API.

New repos show up automatically (under "Other"). Only the section between
<!-- REPOS_START --> and <!-- REPOS_END --> is touched.
"""
import json
import os
import re
import urllib.request

USER = "redtidev1918"
README = "README.md"

# 分类（按顺序渲染）。不在任何分类里的新仓库会自动并到 Other。
CATEGORIES = [
    ("Pixiv", ["PixivFlow", "pixivflow-webui", "pixivflow-telepost-deploy", "pixiv-token-getter"]),
    ("Telegram / Publishing", ["TelePost", "telepress", "graf"]),
    ("DeviantArt", ["daviewer", "deviantart-downloader", "dakit", "deviantdrop"]),
    ("Other", ["NekoTime", "ludum", "paranote"]),
]

# 一句话描述。没写到的仓库回退用 repo 自带 description。
DESC = {
    "release-infra": "基于 GitHub Actions 的无服务器、声明式 DAG 多仓库发布编排器",
    "PixivFlow": "Pixiv 自动下载与任务调度",
    "pixivflow-webui": "PixivFlow 的 Web 前端",
    "pixivflow-telepost-deploy": "PixivFlow + TelePost 部署工具",
    "pixiv-token-getter": "Pixiv token 获取库与 CLI",
    "TelePost": "Telegram 频道投稿机器人，支持搜索、统计和标签",
    "telepress": "Telegraph 文章与图片发布 Python 库",
    "graf": "兼容 Telegraph API 的自托管 Markdown 发布平台",
    "daviewer": "DeviantArt 客户端，支持 Android / macOS / Windows",
    "deviantart-downloader": "DeviantArt 批量下载器",
    "dakit": "Dart / Flutter DeviantArt SDK 与 CLI",
    "deviantdrop": "DeviantArt 链接解析与媒体回传 Telegram Bot",
    "NekoTime": "支持自定义 GIF 主题的桌面悬浮猫娘时钟",
    "ludum": "引擎无关的 TypeScript 游戏系统库",
    "paranote": "网页段落评论与阅读工具",
}

DISPLAY_NAMES = {"release-infra": "ReleaseGraph"}


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats-action",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
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


def short(desc):
    # 只取中文/主要那半段，去掉「中文｜English」这类尾巴
    for sep in ("｜", "|", "。"):
        i = desc.find(sep)
        if i > 8:
            return desc[:i].strip()
    return desc.strip()


def line(repo):
    name = repo["name"]
    desc = DESC.get(name) or short(repo.get("description") or "")
    return f"| [**{DISPLAY_NAMES.get(name, name)}**]({repo['html_url']}) | {desc} |"


TABLE_HEAD = ["| Project | Description |", "| :-- | :-- |"]


def build(repos):
    by_name = {r["name"]: r for r in repos if not r.get("fork") and r["name"] != USER}
    listed = [n for _, names in CATEGORIES for n in names]

    out = []
    for cat, names in CATEGORIES:
        rows = []
        for n in names:
            if n in by_name:
                rows.append(line(by_name[n]))
        if cat == "Other":
            for r in sorted(
                (r for r in by_name.values() if r["name"] not in listed),
                key=lambda x: -x["stargazers_count"],
            ):
                rows.append(line(r))
        if rows:
            out.append(f"### {cat}")
            out.append("")
            out.extend(TABLE_HEAD)
            out.extend(rows)
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    repos = list_repos()
    section = build(repos)

    with open(README, encoding="utf-8") as f:
        content = f.read()

    marker = re.compile(r"<!-- REPOS_START -->.*?<!-- REPOS_END -->", re.S)
    new = "<!-- REPOS_START -->\n" + section + "<!-- REPOS_END -->"
    content, n = marker.subn(new, content, count=1)
    if n == 0:
        raise SystemExit("REPOS markers not found in README.md")

    with open(README, "w", encoding="utf-8") as f:
        f.write(content)
    print("updated README repo list")


if __name__ == "__main__":
    main()
