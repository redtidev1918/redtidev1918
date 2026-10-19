"""Shared, fail-closed repository selection for profile automation."""
import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / "profile-config.json"
FEATURES = {"showcase", "stats", "notify"}


def load_policy(path=CONFIG):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"defaults", "repositories"}:
        raise ValueError("Config must contain defaults and repositories only")
    defaults, repositories = data["defaults"], data["repositories"]
    if not isinstance(defaults, dict) or set(defaults) != FEATURES:
        raise ValueError("defaults must define showcase, stats and notify")
    if not isinstance(repositories, dict):
        raise ValueError("repositories must be an object")
    normalized = {}
    for name, flags in repositories.items():
        if not name or "/" in name or name.casefold() in normalized:
            raise ValueError("Invalid or duplicate repository name: " + name)
        normalized[name.casefold()] = flags
    for flags in [defaults, *normalized.values()]:
        if not isinstance(flags, dict) or set(flags) - FEATURES:
            raise ValueError("Unknown repository policy field")
        if any(type(value) is not bool for value in flags.values()):
            raise ValueError("Policy values must be true or false")
    return {"defaults": defaults, "repositories": normalized}


def selected(repo, feature, policy, owner):
    if feature not in FEATURES:
        raise ValueError("Unknown feature: " + feature)
    # A missing visibility/owner field must not accidentally publish a repository.
    if repo.get("private") is not False or repo.get("fork") is not False:
        return False
    if repo.get("owner", {}).get("login", "").casefold() != owner.casefold():
        return False
    name = repo.get("name", "")
    if not name or name.casefold() == owner.casefold():
        return False
    if feature == "notify" and (repo.get("archived") or repo.get("disabled")):
        return False
    overrides = policy["repositories"].get(name.casefold(), {})
    return overrides.get(feature, policy["defaults"][feature])
