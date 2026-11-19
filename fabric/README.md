# Fabric: Grid Pulse daily-summary Materialized Lake View

**Status (2026-11-19): built, refreshed once, verified against the Grid Pulse numbers.**

## Definition
`grid-pulse/nb_mlv_daily_summary.Notebook` holds one Spark SQL cell: `CREATE MATERIALIZED LAKE VIEW IF NOT EXISTS gold.mlv_grid_daily_summary AS ...` over `silver.readings` and `silver.outages` in lakehouse `grid_pulse_lakehouse` (workspace "Grid Pulse"). Same logic as the Databricks and Snowflake folders: one row per (report_date, region).

Syntax notes (this platform): `CREATE MATERIALIZED LAKE VIEW` runs in a Fabric Spark notebook (not the SQL endpoint); CTEs and left join are fine; the lakehouse is schema-enabled so objects are `schema.table`. The SQL analytics endpoint reads the MLV after a metadata refresh.

## Build and refresh (one of each was run)
- Build: notebook run via the Fabric REST API (`RunNotebook` job), which created and populated the MLV.
- Refresh: one on-demand `refreshMaterializedLakeViews` job on the lakehouse. No schedule exists.

## Verification (T-SQL on the lakehouse SQL endpoint, after build and again after refresh)
| Check | Expected | Got |
|---|---|---|
| rows | 40 | 40 |
| SUM(outage_count) | 30 | 30 |
| SUM(outage_cost_usd) | 203947 | 203947 |
| SUM(customers_affected) | 6109 | 6109 |
| SUM(daily_kwh) vs gold.grid_daily_region_demand | 109417.775 | 109417.775 (float rounding in the 14th digit) |

Source counts checked first: bronze 48 meters / 11,575 readings / 30 outages, silver 48 / 11,520 / 30, gold daily 40.

## Cost
Fabric CU consumption was **not measured**: the Capacity Metrics app was not read. Context only (not a benchmark): the notebook run took about 4 minutes and the refresh about 3.5 minutes, both on the trial capacity, almost all of it Spark session start. The SQL endpoint checks are small.

## Portability (parameter.yml)
`grid-pulse/parameter.yml` replaces the source workspace id, lakehouse id and semantic model id in the notebook, semantic model and report with fabric-cicd dynamic variables (`$workspace.$id`, `$items.Lakehouse.grid_pulse_lakehouse.$id`, `$items.SemanticModel.Grid Pulse.$id`; syntax checked in the installed fabric-cicd source). **Not deployed to a second workspace in this dry run.** The target needs a lakehouse named `grid_pulse_lakehouse` that already has the tables; fabric-cicd moves item definitions, not data. Environment key is `dev`.

## What to watch
- The existing semantic model and report read the gold tables, not this MLV; the MLV is not wired into the report.
- Spark session start dominates cost and latency at this data size.
- fabric-cicd has no MLV-specific support documented; the MLV lives inside the notebook and is created when the notebook runs.
- Cleanup: nothing created outside the Grid Pulse workspace.
