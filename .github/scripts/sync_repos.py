#!/usr/bin/env python3
"""Keep every non-fork repo wired to the profile README.

For each repo: ensure .github/workflows/notify-profile.yml exists (create/update it)
and the PROFILE_REPO_TOKEN secret is set. New repos get wired automatically.

Runs in the profile repo's workflow. Needs SYNC_TOKEN (a PAT with repo scope).
Uses the gh CLI (pre-installed on the runner) so secret encryption is handled for us.
"""
import base64
import os
import subprocess

USER = "redtidev1918"
TOKEN = os.environ["SYNC_TOKEN"]
SECRET = "PROFILE_REPO_TOKEN"
WF_PATH = ".github/workflows/notify-profile.yml"

TEMPLATE = """name: notify-profile

on:
  push:
    branches: [__BRANCH__]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Ping profile repo
        env:
          PROFILE_REPO_TOKEN: ${{ secrets.PROFILE_REPO_TOKEN }}
        run: |
          curl -sS -X POST \\
            -H "Authorization: token $PROFILE_REPO_TOKEN" \\
            -H "Accept: application/vnd.github+json" \\
            -H "X-GitHub-Api-Version: 2022-11-28" \\
            -d '{"event_type":"update-readme"}' \\
            https://api.github.com/repos/redtidev1918/redtidev1918/dispatches || echo "notify skipped"
"""


def gh(*args, input=None):
    env = dict(os.environ, GH_TOKEN=TOKEN)
    return subprocess.run(["gh", *args], input=input, env=env,
                          capture_output=True, text=True)


def list_repos():
    r = gh("api", f"users/{USER}/repos?per_page=100&type=owner",
           "--jq", ".[] | select(.fork==false) | [.name,.default_branch] | @tsv")
    repos = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[0] != USER:
            repos.append((parts[0], parts[1]))
    return repos


def ensure_workflow(name, branch):
    wf = TEMPLATE.replace("__BRANCH__", branch)
    b64 = base64.b64encode(wf.encode()).decode()

    r = gh("api", f"repos/{USER}/{name}/contents/{WF_PATH}", "--jq", ".sha")
    sha = r.stdout.strip() if r.returncode == 0 else ""

    if sha:
        r2 = gh("api", f"repos/{USER}/{name}/contents/{WF_PATH}", "--jq", ".content")
        if r2.returncode == 0:
            existing = base64.b64decode(r2.stdout.strip()).decode()
            if existing == wf:
                return "ok"
        gh("api", "-X", "PUT", f"repos/{USER}/{name}/contents/{WF_PATH}",
           "-f", "message=auto: wire notify-profile", "-f", f"content={b64}",
           "-f", f"branch={branch}", "-f", f"sha={sha}")
        return "updated"
    gh("api", "-X", "PUT", f"repos/{USER}/{name}/contents/{WF_PATH}",
       "-f", "message=auto: wire notify-profile", "-f", f"content={b64}",
       "-f", f"branch={branch}")
    return "created"


def ensure_secret(name):
    r = gh("secret", "list", "--repo", f"{USER}/{name}")
    if SECRET in r.stdout:
        return "ok"
    r2 = gh("secret", "set", SECRET, "--repo", f"{USER}/{name}", input=TOKEN)
    return "set" if r2.returncode == 0 else "fail"


def main():
    for name, branch in list_repos():
        w = ensure_workflow(name, branch)
        s = ensure_secret(name)
        print(f"{name}: workflow={w} secret={s}")


if __name__ == "__main__":
    main()
