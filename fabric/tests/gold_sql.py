"""Helpers: pull the Gold model SQL out of the Fabric notebook so tests can replay it."""
import re
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "grid-pulse" / "nb_mlv_daily_summary.Notebook" / "notebook-content.py"
COLUMNS = ["report_date", "region", "daily_kwh", "outage_count", "outage_cost_usd", "customers_affected"]
MLV_NAME = "gold.mlv_grid_daily_summary"


def notebook_sql() -> str:
    lines = [ln[len("# MAGIC "):] for ln in NOTEBOOK.read_text().splitlines() if ln.startswith("# MAGIC ")]
    return "\n".join(l for l in lines if not l.strip().startswith("%%"))


def select_sql() -> str:
    """The model's SELECT (the MLV prefix removed) for replay in another engine."""
    sql = notebook_sql()
    m = re.search(r"CREATE MATERIALIZED LAKE VIEW IF NOT EXISTS\s+" + re.escape(MLV_NAME) + r"\s+AS\s+", sql, re.I)
    if not m:
        raise AssertionError("notebook does not create " + MLV_NAME)
    return sql[m.end():].strip().rstrip(";")
