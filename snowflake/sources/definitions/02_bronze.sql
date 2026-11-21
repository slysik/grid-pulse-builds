DEFINE TABLE COS_DB{{env_suffix}}.BRONZE.METERS (
  meter_id STRING,
  region STRING,
  customer_type STRING,
  substation STRING,
  capacity_kw FLOAT,
  install_date STRING
);

DEFINE TABLE COS_DB{{env_suffix}}.BRONZE.READINGS (
  meter_id STRING,
  event_time TIMESTAMP_NTZ,
  kwh FLOAT,
  voltage FLOAT,
  temp_c FLOAT,
  region STRING
);

DEFINE TABLE COS_DB{{env_suffix}}.BRONZE.OUTAGES (
  outage_id STRING,
  region STRING,
  start_time TIMESTAMP_NTZ,
  duration_min NUMBER,
  customers_affected NUMBER,
  cause STRING,
  estimated_cost_usd NUMBER,
  crew_lead STRING
);