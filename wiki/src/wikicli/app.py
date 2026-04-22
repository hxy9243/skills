from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import WikiConfig, load_config


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    severity: str = "error"
    source: str | None = None
    path: str | None = None
    line: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    command: str
    data: dict[str, Any] = field(default_factory=dict)
    issues: tuple[Issue, ...] = ()
    fixes: tuple[dict[str, Any], ...] = ()
    exit_code: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "command": self.command,
            "data": self.data,
            "issues": [issue.to_json() for issue in self.issues],
            "fixes": list(self.fixes),
        }


class WikiCli:
    def __init__(self, config: WikiConfig):
        self.config = config

    @classmethod
    def from_config_path(cls, config_path: str | Path | None) -> "WikiCli":
        return cls(load_config(config_path))

    def add_packet(self, raw_packet: str, *, allow_undeclared: bool = False) -> CommandResult:
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
        return CommandResult(True, "index", data={"changed_files": [], "indexed_count": 0, "phase": "skeleton"})

    def search(self, query: str, *, limit: int) -> CommandResult:
        from .search import search

        results = search(query, limit=limit)
        return CommandResult(bool(results), "search", data={"query": query, "results": results}, exit_code=0 if results else 1)

    def synthesize_bundle(
        self,
        category: str | None = None,
        tags: tuple[str, ...] = (),
        limit: int = 10,
        include_body: bool = False,
    ) -> CommandResult:
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
        return CommandResult(True, "tree", data={"categories": [], "phase": "skeleton"})

    def status(self) -> CommandResult:
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
        return CommandResult(True, "show", data={"source": source, "note": None, "phase": "skeleton"})
