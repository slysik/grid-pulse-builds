-- Silver as plain tables (not dynamic tables): Snowflake rejects a native materialized view over a dynamic table
-- ("should be a table", verified 2026-11-19). Rows are loaded by scripts/02_load_and_mv.sql with the Grid Pulse
-- dedupe and quality rules (meter_id + event_time key; kwh >= 0; 0 <= voltage <= 150; outages need customers and cost).
DEFINE TABLE COS_DB{{env_suffix}}.SILVER.METERS (
  meter_id STRING, region STRING, customer_type STRING, substation STRING, capacity_kw FLOAT, install_date STRING
);
DEFINE TABLE COS_DB{{env_suffix}}.SILVER.READINGS (
  meter_id STRING, event_time TIMESTAMP_NTZ, kwh FLOAT, voltage FLOAT, temp_c FLOAT, region STRING
);
DEFINE TABLE COS_DB{{env_suffix}}.SILVER.OUTAGES (
  outage_id STRING, region STRING, start_time TIMESTAMP_NTZ, duration_min NUMBER, customers_affected NUMBER,
  cause STRING, estimated_cost_usd NUMBER, crew_lead STRING
);
