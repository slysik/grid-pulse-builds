import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gold_sql  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
