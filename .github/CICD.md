# TeveBot: small Fabric PR loop (CI only)

CI only. No deploy. Deploy is a later spec.

## Roles
| Who | Does |
|---|---|
| Steve | Provides the spec, branches, opens the PR, reads checks and review, merges. Only merger. |
| TeveBot Agent | Autonomous Claude Code bot. Reviews every non-draft PR (GitHub Action) and posts to Slack. Builds only when asked. |
| Teve | Verifies live (GitHub API, Fabric REST read-only) and reports in the four-part format. |

## The loop
1. Steve approves the spec (`fabric/specs/`).
2. Build on a branch, tests first.
3. Tests and validation pass locally.
4. Teve verifies live; QA checklist run item by item.
5. Steve opens the PR.
6. `fabric-gold-ci.yml` runs validate and test; TeveBot Agent posts its review as PR comments.
7. Steve reads both, merges. Teve confirms main is green.

## Checks (workflow: fabric-gold-ci.yml)
- **validate**: offline item validation (scripts/ci/validate_fabric_items.py). Fails on any workspace id other than the free-trial one.
- **test**: python unittest for scripts, workflow contract, review skill, notifier, and the Gold model.
- **review**: TeveBot Agent. Never approves or blocks. Skips drafts. Skips with a warning only before any fabric/ PR has merged; fails after.
- **notify**: Slack notice. Warns and moves on if the webhook secret is missing.
- **fabric-gold-gate**: the one required check. Red validate or test blocks the merge.

## Steve creates (nobody else, never printed)
- Secret `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` (one of the two).
- Secret `SLACK_WEBHOOK_URL` (Slack channel integrations, incoming webhook).
- Repo variable `FABRIC_DEV_WORKSPACE_ID` = 54634e0b-7658-49fa-8441-0ba7bc594ada (reserved for the later deploy spec; no job reads it yet).
- Branch protection on main: no direct pushes, no force pushes, require `fabric-gold-gate`. Do not require a formal approval in the pilot (an author cannot approve their own PR). Availability on a private repo depends on the GitHub plan.

## Slack (decided 2026-11-21: webhook plus Slack MCP plugin on the Mac)
Channel `#fabric-cicd` in Steve's own workspace.
- **Notices out (CI to Slack):** incoming webhook, repo secret `SLACK_WEBHOOK_URL` (exists). Sent by `scripts/ci/notify_slack.py` from the `notify` job.
- **Ask and read (Mac to Slack):** official Slack MCP plugin in Claude Code. Steve runs `/plugin install slack`, completes OAuth, and approves the integration as workspace admin. Use only one install route (the docs describe two). Then run `/mcp` and record the exact post tool name here: _not yet recorded_.
- Posts through the plugin go out under Steve's name. There is no separate @TeveBot identity.
- Not chosen: legacy @Claude app and Claude Tag (plan and free-workspace limits unverified).

## Rollback
`git revert <merge-commit>` on a branch, then a new PR through the same loop. No shortcuts.

## Known limits
- Workflow changes must be on main before the first Fabric PR runs (a workflow on a branch must match main or the action returns 401).
- The review step uses `anthropics/claude-code-action@v1`; it has not run on GitHub yet. First live run is the proof.
- Offline checks cannot prove: item creation in a workspace, parameter replacement against real ids, MLV state. Teve checks those live, read-only.
