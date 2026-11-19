#!/usr/bin/env python3
"""Deploy Fabric items to the DEV workspace with fabric-cicd. Publish only: never unpublishes/deletes.

Required env: FABRIC_WORKSPACE_ID, FABRIC_ENV_NAME (must be 'dev'), AZURE_TENANT_ID, FABRIC_DEV_TENANT_ID.
Optional env: FABRIC_BLOCKED_WORKSPACE_IDS (comma list, e.g. client workspaces), FABRIC_ITEM_SCOPE.
Auth: AzureCliCredential (a prior azure/login OIDC step provides the az session).
Use --dry-run to run every guard and print the plan without calling Fabric.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_fabric_items as vfi  # noqa: E402

DEFAULT_SCOPE = "SemanticModel,Report,Notebook"


def guards(env: dict[str, str]) -> list[str]:
    problems = []
    if env.get("FABRIC_ENV_NAME") != "dev":
        problems.append("FABRIC_ENV_NAME must be 'dev'; this script deploys DEV only")
    ws = env.get("FABRIC_WORKSPACE_ID", "")
    if not ws:
        problems.append("FABRIC_WORKSPACE_ID is not set")
    blocked = {b.strip().lower() for b in env.get("FABRIC_BLOCKED_WORKSPACE_IDS", "").split(",") if b.strip()}
    if ws.lower() in blocked:
        problems.append("FABRIC_WORKSPACE_ID is on the blocked list (client workspace)")
    expected_tenant = env.get("FABRIC_DEV_TENANT_ID", "")
    if not expected_tenant or env.get("AZURE_TENANT_ID", "") != expected_tenant:
        problems.append("AZURE_TENANT_ID does not match FABRIC_DEV_TENANT_ID (wrong tenant; refusing to deploy)")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("items_dir")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    env = dict(os.environ)
    problems = guards(env)
    res = vfi.validate(Path(args.items_dir))
    problems += [f"{p}: {m}" for p, m in res.errors]
    if problems:
        for p in problems:
            print(f"::error::{p}")
        return 1
    scope = [s.strip() for s in env.get("FABRIC_ITEM_SCOPE", DEFAULT_SCOPE).split(",") if s.strip()]
    ws = env["FABRIC_WORKSPACE_ID"]
    print(f"Target workspace id: {ws} (env=dev)\nItem types in scope: {', '.join(scope)}")
    for t, n, p in res.items:
        print(f"  {'DEPLOY' if t in scope else 'skip  '} {t}/{n}")
    if args.dry_run:
        print("Dry run: guards passed, nothing sent to Fabric.")
        return 0
    from azure.identity import AzureCliCredential  # type: ignore
    from fabric_cicd import FabricWorkspace, publish_all_items  # type: ignore

    target = FabricWorkspace(
        workspace_id=ws,
        environment="dev",
        repository_directory=args.items_dir,
        item_type_in_scope=scope,
        token_credential=AzureCliCredential(),
    )
    publish_all_items(target)
    print("Publish complete (no items were unpublished or deleted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))