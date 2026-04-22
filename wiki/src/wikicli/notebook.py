from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import WikiConfig

DEFAULT_EXCLUDE_PARTS = {
    ".git",
    ".obsidian",
    ".trash",
    ".venv",
    "__pycache__",
    "node_modules",
}
TOKEN_RE = re.compile(r"[a-z0-9]+")
WHITESPACE_RE = re.compile(r"\s+")


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

    @classmethod
    def load(cls, config: WikiConfig, source: str) -> "Note":
        """Read one source note with frontmatter, body text, title, tags, and mtime."""
        normalized = cls.normalize_source(source)
        path = cls.resolve_source(config, normalized)
        metadata = NoteMetadata.read(path)
        return cls(
            source=normalized,
            path=path,
            frontmatter=metadata.frontmatter,
            body=metadata.body,
            title=metadata.title(path),
            tags=metadata.tags(),
            mtime_ns=path.stat().st_mtime_ns,
        )

    @classmethod
    def discover(cls, config: WikiConfig) -> list["Note"]:
        """Load every non-generated markdown note from configured include roots."""
        return [
            cls.load(config, cls.source_for_path(config, path))
            for path in cls.iter_paths(config)
        ]

    @classmethod
    def iter_paths(cls, config: WikiConfig) -> list[Path]:
        """Return sorted markdown paths under include roots, excluding generated files."""
        paths: set[Path] = set()
        for root in config.include_roots:
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                resolved = path.resolve()
                if cls.is_excluded(config, resolved):
                    continue
                paths.add(resolved)
        return sorted(
            paths,
            key=lambda item: item.relative_to(config.notebook_root)
            .as_posix()
            .casefold(),
        )

    @staticmethod
    def normalize_source(source: str) -> str:
        """Normalize a notebook-relative source path and reject path traversal.

        Example: `Notes/DSPy.md` stays `Notes/DSPy.md`; `/tmp/x.md` and
        `../x.md` raise `ValueError` before any filesystem access.
        """
        path = Path(source)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe source path: {source}")
        return path.as_posix()

    @classmethod
    def resolve_source(cls, config: WikiConfig, source: str) -> Path:
        """Resolve a normalized source path under the notebook root."""
        normalized = cls.normalize_source(source)
        path = (config.notebook_root / normalized).resolve()
        try:
            path.relative_to(config.notebook_root)
        except ValueError as exc:
            raise ValueError(f"source path escapes notebook root: {source}") from exc
        return path

    @classmethod
    def source_for_path(cls, config: WikiConfig, path: Path) -> str:
        """Return the notebook-relative POSIX source path for an absolute path."""
        return cls.normalize_source(
            path.resolve().relative_to(config.notebook_root).as_posix()
        )

    @staticmethod
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
            output.append(WHITESPACE_RE.sub(" ", stripped).strip())
        return "\n".join(line for line in output if line).strip()

    @staticmethod
    def clean_title(value: str) -> str:
        """Normalize titles and summaries to single-spaced text."""
        return WHITESPACE_RE.sub(" ", value).strip()

    @staticmethod
    def tokenize(value: str) -> tuple[str, ...]:
        """Tokenize text for deterministic lexical matching."""
        return tuple(TOKEN_RE.findall(value.casefold()))

    @classmethod
    def snippet_around(
        cls, text: str, terms: tuple[str, ...], *, max_chars: int = 180
    ) -> str:
        """Return a short snippet around the first matching term."""
        compact = WHITESPACE_RE.sub(" ", text).strip()
        lower = compact.casefold()
        positions = [
            lower.find(term) for term in terms if term and lower.find(term) >= 0
        ]
        if not positions:
            return compact[:max_chars]
        start = max(0, min(positions) - max_chars // 3)
        return compact[start : start + max_chars].strip()

    @staticmethod
    def write_category(path: Path, category: str) -> bool:
        """Write a source note category frontmatter value if it changed."""
        return NoteMetadata.write_category(path, category)

    @staticmethod
    def is_excluded(config: WikiConfig, path: Path) -> bool:
        """Return true when a path should not be treated as a source note."""
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
            return Note.clean_title(title)
        for line in self.body.splitlines():
            if line.startswith("# "):
                return Note.clean_title(line[2:])
        return Note.clean_title(path.stem.replace("_", " "))

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


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
