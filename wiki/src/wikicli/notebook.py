from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import WikiConfig


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


@dataclass(frozen=True)
class NoteMetadata:
    """Parsed frontmatter/body plus common metadata operations for one note."""

    frontmatter: dict[str, object]
    body: str

    @classmethod
    def parse(cls, text: str) -> "NoteMetadata":
        """Parse simple Obsidian-style YAML frontmatter and body text."""
        if not text.startswith("---\n"):
            return cls({}, text)
        raw_frontmatter, sep, body = text.partition("\n---\n")
        if not sep:
            return cls({}, text)

        frontmatter: dict[str, object] = {}
        current_list_key: str | None = None
        for line in raw_frontmatter.splitlines()[1:]:
            if not line.strip():
                current_list_key = None
                continue
            if current_list_key and line.lstrip().startswith("- "):
                values = frontmatter.setdefault(current_list_key, [])
                if isinstance(values, list):
                    values.append(_unquote(line.split("- ", 1)[1].strip()))
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key = key.strip().lower()
            value = value.strip()
            if not value:
                frontmatter[key] = []
                current_list_key = key
            else:
                frontmatter[key] = _unquote(value)
                current_list_key = None
        return cls(frontmatter, body)

    @classmethod
    def read(cls, path: Path) -> "NoteMetadata":
        """Read and parse metadata from a markdown file."""
        return cls.parse(path.read_text(encoding="utf-8"))

    def render(self) -> str:
        """Render frontmatter and body using the supported YAML subset."""
        if not self.frontmatter:
            return self.body
        lines = ["---"]
        for key in sorted(self.frontmatter):
            value = self.frontmatter[key]
            if isinstance(value, (list, tuple)):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"- {json.dumps(str(item), ensure_ascii=False)}")
            else:
                lines.append(f"{key}: {json.dumps(str(value), ensure_ascii=False)}")
        lines.append("---")
        return "\n".join(lines) + "\n" + self.body.lstrip("\n")

    def title(self, path: Path) -> str:
        """Prefer frontmatter title, then first H1, then the filename stem."""
        title = self.frontmatter.get("title")
        if isinstance(title, str) and title.strip():
            return clean_title(title)
        for line in self.body.splitlines():
            if line.startswith("# "):
                return clean_title(line[2:])
        return clean_title(path.stem.replace("_", " "))

    def tags(self) -> tuple[str, ...]:
        """Normalize frontmatter tags to sorted `#tag` strings."""
        raw = self.frontmatter.get("tags", ())
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return ()
        tags = []
        for item in raw:
            tag = str(item).strip().strip("'\"")
            if not tag:
                continue
            tags.append(tag if tag.startswith("#") else f"#{tag}")
        return tuple(sorted(set(tags)))

    def with_category(self, category: str) -> "NoteMetadata":
        """Return a copy with the category frontmatter value set."""
        frontmatter = dict(self.frontmatter)
        frontmatter["category"] = category
        return NoteMetadata(frontmatter, self.body)

    @classmethod
    def write_category(cls, path: Path, category: str) -> bool:
        """Write a source note category frontmatter value if it changed."""
        original = path.read_text(encoding="utf-8")
        metadata = cls.parse(original)
        if metadata.frontmatter.get("category") == category:
            return False
        updated = metadata.with_category(category).render()
        path.write_text(updated, encoding="utf-8")
        return updated != original


DEFAULT_EXCLUDE_PARTS = {
    ".git",
    ".obsidian",
    ".trash",
    ".venv",
    "__pycache__",
    "node_modules",
}


def normalize_source(source: str) -> str:
    """Normalize a notebook-relative source path and reject path traversal.

    Example: `Notes/DSPy.md` stays `Notes/DSPy.md`; `/tmp/x.md` and
    `../x.md` raise `ValueError` before any filesystem access.
    """
    path = Path(source)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe source path: {source}")
    return path.as_posix()


def resolve_source(config: WikiConfig, source: str) -> Path:
    """Resolve a normalized source path under the notebook root."""
    normalized = normalize_source(source)
    path = (config.notebook_root / normalized).resolve()
    try:
        path.relative_to(config.notebook_root)
    except ValueError as exc:
        raise ValueError(f"source path escapes notebook root: {source}") from exc
    return path


