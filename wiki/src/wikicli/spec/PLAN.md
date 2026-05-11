# wikicli KISS Refactor Plan

## Summary

Refactor toward a smaller set of crucial abstractions:

- `WikiConfig`: load and resolve workspace configuration.
- `Notebook`: source-note filesystem operations.
- `WikiIndex`: generated wiki index, category tree, catalog/log, listing, and note registration.
- `WikiCategoryTree`: in-memory category tree with simple traversal and dump helpers.
- `WikiCli`: stable command facade over those classes.

Keep commands: `add`, `index`, `list`, `search`, `lint`.

Remove commands: `reconcile`, `tree`, `show`, `status`, `synthesize`.

Default output is human-readable text/markdown. Machine output uses global `--format json`.

## Design Decisions

- Keep config close to the current `WikiConfig`, but move loading onto the class for clarity.
- Do not make `Notebook` own the wiki taxonomy. It can build a directory tree from files, but category trees belong to `WikiIndex`/`WikiCategoryTree`.
- Do not add `WikiSearcher` for now. Search can start as `WikiIndex.find()` because it searches indexed catalog metadata plus note content through `Notebook`.
- Use small dataclasses only where they remove ambiguity: records like `Note`, `NewNote`, `CatalogEntry`, `Issue`, and `CommandResult` are still useful. Avoid extra tiny result dataclasses unless tests or readability justify them.
- `WikiIndex` methods return domain types (`CatalogEntry`, `WikiCategoryTree`, `Issue`, `list[CatalogEntry]`). Serialization to JSON dicts happens at the `WikiCli`/`CommandResult` boundary only.
- `synthesize` is removed as a command. Its body-fetching capability is folded into `list` via `--include-body` and into `search` results.
- `Note` stays a pure frozen dataclass (data record). All filesystem operations and utilities live on `Notebook`.
- Backward compatibility is not a goal. Agent workflows will be updated against a CLI migration doc produced after the refactor.

## Core Interfaces

```python
@dataclass(frozen=True)
class WikiConfig:
    notebook_root: Path
    generated_root: Path
    include_roots: tuple[Path, ...]
    exclude_globs: tuple[str, ...] = ()

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "WikiConfig": ...

    @classmethod
    def default(cls, cwd: Path | None = None) -> "WikiConfig": ...

    @property
    def index_path(self) -> Path: ...

    @property
    def log_path(self) -> Path: ...

    @property
    def categories_dir(self) -> Path: ...
```

```python
@dataclass(frozen=True)
class Note:
    """Loaded markdown note — pure data record."""
    source: str
    path: Path
    frontmatter: dict[str, object]
    body: str
    title: str
    tags: tuple[str, ...]
    created: datetime.datetime
    last_modified: datetime.datetime
```

```python
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
```

`Note` and `NewNote` both live in `notebook.py`. `NewNote` replaces the old `Packet` dataclass and `parse_packet()` free function from `packet.py`, which is deleted.

```python
class Notebook:
    def __init__(self, config: WikiConfig) -> None: ...

    # --- read / write ---
    def read(self, source: str) -> Note: ...
    def readdir(self, directory: str | None = None, *, recursive: bool = True) -> list[Note]: ...
    def write(self, source: str, text: str) -> bool: ...
    def update_property(self, source: str, key: str, value: object) -> bool: ...

    # --- discovery ---
    def exists(self, source: str) -> bool: ...
    def discover(self) -> list[Note]: ...
    def resolve(self, source: str) -> Path: ...
    def source_for_path(self, path: Path) -> str: ...

    def build_directory_tree(self, directory: str | None = None) -> dict[str, Any]: ...

    # --- parsing ---
    def parse_new_note(self, raw_json: str) -> tuple[NewNote | None, list[Issue]]: ...

    # --- utilities (no self/config needed) ---
    @staticmethod
    def normalize_source(source: str) -> str: ...

    @staticmethod
    def clean_body_text(body: str) -> str: ...

    @staticmethod
    def tokenize(value: str) -> tuple[str, ...]: ...
```

`Notebook` owns source markdown files only: reading, directory scans, safe path normalization, frontmatter updates, text cleanup, and new-note JSON parsing.

```python
@dataclass(frozen=True)
class WikiCategoryTree:
    """In-memory category tree parsed from index.md. Pure structure."""
    roots: tuple[CategoryNode, ...]

    @classmethod
    def parse(cls, markdown: str) -> "WikiCategoryTree": ...

    def is_leaf(self) -> bool: ...
    def dump(self, format: str = "markdown") -> str: ...
    def children(self, path: CategoryPath | None = None) -> tuple[CategoryNode, ...]: ...
    def contains(self, path: CategoryPath) -> bool: ...
```

