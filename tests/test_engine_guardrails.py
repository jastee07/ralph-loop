from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ralph_loop.engine import init_project, run_loop


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True)
    (root / ".gitignore").write_text("\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)


class EngineGuardrailTests(unittest.TestCase):
    def test_repeated_validation_failures_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            _init_git_repo(root)

            config_path = root / "ralph" / "config.json"
            config = json.loads(config_path.read_text())
            config.update(
                {
                    "require_clean_git": False,
                    "auto_commit": False,
                    "max_iterations": 5,
                    "max_consecutive_failures": 2,
                    "validate_command": "python3 -c 'import sys; sys.exit(1)'",
                }
            )
            config_path.write_text(json.dumps(config, indent=2) + "\n")

            run_loop(
                root=root,
                prd_path=root / "ralph" / "prd.json",
                config_path=config_path,
                launcher="codex",
                model="openai-codex/gpt-5.3-codex",
                max_iterations=None,
                no_commit=True,
                dry_run=True,
            )

            state = json.loads((root / "ralph" / "loop-state.json").read_text())
            self.assertEqual(state["mode"], "blocked")
            self.assertTrue(state["review_needed"])
            self.assertIn("BLOCKED: repeated validation failures", (root / "ralph" / "progress.log").read_text())

    def test_keyboard_interrupt_pauses_for_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_project(root)
            _init_git_repo(root)

            config_path = root / "ralph" / "config.json"
            config = json.loads(config_path.read_text())
            config.update(
                {
                    "require_clean_git": False,
                    "auto_commit": False,
                    "max_iterations": 3,
                }
            )
            config_path.write_text(json.dumps(config, indent=2) + "\n")

            with patch("ralph_loop.engine._run_validation", side_effect=KeyboardInterrupt):
                run_loop(
                    root=root,
                    prd_path=root / "ralph" / "prd.json",
                    config_path=config_path,
                    launcher="codex",
                    model="openai-codex/gpt-5.3-codex",
                    max_iterations=None,
                    no_commit=True,
                    dry_run=True,
                )

            state = json.loads((root / "ralph" / "loop-state.json").read_text())
            self.assertEqual(state["mode"], "paused")
            self.assertEqual(state["last_error"], "interrupted")
            self.assertIn("PAUSED: interrupted by operator", (root / "ralph" / "progress.log").read_text())


if __name__ == "__main__":
    unittest.main()
