from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import WikiConfig, load_config


@dataclass(frozen=True)
class Issue:
    """Structured problem report returned in command JSON instead of stderr text."""

    code: str
    message: str
    severity: str = "error"
    source: str | None = None
    path: str | None = None
    line: int | None = None

    def to_json(self) -> dict[str, Any]:
        """Serialize for stable CLI JSON, omitting unset optional fields."""
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class CommandResult:
    """Uniform app-layer result that the CLI prints and exits from."""

    ok: bool
    command: str
    data: dict[str, Any] = field(default_factory=dict)
    issues: tuple[Issue, ...] = ()
    fixes: tuple[dict[str, Any], ...] = ()
    exit_code: int = 0

    def to_json(self) -> dict[str, Any]:
        """Return the public command envelope shared by all CLI commands."""
        return {
            "ok": self.ok,
            "command": self.command,
            "data": self.data,
            "issues": [issue.to_json() for issue in self.issues],
            "fixes": list(self.fixes),
        }


class WikiCli:
    """Programmatic command surface used by argparse adapters and future agents."""

    def __init__(self, config: WikiConfig):
        """Create an app facade over one resolved wiki workspace config."""
        self.config = config

    @classmethod
    def from_config_path(cls, config_path: str | Path | None) -> "WikiCli":
        """Load config once at the CLI boundary, then run commands against it."""
        return cls(load_config(config_path))

    def add_packet(
        self, raw_packet: str, *, allow_undeclared: bool = False
    ) -> CommandResult:
        """Validate one agent packet and return the add command result envelope.

        Example input: JSON with title, summary, category, tags, and source.
        Skeleton output: the normalized packet plus empty changed-files metadata.
        """
        from .packet import parse_packet

        packet, issues = parse_packet(raw_packet)
        if issues:
            return CommandResult(False, "add", issues=tuple(issues), exit_code=1)

        assert packet is not None
        return CommandResult(
            True,
            "add",
            data={
                "packet": packet.to_json(),
                "changed_files": [],
                "indexed_count": 0,
                "allow_undeclared": allow_undeclared,
                "phase": "skeleton",
            },
        )

    def index(self) -> CommandResult:
        """Reconcile notebook state and generated wiki files."""
        return CommandResult(
            True,
            "index",
            data={"changed_files": [], "indexed_count": 0, "phase": "skeleton"},
        )

    def search(self, query: str, *, limit: int) -> CommandResult:
        """Return ranked search candidates for a user query."""
        from .search import search

        results = search(query, limit=limit)
        return CommandResult(
            bool(results),
            "search",
            data={"query": query, "results": results},
            exit_code=0 if results else 1,
        )

    def synthesize_bundle(
        self,
        category: str | None = None,
        tags: tuple[str, ...] = (),
        limit: int = 10,
        include_body: bool = False,
    ) -> CommandResult:
        """Return a deterministic note bundle for agent-written synthesis."""
        return CommandResult(
            True,
            "synthesize",
            data={
                "category": category,
                "tags": list(tags),
                "limit": limit,
                "include_body": include_body,
                "notes": [],
                "phase": "skeleton",
            },
        )

    def lint(self) -> CommandResult:
        """Run read-only workspace integrity checks."""
        from .lint import lint_workspace

        issues = tuple(lint_workspace(self.config))
        return CommandResult(
            not any(issue.severity == "error" for issue in issues),
            "lint",
            data={"checked": True, "phase": "skeleton"},
            issues=issues,
            exit_code=1 if any(issue.severity == "error" for issue in issues) else 0,
        )

    def tree(self) -> CommandResult:
        """Return the approved category tree in command-result form."""
        return CommandResult(True, "tree", data={"categories": [], "phase": "skeleton"})

    def status(self) -> CommandResult:
        """Return resolved workspace paths and lightweight health metadata."""
        return CommandResult(
            True,
            "status",
            data={
                "notebook_root": str(self.config.notebook_root),
                "generated_root": str(self.config.generated_root),
                "include_roots": [str(path) for path in self.config.include_roots],
                "phase": "skeleton",
            },
        )

    def show(self, source: str) -> CommandResult:
        """Return one catalog/source entry by normalized source path."""
        return CommandResult(
            True, "show", data={"source": source, "note": None, "phase": "skeleton"}
        )
