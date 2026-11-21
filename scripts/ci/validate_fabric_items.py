#!/usr/bin/env python3
"""Offline validation of Fabric Git-format item folders (no workspace, no credentials).

Checks what can be proven from files alone: .platform metadata, item type, logicalId
uniqueness, JSON well-formedness, local report->model references, parameter.yml and
config.yml shape (fabric-cicd), and obvious embedded credentials.

Usage: validate_fabric_items.py ITEMS_DIR [--summary-file FILE] [--allowed-workspace-id GUID]
Exit 0 = pass, 1 = errors found, 2 = bad invocation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Item types accepted by fabric-cicd (names as in its constants.ACCEPTED_ITEM_TYPES, v-checked 2026-11).
# Re-check against https://microsoft.github.io/fabric-cicd/latest/ when upgrading fabric-cicd.
SUPPORTED_TYPES = {
    "ApacheAirflowJob", "CopyJob", "DataAgent", "DataBuildToolJob", "DataPipeline", "Dataflow",
    "Environment", "Eventhouse", "Eventstream", "GraphQLApi", "KQLDashboard", "KQLDatabase",
    "KQLQueryset", "Lakehouse", "MLExperiment", "Map", "MirroredDatabase", "MountedDataFactory",
    "Notebook", "Ontology", "PaginatedReport", "Reflex", "Report", "SQLDatabase", "SemanticModel",
    "SparkJobDefinition", "UserDataFunction", "VariableLibrary", "Warehouse",
}
PARAMETER_KEYS = {"find_replace", "key_value_replace", "spark_pool", "semantic_model_binding", "extend"}
GUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
SECRET_PATTERNS = [
    re.compile(r"AccountKey=[A-Za-z0-9+/=]{20,}"),
    re.compile(r"SharedAccessSignature=", re.I),
    re.compile(r"(?i)\bpassword\s*=\s*[^;\s\"']{4,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
SKIP_DIRS = {".git", ".pbi", "StaticResources", "__pycache__"}
# The ONLY workspace this workflow may reference: Steve's free-trial Grid Pulse workspace.
# Allowlist (not blocklist) so no other workspace id, client or otherwise, is ever named in the repo.
DEFAULT_ALLOWED_WORKSPACE_ID = "54634e0b-7658-49fa-8441-0ba7bc594ada"
WORKSPACE_KEY = re.compile(r"(?i)workspace_?id[\"']?\s*[:=]\s*[\"']?([0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12})")
ONELAKE_PATH = re.compile(r"(?i)onelake\.[a-z.]*fabric\.microsoft\.com/([0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12})/")


class Result:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.items: list[tuple[str, str, str]] = []  # (type, displayName, path)

    def error(self, path: Path | str, msg: str) -> None:
        self.errors.append((str(path), msg))

    def warn(self, path: Path | str, msg: str) -> None:
        self.warnings.append((str(path), msg))


def load_json(path: Path, res: Result):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        res.error(path, f"invalid JSON: {exc}")
        return None


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS):
            yield p


def check_item(item_dir: Path, res: Result, seen_ids: dict, seen_names: dict, allowed_ws: str = DEFAULT_ALLOWED_WORKSPACE_ID) -> None:
    platform = item_dir / ".platform"
    data = load_json(platform, res)
    if not isinstance(data, dict):
        return
    meta = data.get("metadata") or {}
    item_type, name = meta.get("type"), meta.get("displayName")
    if not item_type or not name:
        res.error(platform, "metadata.type and metadata.displayName are required")
        return
    if item_type not in SUPPORTED_TYPES:
        res.error(platform, f"item type {item_type!r} is not a fabric-cicd supported type")
    expected = f"{name}.{item_type}"
    if item_dir.name != expected:
        res.warn(platform, f"folder is {item_dir.name!r}; Git-format convention is {expected!r}")
    logical = (data.get("config") or {}).get("logicalId")
    if not logical or not GUID.match(str(logical)):
        res.error(platform, "config.logicalId must be a GUID")
    elif logical in seen_ids:
        res.error(platform, f"duplicate logicalId also used by {seen_ids[logical]}")
    else:
        seen_ids[logical] = str(item_dir)
    key = (item_type, name)
    if key in seen_names:
        res.error(platform, f"duplicate item {item_type}/{name} also at {seen_names[key]}")
    seen_names[key] = str(item_dir)
    res.items.append((item_type, name, str(item_dir)))

    for f in iter_files(item_dir):
        if f.suffix.lower() in {".json", ".pbir", ".pbism", ".platform"}:
            load_json(f, res)
        if f.suffix.lower() in {".json", ".pbir", ".tmdl", ".py", ".sql", ".ipynb", ".yml", ".yaml", ".dax", ".m"}:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat in SECRET_PATTERNS:
                if pat.search(text):
                    res.error(f, "possible embedded credential (value not shown)")
                    break
            check_workspace_ids(f, text, res, allowed_ws)

    if item_type == "Report":
        pbir = item_dir / "definition.pbir"
        if not pbir.exists():
            res.error(item_dir, "Report has no definition.pbir")
        else:
            ref = (load_json(pbir, res) or {}).get("datasetReference") or {}
            if "byPath" in ref:
                target = (item_dir / ref["byPath"].get("path", "")).resolve()
                if not target.exists():
                    res.error(pbir, f"byPath semantic model not found: {ref['byPath'].get('path')}")
            elif "byConnection" in ref:
                res.warn(pbir, "report is bound by connection to a live semantic model id; a deploy needs parameter.yml "
                               "find_replace (or a byPath model in the repo) or it will point at the original model")


def check_workspace_ids(path: Path, text: str, res: Result, allowed_ws: str) -> None:
    """Any workspace id found must equal the allowed free-trial id (value not echoed)."""
    for pat in (WORKSPACE_KEY, ONELAKE_PATH):
        for m in pat.finditer(text):
            if m.group(1).lower() != allowed_ws.lower():
                res.error(path, "workspace id is not the allowed free-trial workspace (value not shown)")
                return


def check_yaml_files(root: Path, res: Result, allowed_ws: str = DEFAULT_ALLOWED_WORKSPACE_ID) -> None:
    try:
        import yaml  # type: ignore
    except ImportError:
        # Validation never skips silently: a missing dependency is a failure that names the piece.
        res.error(root, "PyYAML is not installed (pip install pyyaml); parameter.yml/config.yml cannot be checked")
        return
    param = root / "parameter.yml"
    if param.exists():
        try:
            doc = yaml.safe_load(param.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            res.error(param, f"invalid YAML: {exc}")
            doc = {}
        if not isinstance(doc, dict):
            res.error(param, "top level must be a mapping")
        else:
            for k in doc:
                if k not in PARAMETER_KEYS:
                    res.error(param, f"unknown top-level key {k!r} (allowed: {sorted(PARAMETER_KEYS)})")
            for i, entry in enumerate(doc.get("find_replace") or []):
                if not isinstance(entry, dict) or "find_value" not in entry or "replace_value" not in entry:
                    res.error(param, f"find_replace[{i}] needs find_value and replace_value")
                    continue
                targets = entry["replace_value"]
                if any("$workspace.$id" in str(v) for v in (targets.values() if isinstance(targets, dict) else [targets])):
                    if str(entry["find_value"]).lower() != allowed_ws.lower():
                        res.error(param, f"find_replace[{i}] maps a workspace id that is not the allowed free-trial workspace")
    cfg = root / "config.yml"
    if cfg.exists():
        try:
            doc = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            res.error(cfg, f"invalid YAML: {exc}")
            return
        core = (doc.get("core") or {}) if isinstance(doc, dict) else {}
        if not ("workspace" in core or "workspace_id" in core) or "repository_directory" not in core:
            res.error(cfg, "core needs workspace or workspace_id, plus repository_directory")


def validate(root: Path, allowed_ws: str = DEFAULT_ALLOWED_WORKSPACE_ID) -> Result:
    res = Result()
    if not root.is_dir():
        res.error(root, "items directory does not exist")
        return res
    item_dirs = sorted(p.parent for p in root.rglob(".platform") if not (set(p.relative_to(root).parts) & SKIP_DIRS))
    if not item_dirs:
        res.error(root, "no .platform item folders found; nothing to validate")
        return res
    seen_ids: dict = {}
    seen_names: dict = {}
    for d in item_dirs:
        check_item(d, res, seen_ids, seen_names, allowed_ws)
    check_yaml_files(root, res, allowed_ws)
    return res


def render(res: Result, root: Path) -> str:
    lines = [f"### Fabric item validation: {'FAILED' if res.errors else 'passed'}", "",
             f"Directory: {root}  |  items: {len(res.items)}  |  errors: {len(res.errors)}  |  warnings: {len(res.warnings)}", ""]
    if res.items:
        lines += ["| Type | Name |", "|---|---|"] + [f"| {t} | {n} |" for t, n, _ in res.items] + [""]
    lines += [f"- ERROR {p}: {m}" for p, m in res.errors] + [f"- WARN {p}: {m}" for p, m in res.warnings]
    lines += ["", "Not checked offline (needs a live workspace): item creation/update, parameter.yml replacement against real",
              "item ids, connection binding, permissions, Lakehouse/MLV state. See .github/CICD.md."]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("items_dir")
    ap.add_argument("--summary-file")
    ap.add_argument("--allowed-workspace-id", default=DEFAULT_ALLOWED_WORKSPACE_ID)
    args = ap.parse_args(argv)
    root = Path(args.items_dir)
    res = validate(root, args.allowed_workspace_id)
    text = render(res, root)
    print(text)
    for p, m in res.errors:
        print(f"::error file={p}::{m}")
    for p, m in res.warnings:
        print(f"::warning file={p}::{m}")
    if args.summary_file:
        with open(args.summary_file, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 1 if res.errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))