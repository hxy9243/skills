from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_EXCLUDES = [
    ".git",
    ".obsidian",
    ".trash",
    ".venv",
    "__pycache__",
    "node_modules",
    "_WIKI",
]


@dataclass
class WikiConfig:
    notebook_root: Path
    include_roots: list[Path]
    exclude_globs: list[str]
    generated_root: Path

    @property
    def categories_dir(self) -> Path:
        return self.generated_root / "categories"

    @property
    def index_path(self) -> Path:
        return self.generated_root / "index.md"

    @property
    def log_path(self) -> Path:
        return self.generated_root / "log.md"

    @property
    def category_tree_path(self) -> Path:
        return self.generated_root / "index.md"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | None) -> WikiConfig:
    import os
    
    explicit_path = Path(config_path).expanduser().resolve() if config_path else None
    global_path = Path("~/.wiki/config.json").expanduser()

    raw = {}
    notebook_root = None
    generated_root = None

    if explicit_path:
        raw = read_json(explicit_path, {}) if explicit_path.exists() else {}
        notebook_root = explicit_path.parent.parent if explicit_path.parent.name == "_WIKI" else explicit_path.parent
        generated_root = notebook_root / "_WIKI"
    else:
        # Traverse upwards to find _WIKI or config.json
        current_dir = Path(os.getcwd()).resolve()
        for parent in [current_dir, *current_dir.parents]:
            local_wiki = parent / "_WIKI"
            if local_wiki.is_dir():
                notebook_root = parent
                generated_root = local_wiki
                local_config = local_wiki / "config.json"
                if local_config.exists():
                    raw = read_json(local_config, {})
                break
        
        if not notebook_root:
            raw = read_json(global_path, {}) if global_path.exists() else {}
            notebook_root = Path(raw.get("notebook_root") or os.getcwd()).expanduser().resolve()
            generated_root = Path(raw.get("generated_root") or str(notebook_root / "_WIKI")).expanduser().resolve()

    notebook_root = Path(raw.get("notebook_root") or notebook_root).expanduser().resolve()
    generated_root = Path(raw.get("generated_root") or generated_root).expanduser().resolve()

    include_roots = []
    for item in raw.get("include_roots") or ["."]:
        root = Path(item)
        include_roots.append(root if root.is_absolute() else (notebook_root / root).resolve())
    exclude_globs = sorted(set(DEFAULT_EXCLUDES + list(raw.get("exclude_globs", []))))
    
    return WikiConfig(
        notebook_root=notebook_root, 
        include_roots=include_roots, 
        exclude_globs=exclude_globs, 
        generated_root=generated_root
    )



