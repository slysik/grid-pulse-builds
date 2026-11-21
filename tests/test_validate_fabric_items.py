import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vfi", ROOT / "scripts" / "ci" / "validate_fabric_items.py")
vfi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vfi)

OK_WS = vfi.DEFAULT_ALLOWED_WORKSPACE_ID
OTHER_WS = "11111111-2222-3333-4444-555555555555"
G1 = "9e35bd07-fa9e-456d-8c3c-ea845aa06272"
G2 = "a58b414a-4712-49c7-9881-cc440ed7f0c9"


def make_item(root: Path, name: str, typ: str, logical: str, files=None):
    d = root / f"{name}.{typ}"
    d.mkdir(parents=True)
    (d / ".platform").write_text(json.dumps(
        {"metadata": {"type": typ, "displayName": name}, "config": {"version": "2.0", "logicalId": logical}}))
    for fname, body in (files or {}).items():
        (d / fname).write_text(body)
    return d


class ValidatorTests(unittest.TestCase):
    def run_v(self, build):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            build(root)
            return vfi.validate(root)

    def test_V1_real_items_pass(self):
        res = vfi.validate(ROOT / "fabric" / "grid-pulse")
        self.assertEqual(res.errors, [])
        self.assertGreaterEqual(len(res.items), 3)

    def test_V1_cli_exit_zero_on_real_items(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts/ci/validate_fabric_items.py"), str(ROOT / "fabric/grid-pulse")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_V2_empty_dir_fails(self):
        self.assertTrue(self.run_v(lambda r: None).errors)

    def test_V2_missing_dir_fails(self):
        self.assertTrue(vfi.validate(Path("/nonexistent/items")).errors)

    def test_V2_missing_platform_metadata_fails(self):
        def build(r):
            d = r / "x.Notebook"
            d.mkdir()
            (d / ".platform").write_text(json.dumps({"metadata": {}}))
        self.assertTrue(self.run_v(build).errors)

    def test_V2_duplicate_logical_id_fails(self):
        def build(r):
            make_item(r, "a", "Notebook", G1)
            make_item(r, "b", "Notebook", G1)
        self.assertTrue(any("duplicate logicalId" in m for _, m in self.run_v(build).errors))

    def test_V2_invalid_json_fails(self):
        res = self.run_v(lambda r: make_item(r, "a", "Report", G1, {"definition.pbir": "{not json"}))
        self.assertTrue(any("invalid JSON" in m for _, m in res.errors))

    def test_V2_unsupported_type_fails(self):
        self.assertTrue(self.run_v(lambda r: make_item(r, "a", "NotAThing", G1)).errors)

    def test_V3_other_workspace_in_notebook_meta_fails(self):
        body = '# META   "default_lakehouse_workspace_id": "%s"\n' % OTHER_WS
        res = self.run_v(lambda r: make_item(r, "n", "Notebook", G1, {"notebook-content.py": body}))
        self.assertTrue(any("allowed free-trial workspace" in m for _, m in res.errors))
        self.assertNotIn(OTHER_WS, "".join(m for _, m in res.errors))  # value never echoed

    def test_V3_allowed_workspace_passes(self):
        body = '# META   "default_lakehouse_workspace_id": "%s"\n' % OK_WS
        res = self.run_v(lambda r: make_item(r, "n", "Notebook", G1, {"notebook-content.py": body}))
        self.assertEqual(res.errors, [])

    def test_V3_onelake_path_other_workspace_fails(self):
        body = 'source = "https://onelake.dfs.fabric.microsoft.com/%s/%s"' % (OTHER_WS, G2)
        res = self.run_v(lambda r: make_item(r, "m", "SemanticModel", G1, {"expressions.tmdl": body}))
        self.assertTrue(res.errors)

    def test_V3_parameter_yml_other_workspace_fails(self):
        def build(r):
            make_item(r, "n", "Notebook", G1)
            (r / "parameter.yml").write_text(
                'find_replace:\n  - find_value: "%s"\n    replace_value:\n      dev: "$workspace.$id"\n' % OTHER_WS)
        self.assertTrue(any("allowed free-trial workspace" in m for _, m in self.run_v(build).errors))

    def test_V4_secret_pattern_fails(self):
        body = "conn = 'AccountKey=" + "A" * 30 + "'"
        res = self.run_v(lambda r: make_item(r, "n", "Notebook", G1, {"notebook-content.py": body}))
        self.assertTrue(any("credential" in m for _, m in res.errors))

    def test_missing_pyyaml_is_error_not_skip(self):
        saved = sys.modules.get("yaml")
        sys.modules["yaml"] = None  # makes "import yaml" raise ImportError
        try:
            res = self.run_v(lambda r: make_item(r, "n", "Notebook", G1))
        finally:
            if saved is not None:
                sys.modules["yaml"] = saved
            else:
                del sys.modules["yaml"]
        self.assertTrue(any("PyYAML" in m for _, m in res.errors))


if __name__ == "__main__":
    unittest.main()
