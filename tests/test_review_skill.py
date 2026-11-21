import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SK = ROOT / ".claude" / "skills" / "fabric-gold-review"


class ReviewSkill(unittest.TestCase):
    def test_S1_router_size_and_frontmatter(self):
        text = (SK / "SKILL.md").read_text()
        self.assertLessEqual(len(text.splitlines()), 150)
        m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", text)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "fabric-gold-review")

    def test_S1_referenced_files_exist(self):
        text = (SK / "SKILL.md").read_text()
        for ref in re.findall(r"references/[a-z-]+\.md", text):
            self.assertTrue((SK / ref).exists(), ref)

    def test_S2_checklist_covers_every_rule(self):
        text = (SK / "references" / "checklist.md").read_text().lower()
        for needle in ("203947", "6109", "40 rows", "secret", "free-trial", "client", "small", "test exists",
                       "ga fabric", "invented", "workflow changes", "deploy"):
            self.assertIn(needle, text, needle)

    def test_S2_priority_order_numbers_security_scope(self):
        text = (SK / "references" / "checklist.md").read_text()
        self.assertLess(text.index("## 1. Numbers"), text.index("## 2. Security"))
        self.assertLess(text.index("## 2. Security"), text.index("## 3. Scope"))

    def test_output_shape_fields(self):
        text = (SK / "references" / "output-shape.md").read_text().lower()
        for f in ("severity", "file", "problem", "why it matters", "suggested fix", "advisory"):
            self.assertIn(f, text)

    def test_never_approve_block_merge(self):
        text = (SK / "SKILL.md").read_text().lower()
        for f in ("never approve", "never merge", "never invent"):
            self.assertIn(f, text)


if __name__ == "__main__":
    unittest.main()
