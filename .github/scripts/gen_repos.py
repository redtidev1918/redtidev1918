#!/usr/bin/env python3
"""Auto-generate the project index in README.md from the GitHub API.

New unlisted repos show up automatically at the end (under 其他项目). Only the
section between <!-- REPOS_START --> and <!-- REPOS_END --> is touched.
"""
import json
import os
import re
import urllib.request

USER = "redtidev1918"
README = "README.md"

# 分类（按顺序渲染）。名字必须和 GitHub 上的仓库名完全一致（大小写敏感），
# 否则仓库会掉进「其他项目」。
CATEGORIES = [
    ("Pixiv", ["PixivFlow", "pixivflow-webui", "pixiv-token-getter"]),
    ("Telegram / Publishing", ["TelePost", "TelePress", "Graf", "ParaNote"]),
    ("DeviantArt", ["DAKit", "DAViewer", "DeviantDrop", "deviantart-downloader"]),
    ("Apps & Libraries", ["NekoTime", "ludum"]),
    ("Tooling & Infrastructure", ["pixivflow-telepost-deploy", "docsite", "releasegraph"]),
    ("其他项目", []),
]

# 一句话描述。没写到的仓库回退用 repo 自带 description。
DESC = {
    "releasegraph": "基于 GitHub Actions 的无服务器、声明式 DAG 多仓库发布编排器",
    "PixivFlow": "Pixiv 下载、筛选与自动收集工具，支持批量下载、定时任务和可靠 HTTP 交付",
    "pixivflow-webui": "PixivFlow 的 Web 前端",
    "pixivflow-telepost-deploy": "PixivFlow + TelePost 的部署与运维套件",
    "pixiv-token-getter": "Pixiv API token 获取库与 CLI",
    "TelePost": "Telegram 频道投稿、审核与自动化发布平台",
    "TelePress": "轻松向 Telegraph 发布文本、图片和档案",
    "Graf": "极简自托管 Markdown 发布平台，Telegraph API 兼容",
    "ParaNote": "轻量级段落评论服务 + 通用网页阅读器",
    "DAKit": "面向 Dart / Flutter 的模块化 DeviantArt 客户端 SDK",
    "DAViewer": "开源 DeviantArt 客户端，支持 Android / macOS / Windows",
    "DeviantDrop": "Telegram 机器人：发 DeviantArt 作品链接，回传原图/视频/GIF 并附原页面链接",
    "deviantart-downloader": "DeviantArt 批量下载器",
    "NekoTime": "支持自定义 GIF 主题的桌面悬浮猫娘时钟",
    "ludum": "引擎无关、零运行时依赖的 TypeScript 游戏系统库",
    "docsite": "零依赖 docsify 文档站脚手架",
}

DISPLAY_NAMES = {"releasegraph": "ReleaseGraph"}


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
        if cat == "其他项目":
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
