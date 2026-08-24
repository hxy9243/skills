#!/usr/bin/env python3
"""
Unit and Integration Tests for Lightweight Project Tracker CLI
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import tracker


class TestProjectTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="tracker_test_")
        self.temp_path = Path(self.temp_dir)
        self.repo_dir = self.temp_path / "test_repo"
        self.repo_dir.mkdir()
        self.vault_dir = self.temp_path / "obsidian_vault"
        self.vault_dir.mkdir()
        self.registry_file = self.temp_path / "registry.json"

        os.environ["PROJECT_TRACKER_REGISTRY"] = str(self.registry_file)

        # Initialize a real git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=str(self.repo_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Agent"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "config", "user.email", "agent@test.com"], cwd=str(self.repo_dir), check=True)
        
        # Create an initial commit
        test_file = self.repo_dir / "README.md"
        test_file.write_text("# Test Repo\nInitial content\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(self.repo_dir), check=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if "PROJECT_TRACKER_REGISTRY" in os.environ:
            del os.environ["PROJECT_TRACKER_REGISTRY"]

    def run_cli(self, args_list: list[str]) -> tuple[int, str, str]:
        parser = tracker.build_parser()
        args = parser.parse_args(args_list)
        # Capture stdout & stderr
        import io
        from contextlib import redirect_stdout, redirect_stderr

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = args.func(args)
        return code, out.getvalue(), err.getvalue()

    def test_init_and_idempotence(self):
        """Test tracker init in Obsidian vault and re-running to update configuration."""
        code, out, err = self.run_cli([
            "init",
            "--repo", str(self.repo_dir),
            "--name", "TestProject",
            "--notes-root", str(self.vault_dir),
            "--cloud-branch", "origin/main",
            "--cloud-task-ref", "task-999",
            "--json",
        ])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["project_name"], "TestProject")
        self.assertIn("harness_memory_hint", data)

        note_file = Path(data["note_file"])
        history_file = Path(data["history_file"])
        self.assertTrue(note_file.exists())
        self.assertTrue(history_file.exists())

        # Check note content
        content = note_file.read_text(encoding="utf-8")
        self.assertIn("# TestProject", content)
        self.assertIn(tracker.START_DELIMITER, content)
        self.assertIn(tracker.END_DELIMITER, content)
        self.assertIn("Revision**: #1", content)

        # Check history.jsonl content
        events = tracker.read_history_events(history_file)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].revision, 1)

        # Re-run init with new cloud task ref
        code2, out2, err2 = self.run_cli([
            "init",
            "--repo", str(self.repo_dir),
            "--cloud-task-ref", "task-1000",
            "--json",
        ])
        self.assertEqual(code2, 0)
        reg = tracker.load_registry()
        self.assertEqual(reg[str(self.repo_dir)]["cloud_task_ref"], "task-1000")
        # History length remains 1
        events2 = tracker.read_history_events(history_file)
        self.assertEqual(len(events2), 1)

    def test_checkpoint_preserves_human_notes(self):
        """Test checkpoint updates generated section while preserving human notes above and below."""
        # Init
        self.run_cli(["init", "--repo", str(self.repo_dir), "--notes-root", str(self.vault_dir)])
        _, _, note_path, history_path, _ = tracker.resolve_project_config(repo_override=str(self.repo_dir))

        # Add custom human text before and after delimiters
        custom_content = (
            "# My Custom Header\n\n"
            "Important context for the team.\n\n"
            f"{tracker.START_DELIMITER}\nOld Status\n{tracker.END_DELIMITER}\n\n"
            "## Decisions and Notes\n\n"
            "- Decision 1: Use Python standard library\n"
            "- Decision 2: Plaintext first\n"
        )
        note_path.write_text(custom_content, encoding="utf-8")

        # Record checkpoint
        code, out, err = self.run_cli([
            "checkpoint",
            "--repo", str(self.repo_dir),
            "--summary", "Built auth system",
            "--actions", "Created login route, Created token validator",
            "--verification", "pytest passed 10/10",
            "--next-step", "Build dashboard",
            "--harness", "unit-test",
            "--json",
        ])
        self.assertEqual(code, 0)

        updated_note = note_path.read_text(encoding="utf-8")
        self.assertIn("# My Custom Header", updated_note)
        self.assertIn("Important context for the team.", updated_note)
        self.assertIn("## Decisions and Notes", updated_note)
        self.assertIn("Decision 1: Use Python standard library", updated_note)
        self.assertIn("Summary\nBuilt auth system", updated_note)
        self.assertIn("1. Created login route", updated_note)
        self.assertIn("2. Created token validator", updated_note)
        self.assertIn("Verification\npytest passed 10/10", updated_note)
        self.assertIn("Next Step\nBuild dashboard", updated_note)
        self.assertIn("Revision**: #2", updated_note)

    def test_checkpoint_concurrency_locking(self):
        """Verify concurrent checkpoints do not interleave or corrupt history."""
        self.run_cli(["init", "--repo", str(self.repo_dir), "--notes-root", str(self.vault_dir)])
        _, _, note_path, history_path, _ = tracker.resolve_project_config(repo_override=str(self.repo_dir))

        num_threads = 5
        errors = []

        def worker(thread_id: int):
            try:
                code, out, err = self.run_cli([
                    "checkpoint",
                    "--repo", str(self.repo_dir),
                    "--summary", f"Concurrent checkpoint from thread {thread_id}",
                    "--actions", f"Action {thread_id}",
                    "--lock-timeout", "10.0",
                ])
                if code != 0:
                    errors.append(f"Thread {thread_id} failed with error: {err}")
            except Exception as e:
                errors.append(f"Thread {thread_id} raised: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        events = tracker.read_history_events(history_path)
        # 1 init + 5 checkpoints = 6 total events
        self.assertEqual(len(events), 6)
        revisions = [e.revision for e in events]
        self.assertEqual(revisions, list(range(1, 7)))

    def test_stale_revision_detection(self):
        """Test that checkpoint detects stale revisions and handles retry."""
        self.run_cli(["init", "--repo", str(self.repo_dir), "--notes-root", str(self.vault_dir)])

        # Current revision is 1. If we provide expected revision 0 (stale), it should reject
        code, out, err = self.run_cli([
            "checkpoint",
            "--repo", str(self.repo_dir),
            "--summary", "Stale check",
            "--expected-revision", "0",
        ])
        self.assertEqual(code, 1)
        self.assertIn("Stale revision detected", err)

        # Providing matching expected revision 1 should succeed and bump to 2
        code, out, err = self.run_cli([
            "checkpoint",
            "--repo", str(self.repo_dir),
            "--summary", "Valid revision check",
            "--expected-revision", "1",
        ])
        self.assertEqual(code, 0)

    def test_history_limit_and_formats(self):
        """Test history --limit n with Markdown and JSON outputs."""
        self.run_cli(["init", "--repo", str(self.repo_dir), "--notes-root", str(self.vault_dir)])

        for i in range(5):
            self.run_cli([
                "checkpoint",
                "--repo", str(self.repo_dir),
                "--summary", f"Checkpoint {i+1}",
                "--actions", f"Step {i+1}",
            ])

        # Test history --limit 3 (JSON)
        code, out, err = self.run_cli([
            "history",
            "--repo", str(self.repo_dir),
            "--limit", "3",
            "--format", "json",
        ])
        self.assertEqual(code, 0)
        items = json.loads(out)
        self.assertEqual(len(items), 3)
        # Newest first by default
        self.assertEqual(items[0]["summary"], "Checkpoint 5")
        self.assertEqual(items[1]["summary"], "Checkpoint 4")
        self.assertEqual(items[2]["summary"], "Checkpoint 3")

        # Test history --limit 2 (Markdown)
        code, out, err = self.run_cli([
            "history",
            "--repo", str(self.repo_dir),
            "--limit", "2",
            "--format", "markdown",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Showing 2 checkpoints", out)
        self.assertIn("Checkpoint 5", out)
        self.assertIn("Checkpoint 4", out)
        self.assertNotIn("Checkpoint 1", out)

    def test_lint_with_new_commits_and_git_evidence(self):
        """Test lint imports new git commits as git-evidence when cloud task is unreachable."""
        self.run_cli(["init", "--repo", str(self.repo_dir), "--notes-root", str(self.vault_dir)])

        # Create 2 new commits in git repo
        f1 = self.repo_dir / "feature1.py"
        f1.write_text("print('f1')\n")
        subprocess.run(["git", "add", "feature1.py"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "feat: add feature 1"], cwd=str(self.repo_dir), check=True)

        f2 = self.repo_dir / "feature2.py"
        f2.write_text("print('f2')\n")
        subprocess.run(["git", "add", "feature2.py"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "feat: add feature 2"], cwd=str(self.repo_dir), check=True)

        # Run lint
        code, out, err = self.run_cli([
            "lint",
            "--repo", str(self.repo_dir),
            "--no-fetch",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Imported checkpoint", out)

        _, _, note_path, history_path, _ = tracker.resolve_project_config(repo_override=str(self.repo_dir))
        events = tracker.read_history_events(history_path)
        latest = events[-1]
        self.assertEqual(latest.source, "git-evidence")
        self.assertTrue(latest.missing_narrative_context)
        self.assertIn("feat: add feature 2", latest.summary)
        # Ensure no hallucinated verification or decisions
        self.assertIsNone(latest.verification)

        # Running lint again should find no untracked commits
        code2, out2, err2 = self.run_cli([
            "lint",
            "--repo", str(self.repo_dir),
            "--no-fetch",
        ])
        self.assertEqual(code2, 0)
        self.assertIn("All recent Git commits are represented", out2)

    def test_doctor_diagnostics_and_repairs(self):
        """Test doctor diagnostic checks and non-destructive repair reporting."""
        # Uninitialized repo
        code, out, err = self.run_cli(["doctor", "--repo", str(self.repo_dir)])
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)
        self.assertIn("Registry Resolution", out)

        # Initialize
        self.run_cli(["init", "--repo", str(self.repo_dir), "--notes-root", str(self.vault_dir)])
        code, out, err = self.run_cli(["doctor", "--repo", str(self.repo_dir)])
        self.assertEqual(code, 0)
        self.assertIn("All project tracker diagnostics passed", out)

        _, _, note_path, history_path, _ = tracker.resolve_project_config(repo_override=str(self.repo_dir))

        # Check revision mismatch detection
        note_path.write_text("# Test\n<!-- PROJECT-TRACKER:START -->\nRevision: #999\n<!-- PROJECT-TRACKER:END -->\n", encoding="utf-8")
        code, out, err = self.run_cli(["doctor", "--repo", str(self.repo_dir)])
        self.assertEqual(code, 1)
        self.assertIn("Summary Revision Consistency", out)

        # Re-save note
        events = tracker.read_history_events(history_path)
        tracker.update_markdown_note(note_path, "TestProject", events[-1])

        # Corrupt one line in history.jsonl
        with open(history_path, "a", encoding="utf-8") as f:
            f.write("{invalid json line\n")

        code, out, err = self.run_cli(["doctor", "--repo", str(self.repo_dir)])
        self.assertEqual(code, 1)
        self.assertIn("JSONL Validity", out)
        self.assertIn("Never delete history lines blindly; repair broken JSON syntax.", out)

    def test_lint_with_cloud_messenger(self):
        """Test lint with simulated cloud task messenger command."""
        messenger_script = self.temp_path / "mock_messenger.sh"
        messenger_script.write_text(
            '#!/bin/sh\necho \'{"summary": "Cloud agent finished payment API", "actions": ["Added stripe webhook", "Verified charges"], "verification": "all pass"}\'',
            encoding="utf-8",
        )
        messenger_script.chmod(0o755)

        self.run_cli([
            "init",
            "--repo", str(self.repo_dir),
            "--notes-root", str(self.vault_dir),
            "--cloud-branch", "main",
            "--cloud-task-ref", "task-cloud-1",
            "--cloud-messenger-cmd", str(messenger_script),
        ])

        # Add commit
        f1 = self.repo_dir / "payment.py"
        f1.write_text("print('payment')\n")
        subprocess.run(["git", "add", "payment.py"], cwd=str(self.repo_dir), check=True)
        subprocess.run(["git", "commit", "-m", "feat: stripe payment"], cwd=str(self.repo_dir), check=True)

        code, out, err = self.run_cli([
            "lint",
            "--repo", str(self.repo_dir),
            "--no-fetch",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Imported checkpoint", out)
        self.assertIn("cloud", out)

        _, _, note_path, history_path, _ = tracker.resolve_project_config(repo_override=str(self.repo_dir))
        events = tracker.read_history_events(history_path)
        latest = events[-1]
        self.assertEqual(latest.source, "cloud")
        self.assertEqual(latest.summary, "Cloud agent finished payment API")
        self.assertEqual(latest.verification, "all pass")
        self.assertFalse(latest.missing_narrative_context)


if __name__ == "__main__":
    unittest.main()
