# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "eadde634-753a-45f4-a622-007644ac9edd",
# META       "default_lakehouse_name": "grid_pulse_lakehouse",
# META       "default_lakehouse_workspace_id": "54634e0b-7658-49fa-8441-0ba7bc594ada"
# META     }
# META   }
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE MATERIALIZED LAKE VIEW IF NOT EXISTS gold.mlv_grid_daily_summary AS
# MAGIC WITH r AS (
# MAGIC   SELECT CAST(event_time AS DATE) AS report_date, region, SUM(kwh) AS daily_kwh
# MAGIC   FROM silver.readings
# MAGIC   GROUP BY CAST(event_time AS DATE), region
# MAGIC ),
# MAGIC o AS (
# MAGIC   SELECT CAST(start_time AS DATE) AS report_date, region,
# MAGIC          COUNT(*) AS outage_count,
# MAGIC          SUM(estimated_cost_usd) AS outage_cost_usd,
# MAGIC          SUM(customers_affected) AS customers_affected
# MAGIC   FROM silver.outages
# MAGIC   GROUP BY CAST(start_time AS DATE), region
# MAGIC )
# MAGIC SELECT r.report_date, r.region, r.daily_kwh,
# MAGIC        COALESCE(o.outage_count, 0) AS outage_count,
# MAGIC        COALESCE(o.outage_cost_usd, 0) AS outage_cost_usd,
# MAGIC        COALESCE(o.customers_affected, 0) AS customers_affected
# MAGIC FROM r LEFT JOIN o ON o.report_date = r.report_date AND o.region = r.region
