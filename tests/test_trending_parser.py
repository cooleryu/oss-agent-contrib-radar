import unittest

from scripts.collect_repo_context import parse_trending_html


class TrendingParserTest(unittest.TestCase):
    def test_ignores_non_title_links_inside_article(self):
        html = """
        <article class="Box-row">
          <a href="/sponsors/luongnv89">Sponsor</a>
          <h2 class="h3 lh-condensed">
            <a href="/coleam00/Archon">
              coleam00 / Archon
            </a>
          </h2>
          <p class="col-9 color-fg-muted my-1 pr-4">
            AI agent knowledge and task management.
          </p>
          <span itemprop="programmingLanguage">Python</span>
          <a class="Link--muted" href="/coleam00/Archon/stargazers">
            9,500
          </a>
          <span class="d-inline-block float-sm-right">
            1,200 stars this month
          </span>
        </article>
        """

        repos = parse_trending_html(html, since="monthly", language="Python")

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["fullName"], "coleam00/Archon")
        self.assertEqual(repos[0]["trending"]["monthlyStars"], 1200)

    def test_parse_repo_name_stars_period_and_language(self):
        html = """
        <article class="Box-row">
          <h2 class="h3 lh-condensed">
            <a href="/openai/openai-agents-python">
              openai / openai-agents-python
            </a>
          </h2>
          <p class="col-9 color-fg-muted my-1 pr-4">
            A lightweight agent framework for tool calling.
          </p>
          <span itemprop="programmingLanguage">Python</span>
          <a class="Link--muted" href="/openai/openai-agents-python/stargazers">
            14,240
          </a>
          <a class="Link--muted" href="/openai/openai-agents-python/forks">
            1,020
          </a>
          <span class="d-inline-block float-sm-right">
            820 stars this week
          </span>
        </article>
        """

        repos = parse_trending_html(html, since="weekly", language="Python")

        self.assertEqual(len(repos), 1)
        repo = repos[0]
        self.assertEqual(repo["fullName"], "openai/openai-agents-python")
        self.assertEqual(repo["description"], "A lightweight agent framework for tool calling.")
        self.assertEqual(repo["primaryLanguage"], "Python")
        self.assertEqual(repo["stars"], 14240)
        self.assertEqual(repo["forks"], 1020)
        self.assertEqual(repo["trending"]["weeklyStars"], 820)
        self.assertEqual(repo["trending"]["language"], "Python")


if __name__ == "__main__":
    unittest.main()
