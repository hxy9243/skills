from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WikiConfig:
    """Resolved filesystem configuration for one generated wiki workspace."""

    notebook_root: Path
    generated_root: Path
    include_roots: tuple[Path, ...]
    exclude_globs: tuple[str, ...] = ()

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "WikiConfig":
        """Load config JSON, auto-discover from cwd, or derive a minimal workspace.

        Resolution order when config_path is None:
        1. Look for ``_WIKI/config.json`` in the current working directory.
        2. Fall back to a bare default (cwd as notebook root, ``_WIKI`` as generated root).
        """
        if config_path is None:
            discovered = Path.cwd().resolve() / "_WIKI" / "config.json"
            if discovered.is_file():
                return cls.load(discovered)
            return cls.default()

        path = Path(config_path).expanduser().resolve()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("config must be a JSON object")

        base = path.parent
        notebook_root = _resolve_path(raw.get("notebook_root", "."), base)
        generated_root = _resolve_path(
            raw.get("generated_root", notebook_root / "_WIKI"), base
        )
        include_roots = tuple(
            _resolve_path(value, notebook_root)
            for value in raw.get("include_roots", ["."])
        )
        exclude_globs = tuple(str(value) for value in raw.get("exclude_globs", ()))
        return cls(
            notebook_root=notebook_root,
            generated_root=generated_root,
            include_roots=include_roots,
            exclude_globs=exclude_globs,
        )

    @classmethod
    def default(cls, cwd: Path | None = None) -> "WikiConfig":
        """Derive a minimal workspace config from the current directory."""
        root = (cwd or Path.cwd()).resolve()
        return cls(
            notebook_root=root,
            generated_root=root / "_WIKI",
            include_roots=(root,),
        )

    @property
    def index_path(self) -> Path:
        """Path to the generated wiki index."""
        return self.generated_root / "index.md"

    @property
    def log_path(self) -> Path:
        """Path to the append-only wiki event log."""
        return self.generated_root / "log.md"

    @property
    def categories_dir(self) -> Path:
        """Path to generated category pages."""
        return self.generated_root / "categories"


def _resolve_path(value: Any, base: Path) -> Path:
    """Resolve a config path relative to a base directory."""
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()
