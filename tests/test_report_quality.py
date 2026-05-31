import unittest

from scripts.generate_repo_report import report_lines


class ReportQualityTest(unittest.TestCase):
    def test_report_contains_anti_pr_farming_boundary(self):
        lines = report_lines(scored=[], rejected=[])
        text = "\n".join(lines)

        self.assertIn("Contribution Ethics", text)
        self.assertIn("not a PR farming queue", text)
        self.assertIn("Prefer zero recommendations over low-quality recommendations", text)


if __name__ == "__main__":
    unittest.main()
