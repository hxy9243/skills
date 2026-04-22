from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wikicli import cli
from wikicli.app import CommandResult, Issue, WikiCli
from wikicli.config import WikiConfig


class CliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.notebook = self.root / "notebook"
        self.generated = self.notebook / "_WIKI"
        self.generated.mkdir(parents=True)
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "notebook_root": str(self.notebook),
                    "generated_root": str(self.generated),
                    "include_roots": ["."],
                    "exclude_globs": ["Templates/**"],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli_json(self, *args: str) -> tuple[int, dict[str, object]]:
        buffer = StringIO()
        with redirect_stdout(buffer):
            rc = cli.main(["--config", str(self.config_path), *args])
        return rc, json.loads(buffer.getvalue())

    def test_command_result_envelope_is_stable_json(self) -> None:
        result = CommandResult(
            False,
            "lint",
            data={"checked": True},
            issues=(Issue("missing", "missing thing", path="/tmp/x"),),
            exit_code=1,
        )

        self.assertEqual(
            result.to_json(),
            {
                "ok": False,
                "command": "lint",
                "data": {"checked": True},
                "issues": [
                    {
                        "code": "missing",
                        "message": "missing thing",
                        "severity": "error",
                        "path": "/tmp/x",
                    }
                ],
                "fixes": [],
            },
        )

    def test_status_prints_json(self) -> None:
        rc, payload = self.run_cli_json("status")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["command"], "status")
        self.assertEqual(
            payload["data"]["generated_root"], str(self.generated.resolve())
        )

    def test_add_rejects_packet_lists_as_json_issue(self) -> None:
        rc, payload = self.run_cli_json("add", "--packet", "[]")

        self.assertEqual(rc, 1)
        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["issues"][0]["code"], "packet_not_object")

    def test_thin_reconcile_alias_uses_index_command(self) -> None:
        rc, payload = self.run_cli_json("reconcile")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["command"], "index")

    def test_wikicli_method_surface_exists(self) -> None:
        app = WikiCli(WikiConfig(self.notebook, self.generated, (self.notebook,)))

        self.assertEqual(app.tree().command, "tree")
        self.assertEqual(app.show("Notes/A.md").command, "show")
        self.assertEqual(app.synthesize_bundle(tags=("x",)).command, "synthesize")


if __name__ == "__main__":
    unittest.main()
