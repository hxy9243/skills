# wikicli Architecture Spec

## High-Level Overview

`wikicli` is a deterministic Python CLI backend for maintaining a generated wiki
from a markdown notebook. It owns filesystem-safe operations that should not be
left to an agent directly: loading workspace config, validating classification
packets, updating source-note frontmatter, replaying the wiki event log,
regenerating category pages, searching indexed notes, and linting workspace
integrity.

The architecture is intentionally split into three layers:

1. CLI adapter layer
   - Files: `cli.py`, `__main__.py`, `commands/*.py`
   - Responsibility: parse command-line arguments, load config once, call the
     app facade, print deterministic output, and return process exit codes.

2. App facade layer
   - File: `app.py`
   - Responsibility: expose the stable programmatic command surface through
     `WikiCli`, normalize all command responses into `CommandResult`, and report
     failures as structured `Issue` objects.

3. Domain implementation layer
   - Files: `wiki.py`, `notebook.py`, `category.py`, `packet.py`, `search.py`,
     `lint.py`, `config.py`
   - Responsibility: implement the actual notebook, category tree, catalog,
     search, rendering, config, and validation behavior.

The CLI command flow is:

```text
console script `wiki`
  -> wikicli.cli:main()
  -> build_parser()
  -> command module register() attaches handler
  -> WikiCli.from_config_path()
  -> WikiCli.<command>()
  -> domain module implementation
  -> CommandResult
  -> JSON or selected human output
```

The package can also be run as a module:

```bash
python -m wikicli ...
```

The installed console entrypoint is declared in `pyproject.toml`:

```toml
[project.scripts]
wiki = "wikicli.cli:main"
```

## Workspace Model

`WikiConfig` in `config.py` is the resolved workspace schema:

```python
WikiConfig(
    notebook_root: Path,
    generated_root: Path,
    include_roots: tuple[Path, ...],
    exclude_globs: tuple[str, ...] = (),
    search: dict[str, Any] | None = None,
)
```

If `--config` is omitted, the current working directory becomes the notebook
root and generated files are written under `_WIKI`.

If `--config path/to/config.json` is provided, `load_config()` reads a JSON
object with these supported keys:

```json
{
  "notebook_root": ".",
  "generated_root": "_WIKI",
  "include_roots": ["."],
  "exclude_globs": [],
  "search": {}
}
```

Config paths are resolved relative to the config file or notebook root, then
stored as absolute `Path` values.

Generated wiki state lives under `generated_root`:

```text
_WIKI/
  index.md
  log.md
  categories/
    <category-slug>/
      index.md
```

`log.md` is the append-only event source. The active catalog is reconstructed by
replaying valid JSON events from this file. `index.md` contains the approved
category tree and generated wiki index. `categories/` contains generated
category pages.

## CLI Interface

All commands accept the global `--config` option before the command name:

```bash
wiki --config path/to/wiki.json <command> ...
```

Most commands print compact JSON with sorted keys. `tree` defaults to human
readable markdown output unless `--format json` is passed.

### `wiki add`

Adds one classified packet to the wiki.

```bash
wiki add --packet '{"title":"DSPy","summary":"Prompt optimization","category":"Computer Science > AI Systems","tags":["#ai"],"search_terms":["dspy"],"source":"Notes/DSPy.md"}'
```

Options:

- `--packet`: required JSON object.
- `--allow-undeclared`: allow a packet category outside the approved leaf
  category tree.

Behavior:

- Parses and validates packet JSON through `packet.py`.
- Ensures the source note exists under `notebook_root`.
- Rejects categories that are not approved leaf categories unless
  `--allow-undeclared` is set.
- Writes the note `category` frontmatter if needed.
- Appends an `add` event to `log.md`.
- Rebuilds generated index and category pages.

### `wiki index`

Reconciles notebook state and regenerates generated wiki files.

```bash
wiki index
```

Behavior:

- Ensures `_WIKI` layout exists.
- Discovers markdown notes from configured include roots.
- Appends `remove` events for catalog entries whose source notes are missing.
- Reports modified and unindexed notes.
- Rebuilds `index.md` and category pages.

### `wiki reconcile`

Alias for `wiki index`.

```bash
wiki reconcile
```

### `wiki search`

Searches indexed wiki notes.

```bash
wiki search "prompt optimization" --limit 5
```

Options:

- `query`: required search text.
- `--limit`: maximum number of results, default `10`.

Behavior:

