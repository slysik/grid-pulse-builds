-- Grid Pulse daily summary: one row per (date, region).
-- Same logic as snowflake/ and fabric/; see README.md in this folder for syntax differences.
CREATE OR REFRESH MATERIALIZED VIEW mv_grid_daily_summary
COMMENT 'Grid Pulse daily summary: kWh, outage count, outage cost, customers affected per date and region'
AS
WITH r AS (
  SELECT CAST(event_time AS DATE) AS report_date, region, SUM(kwh) AS daily_kwh
  FROM fde.silver.grid_readings_clean
  GROUP BY CAST(event_time AS DATE), region
),
o AS (
  SELECT CAST(start_time AS DATE) AS report_date, region,
         COUNT(*) AS outage_count,
         SUM(estimated_cost_usd) AS outage_cost_usd,
         SUM(customers_affected) AS customers_affected
  FROM fde.silver.grid_outages_clean
  GROUP BY CAST(start_time AS DATE), region
)
SELECT r.report_date, r.region, r.daily_kwh,
       COALESCE(o.outage_count, 0) AS outage_count,
       COALESCE(o.outage_cost_usd, 0) AS outage_cost_usd,
       COALESCE(o.customers_affected, 0) AS customers_affected
FROM r LEFT JOIN o ON o.report_date = r.report_date AND o.region = r.region
