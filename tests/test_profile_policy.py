import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.github' / 'scripts'))
from profile_policy import load_policy, selected
import gen_repos
import gen_stats


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"defaults": {"showcase": False, "stats": True, "notify": False},
                       "repositories": {"chosen": {"showcase": True}, "hidden": {"stats": False}}}

    def repo(self, name="new", **flags):
        return dict(name=name, private=False, fork=False, owner={"login": "redtidev1918"},
                    html_url="https://example.com/repo", stargazers_count=0, **flags)

    def test_defaults_and_overrides(self):
        self.assertFalse(selected(self.repo(), "showcase", self.policy, gen_repos.USER))
        self.assertTrue(selected(self.repo(), "stats", self.policy, gen_repos.USER))
        self.assertFalse(selected(self.repo(), "notify", self.policy, gen_repos.USER))
        self.assertTrue(selected(self.repo("CHOSEN"), "showcase", self.policy, gen_repos.USER))
        self.assertFalse(selected(self.repo("hidden"), "stats", self.policy, gen_repos.USER))

    def test_visibility_guards(self):
        for change in ({"private": True}, {"fork": True}, {"owner": {"login": "other"}},
                       {"name": gen_repos.USER}, {"private": None}):
            repo = self.repo("chosen")
            repo.update(change)
            for feature in ("showcase", "stats", "notify"):
                self.assertFalse(selected(repo, feature, self.policy, gen_repos.USER))

    def test_archived_notification(self):
        self.policy['defaults']['notify'] = True
        self.assertFalse(selected(self.repo(archived=True), 'notify', self.policy, gen_repos.USER))

    def test_bilingual_filter(self):
        for lang in ("zh", "en"):
            output = gen_repos.build([self.repo("chosen"), self.repo("new")], lang, self.policy)
            self.assertIn("**chosen**", output)
            self.assertNotIn("**new**", output)

    def test_validation(self):
        for invalid in ({}, {"defaults": {"showcase": "false", "stats": True, "notify": False}, "repositories": {}},
                        {"defaults": self.policy['defaults'], "repositories": {"A": {}, "a": {}}},
                        {"defaults": self.policy['defaults'], "repositories": {"A": {"typo": True}}}):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'config.json'
                path.write_text(json.dumps(invalid), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_policy(path)

    def test_real_config(self):
        self.assertFalse(load_policy()['defaults']['showcase'])

    def test_empty_stats(self):
        self.assertEqual(gen_stats.count_loc([]), 0)


if __name__ == '__main__':
    unittest.main()
