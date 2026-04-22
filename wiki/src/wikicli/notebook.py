from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Note:
    """Loaded markdown note with normalized source path and parsed metadata."""

    source: str
    path: Path
    frontmatter: dict[str, object]
    body: str
    title: str
    tags: tuple[str, ...]
    mtime_ns: int


def normalize_source(source: str) -> str:
    """Normalize a notebook-relative source path and reject path traversal.

    Example: `Notes/DSPy.md` stays `Notes/DSPy.md`; `/tmp/x.md` and
    `../x.md` raise `ValueError` before any filesystem access.
    """
    path = Path(source)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe source path: {source}")
    return path.as_posix()
