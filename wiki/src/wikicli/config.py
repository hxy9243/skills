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
    category_rules: list[dict[str, list[str]]]

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
    explicit_path = Path(config_path).expanduser().resolve() if config_path else None
    global_path = Path("~/.wiki/config.json").expanduser()

    if explicit_path:
        raw = read_json(explicit_path, {}) if explicit_path.exists() else {}
    else:
        raw = read_json(global_path, {}) if global_path.exists() else {}
        hinted_notebook_root = Path(raw.get("notebook_root") or str(Path.home() / "Documents" / "kevinhusnotes")).expanduser().resolve()
        hinted_generated_root = Path(raw.get("generated_root") or str(hinted_notebook_root / "_WIKI")).expanduser().resolve()
        local_path = hinted_generated_root / "config.json"
        if local_path.exists():
            raw = merge_dicts(raw, read_json(local_path, {}))

    notebook_root = Path(raw.get("notebook_root") or str(Path.home() / "Documents" / "kevinhusnotes")).expanduser().resolve()
    generated_root = Path(raw.get("generated_root") or str(notebook_root / "_WIKI")).expanduser().resolve()
    include_roots = []
    for item in raw.get("include_roots") or ["."]:
        root = Path(item)
        include_roots.append(root if root.is_absolute() else (notebook_root / root).resolve())
    exclude_globs = sorted(set(DEFAULT_EXCLUDES + list(raw.get("exclude_globs", []))))
    
    category_rules = []
    for rule in raw.get("category_rules", []):
        if "keywords" in rule and "category" in rule:
            category_rules.append({
                "keywords": [str(k) for k in rule["keywords"]],
                "category": [str(c) for c in rule["category"]]
            })

    return WikiConfig(
        notebook_root=notebook_root, 
        include_roots=include_roots, 
        exclude_globs=exclude_globs, 
        generated_root=generated_root,
        category_rules=category_rules
    )


def ensure_layout(config: WikiConfig) -> None:
    config.generated_root.mkdir(parents=True, exist_ok=True)
    config.categories_dir.mkdir(parents=True, exist_ok=True)
    if not config.log_path.exists():
        config.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    if not config.index_path.exists():
        config.index_path.write_text("# Wiki Index\n\n## Category Tree\n\n---\n\n## Skipped System Notes\n- None\n", encoding="utf-8")
