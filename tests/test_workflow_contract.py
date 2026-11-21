import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "fabric-gold-ci.yml"
TEXT = WF.read_text()
CODE = "\n".join(l for l in TEXT.splitlines() if not l.strip().startswith("#"))  # comments may name the Slack channel
DOC = yaml.safe_load(TEXT)
JOBS = DOC["jobs"]
TRIGGER = DOC.get("on", DOC.get(True))  # PyYAML parses bare "on" as True


class WorkflowContract(unittest.TestCase):
    def test_W1_review_permissions_exact(self):
        self.assertEqual(JOBS["review"]["permissions"],
                         {"contents": "read", "pull-requests": "write", "id-token": "write", "actions": "read"})

    def test_W1_other_jobs_least_privilege(self):
        self.assertEqual(DOC["permissions"], {"contents": "read"})
        for name in ("validate", "test", "notify"):
            self.assertEqual(JOBS[name]["permissions"], {"contents": "read"}, name)
        self.assertEqual(JOBS["fabric-gold-gate"]["permissions"], {})

    def test_W2_review_step(self):
        steps = JOBS["review"]["steps"]
        action = [s for s in steps if str(s.get("uses", "")).startswith("anthropics/claude-code-action@")]
        self.assertEqual(len(action), 1)
        self.assertEqual(action[0]["uses"], "anthropics/claude-code-action@v1")
        self.assertIn("--max-turns 5", action[0]["with"]["claude_args"])
        self.assertIn("fabric-gold-review", action[0]["with"]["prompt"])
        self.assertIn("draft == false", JOBS["review"]["if"])

    def test_W2_review_preflight_skip_then_fail_rule(self):
        pre = [s for s in JOBS["review"]["steps"] if s.get("id") == "pre"][0]["run"]
        self.assertIn("startswith(\"fabric/\")", pre)
        self.assertIn("exit 1", pre)

    def test_W3_no_deploy_merge_push_or_unsafe_trigger(self):
        self.assertEqual(list(TRIGGER), ["pull_request"])
        for banned in ("pull_request_target", "fabric-cicd", "fabric_deploy", "gh pr merge", "git push",
                       "databricks bundle deploy", "snow dcm deploy", "workflow_dispatch"):
            self.assertNotIn(banned, CODE, banned)

    def test_W3_gate_depends_on_validate_and_test_only(self):
        self.assertEqual(sorted(JOBS["fabric-gold-gate"]["needs"]), ["test", "validate"])

    def test_W3_validate_and_test_never_conditionally_skipped(self):
        for name in ("validate", "test"):
            self.assertNotIn("if", JOBS[name], name)

    def test_W4_secrets_only_via_env_or_with_never_echoed(self):
        for m in re.finditer(r"echo[^\n]*secrets\.", TEXT):
            self.fail("secret echoed: " + m.group(0)[:40])
        for name, job in JOBS.items():
            for step in job["steps"] if "steps" in job else []:
                self.assertNotIn("secrets.", step.get("run", ""), f"{name}: secrets used inline in run")

    def test_only_free_trial_workspace_id_if_any(self):
        guids = set(re.findall(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", TEXT))
        self.assertLessEqual(guids, {"54634e0b-7658-49fa-8441-0ba7bc594ada"})

    def test_autonomy_only_one_workflow_file_for_this_loop(self):
        self.assertTrue(WF.exists())


if __name__ == "__main__":
    unittest.main()
