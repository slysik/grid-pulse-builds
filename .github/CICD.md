# CI/CD for Grid Pulse on Databricks, Snowflake and Fabric

> Adapted from open-skills PR #12 for this repo: bundle at databricks/, DCM project at snowflake/, Fabric items at fabric/grid-pulse/. Secrets and approvals are not created yet; everything below the checklist is still to be provided by the owner.

GitHub Actions is the engine. Phase 1 (checks) and Phase 2 (deploy to DEV) are in place but **inert until you switch them on**. Phase 3 is design only: [CICD-phase3-design.md](CICD-phase3-design.md).
The existing workflow [ci.yml](workflows/ci.yml) (just check, just validate, tests, packaging) is untouched. Nothing here changes a validator rule or the 150-line router cap.

## Files

| File | Phase | Does |
|---|---|---|
| workflows/platform-ci.yml | 1 | On PRs to main: per-platform read-only check, plus one required gate job (platform-ci-gate) |
| workflows/cd-databricks-dev.yml | 2 | On main push: bundle validate, then bundle deploy -t dev |
| workflows/cd-snowflake-dev.yml | 2 | On main push: snow dcm plan, then snow dcm deploy --target GRIDPULSE_DEV |
| workflows/cd-fabric-dev.yml | 2 | On main push: offline validation, guards, then fabric-cicd publish to the dev workspace |
| ../scripts/ci/validate_fabric_items.py | 1 | Offline checks on Fabric item folders (no credentials) |
| ../scripts/ci/fabric_deploy.py | 2 | Guarded publish-only deploy (dev tenant, dev workspace, blocklist, dry run) |
| ../tests/test_fabric_validate.py | 1 | Unit tests for both scripts, run by the existing ci.yml |

## How it flows

~~~
PR to main
  ci.yml (existing)  : just check, just validate, tests, package
  platform-ci.yml    : changes -> databricks | snowflake | fabric -> platform-ci-gate   (read-only, no deploy)
merge to main (a human reviewed and merged)
  cd-<platform>-dev.yml, only if its path changed
    -> job skipped unless repo variable CICD_ENABLE_CD_<PLATFORM> = 'true'
    -> then waits for the required reviewer on the <platform>-dev environment
    -> deploys DEV only; prints what, where, and how to roll back
~~~

Two locks on every deploy: the repo variable switch, and the environment approval. Production is not referenced anywhere.

## Phase 1: what each check does

- **Databricks:** databricks bundle validate --strict -t dev in databricks. Auth is GitHub OIDC (no stored token).
- **Snowflake:** snow dcm plan --target GRIDPULSE_DEV --save-output in snowflake. Read-only. Key-pair auth.
- **Fabric (offline, no credentials):** .platform metadata and item type, logicalId uniqueness, JSON well-formed, report byPath target exists, parameter.yml and config.yml shape, embedded-credential patterns.
  - Needs a live workspace (not checked): that items create or update, parameter.yml replacement against real item ids, connection binding, permissions, Lakehouse and Materialized Lake View state.
- Each job fails with an ::error annotation and a step summary, and passes with a short summary. A job whose folder or credentials are missing is **skipped with a warning**, not failed, so the pipeline can land before the artifacts do. Remove that leniency once the artifacts exist if you want missing-credentials to fail.
- Make **platform-ci-gate** the required check in branch protection. Per-platform jobs are skipped when their paths are untouched, so do not require them directly.

## What is NOT in the repo yet (verified 2026-11-19)

Workflows point at these paths; none exist on main:

| Platform | Expected path | What I found |
|---|---|---|
| Databricks | databricks/databricks.yml | No Grid Pulse bundle anywhere on this machine. Only synaptiq and EDA bundles exist (exercise-1, exercise-2). |
| Snowflake | snowflake/manifest.yml | No DCM scaffold. Only examples/grid-pulse-snowflake (app.py, README) on branch teve-snowflake-grid-pulse-learnings. |
| Fabric | fabric/grid-pulse/ | Report item exists outside the repo at ~/grid-pulse-report (GridPulseDashboard.Report). The offline validator passes on it. It is bound by connection to a semantic model id, so a deploy needs a parameter.yml find_replace (the validator warns). |

Change the path variables at the top of platform-ci.yml and the cd-*.yml files if you put them elsewhere.

## Verified blockers

