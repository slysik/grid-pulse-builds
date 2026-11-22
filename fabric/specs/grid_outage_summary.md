# Spec: Grid Pulse daily outage summary (Gold)

Status: DRAFT written by TeveBot Agent from the verified 2026-11-19 results. Steve edits and approves; his approval is the spec gate.

## Model
Item: `fabric/grid-pulse/nb_mlv_daily_summary.Notebook` creates `gold.mlv_grid_daily_summary` in lakehouse `grid_pulse_lakehouse` (free-trial workspace 54634e0b-7658-49fa-8441-0ba7bc594ada).

## Sources
- `silver.readings` (event_time, region, kwh)
- `silver.outages` (start_time, region, estimated_cost_usd, customers_affected)

## Grain
One row per (report_date, region), where report_date is the calendar date of the reading.

## Output columns (in this order)
report_date, region, daily_kwh, outage_count, outage_cost_usd, customers_affected

## Rules
- daily_kwh = sum of kwh for the date and region.
- Outages are grouped by the calendar date of start_time and region, then LEFT JOINed to readings.
- Date and region with readings but no outages: outage_count, outage_cost_usd, customers_affected are 0.
- Known behavior, pinned by a test: an outage on a date and region with no readings does not appear in the output.

## Must reproduce (verified numbers)
- rows: 40
- outage_count total: 30
- outage_cost_usd total: 203947
- customers_affected total: 6109
- daily_kwh total: 109417.775

Machine-readable copy: `fabric/specs/expected.json`.

## Fixture
`fabric/tests/fixtures/silver_readings.csv` (11520 rows) and `silver_outages.csv` (30 rows): read-only export of the silver tables from the free-trial workspace SQL endpoint on 2026-11-20. Synthetic Grid Pulse data.