- Searches the active catalog plus source-note body text.
- Scores title, search terms, tags, hierarchy, summary, and content with
  deterministic weights.
- Returns ranked JSON results.
- Exits with code `1` when no results are found.

### `wiki synthesize`

Returns a deterministic note bundle for agent-written synthesis.

```bash
wiki synthesize --category "Computer Science > AI Systems" --tag '#ai' --limit 10 --include-body
```

Options:

- `--category`: filter by exact category display string.
- `--tag`: repeatable tag filter.
- `--limit`: maximum entries, default `10`.
- `--include-body`: include cleaned source-note body text.

Behavior:

- Reads active catalog entries.
- Applies category and tag filters.
- Optionally loads cleaned note bodies for downstream synthesis.

### `wiki lint`

Runs read-only workspace integrity checks.

```bash
wiki lint
```

Behavior:

- Checks notebook and generated roots.
- Checks `index.md` and `log.md`.
- Reports malformed log events.
- Reports missing, modified, unindexed, invalid-category, and unapproved-category
  notes.
- Exits with code `1` when any error-severity issue exists.

### `wiki tree`

Shows the approved category tree parsed from generated `index.md`.

```bash
wiki tree
wiki tree --format json
```

Options:

- `--format markdown`: default human-readable markdown bullets.
- `--format json`: command-result JSON containing `data.categories`.

### `wiki show`

Shows one indexed source note entry.

```bash
wiki show Notes/DSPy.md
```

Behavior:

- Normalizes the source path.
- Looks up the source in the active catalog.
- Returns the catalog entry or a structured `not_found` issue.

### `wiki status`

Shows resolved workspace paths.

```bash
wiki status
```

Behavior:

- Returns `notebook_root`, `generated_root`, and `include_roots`.

## Command Result Schema

Every app-layer command returns `CommandResult` from `app.py`:

```python
CommandResult(
    ok: bool,
    command: str,
    data: dict[str, Any] = {},
    issues: tuple[Issue, ...] = (),
    fixes: tuple[dict[str, Any], ...] = (),
    exit_code: int = 0,
)
```

The public JSON envelope is:

```json
{
  "ok": true,
  "command": "status",
  "data": {},
  "issues": [],
  "fixes": []
}
```

`Issue` is the structured diagnostic schema:

```python
Issue(
    code: str,
    message: str,
    severity: str = "error",
    source: str | None = None,
    path: str | None = None,
    line: int | None = None,
)
```

Unset optional issue fields are omitted from JSON. This keeps command output
machine-readable and stable for agents, scripts, and tests.

## Data Schemas

### Packet

`Packet` in `packet.py` is the accepted input schema for `wiki add`:

```json
{
  "title": "DSPy",
  "summary": "Prompt optimization",
  "category": "Computer Science > AI Systems",
  "tags": ["#ai"],
  "search_terms": ["dspy", "prompt optimization"],
  "source": "Notes/DSPy.md"
}
```

Required fields:

- `title`: non-empty string.
- `summary`: non-empty string.
- `category`: non-empty `>`-delimited category path.
- `source`: non-empty notebook-relative markdown path.

Optional fields:

- `tags`: list of strings.
- `search_terms`: list of strings.

`parse_packet()` rejects invalid JSON, list payloads, non-object payloads,
missing required fields, invalid category strings, unsafe source paths, and
non-list tag/search fields.

### CategoryPath

`CategoryPath` in `category.py` represents normalized category lineage:

```python
CategoryPath(("Computer Science", "AI Systems"))
```

Important renderings:

- `display()`: `Computer Science > AI Systems`
- `layer_labels()`: `("layer1: Computer Science", "layer2: AI Systems")`
- `slug_parts()`: filesystem-safe lowercase path parts for category pages.

The approved category tree is parsed from `index.md` bullets shaped like:

```markdown
- layer1: Computer Science
  - layer2: AI Systems
```

Only leaf paths are approved for normal `add` operations.

### CatalogEntry

`CatalogEntry` in `wiki.py` is the active record after replaying log events:

```python
CatalogEntry(
    source: str,
    title: str,
    summary: str,
    category: str,
    tags: tuple[str, ...],
    search_terms: tuple[str, ...] = (),
    source_mtime_ns: int | None = None,
    updated_at: str | None = None,
)
```

The active catalog is not stored as a separate database. It is computed by
`active_catalog()` from `log.md`:

- `add` events insert or replace an entry by normalized source path.
- `remove` events delete an entry by source path.
- malformed log lines are ignored by catalog replay and reported by lint.

