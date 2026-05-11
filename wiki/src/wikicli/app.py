from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import WikiConfig
from .notebook import Notebook
from .wiki import WikiIndex


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
        self._notebook = Notebook(config)

    @classmethod
    def from_config_path(cls, config_path: str | Path | None) -> "WikiCli":
        """Load config once at the CLI boundary, then run commands against it."""
        return cls(WikiConfig.load(config_path))

    def add(
        self, raw_json: str, *, allow_undeclared: bool = False
    ) -> CommandResult:
        """Validate and apply one agent new-note payload.

        Example input: JSON with title, summary, category, tags, and source.
        Output includes normalized note metadata and files changed by rendering.
        """
        notebook = self._notebook
        index = WikiIndex(self.config, notebook)
        index._ensure_layout()

        note, issues = notebook.parse_new_note(raw_json)
        if issues:
            return CommandResult(False, "add", issues=tuple(issues), exit_code=1)

        assert note is not None
        source_path = notebook.resolve(note.source)
        if not source_path.exists():
            return CommandResult(
                False,
                "add",
                issues=(
                    Issue(
                        "source_missing",
                        f"source note does not exist: {note.source}",
                        source=note.source,
                    ),
                ),
                exit_code=1,
            )
        tree = index.read_tree()
        leafs = tree.leaf_paths()
        if note.category not in leafs and not allow_undeclared:
            return CommandResult(
                False,
                "add",
                issues=(
                    Issue(
                        "category_not_approved",
                        f"category is not an approved leaf: {note.category.display()}",
                    ),
                ),
                exit_code=1,
            )
        data = index.add_note(note, allow_undeclared=allow_undeclared)
        data["allow_undeclared"] = allow_undeclared
        return CommandResult(True, "add", data=data)

    def index(self) -> CommandResult:
        """Reconcile notebook state and generated wiki files."""
        index = WikiIndex(self.config, self._notebook)
        return CommandResult(True, "index", data=index.index())

    def list(
        self,
        category: str | None = None,
        *,
        recursive: bool = False,
        include_body: bool = False,
    ) -> CommandResult:
        """List subcategories and catalog entries at a category level."""
        index = WikiIndex(self.config, self._notebook)
        listing = index.list(category, recursive=recursive)
        entries = [entry.to_json() for entry in listing["entries"]]
        if include_body:
            for item in entries:
                try:
                    note = self._notebook.read(str(item["source"]))
                    item["body"] = Notebook.clean_body_text(note.body)
                except OSError:
                    item["body"] = ""
        return CommandResult(
            True,
            "list",
            data={
                "category": category,
                "recursive": recursive,
                "include_body": include_body,
                "subcategories": listing["subcategories"],
                "entries": entries,
            },
        )

    def search(
        self,
        query: str | None = None,
        *,
        tags: tuple[str, ...] = (),
        limit: int = 10,
        include_body: bool = False,
    ) -> CommandResult:
        """Return ranked search candidates for a user query."""
        index = WikiIndex(self.config, self._notebook)
        results = index.find(
            query, tags=tags, limit=limit, include_body=include_body
        )
        result_dicts = [r.to_json() for r in results]
        if include_body:
            for item in result_dicts:
                try:
                    note = self._notebook.read(str(item["source"]))
                    item["body"] = Notebook.clean_body_text(note.body)
                except OSError:
                    item["body"] = ""
        return CommandResult(
            bool(results),
            "search",
            data={"query": query, "results": result_dicts},
            exit_code=0 if results else 1,
        )

    def lint(self) -> CommandResult:
        """Run read-only workspace integrity checks."""
        index = WikiIndex(self.config, self._notebook)
        issues = tuple(index.lint())
        return CommandResult(
            not any(issue.severity == "error" for issue in issues),
            "lint",
            data={"checked": True, "phase": "skeleton"},
            issues=issues,
            exit_code=1
            if any(issue.severity == "error" for issue in issues)
            else 0,
        )
