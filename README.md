# grid-pulse-builds

A cost-controlled ADLC and CI/CD learning exercise: the same Grid Pulse daily-summary materialized view on Databricks, Snowflake and Microsoft Fabric. Not a performance test.

## ADLC flow
1. **Define:** one SQL definition of the daily summary (date, region, kWh, outage count, cost, customers).
2. **Build:** Claude Code writes the platform folder and runs one build and one refresh in dev.
3. **Validate:** check the result against the Grid Pulse numbers (40 rows, 30 outages, $203,947, 6,109 customers).
4. **PR review:** Teve verifies and opens the PR; the owner reviews and merges. Nothing reaches main without that.
5. **Gated dev deploy:** merge triggers the dev deploy workflow, which waits for an environment approval (off until enabled).
6. **Verify:** re-check the numbers in the dev target.

## Layout
- `databricks/`: Lakeflow bundle ([README](databricks/README.md))
- `snowflake/`: DCM project ([README](snowflake/README.md))
- `fabric/`: MLV notebook, semantic model, report, parameter.yml ([README](fabric/README.md))
- `.github/workflows/`: platform CI and gated dev deploys; setup checklist in [.github/CICD.md](.github/CICD.md)
- [MATRIX.md](MATRIX.md): pros and cons across the three

## Status
See the matrix. Fabric and Snowflake built and verified against the Grid Pulse numbers; Databricks build blocked by trial compute.