### Note

`Note` in `notebook.py` represents a loaded markdown note:

```python
Note(
    source: str,
    path: Path,
    frontmatter: dict[str, object],
    body: str,
    title: str,
    tags: tuple[str, ...],
    mtime_ns: int,
)
```

`NoteMetadata` parses a deliberately small YAML frontmatter subset:

- scalar key/value fields.
- list fields written as `key:` followed by `- value` lines.
- title from frontmatter `title`, first `# H1`, or filename stem.
- tags normalized to sorted `#tag` values.

Source paths are always notebook-relative POSIX paths. Absolute paths and paths
containing `..` are rejected before filesystem access.

## Important Modules

### `cli.py`

Owns the Python command-line interface:

- Builds the root `argparse.ArgumentParser`.
- Adds global `--config`.
- Registers command modules.
- Creates `WikiCli` from the config path.
- Converts config and value errors into structured command results.
- Prints command output.

`print_result()` emits compact deterministic JSON. `print_cli_output()` special
cases successful markdown tree output for human readability.

### `commands/*.py`

Each command module is a thin argparse adapter. It has:

- `register(subparsers)`: declares arguments and attaches `handler`.
- `run(app, args)`: calls the matching `WikiCli` method.

These modules should stay small. Business logic belongs in `WikiCli` or the
domain modules.

### `app.py`

Defines:

- `Issue`: structured diagnostics.
- `CommandResult`: stable output envelope.
- `WikiCli`: the programmatic command surface.

`WikiCli` is the boundary between CLI adapters and implementation. Future
automation can call `WikiCli` directly without going through `argparse`.

### `config.py`

Defines `WikiConfig` and `load_config()`. It resolves workspace paths and
provides derived paths for `index.md`, `log.md`, and `categories/`.

### `notebook.py`

Owns markdown source-note discovery and note metadata:

- excludes generated wiki files and common ignored directories.
- applies `exclude_globs`.
- parses and renders the supported frontmatter subset.
- normalizes safe source paths.
- writes the `category` frontmatter field.
- cleans body text for search and synthesis.

### `category.py`

Owns category tree parsing and rendering:

- parses `layerN:` markdown bullets from `index.md`.
- computes approved leaf paths and all category paths.
- computes child category names.
- converts category names to stable slugs.
- renders tree JSON and markdown.

### `packet.py`

Owns untrusted packet parsing and validation. It turns raw JSON into a
normalized `Packet` or a list of structured `Issue` objects.

### `wiki.py`

Owns persistent wiki behavior:

- `ensure_layout()`: creates generated directories and seed files.
- `read_events()` and `append_event()`: read and write log events.
- `active_catalog()`: replay log events into current catalog state.
- `add_packet()`: write note category, append log event, regenerate views.
- `index_workspace()`: reconcile removed, modified, and unindexed notes.
- `rebuild_generated()`: rewrite `index.md` and category pages.
- rendering helpers for generated index and category pages.

This is the main implementation module for mutating and regenerating wiki state.

### `search.py`

Owns deterministic lexical search over indexed notes. It scores matches across:

- title, weight 8.
- search terms, weight 6.
- tags, weight 5.
- hierarchy, weight 4.
- summary, weight 3.
- source body content, weight 1.

Results sort by descending score and then source path for stable output.

### `lint.py`

Owns read-only integrity checks. It reports workspace, log, catalog, source-note,
and approved-category problems as `Issue` objects.

## Implementation Notes

- The package has no runtime dependencies outside the Python standard library.
- The supported Python version is `>=3.12,<3.13`.
- Generated files are rewritten only when content changes through
  `_write_if_changed()`.
- The event log uses JSON objects embedded in markdown list items:

```markdown
- {"action":"add","source":"Notes/DSPy.md",...}
```

- `index.md` is both generated output and the source of the approved category
  tree. Commands parse the `## Category Tree` section up to the `---` divider.
- The app facade uses lazy imports inside command methods to keep module loading
  simple and avoid command-layer cycles.
- `src/wikicli.back/` and `.rewrite-backups/` contain older or backup code and
  are not part of the active package declared by `pyproject.toml`.

## Testing Surface

The most important contract tests should cover:

- CLI argument parsing and command registration.
- `CommandResult` and `Issue` JSON envelopes.
- packet validation failures and successful normalization.
- safe source path normalization.
- frontmatter parsing and category writes.
- active catalog replay from add/remove events.
- generated index/category rendering.
- search ranking determinism.
- lint issue reporting.

