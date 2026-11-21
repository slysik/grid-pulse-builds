-- scripts/02_load_and_mv.sql: runs AFTER snow dcm deploy. Outside DCM because DCM definition files accept only
-- DEFINE / GRANT / ATTACH statements (so no INSERT) and the supported-entities list has no MATERIALIZED VIEW.
-- Run once, dev only. Reads (never writes) the live COS_DB.BRONZE tables.
USE WAREHOUSE COS_WH_ETL_DEV;

INSERT OVERWRITE INTO COS_DB_DEV.SILVER.METERS
SELECT meter_id, region, customer_type, substation, capacity_kw, install_date FROM COS_DB_DEV.BRONZE.METERS;

INSERT OVERWRITE INTO COS_DB_DEV.SILVER.READINGS
SELECT meter_id, event_time, kwh, voltage, temp_c, region
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY meter_id, event_time ORDER BY event_time) AS rn
  FROM COS_DB_DEV.BRONZE.READINGS
  WHERE meter_id IS NOT NULL AND kwh >= 0 AND voltage >= 0 AND voltage <= 150
)
WHERE rn = 1;

INSERT OVERWRITE INTO COS_DB_DEV.SILVER.OUTAGES
SELECT outage_id, region, start_time, duration_min, customers_affected, cause, estimated_cost_usd, crew_lead
FROM COS_DB_DEV.BRONZE.OUTAGES
WHERE customers_affected > 0 AND estimated_cost_usd >= 0;

-- NOTE: GROUP BY DATE(col) with the same expression aliased in SELECT made the MV unreadable ("duplicate column name",
-- verified 2026-11-19); GROUP BY 1, 2 works.
-- A native MV is single-table (no join), so the daily summary is two MVs plus a plain view that joins them.
CREATE MATERIALIZED VIEW COS_DB_DEV.GOLD.MV_DAILY_READINGS AS
SELECT DATE(event_time) AS report_date, region, SUM(kwh) AS daily_kwh
FROM COS_DB_DEV.SILVER.READINGS
GROUP BY 1, 2;

CREATE MATERIALIZED VIEW COS_DB_DEV.GOLD.MV_DAILY_OUTAGES AS
SELECT DATE(start_time) AS report_date, region,
       COUNT(*) AS outage_count, SUM(estimated_cost_usd) AS outage_cost_usd, SUM(customers_affected) AS customers_affected
FROM COS_DB_DEV.SILVER.OUTAGES
GROUP BY 1, 2;

CREATE VIEW COS_DB_DEV.GOLD.GRID_DAILY_SUMMARY AS
SELECT r.report_date, r.region, r.daily_kwh,
       COALESCE(o.outage_count, 0) AS outage_count,
       COALESCE(o.outage_cost_usd, 0) AS outage_cost_usd,
       COALESCE(o.customers_affected, 0) AS customers_affected
FROM COS_DB_DEV.GOLD.MV_DAILY_READINGS r
LEFT JOIN COS_DB_DEV.GOLD.MV_DAILY_OUTAGES o ON o.report_date = r.report_date AND o.region = r.region;
