# grid-pulse-builds: always-on rules

These rules apply to every agent working in this repo (TeveBot Agent in CI, Claude Code on the Mac, Teve).

- Never merge a pull request. Steve merges, in GitHub.
- Never push to `main`. Everything arrives as a PR.
- Never deploy. This repo's CI is checks only.
- Never create, print, or commit a secret value.
- Use only the free-trial workspace id 54634e0b-7658-49fa-8441-0ba7bc594ada. No other workspace id anywhere.
- Never invent Fabric commands, API endpoints, or item definitions. Use the installed Fabric skills; if unsure, stop and report.
- One Gold model or one change per PR. Workflow changes travel alone.
- A test for every switch.
- Review procedure lives in `.claude/skills/fabric-gold-review/`.
- Report in four parts: what changed, what was verified live and how, what is blocked, what Steve needs to do.
