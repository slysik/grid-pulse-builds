# Review checklist (in priority order)

## 1. Numbers (first)
- The Gold model must reproduce the verified numbers: 40 rows, 30 outages, 203947 outage cost, 6109 customers affected, kWh 109417.775.
- A change to `fabric/specs/expected.json`, the model SQL, or a fixture must say why, and the Gold tests must still pass.
- Output columns stay: report_date, region, daily_kwh, outage_count, outage_cost_usd, customers_affected.

## 2. Security
- No secret, key, token, password, connection string, or webhook URL in any file.
- No workspace id other than the free-trial workspace. No client workspace ids anywhere, not even as a blocklist.
- Workflow permissions are least privilege. `pull-requests: write` only where the review job needs it. No `pull_request_target`.

## 3. Scope
- Small: one Gold model or one change per PR. If it does more than one thing, say it should be split.
- A test exists for every switch or rule added. No test, no merge.
- Workflow changes (`.github/workflows/**`) travel alone, not bundled with other changes.
- GA Fabric features only. No preview items.
- No deploy, publish, or merge steps. CI only.
- No invented CLI commands, API endpoints, or item definitions. The repo is the source of truth.