def source_for_path(config: WikiConfig, path: Path) -> str:
    """Return the notebook-relative POSIX source path for an absolute path."""
    return normalize_source(path.resolve().relative_to(config.notebook_root).as_posix())


def discover_notes(config: WikiConfig) -> list[Note]:
    """Load every non-generated markdown note from configured include roots."""
    return [
        load_note(config, source_for_path(config, path))
        for path in iter_markdown_paths(config)
    ]


def iter_markdown_paths(config: WikiConfig) -> list[Path]:
    """Return sorted markdown paths under include roots, excluding generated files."""
    paths: set[Path] = set()
    for root in config.include_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            resolved = path.resolve()
            if _is_excluded(config, resolved):
                continue
            paths.add(resolved)
    return sorted(
        paths,
        key=lambda item: item.relative_to(config.notebook_root).as_posix().casefold(),
    )


def load_note(config: WikiConfig, source: str) -> Note:
    """Read one source note with frontmatter, body text, title, tags, and mtime."""
    normalized = normalize_source(source)
    path = resolve_source(config, normalized)
    metadata = NoteMetadata.read(path)
    return Note(
        source=normalized,
        path=path,
        frontmatter=metadata.frontmatter,
        body=metadata.body,
        title=metadata.title(path),
        tags=metadata.tags(),
        mtime_ns=path.stat().st_mtime_ns,
    )


def parse_markdown(text: str) -> tuple[dict[str, object], str]:
    """Parse markdown into frontmatter/body; prefer `NoteMetadata.parse` in new code."""
    metadata = NoteMetadata.parse(text)
    return metadata.frontmatter, metadata.body


def render_markdown(frontmatter: dict[str, object], body: str) -> str:
    """Render markdown; prefer `NoteMetadata.render` in new code."""
    return NoteMetadata(frontmatter, body).render()


def set_frontmatter_category(path: Path, category: str) -> bool:
    """Compatibility wrapper for `NoteMetadata.write_category`."""
    return NoteMetadata.write_category(path, category)


def extract_title(frontmatter: dict[str, object], body: str, path: Path) -> str:
    """Compatibility wrapper for `NoteMetadata.title`."""
    return NoteMetadata(frontmatter, body).title(path)


def extract_tags(frontmatter: dict[str, object]) -> tuple[str, ...]:
    """Compatibility wrapper for `NoteMetadata.tags`."""
    return NoteMetadata(frontmatter, "").tags()


def clean_body_text(body: str) -> str:
    """Strip obvious markdown syntax noise for snippets and lexical search."""
    output: list[str] = []
    in_code = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or stripped.startswith("!["):
            continue
        output.append(re.sub(r"\s+", " ", stripped).strip())
    return "\n".join(line for line in output if line).strip()


def clean_title(value: str) -> str:
    """Normalize titles and summaries to single-spaced text."""
    return re.sub(r"\s+", " ", value).strip()


def tokenize(value: str) -> tuple[str, ...]:
    """Tokenize text for deterministic lexical matching."""
    return tuple(re.findall(r"[a-z0-9]+", value.casefold()))


def snippet_around(text: str, terms: tuple[str, ...], *, max_chars: int = 180) -> str:
    """Return a short snippet around the first matching term."""
    compact = re.sub(r"\s+", " ", text).strip()
    lower = compact.casefold()
    positions = [lower.find(term) for term in terms if term and lower.find(term) >= 0]
    if not positions:
        return compact[:max_chars]
    start = max(0, min(positions) - max_chars // 3)
    return compact[start : start + max_chars].strip()


def _is_excluded(config: WikiConfig, path: Path) -> bool:
    try:
        rel = path.relative_to(config.notebook_root)
    except ValueError:
        return True
    rel_posix = rel.as_posix()
    if config.generated_root == path or config.generated_root in path.parents:
        return True
    if any(part in DEFAULT_EXCLUDE_PARTS for part in rel.parts):
        return True
    return any(
        fnmatch.fnmatch(rel_posix, pattern) or fnmatch.fnmatch(path.name, pattern)
        for pattern in config.exclude_globs
    )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
