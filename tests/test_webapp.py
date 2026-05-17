import sys
import tempfile
import unittest
from pathlib import Path

from internet_testing.webapp import RunConfig, build_run_commands, create_run


class WebAppTests(unittest.TestCase):
    def test_build_run_commands_keeps_llm_generation_separate_from_pytest_execution(self):
        config = RunConfig(
            url="https://www.flipkart.com/",
            max_pages=4,
            max_depth=1,
            llm_command="python scripts/write_tests.py",
        )

        generation, execution = build_run_commands(config, Path("/tmp/run/test_generated.py"))

        self.assertIn("--llm-command", generation)
        self.assertIn("python scripts/write_tests.py", generation)
        self.assertEqual(generation[:3], [sys.executable, "-m", "internet_testing.cli"])
        self.assertEqual(execution[:3], [sys.executable, "-m", "pytest"])
        self.assertNotIn("--llm-command", execution)
        self.assertNotIn("write_tests.py", " ".join(execution))

    def test_build_run_commands_keeps_openai_generation_separate_from_pytest_execution(self):
        config = RunConfig(
            url="https://www.flipkart.com/",
            max_pages=4,
            max_depth=1,
            use_openai=True,
            openai_model="gpt-5.5",
            openai_reasoning_effort="medium",
            agent_max_tool_calls=9,
            agent_max_urls=4,
            agent_max_seconds=30,
        )

        generation, execution = build_run_commands(config, Path("/tmp/run/test_generated.py"))

        self.assertIn("--openai", generation)
        self.assertIn("--openai-model", generation)
        self.assertIn("gpt-5.5", generation)
        self.assertIn("--openai-reasoning-effort", generation)
        self.assertIn("--agent-max-tool-calls", generation)
        self.assertIn("9", generation)
        self.assertIn("--agent-max-urls", generation)
        self.assertIn("4", generation)
        self.assertIn("--agent-max-seconds", generation)
        self.assertIn("30", generation)
        self.assertEqual(generation[:3], [sys.executable, "-m", "internet_testing.cli"])
        self.assertEqual(execution[:3], [sys.executable, "-m", "pytest"])
        self.assertNotIn("--openai", execution)
        self.assertNotIn("--openai-model", execution)
        self.assertNotIn("--agent-max-tool-calls", execution)

    def test_create_run_stores_initial_log_and_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run = create_run(
                RunConfig(url="https://www.amazon.in/", max_pages=2, max_depth=1, llm_command=""),
                runs_dir=Path(tmpdir),
                autostart=False,
            )

            self.assertEqual(run.status, "queued")
            self.assertTrue(run.output_path.name.endswith(".py"))
            self.assertIn("Queued run", "\n".join(run.logs))


if __name__ == "__main__":
    unittest.main()
