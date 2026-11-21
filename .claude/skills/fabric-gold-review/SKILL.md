---
name: fabric-gold-review
description: Review a pull request that touches Fabric Gold items in grid-pulse-builds. Use when TeveBot Agent or a human asks to review a PR diff for numbers, security and scope. Reviews only the diff against main, posts a few high-confidence findings, never approves or blocks.
---

# fabric-gold-review

Thin router. Detail lives in `references/`.

## When to use
A pull request changes files under `fabric/`, `scripts/ci/`, `tests/`, or `.github/workflows/`.

## Steps
1. Get the diff against `main` only (`gh pr diff`). Read surrounding files only when a finding needs them. Ignore uncommitted local changes.
2. Walk `references/checklist.md` in order: numbers, security, scope.
3. Report using `references/output-shape.md`. Prefer a few high-confidence findings over many speculative ones.
4. Post the result as one comment on the pull request.

## Always-on rules
- Never approve, never block, never merge.
- Never invent commands, endpoints, or fabric-cicd capabilities. If something is unverified, say so.
- Never print a secret value.
- Free-trial workspace only. Any other workspace id in the diff is a finding.
