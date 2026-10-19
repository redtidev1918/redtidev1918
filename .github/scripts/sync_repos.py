#!/usr/bin/env python3
"""Explicitly wire opted-in public repositories to the profile README.

For each repo: ensure .github/workflows/notify-profile.yml exists (create/update it)
and the PROFILE_REPO_TOKEN secret is set. Disabled repos are not modified.

Runs in the profile repo's workflow. Needs SYNC_TOKEN (a PAT with repo scope).
Uses the gh CLI (pre-installed on the runner) so secret encryption is handled for us.
"""
import base64
import os
import subprocess
import json
from profile_policy import load_policy, selected

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
    policy = load_policy()
    r = gh("api", f"users/{USER}/repos?per_page=100&type=owner", "--paginate", "--slurp")
    if r.returncode:
        raise RuntimeError("Unable to list repositories: " + r.stderr)
    repos = []
    for page in json.loads(r.stdout):
        for repo in page:
            if selected(repo, "notify", policy, USER):
                repos.append((repo["name"], repo["default_branch"]))
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
        result = gh("api", "-X", "PUT", f"repos/{USER}/{name}/contents/{WF_PATH}",
           "-f", "message=auto: wire notify-profile", "-f", f"content={b64}",
           "-f", f"branch={branch}", "-f", f"sha={sha}")
        if result.returncode:
            raise RuntimeError(f"Cannot update notification workflow for {name}")
        return "updated"
    result = gh("api", "-X", "PUT", f"repos/{USER}/{name}/contents/{WF_PATH}",
       "-f", "message=auto: wire notify-profile", "-f", f"content={b64}",
       "-f", f"branch={branch}")
    if result.returncode:
        raise RuntimeError(f"Cannot create notification workflow for {name}")
    return "created"


def ensure_secret(name):
    r = gh("secret", "list", "--repo", f"{USER}/{name}")
    if r.returncode:
        raise RuntimeError(f"Cannot inspect notification secret for {name}")
    if SECRET in r.stdout:
        return "ok"
    r2 = gh("secret", "set", SECRET, "--repo", f"{USER}/{name}", input=TOKEN)
    if r2.returncode:
        raise RuntimeError(f"Cannot set notification secret for {name}")
    return "set"


def main():
    for name, branch in list_repos():
        w = ensure_workflow(name, branch)
        s = ensure_secret(name)
        print(f"{name}: workflow={w} secret={s}")


if __name__ == "__main__":
    main()
