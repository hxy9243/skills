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
    search: dict[str, Any] | None = None


def load_config(config_path: str | Path | None) -> WikiConfig:
    """Load config JSON or derive a minimal workspace from the current directory."""
    if config_path is None:
        cwd = Path.cwd().resolve()
        return WikiConfig(
            notebook_root=cwd, generated_root=cwd / "_WIKI", include_roots=(cwd,)
        )

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
        _resolve_path(value, notebook_root) for value in raw.get("include_roots", ["."])
    )
    exclude_globs = tuple(str(value) for value in raw.get("exclude_globs", ()))
    search = raw.get("search")
    return WikiConfig(
        notebook_root=notebook_root,
        generated_root=generated_root,
        include_roots=include_roots,
        exclude_globs=exclude_globs,
        search=search if isinstance(search, dict) else None,
    )


def _resolve_path(value: Any, base: Path) -> Path:
    """Resolve a config path relative to a base directory."""
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()
