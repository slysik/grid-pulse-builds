-- Warehouse, database, schemas for the dev copy. {{env_suffix}} renders _DEV, so the live COS_DB is never touched.
DEFINE WAREHOUSE COS_WH_ETL{{env_suffix}}
  WITH
    warehouse_size = '{{wh_size}}'
    auto_suspend = 60
    initially_suspended = TRUE
    COMMENT = 'Grid Pulse MV dry run warehouse (DCM-managed, smallest size)';

DEFINE DATABASE COS_DB{{env_suffix}}
  COMMENT = 'Grid Pulse MV dry run (DCM-managed, safe to drop)';

DEFINE SCHEMA COS_DB{{env_suffix}}.BRONZE COMMENT = 'Raw landing';
DEFINE SCHEMA COS_DB{{env_suffix}}.SILVER COMMENT = 'Cleaned, deduped readings and outages';
DEFINE SCHEMA COS_DB{{env_suffix}}.GOLD COMMENT = 'Daily summary views (MVs are created by scripts/02_load_and_mv.sql)';
