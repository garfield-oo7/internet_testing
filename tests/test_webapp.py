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
