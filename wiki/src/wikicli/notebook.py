from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .category import CategoryPath
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
    """Loaded markdown note — pure data record."""

    source: str
    path: Path
    frontmatter: dict[str, object]
    body: str
    title: str
    tags: tuple[str, ...]
    created: datetime
    last_modified: datetime


@dataclass(frozen=True)
class NewNote:
    """Agent-produced classification payload for one source note.

    Renamed from Packet. Parsed from untrusted JSON by Notebook.parse_new_note().
    """

    title: str
    summary: str
    category: CategoryPath
    tags: tuple[str, ...]
    search_terms: tuple[str, ...]
    source: str

    def to_json(self) -> dict[str, Any]:
        """Serialize the normalized note for CLI responses and log events."""
        return {
            "title": self.title,
            "summary": self.summary,
            "category": self.category.to_json(),
            "tags": list(self.tags),
            "search_terms": list(self.search_terms),
            "source": self.source,
        }


class Notebook:
    """Source-note filesystem operations for one wiki workspace."""

    def __init__(self, config: WikiConfig) -> None:
        self.config = config

    # --- read / write ---

    def read(self, source: str) -> Note:
        """Read one source note with frontmatter, body text, title, tags, and timestamps."""
        normalized = self.normalize_source(source)
        path = self.resolve(normalized)
        metadata = NoteMetadata.read(path)
        stat = path.stat()
        return Note(
            source=normalized,
            path=path,
            frontmatter=metadata.frontmatter,
            body=metadata.body,
            title=metadata.title(path),
            tags=metadata.tags(),
            created=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )

    def readdir(
        self, directory: str | None = None, *, recursive: bool = True
    ) -> list[Note]:
        """Read notes from a directory under the notebook root."""
        base = self.config.notebook_root
        if directory:
            base = base / directory
        if not base.exists():
            return []
        pattern = "**/*.md" if recursive else "*.md"
        notes: list[Note] = []
        for path in sorted(base.glob(pattern)):
            resolved = path.resolve()
            if self._is_excluded(resolved):
                continue
            notes.append(self.read(self.source_for_path(resolved)))
        return notes

    def write(self, source: str, text: str) -> bool:
        """Write text to a source note, creating directories as needed."""
        path = self.resolve(source)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") == text:
            return False
        path.write_text(text, encoding="utf-8")
        return True

    def update_property(self, source: str, key: str, value: object) -> bool:
        """Update a single frontmatter property on a source note."""
        path = self.resolve(source)
        original = path.read_text(encoding="utf-8")
        metadata = NoteMetadata.parse(original)
        frontmatter = dict(metadata.frontmatter)
        if frontmatter.get(key) == value:
            return False
        frontmatter[key] = value
        updated = NoteMetadata(frontmatter, metadata.body).render()
        path.write_text(updated, encoding="utf-8")
        return updated != original

    # --- discovery ---

    def exists(self, source: str) -> bool:
        """Return true if a source note exists on disk."""
        try:
            path = self.resolve(source)
            return path.exists()
        except ValueError:
            return False

    def discover(self) -> list[Note]:
        """Load every non-generated markdown note from configured include roots."""
        return [self.read(self.source_for_path(path)) for path in self._iter_paths()]

    def resolve(self, source: str) -> Path:
        """Resolve a normalized source path under the notebook root."""
        normalized = self.normalize_source(source)
        path = (self.config.notebook_root / normalized).resolve()
        try:
            path.relative_to(self.config.notebook_root)
        except ValueError as exc:
            raise ValueError(f"source path escapes notebook root: {source}") from exc
        return path

    def source_for_path(self, path: Path) -> str:
        """Return the notebook-relative POSIX source path for an absolute path."""
        return self.normalize_source(
            path.resolve().relative_to(self.config.notebook_root).as_posix()
        )

    def build_directory_tree(
        self, directory: str | None = None
    ) -> dict[str, Any]:
        """Build a filesystem tree dict from notes on disk."""
        base = self.config.notebook_root
        if directory:
            base = base / directory
        tree: dict[str, Any] = {"name": base.name, "children": []}
        if not base.exists():
            return tree
        for path in sorted(base.iterdir()):
            resolved = path.resolve()
            if self._is_excluded(resolved):
                continue
            if path.is_dir():
                tree["children"].append(
                    self.build_directory_tree(
                        str(path.relative_to(self.config.notebook_root))
                    )
                )
            elif path.suffix == ".md":
                tree["children"].append({"name": path.name, "children": []})
        return tree

    # --- parsing ---

    def parse_new_note(self, raw_json: str) -> tuple[NewNote | None, list[Any]]:
        """Parse untrusted new-note JSON into a normalized NewNote or issues.

        Success input:
        `{"title":"DSPy","summary":"Prompt optimization","category":"CS > AI","tags":["#ai"],"source":"Notes/DSPy.md"}`

        Success output is `(NewNote(...), [])`; failure output is `(None, [Issue(...)])`.
        """
        from .app import Issue

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            return None, [
                Issue(
                    "packet_json_invalid",
                    f"packet JSON is invalid: {exc.msg}",
                    line=exc.lineno,
                )
            ]

        if isinstance(payload, list):
            return None, [
                Issue(
                    "packet_not_object",
                    "packet payload must be a single object, not a list",
                )
            ]
        if not isinstance(payload, dict):
            return None, [
                Issue("packet_not_object", "packet payload must be a JSON object")
            ]

        issues: list[Issue] = []
        title = _required_string(payload, "title", issues)
        summary = _required_string(payload, "summary", issues)
        category_raw = _required_string(payload, "category", issues)
        source_raw = _required_string(payload, "source", issues)

        try:
            category = CategoryPath.parse(category_raw) if category_raw else None
        except ValueError as exc:
            category = None
            issues.append(Issue("packet_category_invalid", str(exc)))

        try:
            source = self.normalize_source(source_raw) if source_raw else ""
        except ValueError as exc:
            source = ""
            issues.append(
                Issue("packet_source_invalid", str(exc), source=source_raw)
            )

        tags = _string_tuple(payload.get("tags", ()), "tags", issues)
        search_terms = _string_tuple(
            payload.get("search_terms", ()), "search_terms", issues
        )

        if issues or category is None:
            return None, issues
        return NewNote(title, summary, category, tags, search_terms, source), []

    # --- utilities (no self/config needed) ---

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

    @staticmethod
    def snippet_around(
        text: str, terms: tuple[str, ...], *, max_chars: int = 180
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

    # --- private helpers ---

    def _iter_paths(self) -> list[Path]:
        """Return sorted markdown paths under include roots, excluding generated files."""
        paths: set[Path] = set()
        for root in self.config.include_roots:
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                resolved = path.resolve()
                if self._is_excluded(resolved):
                    continue
                paths.add(resolved)
        return sorted(
            paths,
            key=lambda item: item.relative_to(self.config.notebook_root)
            .as_posix()
            .casefold(),
        )

    def _is_excluded(self, path: Path) -> bool:
        """Return true when a path should not be treated as a source note."""
        try:
            rel = path.relative_to(self.config.notebook_root)
        except ValueError:
            return True
        rel_posix = rel.as_posix()
        if (
            self.config.generated_root == path
            or self.config.generated_root in path.parents
        ):
            return True
        if any(part in DEFAULT_EXCLUDE_PARTS for part in rel.parts):
            return True
        return any(
            fnmatch.fnmatch(rel_posix, pattern)
            or fnmatch.fnmatch(path.name, pattern)
            for pattern in self.config.exclude_globs
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
            return Notebook.clean_title(title)
        for line in self.body.splitlines():
            if line.startswith("# "):
                return Notebook.clean_title(line[2:])
        return Notebook.clean_title(path.stem.replace("_", " "))

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

    def with_property(self, key: str, value: object) -> "NoteMetadata":
        """Return a copy with a frontmatter value set."""
        frontmatter = dict(self.frontmatter)
        frontmatter[key] = value
        return NoteMetadata(frontmatter, self.body)

    @classmethod
    def write_category(cls, path: Path, category: str) -> bool:
        """Write a source note category frontmatter value if it changed."""
        original = path.read_text(encoding="utf-8")
        metadata = cls.parse(original)
        if metadata.frontmatter.get("category") == category:
            return False
        updated = metadata.with_property("category", category).render()
        path.write_text(updated, encoding="utf-8")
        return updated != original


# --- private helpers ---


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _required_string(payload: dict[str, Any], key: str, issues: list[Any]) -> str:
    """Read one required non-empty string field and accumulate issues."""
    from .app import Issue

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(
            Issue(
                "packet_field_invalid",
                f"packet field must be a non-empty string: {key}",
            )
        )
        return ""
    return value.strip()


def _string_tuple(value: Any, key: str, issues: list[Any]) -> tuple[str, ...]:
    """Normalize optional list-of-string fields into tuples."""
    from .app import Issue

    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not all(
        isinstance(item, str) for item in value
    ):
        issues.append(
            Issue(
                "packet_field_invalid",
                f"packet field must be a list of strings: {key}",
            )
        )
        return ()
    return tuple(item.strip() for item in value if item.strip())
