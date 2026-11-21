# Databricks: Grid Pulse daily-summary materialized view

**Status (2026-11-19): definition validated and deployed to dev; the build did NOT run. Verification against the gold numbers is pending.**

## Definition
`src/mv_grid_daily_summary.sql` creates `fde.mv_dryrun.mv_grid_daily_summary`: one row per (report_date, region) with daily kWh from `fde.silver.grid_readings_clean`, left-joined to outage count, cost and customers affected from `fde.silver.grid_outages_clean`. Same logic as the Snowflake and Fabric folders.

Syntax notes (this platform): `CREATE OR REFRESH MATERIALIZED VIEW` inside a Lakeflow pipeline SQL file; the MV is owned and refreshed by the pipeline. CTEs and joins are allowed. Source tables are streaming tables, so the MV reads them as ordinary tables.

## Build and refresh
```
cd databricks
databricks bundle validate --strict -t dev --profile <profile>
databricks bundle deploy -t dev --profile <profile>
databricks bundle run grid_pulse_mv_pipeline -t dev --profile <profile>   # build, and again for a refresh
```
Serverless pipeline, triggered only, no schedule anywhere in the bundle. `mv_dryrun` schema was created once by hand (`databricks schemas create mv_dryrun fde`).

## What happened
- `bundle validate --strict`: OK. `bundle deploy -t dev`: pipeline created.
- First (only) run attempt failed at pipeline start: `RESOURCE_EXHAUSTED: Cannot create the resource` (free-trial compute limit). No retry loop was run, per the cost rules. The SQL warehouse was also reported blocked, so row counts could not be read.

## Second attempt: SQL warehouse materialized view (2026-11-19)
Tried `CREATE MATERIALIZED VIEW` on warehouse `ab98e3090cc13476` (Serverless Starter, 2X-Small) as a manual-refresh alternative to the pipeline. The statement was rejected immediately ("The request could not be processed by the warehouse"), and `databricks warehouses start` returned "Cannot create the resource, please try again later." The warehouse stayed STOPPED. One attempt each, no retries. The pipeline was also retried once and failed with the same RESOURCE_EXHAUSTED error. The workspace refuses to create any compute, so both paths are blocked until the trial limit clears. The documented SQL-warehouse form is `CREATE MATERIALIZED VIEW ... AS ...` then `REFRESH MATERIALIZED VIEW ...` (no SCHEDULE), and note a warehouse MV also runs on a serverless pipeline behind the scenes (docs).

## Cost
Unknown. The run failed before creating compute; no billing view was readable (system tables need a SQL warehouse).

## To verify once compute is available
Expect 40 rows; SUM(outage_count)=30, SUM(outage_cost_usd)=203947, SUM(customers_affected)=6109, SUM(daily_kwh)=109417.775 (these were reproduced on the Fabric silver tables with the same logic).

## What to watch
Free-trial serverless limits; the `fde.silver` tables are streaming tables owned by the `grid-pulse-sample` pipeline, which this bundle only reads.
