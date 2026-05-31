import unittest

from scripts.collect_repo_context import file_signals


class FileSignalsTest(unittest.TestCase):
    def test_detects_maven_src_test_and_infers_mvn_test(self):
        signals = file_signals(
            files=[
                "pom.xml",
                ".github/workflows/ci.yml",
                "src/main/java/dev/langchain4j/App.java",
                "src/test/java/dev/langchain4j/AppTest.java",
            ],
            readme_text="Java library for tool calling and agents.",
            repo_data={"license": {"spdx_id": "Apache-2.0"}},
        )

        self.assertTrue(signals["hasTests"])
        self.assertIn("mvn test", signals["testCommands"])


if __name__ == "__main__":
    unittest.main()