`WikiCategoryTree.dump_markdown()` renders the tree structure only (indented `- name` bullets). `WikiCategoryTree.dump_json()` returns the nested `[{name, children}]` structure.

```python
class WikiIndex:
    def __init__(self, config: WikiConfig, notebook: Notebook) -> None: ...

    # --- tree ---
    def read_tree(self) -> WikiCategoryTree: ...
    def add_category(self, path: str | CategoryPath) -> WikiCategoryTree: ...

    # --- catalog ---
    def catalog(self) -> dict[str, CatalogEntry]: ...

    # --- listing ---
    def list(
        self,
        category: str | CategoryPath | None = None,
        *,
        recursive: bool = False,
        include_body: bool = False,
    ) -> list[CatalogEntry]: ...

    # --- mutations ---
    def add_note(self, note: NewNote, *, allow_undeclared: bool = False) -> dict[str, Any]: ...
    def index(self) -> dict[str, Any]: ...

    # --- rendering ---
    def render(self) -> dict[str, Any]: ...

    # --- search ---
    def find(
        self,
        query: str | None = None,
        *,
        tags: tuple[str, ...] = (),
        limit: int = 10,
        include_body: bool = False,
    ) -> list[SearchResult]: ...

    # --- checks ---
    def lint(self) -> tuple[Issue, ...]: ...
```

`WikiIndex` owns generated wiki state: reading the category tree from `index.md`, replaying `log.md`, listing categories/notes, adding notes/categories, rebuilding generated pages, sync checks, and search over indexed data.

- `render()` rebuilds `index.md` (tree + note listings + skipped system notes) and category pages. This is the full page render — distinct from `WikiCategoryTree.dump_markdown()` which renders only the tree structure.
- `list()` with `include_body=True` replaces the old `synthesize` command. Agents that need full note bodies for synthesis call `wiki list --category "..." --include-body`.
- `find()` returns `list[SearchResult]` — a proper domain type — not pre-serialized dicts. `SearchResult` keeps its current fields (source, title, hierarchy, score, match_reasons, snippets, tags).
- `catalog()` replaces the old `active_catalog()` free function. Returns domain-typed `dict[str, CatalogEntry]`.
- `add_note()` still returns `dict[str, Any]` because its response is a mixed bag of changed files, counts, and rendering metadata. This is serialized directly into `CommandResult.data`.

```python
class WikiCli:
    def __init__(self, config: WikiConfig) -> None: ...

    @classmethod
    def from_config_path(cls, config_path: str | Path | None) -> "WikiCli": ...

    def add(
        self,
        json_packet: str,
        *,
        allow_undeclared: bool = False,
    ) -> CommandResult: ...

    def index(self) -> CommandResult: ...

    def list(
        self,
        category: str | None = None,
        *,
        recursive: bool = False,
        include_body: bool = False,
    ) -> CommandResult: ...

    def search(
        self,
        query: str | None = None,
        *,
        tags: tuple[str, ...] = (),
        limit: int = 10,
        include_body: bool = False,
    ) -> CommandResult: ...

    def lint(self) -> CommandResult: ...
```

## CLI Interface

```text
wiki [--config PATH] [--format json] <command> [options]
```

### `wiki add --json '<JSON>' [--allow-undeclared]`

Add one classified note to the wiki.

### `wiki index`

Reconcile notebook state and regenerate wiki files.

### `wiki list [CATEGORY] [--recursive] [--include-body] [--limit N]`

List catalog entries. Without arguments, lists top-level categories. With `--include-body`, includes cleaned note body text (replaces old `synthesize` command).

### `wiki search QUERY [--tag TAG ...] [--limit N] [--include-body]`

Search indexed notes. `--include-body` includes cleaned note body text in results.

### `wiki lint`

Run read-only workspace integrity checks.

## Implementation Changes

### File changes

