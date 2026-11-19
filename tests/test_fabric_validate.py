import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "vfi", Path(__file__).resolve().parents[1] / "scripts" / "ci" / "validate_fabric_items.py")
vfi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vfi)
DEPLOY = importlib.util.spec_from_file_location(
    "fd", Path(__file__).resolve().parents[1] / "scripts" / "ci" / "fabric_deploy.py")


def make_item(root: Path, name: str, typ: str, logical: str, extra=None):
    d = root / f"{name}.{typ}"
    d.mkdir(parents=True)
    (d / ".platform").write_text(json.dumps(
        {"metadata": {"type": typ, "displayName": name}, "config": {"version": "2.0", "logicalId": logical}}))
    for fname, body in (extra or {}).items():
        (d / fname).write_text(body)
    return d


G1 = "9e35bd07-fa9e-456d-8c3c-ea845aa06272"
G2 = "11111111-2222-3333-4444-555555555555"


class FabricValidateTests(unittest.TestCase):
    def run_v(self, build):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            build(root)
            return vfi.validate(root)

    def test_valid_report_passes(self):
        res = self.run_v(lambda r: make_item(r, "Dash", "Report", G1, {"definition.pbir": json.dumps({"version": "4.0"})}))
        self.assertEqual(res.errors, [])

    def test_empty_dir_fails(self):
        self.assertTrue(self.run_v(lambda r: None).errors)

    def test_missing_dir_fails(self):
        self.assertTrue(vfi.validate(Path("/nonexistent-dir-xyz")).errors)

    def test_bad_json_fails(self):
        res = self.run_v(lambda r: make_item(r, "Dash", "Report", G1, {"definition.pbir": "{not json"}))
        self.assertTrue(any("invalid JSON" in m for _, m in res.errors))

    def test_duplicate_logical_id_fails(self):
        def build(r):
            make_item(r, "A", "Notebook", G1)
            make_item(r, "B", "Notebook", G1)
        self.assertTrue(any("duplicate logicalId" in m for _, m in self.run_v(build).errors))

    def test_unsupported_type_fails(self):
        self.assertTrue(self.run_v(lambda r: make_item(r, "X", "NotAType", G2)).errors)

    def test_embedded_credential_fails(self):
        res = self.run_v(lambda r: make_item(r, "NB", "Notebook", G2, {"nb.py": "conn='Password=hunter22xyz'"}))
        self.assertTrue(any("credential" in m for _, m in res.errors))

    def test_deploy_guards(self):
        spec = DEPLOY
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ok = {"FABRIC_ENV_NAME": "dev", "FABRIC_WORKSPACE_ID": "w1", "AZURE_TENANT_ID": "t", "FABRIC_DEV_TENANT_ID": "t"}
        self.assertEqual(mod.guards(ok), [])
        self.assertTrue(mod.guards({**ok, "FABRIC_ENV_NAME": "prod"}))
        self.assertTrue(mod.guards({**ok, "FABRIC_BLOCKED_WORKSPACE_IDS": "W1"}))
        self.assertTrue(mod.guards({**ok, "AZURE_TENANT_ID": "other"}))


if __name__ == "__main__":
    unittest.main()