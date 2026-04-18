from __future__ import annotations

import fnmatch
from pathlib import Path

from wikicli.config import DEFAULT_EXCLUDES, WikiConfig


def normalize_path(path: Path) -> str:
    """
    Convert a Path object to a POSIX-style string path.
    
    Args:
        path (Path): The path to normalize.
        
    Returns:
        str: The normalized path string.
    """
    return path.as_posix()


def gather_source_files(config: WikiConfig) -> list[Path]:
    """
    Discover all markdown files in the notebook, respecting exclusions.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        
    Returns:
        list[Path]: A sorted list of valid source markdown file paths.
    """
    files: list[Path] = []
    generated_marker = normalize_path(config.generated_root)
    for root in config.include_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            resolved = path.resolve()
            rel = normalize_path(resolved.relative_to(config.notebook_root))
            if normalize_path(resolved).startswith(generated_marker):
                continue
            if any(part in DEFAULT_EXCLUDES for part in resolved.relative_to(config.notebook_root).parts):
                continue
            if any(fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in config.exclude_globs):
                continue
            files.append(resolved)
    return sorted(set(files))


def source_mtime_ns(config: WikiConfig, source: str) -> int | None:
    """
    Get the modification time of a source file in nanoseconds.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        source (str): The relative path to the source file.
        
    Returns:
        int | None: The mtime in nanoseconds, or None if the file doesn't exist.
    """
    path = (config.notebook_root / source).resolve()
    if not path.exists():
        return None
    return path.stat().st_mtime_ns


def ensure_layout(config: WikiConfig) -> None:
    """
    Initialize the generated wiki directory structure and core files.
    
    Creates the categories directory, an empty log.md if it doesn't exist,
    and a default index.md if it doesn't exist.
    
    Args:
        config (WikiConfig): The active wiki configuration.
    """
    config.generated_root.mkdir(parents=True, exist_ok=True)
    config.categories_dir.mkdir(parents=True, exist_ok=True)
    if not config.log_path.exists():
        config.log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    if not config.index_path.exists():
        config.index_path.write_text("# Wiki Index\n\n## Category Tree\n\n---\n\n## Skipped System Notes\n- None\n", encoding="utf-8")
