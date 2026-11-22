import json
import re
import sys
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gold_sql  # noqa: E402

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
SPEC_DIR = HERE.parent / "specs"
EXPECTED = json.loads((SPEC_DIR / "expected.json").read_text())


def replay(readings_sql: str, outages_sql: str):
    """Run the notebook's SELECT in DuckDB against the given source tables (schema silver)."""
    con = duckdb.connect()
    con.execute("CREATE SCHEMA silver")
    con.execute(readings_sql)
    con.execute(outages_sql)
    return con, con.execute(gold_sql.select_sql()).fetchall()


def load_fixture():
    r = f"CREATE TABLE silver.readings AS SELECT * FROM read_csv('{FIX / 'silver_readings.csv'}', header=true, columns={{'event_time':'TIMESTAMP','region':'VARCHAR','kwh':'DOUBLE'}})"
    o = f"CREATE TABLE silver.outages AS SELECT * FROM read_csv('{FIX / 'silver_outages.csv'}', header=true, columns={{'start_time':'TIMESTAMP','region':'VARCHAR','estimated_cost_usd':'BIGINT','customers_affected':'BIGINT'}})"
    return replay(r, o)


class GoldStructure(unittest.TestCase):
    def test_G1_creates_expected_view(self):
        self.assertIn("CREATE MATERIALIZED LAKE VIEW IF NOT EXISTS " + gold_sql.MLV_NAME, gold_sql.notebook_sql())

    def test_G1_output_columns_in_order(self):
        sel = gold_sql.select_sql()
        final = sel[sel.rindex("SELECT r.report_date"):sel.rindex("FROM r")]
        aliases = re.findall(r"(?:AS\s+(\w+))|(?:r\.(\w+))", final)
        names = [a or b for a, b in aliases]
        self.assertEqual(names, gold_sql.COLUMNS)

    def test_G1_grain_and_join(self):
        sel = gold_sql.select_sql()
        self.assertIn("LEFT JOIN o ON o.report_date = r.report_date AND o.region = r.region", sel)
        self.assertEqual(sel.count("GROUP BY CAST("), 2)


class GoldNumbers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con, cls.rows = load_fixture()

    def test_G2_fixture_sizes_match_export(self):
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM silver.readings").fetchone()[0], EXPECTED["fixture_silver_readings_rows"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM silver.outages").fetchone()[0], EXPECTED["fixture_silver_outages_rows"])

    def test_G2_row_count(self):
        self.assertEqual(len(self.rows), EXPECTED["rows"])

    def test_G2_totals_reproduce_verified_numbers(self):
        # columns: report_date, region, daily_kwh, outage_count, outage_cost_usd, customers_affected
        self.assertEqual(sum(r[3] for r in self.rows), EXPECTED["outage_count"])
        self.assertEqual(sum(r[4] for r in self.rows), EXPECTED["outage_cost_usd"])
        self.assertEqual(sum(r[5] for r in self.rows), EXPECTED["customers_affected"])
        self.assertAlmostEqual(sum(r[2] for r in self.rows), EXPECTED["daily_kwh"], delta=EXPECTED["kwh_tolerance"] * 1000)

    def test_G2_grain_unique(self):
        keys = [(r[0], r[1]) for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)))


class GoldEdges(unittest.TestCase):
    R = "CREATE TABLE silver.readings AS SELECT * FROM (VALUES (TIMESTAMP '2026-08-01 00:00:00','A',1.5),(TIMESTAMP '2026-08-01 05:00:00','A',2.5),(TIMESTAMP '2026-08-02 00:00:00','A',4.0)) t(event_time,region,kwh)"

    def test_G3_day_without_outages_yields_zeros(self):
        o = "CREATE TABLE silver.outages AS SELECT * FROM (VALUES (TIMESTAMP '2026-08-01 09:00:00','A',100::BIGINT,7::BIGINT)) t(start_time,region,estimated_cost_usd,customers_affected)"
        _, rows = replay(self.R, o)
        by_day = {str(r[0]): r for r in rows}
        self.assertEqual(by_day["2026-08-01"][2:], (4.0, 1, 100, 7))
        self.assertEqual(by_day["2026-08-02"][2:], (4.0, 0, 0, 0))

    def test_G4_outage_without_readings_is_dropped(self):
        o = "CREATE TABLE silver.outages AS SELECT * FROM (VALUES (TIMESTAMP '2026-08-09 09:00:00','A',999::BIGINT,5::BIGINT)) t(start_time,region,estimated_cost_usd,customers_affected)"
        _, rows = replay(self.R, o)
        self.assertEqual(sum(r[4] for r in rows), 0)
        self.assertEqual(len(rows), 2)

    def test_G3_multiple_outages_same_day_are_summed(self):
        o = "CREATE TABLE silver.outages AS SELECT * FROM (VALUES (TIMESTAMP '2026-08-01 01:00:00','A',10::BIGINT,1::BIGINT),(TIMESTAMP '2026-08-01 23:00:00','A',20::BIGINT,2::BIGINT)) t(start_time,region,estimated_cost_usd,customers_affected)"
        _, rows = replay(self.R, o)
        day = [r for r in rows if str(r[0]) == "2026-08-01"][0]
        self.assertEqual(day[3:], (2, 30, 3))


class SpecAgreement(unittest.TestCase):
    def test_G5_expected_json_matches_spec_text(self):
        text = (SPEC_DIR / "grid_outage_summary.md").read_text()
        for label, key in (("rows", "rows"), ("outage_count total", "outage_count"), ("outage_cost_usd total", "outage_cost_usd"),
                           ("customers_affected total", "customers_affected"), ("daily_kwh total", "daily_kwh")):
            m = re.search(r"- " + re.escape(label) + r": ([0-9.]+)", text)
            self.assertIsNotNone(m, label)
            self.assertEqual(float(m.group(1)), float(EXPECTED[key]), label)

    def test_G5_expected_json_matches_fabric_readme(self):
        readme = (HERE.parent / "README.md").read_text()
        for needle in ("203947", "6109", "109417.775", "40"):
            self.assertIn(needle, readme)


if __name__ == "__main__":
    unittest.main()
