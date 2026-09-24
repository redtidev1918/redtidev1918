#!/usr/bin/env python3
"""Auto-generate the project index in README.md (zh) and README.en.md (en)
from the GitHub API.

New unlisted repos show up automatically at the end (under 更多项目 / More
projects). Only the sections between the REPOS markers are touched:

  README.md    <!-- REPOS_START -->    ... <!-- REPOS_END -->
  README.en.md <!-- REPOS_EN_START -->  ... <!-- REPOS_EN_END -->
"""
import json
import os
import re
import urllib.request

USER = "redtidev1918"
README = "README.md"
README_EN = "README.en.md"

# 分类（按顺序渲染）。名字必须和 GitHub 上的仓库名完全一致（大小写敏感），
# 否则仓库会掉进「更多项目」。按产品族分组，方便不懂技术的人浏览。
CATEGORIES = [
    ("DeviantArt", ["DAKit", "DAViewer", "DeviantDrop", "deviantart-downloader"]),
    ("Pixiv", ["PixivFlow", "pixivflow-webui", "pixiv-token-getter"]),
    ("Telegram", ["TelePost", "TelePress", "pixivflow-telepost-deploy"]),
    ("发布工具", ["releasegraph"]),
    ("Skills", ["use-bash"]),
    ("更多项目", ["Graf", "NekoTime", "ludum", "ParaNote", "docsite"]),
]

CAT_EN = {
    "发布工具": "Publishing tools",
    "Skills": "Skills",
    "更多项目": "More projects",
}

# 一句话描述。没写到的仓库回退用 repo 自带 description。
DESC = {
    "releasegraph": "基于 GitHub Actions 的无服务器、声明式 DAG 多仓库发布编排器",
    "PixivFlow": "Pixiv 下载、筛选与自动收集工具，支持批量下载、定时任务和可靠 HTTP 交付",
    "pixivflow-webui": "PixivFlow 的 Web 前端",
    "pixivflow-telepost-deploy": "PixivFlow + TelePost 的部署与运维套件",
    "pixiv-token-getter": "Pixiv API token 获取库与 CLI",
    "TelePost": "Telegram 频道投稿、审核与自动化发布平台",
    "TelePress": "向 Telegraph 发布文本、图片与档案的 Python 库与 CLI",
    "Graf": "自托管 Markdown 发布平台，兼容 Telegraph API",
    "ParaNote": "网页段落评论服务 + 通用阅读器，与 Telegram 无关",
    "DAKit": "面向 Dart / Flutter 的模块化 DeviantArt 客户端 SDK",
    "DAViewer": "开源 DeviantArt 客户端，支持 Android / macOS / Windows",
    "DeviantDrop": "Telegram 机器人：发 DeviantArt 作品链接，回传原图/视频/GIF 并附原页面链接",
    "deviantart-downloader": "DeviantArt 批量下载器",
    "NekoTime": "支持自定义 GIF 主题的桌面悬浮猫娘时钟",
    "ludum": "引擎无关、零运行时依赖的 TypeScript 游戏系统库",
    "docsite": "零依赖 docsify 文档站脚手架",
    "use-bash": "让 AI 编程代理在 Windows 上默认用 bash 代替 PowerShell：一个 skill、一份 AGENTS.md",
}

DESC_EN = {
    "releasegraph": "Serverless, declarative DAG release orchestrator for multiple repos, built on GitHub Actions",
    "PixivFlow": "Pixiv downloader with filtering and auto-collection: batch downloads, scheduled tasks, reliable HTTP delivery",
    "pixivflow-webui": "Web frontend for PixivFlow",
    "pixivflow-telepost-deploy": "Deployment and ops toolkit for PixivFlow + TelePost",
    "pixiv-token-getter": "Pixiv API token library and CLI",
    "TelePost": "Telegram channel posting, review and automation platform",
    "TelePress": "Python library and CLI for publishing text, images and archives to Telegraph",
    "Graf": "Self-hosted Markdown publishing platform, Telegraph API compatible",
    "ParaNote": "Web paragraph commenting service and universal reader, Telegram-independent",
    "DAKit": "Modular DeviantArt client SDK for Dart / Flutter",
    "DAViewer": "Open-source DeviantArt client for Android / macOS / Windows",
    "DeviantDrop": "Telegram bot: send a DeviantArt link, get the original image/video/GIF back with the source page",
    "deviantart-downloader": "Bulk downloader for DeviantArt",
    "NekoTime": "Desktop floating catgirl clock with custom GIF themes",
    "ludum": "Engine-agnostic, zero-runtime-dependency TypeScript game systems library",
    "docsite": "Zero-dependency docsify docs site scaffold",
    "use-bash": "Make AI coding agents default to bash over PowerShell on Windows: one skill, one AGENTS.md",
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


def line(repo, lang):
    name = repo["name"]
    table = DESC if lang == "zh" else DESC_EN
    desc = table.get(name) or short(repo.get("description") or "")
    # 文档站地址严格用仓库名——Pages 路径区分大小写，写成 daKit 会 404。
    docs_label = "文档" if lang == "zh" else "Docs"
    docs = f"[{docs_label}](https://{USER}.github.io/{name}/)" if repo.get("has_pages") else ""
    return (
        f"| [**{DISPLAY_NAMES.get(name, name)}**]({repo['html_url']}) | {desc} | {docs} |"
    )


TABLE_HEAD = ["| Project | Description | Docs |", "| :-- | :-- | :-: |"]


def build(repos, lang):
    by_name = {r["name"]: r for r in repos if not r.get("fork") and r["name"] != USER}
    listed = [n for _, names in CATEGORIES for n in names]
    more_label = "更多项目" if lang == "zh" else "More projects"

    out = []
    for cat, names in CATEGORIES:
        label = cat if lang == "zh" else CAT_EN.get(cat, cat)
        rows = []
        for n in names:
            if n in by_name:
                rows.append(line(by_name[n], lang))
        if cat == "更多项目":
            for r in sorted(
                (r for r in by_name.values() if r["name"] not in listed),
                key=lambda x: -x["stargazers_count"],
            ):
                rows.append(line(r, lang))
        if rows:
            out.append(f"### {label}")
            out.append("")
            out.extend(TABLE_HEAD)
            out.extend(rows)
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def apply(path, marker_name, section):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    marker = re.compile(rf"<!-- {marker_name}_START -->.*?<!-- {marker_name}_END -->", re.S)
    new = f"<!-- {marker_name}_START -->\n" + section + f"<!-- {marker_name}_END -->"
    content, n = marker.subn(new, content, count=1)
    if n == 0:
        raise SystemExit(f"{marker_name} markers not found in {path}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def main():
    repos = list_repos()
    apply(README, "REPOS", build(repos, "zh"))
    apply(README_EN, "REPOS_EN", build(repos, "en"))
    print("updated repo lists (README.md, README.en.md)")


if __name__ == "__main__":
    main()
