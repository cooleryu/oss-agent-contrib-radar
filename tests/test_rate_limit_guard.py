import unittest

from scripts.common import evaluate_rate_limit


class RateLimitGuardTest(unittest.TestCase):
    def test_allows_authenticated_budget(self):
        ok, reasons = evaluate_rate_limit(
            {
                "resources": {
                    "core": {"remaining": 5000, "limit": 5000},
                    "search": {"remaining": 30, "limit": 30},
                    "code_search": {"remaining": 10, "limit": 10},
                    "graphql": {"remaining": 5000, "limit": 5000},
                }
            },
            min_core=200,
            min_search=2,
            min_code_search=1,
            min_graphql=100,
        )

        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_rejects_low_core_budget(self):
        ok, reasons = evaluate_rate_limit(
            {
                "resources": {
                    "core": {"remaining": 20, "limit": 5000},
                    "search": {"remaining": 30, "limit": 30},
                    "code_search": {"remaining": 10, "limit": 10},
                    "graphql": {"remaining": 5000, "limit": 5000},
                }
            },
            min_core=200,
            min_search=2,
            min_code_search=1,
            min_graphql=100,
        )

        self.assertFalse(ok)
        self.assertIn("core remaining 20 < required 200", reasons)


if __name__ == "__main__":
    unittest.main()
