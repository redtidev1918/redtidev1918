#!/usr/bin/env python3
"""Auto-generate the project list in README.md from the GitHub API.

New repos show up automatically (under "其他"); star counts refresh on every run.
Only the section between <!-- REPOS_START --> and <!-- REPOS_END --> is touched.
"""
import json
import os
import re
import urllib.request

USER = "redtidev1918"
README = "README.md"

# 分类（按顺序渲染）。不在任何分类里的新仓库会自动并到「其他」。
CATEGORIES = [
    ("Pixiv", ["PixivFlow", "pixivflow-webui", "pixivflow-telepost-deploy", "pixiv-token-getter"]),
    ("Telegram / Telegraph", ["TelePost", "telepress", "graf"]),
    ("DeviantArt", ["daviewer", "deviantart-downloader", "dakit", "deviantdrop"]),
    ("其他", ["NekoTime", "ludum", "paranote"]),
]

# 一句话描述。没写到的仓库回退用 repo 自带 description。
DESC = {
    "PixivFlow": "Pixiv 自动下载",
    "pixivflow-webui": "PixivFlow 的 React 前端",
    "pixivflow-telepost-deploy": "PixivFlow + TelePost 部署套件（Go 单二进制 deploy CLI，Docker / Fly / 裸机 VPS，多 Bot + 低成本拆分）",
    "pixiv-token-getter": "取 Pixiv token 的库和命令行",
    "TelePost": "Telegram 频道投稿机器人，带搜索、统计、标签",
    "telepress": "往 Telegraph 发文章和图的 Python 库，`pip install telepress`",
    "graf": "自托管极简 Markdown 发布平台，兼容 Telegraph API，跑在 Cloudflare Workers + D1；附 grafctl 零依赖跨平台部署器",
    "daviewer": "开源 DeviantArt 客户端，Flutter 写的，Android / macOS / Windows",
    "deviantart-downloader": "DeviantArt 批量下载",
    "dakit": "DeviantArt 的 Dart / Flutter SDK，附带 dakit 跨平台命令行",
    "deviantdrop": "Telegram Bot，发 DeviantArt 作品链接，回图片/视频/GIF",
    "NekoTime": "桌面悬浮猫娘时钟，支持自定义 GIF 主题",
    "ludum": "引擎无关、零运行时依赖的 TypeScript 游戏系统库（ECS / 资源 / 状态机 / 对话 / 加权随机 / 几何 / 交互），已发布 npm",
    "paranote": "给网页加段落评论，顺带当阅读器",
}

# 只有真正的文档站才放进「文档」列；repo homepage 没有链接类型信息。
DOCS = {
    name: f"https://redtidev1918.github.io/{name}/"
    for name in (
        "PixivFlow",
        "pixivflow-webui",
        "pixivflow-telepost-deploy",
        "pixiv-token-getter",
        "TelePost",
        "telepress",
        "graf",
        "daviewer",
        "deviantart-downloader",
        "dakit",
        "deviantdrop",
        "NekoTime",
        "ludum",
        "paranote",
    )
}


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
    stars = repo["stargazers_count"]
    desc = DESC.get(name) or short(repo.get("description") or "")
    doc = f"[文档]({DOCS[name]})" if name in DOCS else "—"
    return f"| [{name}]({repo['html_url']}) | {stars} | {desc} | {doc} |"


TABLE_HEAD = ["| 项目 | ⭐ | 说明 | 文档 |", "| :--- | :-: | :--- | :--- |"]


def build(repos):
    by_name = {r["name"]: r for r in repos if not r.get("fork") and r["name"] != USER}
    listed = [n for _, names in CATEGORIES for n in names]

    out = []
    for cat, names in CATEGORIES:
        rows = []
        for n in names:
            if n in by_name:
                rows.append(line(by_name[n]))
        if cat == "其他":
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