- **Snowflake CLI:** your installed CLI is 2.8.2 and has no snow dcm command (verified). DCM needs Snowflake CLI 3.24 or later per Snowflake docs; I confirmed plan and deploy flags on 3.34 in a scratch venv. Workflows install snowflake-cli>=3.24.0,<4 themselves. I made no Snowflake calls, so the PAT failure is not re-tested. Key pair is generated but **not registered; I registered nothing**.
- **Databricks:** bundle validate fails without credentials (verified: "cannot configure default credentials"). A Genie-only token cannot validate or deploy. You need a service principal with an OIDC federation policy. Whether the free trial allows it is not verified.
- **Fabric:** deploys go to your dev workspace only. fabric_deploy.py refuses unless FABRIC_ENV_NAME is dev, the tenant matches FABRIC_DEV_TENANT_ID, and the workspace is not in FABRIC_BLOCKED_WORKSPACE_IDS (list the Avon Risk workspace ids there). It publishes only; it never unpublishes or deletes.

## Not verified (check before enabling)

- fab deploy (Fabric CLI 1.6.1 has it) is not used; fabric-cicd is, because its API is documented. Docs list 31 item types; the installed package accepts 29. The validator uses the installed list.
- No Materialized Lake View support is documented in fabric-cicd. Lakehouse is not in the default deploy scope (FABRIC_ITEM_SCOPE, default SemanticModel,Report,Notebook).
- Databricks OIDC subject for PR jobs: the federation policy must match repo:slysik/open-skills:environment:databricks-ci (environment form is the documented one; confirm in your workspace).
- DROP detection in the Snowflake deploy is a text heuristic; the plan.json schema is unverified. DCM deployment history and restore commands are unverified; rollback is git revert then redeploy.
- Actions are pinned by tag, matching ci.yml. For SHA pins: setup-cli v1.27.0 = 12452ad4003a2dd61d5a7cee30bc068f750a2e00, checkout v4 = 11d5960a326750d5838078e36cf38b85af677262, setup-python v5 = a26af69be951a213d495a4c3e4e4022e16d87065, azure/login v2 = 8216e11d8cd9b42fe925c852af8e76311ff067ac.
- Workflows were linted with actionlint 1.7.12 and the scripts unit-tested. They have **not** run on GitHub.
- Fork PRs get no secrets, so those checks skip.

## Checklist: what you provide

Create these in GitHub (Settings > Secrets and variables > Actions, and Settings > Environments). I created none and need no values from you in chat.

### Phase 1 (checks)
| Name | Kind | Scope | Purpose |
|---|---|---|---|
| databricks-ci | Environment, no reviewers | repo | OIDC subject for PR validation |
| DATABRICKS_HOST | Variable | databricks-ci | Dev workspace URL |
| DATABRICKS_CLIENT_ID | Secret | databricks-ci | Service principal application id (OIDC; no client secret) |
| (federation policy) | Databricks side | service principal | GitHub Actions policy for the databricks-ci subject |
| snowflake-ci | Environment, no reviewers | repo | Holds CI credentials |
| SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER | Secrets | snowflake-ci | Account locator and a plan-only user |
| SNOWFLAKE_PRIVATE_KEY | Secret | snowflake-ci | PEM private key. Register its public key on that user first (manual) |
| SNOWFLAKE_PRIVATE_KEY_PASSPHRASE | Secret | snowflake-ci | Only if the key is encrypted (read as PRIVATE_KEY_PASSPHRASE) |
| SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE | Variables | snowflake-ci | Optional |
| Branch protection | Setting | main | Require platform-ci-gate and CI / check; require review |
| Grid Pulse artifacts | Commit | repo | Put the bundle, DCM project and Fabric items at the paths above |

### Phase 2 (deploy to DEV; your approval needed first)
| Name | Kind | Purpose |
|---|---|---|
| databricks-dev, snowflake-dev, fabric-dev | Environments with you as required reviewer | The approval gate |
| CICD_ENABLE_CD_DATABRICKS / _SNOWFLAKE / _FABRIC | Variables, set to 'true' | Master switch, off by default |
| DATABRICKS_HOST, DATABRICKS_CLIENT_ID | Variable, secret on databricks-dev | Same names as Phase 1, dev-deploy service principal; federation subject environment:databricks-dev |
| SNOWFLAKE_* | Same names on snowflake-dev | A user whose role may deploy to GRIDPULSE_DEV only |
| AZURE_CLIENT_ID, AZURE_TENANT_ID | Secrets on fabric-dev | App registration with OIDC federated credential, member or contributor on your dev workspace |
| FABRIC_DEV_WORKSPACE_ID, FABRIC_DEV_TENANT_ID | Variables on fabric-dev | The only workspace and tenant allowed |
| FABRIC_BLOCKED_WORKSPACE_IDS | Variable on fabric-dev | Avon Risk workspace ids to refuse |