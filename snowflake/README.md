# Snowflake: Grid Pulse daily-summary materialized views + DCM

**Status (2026-11-19): built in DEV and verified against the Grid Pulse numbers.** Target: `GRIDPULSE_DEV` only (no STAGE/PROD targets in this repo). Live `COS_DB` was only read, never written.

## Definition
Same logic as the Databricks and Fabric folders: one row per (report_date, region). Snowflake's native MV is single-table (joins are rejected), so it is two MVs plus a plain view:
- `COS_DB_DEV.GOLD.MV_DAILY_READINGS`: daily kWh from `SILVER.READINGS`
- `COS_DB_DEV.GOLD.MV_DAILY_OUTAGES`: outage count, cost, customers affected from `SILVER.OUTAGES`
- `COS_DB_DEV.GOLD.GRID_DAILY_SUMMARY`: view joining the two

## What DCM manages, and what it can't
- **In DCM (`sources/definitions/`):** warehouse `COS_WH_ETL_DEV` (X-SMALL, auto-suspend 60 s), database `COS_DB_DEV`, schemas, bronze and silver tables.
- **Outside DCM (`scripts/02_load_and_mv.sql`):** the data load and the MVs. DCM definition files accept only DEFINE, GRANT and ATTACH, so no INSERT; and the supported-entities page lists VIEW and DYNAMIC TABLE but not MATERIALIZED VIEW (docs).

## Build
```
snow sql -f - <<< "CREATE DATABASE IF NOT EXISTS GRIDPULSE_DCM; CREATE SCHEMA IF NOT EXISTS GRIDPULSE_DCM.PROJECTS; CREATE DCM PROJECT IF NOT EXISTS GRIDPULSE_DCM.PROJECTS.GRIDPULSE_DCM_DEV"   # once
cd snowflake
snow dcm plan --target GRIDPULSE_DEV --save-output       # needs Snowflake CLI >= 3.24; read-only
snow dcm deploy --target GRIDPULSE_DEV --alias dryrun-1
snow sql -f scripts/02_load_and_mv.sql
```
**Refresh:** none to run. Snowflake maintains MVs itself and there is no manual refresh step, so the "one refresh" for this platform is not applicable. Data is static after the load.

## Findings (all observed 2026-11-19)
1. A native MV on a **dynamic table** fails: "'...SILVER.READINGS' should be a table". The scaffold's silver dynamic tables were replaced by plain tables loaded with the same dedupe rules.
2. Changing an object from DYNAMIC TABLE to TABLE through DCM fails ("already exists as DYNAMIC_TABLE"); the dev dynamic tables were dropped by hand first.
3. `GROUP BY DATE(event_time)` together with `DATE(event_time) AS report_date` created an MV that could not be read ("duplicate column name 'REPORT_DATE'"). `GROUP BY 1, 2` works.

## Verification (on `GRID_DAILY_SUMMARY`)
| Check | Expected | Got |
|---|---|---|
| silver rows | 11,520 readings, 48 meters, 30 outages | 11,520 / 48 / 30 |
| rows | 40 | 40 |
| SUM(outage_count) | 30 | 30 |
| SUM(outage_cost_usd) | 203947 | 203947 |
| SUM(customers_affected) | 6109 | 6109 |
| SUM(daily_kwh) | 109417.775 | 109417.775 (float rounding) |

DCM plan/deploy: first plan 12 create, 1 alter, 0 drop; 0 drops in every plan.

## Cost (this dry run)
- Warehouse `COS_WH_ETL_DEV` (X-SMALL): **0.066354 credits** (metering history, last 3 h), covering two DCM deploys, the loads, three dynamic-table refreshes (later dropped), the MV creations and test MVs. `COMPUTE_WH`: 0.000016 credits.
- MV background maintenance credits: **not yet visible** (`MATERIALIZED_VIEW_REFRESH_HISTORY` returned no rows); unknown.
- Warehouse suspended after the build. Cloud services cost for DCM plan/deploy not separately read.

## What to watch / deviations
- Project owner is ACCOUNTADMIN for this dry run. Follow-up: a least-privilege DCM_DEVELOPER role (the scaffold's pre-deploy script is a TODO). I did not run its account-wide `ALTER ACCOUNT SET FEATURE_RBAC_INHERITED_GRANTS`.
- A few extra statements ran beyond the final script (test MVs, a drop and recreate), so cost is slightly higher than a clean run.
- MV requires Enterprise edition (docs, not checked on this account).
- Key-pair auth: connection `gridpulse_dev` with a locally generated key; nothing secret is in this repo.
