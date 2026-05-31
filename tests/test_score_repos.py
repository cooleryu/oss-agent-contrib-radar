import unittest

from scripts.score_repos import issue_score, score_repo


class ScoreReposTest(unittest.TestCase):
    def test_issue_score_accepts_comment_lists_from_gh_cli(self):
        issue = {
            "title": "Bug in tool call tracing",
            "labels": [{"name": "bug"}],
            "comments": [{"author": {"login": "maintainer"}}],
            "assignees": [],
        }

        self.assertGreaterEqual(issue_score(issue), 8)

    def test_scores_agent_repo_that_passes_hard_filters(self):
        context = {
            "fullName": "openai/openai-agents-python",
            "url": "https://github.com/openai/openai-agents-python",
            "description": "Agent framework with tool calling, tracing, and handoffs.",
            "stars": 14000,
            "forks": 1000,
            "primaryLanguage": "Python",
            "isArchived": False,
            "isFork": False,
            "topics": ["agents", "llm", "tool-calling"],
            "readmeExcerpt": "Build AI agents with tools, tracing, evals, and workflows.",
            "signals": {
                "hasReadme": True,
                "hasCi": True,
                "hasTests": True,
                "hasContributing": True,
                "testCommands": ["pytest"],
            },
            "trending": {
                "periods": ["weekly", "monthly"],
                "weeklyStars": 820,
                "monthlyStars": 2400,
            },
        }
        activity = {
            "lastCommitAt": "2026-04-25T00:00:00Z",
            "lastMergedPrAt": "2026-04-24T00:00:00Z",
            "lastIssueOrPrUpdatedAt": "2026-04-23T00:00:00Z",
            "recentMergedPrCount7d": 5,
            "openPrCount": 20,
            "openIssues": [
                {
                    "title": "Improve tracing around tool call failures",
                    "url": "https://github.com/openai/openai-agents-python/issues/1",
                    "labels": [{"name": "bug"}, {"name": "help wanted"}],
                    "updatedAt": "2026-04-23T00:00:00Z",
                    "comments": 3,
                }
            ],
            "workflowRuns": [{"status": "completed", "conclusion": "success"}],
        }

        result = score_repo(context, activity, now_iso="2026-04-26T00:00:00Z")

        self.assertTrue(result["passedFilters"])
        self.assertEqual(result["rejectionReasons"], [])
        self.assertGreaterEqual(result["score"], 80)
        self.assertEqual(result["topIssues"][0]["recommendation"], "Pick")

    def test_rejects_repo_without_ci(self):
        context = {
            "fullName": "example/no-ci-agent",
            "url": "https://github.com/example/no-ci-agent",
            "description": "Agent framework",
            "stars": 2000,
            "primaryLanguage": "Python",
            "isArchived": False,
            "isFork": False,
            "topics": ["agent"],
            "readmeExcerpt": "Agent framework.",
            "signals": {
                "hasReadme": True,
                "hasCi": False,
                "hasTests": True,
                "hasContributing": False,
                "testCommands": ["pytest"],
            },
            "trending": {"periods": ["weekly"], "weeklyStars": 100},
        }
        activity = {
            "lastCommitAt": "2026-04-25T00:00:00Z",
            "lastMergedPrAt": "2026-04-24T00:00:00Z",
            "lastIssueOrPrUpdatedAt": "2026-04-23T00:00:00Z",
            "recentMergedPrCount7d": 2,
            "openPrCount": 10,
            "openIssues": [],
            "workflowRuns": [],
        }

        result = score_repo(context, activity, now_iso="2026-04-26T00:00:00Z")

        self.assertFalse(result["passedFilters"])
        self.assertIn("missing_ci", result["rejectionReasons"])


if __name__ == "__main__":
    unittest.main()