- **Delete `packet.py`**: `NewNote` dataclass and `parse_new_note()` move into `notebook.py`.
- **Delete `commands/`**: all command modules. Parser setup collapses into `cli.py`.
- **Delete `search.py`**: search logic moves into `WikiIndex.find()` or a private `_search()` helper called by `WikiIndex`.
- **Rewrite `category.py`**: keep `CategoryPath` and `CategoryNode`. Replace free functions (`parse_category_tree`, `leaf_paths`, `all_paths`, `child_names`, `tree_to_json`, `tree_to_markdown`) with `WikiCategoryTree` methods. Remove functions if not necessary.
- **Rewrite `wiki.py`**: replace free functions with `WikiIndex` class methods. Keep `CatalogEntry` as a domain dataclass.
- **Rewrite `notebook.py`**: `Note` becomes a pure data record. Current `Note` class/static methods move to `Notebook` instance methods. `NoteMetadata` (frontmatter parser) stays as an internal helper. `NewNote` + `parse_new_note()` absorb `packet.py`.
- **Rewrite `app.py`**: `WikiCli` methods call `WikiIndex`/`Notebook` instead of free functions. Remove `synthesize_bundle`, `tree`, `show`, `status` methods.
- **Rewrite `cli.py`**: inline all argparse setup, add global `--format` flag, register only `add`, `index`, `list`, `search`, `lint`.
- **Update `spec.md`**: reflect new interfaces, removed commands, `NewNote` naming.

### Naming changes

| Old | New | Location |
|---|---|---|
| `Packet` | `NewNote` | `notebook.py` |
| `parse_packet()` | `Notebook.parse_new_note()` | `notebook.py` |
| `add_packet()` | `WikiIndex.add_note()` | `wiki.py` |
| `active_catalog()` | `WikiIndex.catalog()` | `wiki.py` |
| `read_tree()` | `WikiIndex.read_tree()` | `wiki.py` |
| `rebuild_generated()` | `WikiIndex.render()` | `wiki.py` |
| `index_workspace()` | `WikiIndex.index()` | `wiki.py` |
| `parse_category_tree()` | `WikiCategoryTree.parse()` | `category.py` |
| `leaf_paths()` | `WikiCategoryTree.leaf_paths()` | `category.py` |
| `all_paths()` | `WikiCategoryTree.all_paths()` | `category.py` |
| `tree_to_markdown()` | `WikiCategoryTree.dump_markdown()` | `category.py` |
| `tree_to_json()` | `WikiCategoryTree.dump_json()` | `category.py` |

## Migration Phases

### Phase 1: Domain classes

Introduce `WikiCategoryTree` in `category.py` and `WikiIndex` in `wiki.py` as new classes wrapping existing free functions. Introduce `Notebook` class in `notebook.py` wrapping existing `Note` class/static methods. Move `Packet` → `NewNote` into `notebook.py`, delete `packet.py`.

### Phase 2: Wire up

Migrate `WikiCli` methods to call `WikiIndex`/`Notebook` instead of free functions. Remove old free functions. Merge `search.py` into `WikiIndex`.

### Phase 3: CLI cleanup

Remove `commands/` modules. Collapse all argparse setup into `cli.py`. Remove deprecated commands (`reconcile`, `tree`, `show`, `status`, `synthesize`). Add global `--format json` flag.

### Phase 4: Docs

Update `spec.md`. Produce CLI migration doc for agent refactoring.

## Test Plan

- CLI tests:
  - Kept commands parse and call the right `WikiCli` methods.
  - Removed commands fail through argparse.
  - Default output is human-readable.
  - `--format json` returns the stable `CommandResult` envelope across all commands.
- Notebook tests:
  - `read`, `readdir`, `write`, `update_property`.
  - Safe source normalization.
  - Excludes generated files and configured globs.
  - `parse_new_note` validates and rejects bad JSON, missing fields, unsafe paths.
- WikiCategoryTree tests:
  - `parse` from index markdown.
  - `leaf_paths`, `all_paths`, `contains`, `is_leaf`.
  - `dump_markdown` and `dump_json` round-trip.
- WikiIndex tests:
  - `read_tree` parses category tree from `index.md`.
  - `list` supports root, direct category listing, recursive listing, and `include_body`.
  - `add_note` updates note property, appends log event, and rebuilds output.
  - `index` reports removed, modified, and unindexed notes.
  - `find` supports text-only, tag-only, text-plus-tag, and `include_body` search.
  - `lint` reports missing, updated, deleted, unindexed, malformed-log, and invalid-category issues.
  - `catalog` replays add/remove events correctly.

## Assumptions

- `Notebook.build_directory_tree()` means filesystem tree, not semantic category generation.
- `WikiIndex.add_category()` edits the category tree in `index.md`; it does not classify notes.
- `WikiIndex.find()` is enough for now; add a separate search service only if search logic grows materially.
- Small dataclasses are allowed when they clarify core records, but avoid creating a dataclass for every intermediate return value.
- `NoteMetadata` (frontmatter parser) stays internal to `notebook.py` — it is not part of the public interface.
