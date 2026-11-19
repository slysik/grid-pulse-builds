# Platform matrix: one Grid Pulse materialized view on three platforms

Dry run on 2026-11-19. This is a learning exercise, **not a benchmark**: one build and one refresh per platform on small data. Cells say what was observed here; "docs" means taken from vendor docs and not tested in this run; "not run" means it did not happen.

Same logic on all three: one row per (date, region) with daily kWh, outage count, outage cost and customers affected, from the silver readings and outages tables. Expected result (Grid Pulse source of truth): 40 rows, 30 outages, $203,947, 6,109 customers.

| Dimension | Databricks (Lakeflow MV) | Snowflake (native MV + DCM) | Fabric (Materialized Lake View) |
|---|---|---|---|
| Result of this dry run | Validated and deployed; **build failed** (RESOURCE_EXHAUSTED on trial compute). Not verified. | **Not built.** Waiting on scaffold files and a registered key. | **Built, refreshed once, verified**: 40 rows, 30, $203,947, 6,109, kWh equals gold. |
| Definition syntax | `CREATE OR REFRESH MATERIALIZED VIEW` in a pipeline SQL file; CTEs and joins accepted (bundle validated). | `CREATE MATERIALIZED VIEW` is single-table only (no joins, subqueries, window functions; docs, to confirm against Snowflake's "Limitations on creating materialized views" page). The join logic needs two MVs plus a plain view, or a dynamic table. | `CREATE MATERIALIZED LAKE VIEW ... AS` in a Spark SQL notebook cell; CTEs and left join worked. |
| Refresh behavior | Pipeline update, run manually (`bundle run`). No schedule defined. Refresh not reached. | Maintained automatically by Snowflake in the background (docs, not tested). | On-demand job through the REST API (worked); a schedule is optional and was not set. In an earlier test on other data, GROUP BY views were fully rewritten, not incremental. |
| Cost (this dry run only) | Unknown: the run failed before compute started and no billing view was readable. | Not run: 0 credits used. | CU not measured (Capacity Metrics app not read). Notebook run about 4 min and refresh about 3.5 min wall clock on trial capacity, mostly Spark session start; context only. |
| Governance | Unity Catalog objects (catalog fde, new schema mv_dryrun); grants not changed. | Roles and DCM project ownership via manifest (docs, not tested). | Workspace roles; Git-format items carry a logicalId. No item-level change made. |
| Limits (what it can't do) | Free-trial compute ceiling blocked both pipeline start and SQL warehouse (reported). Source silver tables are streaming tables owned by another pipeline. | No joins in a native MV (above); Enterprise edition needed (docs, unverified here). | Lakehouse data is not moved by deployment; GROUP BY refresh is a full recompute in the earlier test; SQL endpoint needs a metadata refresh before new tables are visible. |
| BI / Direct Lake | Not tested. | Not tested. | The existing Grid Pulse semantic model is Direct Lake over OneLake and the report binds to it. The new MLV is not wired into either. |
| CI/CD deployability | Bundles: `validate --strict` and `deploy -t dev` both worked from the CLI. | DCM: `snow dcm plan/deploy` flags confirmed on CLI 3.34; not run (no auth). | fabric-cicd with parameter.yml: offline validator passes; deploy to a second workspace not run. |
| Time to build | Fast to author and deploy; blocked at run. | n/a | Slowest step was waiting for Spark session start. |

## What each platform couldn't do in this run
- **Databricks:** run the pipeline, so no verification and no cost number.
- **Snowflake:** anything; blocked on inputs. Also cannot express the join as one native MV.
- **Fabric:** be deployed to a second workspace, and report CU.
