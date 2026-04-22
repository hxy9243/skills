# Wiki CLI Ground-Up Implementation Plan

## Goal

Build a deterministic Python backend for the wiki skill. The backend should be a reliable helper for AI agents, not a second agent. It should own repeatable mechanics:

- config resolution and validation
- notebook scanning
- markdown/frontmatter parsing and updates
- packet validation
- category tree parsing and rendering
- append-only JSON-lines log replay
- generated wiki artifact writing
- deterministic search candidate retrieval
- lint/status checks
- stable JSON command output

Agents should keep owning semantic work:

- interpreting note meaning
- selecting or proposing categories
- deciding when a taxonomy should split, merge, or grow
- writing synthesized prose
- resolving ambiguous user preferences from `RULES.md`
- deciding which lint findings require a human/taxonomy review

The implementation should be designed from first principles, but kept small. Avoid a module split that is more complicated than the project.

## Non-Negotiable Design Rules

- Deterministic output: same filesystem state plus same command args should produce the same JSON and generated markdown, except timestamps for intentional log writes.
- Source notes stay in the notebook. Generated wiki artifacts stay in `generated_root`.
- `index.md` remains the approved classification reference.
- `log.md` remains append-only event history, stored as one JSON object per markdown bullet line.
- Commands must print valid JSON on both success and known integrity failures.
- Command ordering must be stable: paths sorted by normalized POSIX path, categories sorted by normalized display name, search ties sorted by source path.
- The backend must never invent semantic categories or summaries.
- `lint` should be read-only. Automated repair is out of scope for the first rewrite.
- Existing command names should keep working: `add`, `index`, `reconcile`, `search`, `synthesize`, `lint`.

## Review Of Current Implementation

The existing package is useful as a behavior prototype, but it should not be treated as the target architecture. The main issue is that command adapters, storage rules, path handling, rendering, search, and repair behavior are intertwined. That makes deterministic contracts harder to test and makes agent prompt behavior depend on incidental implementation details.

Current strengths worth preserving:

- Commands already emit JSON for normal success paths.
- `log.md` replay gives a simple, inspectable catalog model.
- `index.md` is already the approved classification reference.
- Generated category pages are plain markdown and easy to inspect.
- Tests cover the current add/index/search/lint flows well enough to use as behavior references for the rewrite.

Current risks to address:

- `commands/*.py` contain domain logic. They should become thin argparse adapters over a programmatic service.
- Source paths are accepted as strings for too long. Packet sources should be normalized before any filesystem join.
- `add` currently writes frontmatter and log events before category validity is a first-class command decision. Target behavior should validate packet, source, and category first, then mutate.
- Invalid categories are currently logged and omitted from generated views. That creates hidden catalog state. Target behavior should reject by default and provide `--allow-undeclared` only if a review queue is needed later.
- `lint` mutates source note frontmatter and appends add events while presenting itself as validation. For the next implementation, make it read-only.
- The frontmatter parser is a custom YAML subset. It will eventually break on common Obsidian frontmatter values such as booleans, numbers, nested lists, comments, quoted colons, and multiline strings.
- `read_log_events` silently drops invalid log lines. For now, keep log handling simple but have `lint` report malformed JSON lines.
- Search shells out to `rg` and optionally `obsidian-cli`. That is acceptable for a small CLI, as long as results are normalized and stable.
- Generated page rendering computes and writes in one pass. This is acceptable initially, but keep rendering functions pure enough to test expected text before writing.
- Staleness uses `mtime_ns`. Keep that for now. Content hashes and generated metadata can be a future improvement.

## Target Architecture

The backend should be a small deterministic library with a CLI wrapper, not a CLI script collection.

Keep three practical layers:

1. **Command layer**
   Thin argparse adapters. No domain logic.

2. **Application layer**
   `WikiCli` methods that implement command behavior and mutation order.

3. **Helper modules**
   Focused modules for config, notebook IO, category parsing, wiki state/rendering, search, lint, and JSON output.

Dependency direction should stay simple:

```text
commands -> app -> helper modules
```

Avoid splitting modules just because the domain model has several nouns. Split only when a file becomes hard to read, hard to test, or has unrelated reasons to change.

## Key Review Decisions

These decisions keep the implementation small while leaving room to grow.

1. **Result envelope**
   - Use `{ "ok": true, "command": "...", "data": {}, "issues": [], "fixes": [] }` internally.
   - Match the old command-specific top-level JSON only where `SKILL.md`, agents, or tests rely on it.

2. **Lint side effects**
   - `lint` is read-only.
   - No `lint --fix`, no placeholder repair command in the first rewrite.

3. **Invalid category on `add`**
   - Reject packets whose category is not an approved leaf.
   - Future TODO: add `--allow-undeclared` if agents need a review queue.

4. **Frontmatter parser**
   - Use `PyYAML` if dependency policy allows it.
   - If staying dependency-free, explicitly document the supported YAML subset and test it.

5. **Search backend**
   - Keep `rg` and optional `obsidian-cli` in the same `search.py` module for now.
   - Normalize all backend results into one stable result shape.
   - Future TODO: add backend abstraction only if more search providers are added.

6. **Synthesis freshness**
   - Use source `mtime_ns` for now.
   - Future TODO: store source content hashes and generated metadata blocks.

7. **Index ownership**
   - Own the generated `index.md` structure.
   - Avoid preserving arbitrary hand-written text inside generated regions.

8. **Command naming**
   - Keep `WikiCli` as the programmatic command surface.

9. **Log format**
   - Keep `log.md` simple: markdown heading plus `- {json}` event lines.
   - Parse valid JSON lines into events.
   - Have `lint` report malformed event lines.
   - Future TODO: schema versions, richer invalid-event preservation, and upgrade tooling.

10. **Writes**
    - Direct `Path.write_text` is acceptable for the initial small project.
    - Future TODO: atomic writes if partial writes become a real risk.

## Domain Model

Use small dataclasses where they prevent stringly typed mistakes. Do not build a large object graph up front, and do not create a dedicated `models.py`. Put each dataclass in the module closest to its concept.

Core records:

- `WikiConfig`
  - lives in `config.py`
  - absolute `notebook_root`
  - absolute `generated_root`
  - absolute `include_roots`
  - normalized `exclude_globs`
  - search settings

- `Note`
  - lives in `notebook.py`
  - `source: str`
  - `path: Path`
  - `frontmatter: dict`
  - `body: str`
  - `title: str`
  - `tags: tuple[str, ...]`
  - `mtime_ns: int`

- `CategoryPath`
  - lives in `category.py`
  - `parts: tuple[str, ...]`
  - renders `Layer 1 > Layer 2 > Layer 3`
  - renders `layer1: ...`
  - renders slug path

- `Packet`
  - lives in `packet.py`
  - `title`
  - `summary`
  - `category: CategoryPath`
  - `tags`
  - `search_terms`
  - `source: str`

- `CatalogEntry`
  - lives in `wiki.py`
  - active note state after log replay
  - derived from latest valid `add` minus later `remove`

- `SearchResult`
  - lives in `search.py`
  - `source`
  - `title`
  - `hierarchy`
  - `score`
  - `match_reasons`
  - `snippets`
  - `tags`

- `Issue`
  - lives in `app.py` unless it becomes large enough to justify its own module
  - `code`
  - `message`
  - `severity`
  - optional `source`
  - optional `path`
  - optional `line`

- `CommandResult`
  - lives in `app.py`
  - `ok`
  - `command`
  - `data`
  - `issues`
  - `fixes`
  - `exit_code`

Future TODOs:

- `SourcePath` value object if path bugs continue.
- `LogEvent` schema versions.
- Source content hashes for reproducible stale detection.

## High-Level Module Design

Keep the first version compact:

- `app.py`
  Programmatic orchestration boundary. Owns command behavior, mutation ordering, `CommandResult`, `Issue`, and JSON-serializable result construction.

- `cli.py`
  Argparse entrypoint. Registers commands, calls `WikiCli`, prints stable JSON, and returns process exit codes.

- `config.py`
  Config discovery, JSON loading, merging, and validation.

- `notebook.py`
  Notebook-safe path helpers, markdown discovery, note loading, frontmatter parsing/rendering, title/tag extraction, and source frontmatter updates. This intentionally combines the earlier `paths.py`, `notebook.py`, and `markdown.py` proposal.

- `category.py`
  Category path normalization, layer labels, category tree parsing, leaf lookup, and category tree rendering.

- `packet.py`
  Agent packet validation and normalization.

- `wiki.py`
  Catalog replay, log append/read, index rendering, category page rendering, generated artifact writes, and orphan cleanup. This intentionally combines the earlier `logstore.py`, `catalog.py`, `index.py`, and `render.py` proposal.

- `search.py`
  Query tokenization, `rg` search, optional `obsidian-cli` search, generated page search, tag/hierarchy matches, result merging, and stable scoring.

- `lint.py`
  Read-only integrity checks. Reports missing notes, unindexed notes, modified notes, malformed log lines, undeclared categories, and generated artifact drift when cheap to detect.

- Text helpers stay with the modules that use them. Keep title cleanup, markdown cleanup, tokenization, and snippets in `notebook.py`; keep category slugging and layer labels in `category.py`.

This layout keeps separation by workflow, not by every domain noun.

## Proposed Physical Layout

```text
wiki/
  pyproject.toml
  src/wikicli/
    __init__.py
    __main__.py
    app.py
    cli.py
    config.py
    notebook.py
    category.py
    packet.py
    wiki.py
    search.py
    lint.py
    commands/
      __init__.py
      add.py
      index.py
      search.py
      synthesize.py
      lint.py
      tree.py
      show.py
      status.py
  tests/
    test_config.py
    test_notebook.py
    test_category.py
    test_packet.py
    test_wiki_state.py
    test_search.py
    test_lint.py
    test_cli_contract.py
    fixtures/
      sample_notebook/
```

Clean-slate rewrite rule:

- Back up the original `src/wikicli` and `tests` before rewriting.
- Do not move old files into the new design.
- Reimplement the package from scratch using this TODO as the design.
- Use the old code only as a CLI behavior reference.
- Keep old tests or captured command outputs only where they express behavior that should remain true.

## Module Responsibilities

### `app.py`

Command methods should follow the same mutation pattern:

1. Load current workspace state.
2. Normalize untrusted inputs.
3. Validate all preconditions and collect issues.
4. If the command is mutating and validation passed, apply writes in deterministic order.
5. Return a `CommandResult`.

Core methods:

- `add_packet(raw_packet, *, allow_undeclared=False) -> CommandResult`
- `index() -> CommandResult`
- `search(query, *, limit) -> CommandResult`
- `synthesize_bundle(category=None, tags=(), limit=10, include_body=False) -> CommandResult`
- `lint() -> CommandResult`
- `tree() -> CommandResult`
- `status() -> CommandResult`
- `show(source) -> CommandResult`

### `notebook.py`

Owns filesystem and markdown mechanics:

- normalize relative source paths
- reject absolute paths and `..`
- resolve source paths under `notebook_root`
- discover markdown files under `include_roots`
- apply exclude globs
- parse/render frontmatter
- load notes
- extract title/tags/body text
- update note `category` frontmatter

### `category.py`

Owns category semantics:

- parse and normalize category paths
- format layer labels
- parse the category tree from `index.md`
- render the category tree with note assignments
- return leaf paths and all paths
- compute category page slug paths

### `wiki.py`

Owns generated wiki state:

- ensure `_WIKI` layout exists
- read and append `log.md` JSON events
- replay active catalog
- compute removed, modified, and unindexed notes
- render `index.md`
- render category pages
- remove orphan generated pages
- export catalog data for commands

Log handling should stay intentionally small:

- each event is one JSON object on a markdown bullet line
- valid lines are replayed
- malformed lines are ignored for replay and reported by `lint`
- log schema upgrades are a future TODO

### `search.py`

Owns all search behavior for now:

- tokenize query
- search source notes with `rg`
- call `obsidian-cli search-content` when available
- search generated wiki pages
- match tags and hierarchy from catalog entries
- normalize and merge results
- sort ties by source path

Future TODO: split external backends only when another backend makes this file hard to maintain.

### `lint.py`

Read-only checks:

- missing `index.md` or `log.md`
- malformed log lines
- catalog entries whose source file is missing
- catalog entries whose category is not an approved leaf
- modified notes based on `mtime_ns`
- unindexed notes
- generated pages that are missing or orphaned if cheap to detect

Do not update frontmatter, append events, or rewrite generated pages from `lint`.

## Command Surface

### Existing commands to preserve

- `wiki add --packet JSON`
  - Parse packet.
  - Validate source exists and is inside notebook.
  - Validate category path against approved leaf paths.
  - Update source note category frontmatter only after packet is accepted.
  - Append `add` event.
  - Rebuild generated artifacts.
  - Return added packet, changed files, issues, and indexed count.

- `wiki index` / `wiki reconcile`
  - Scan notebook.
  - Replay catalog.
  - Append remove events for missing indexed notes only if this behavior is intentionally retained.
  - Report modified and unindexed notes.
  - Rebuild generated artifacts.

- `wiki search QUERY --limit N`
  - Load notes, catalog, tree, and generated artifacts.
  - Return merged results with hierarchy, reasons, snippets, and stable score.
  - Return non-zero only when no results or fatal input/config error.

- `wiki synthesize`
  - Return a deterministic note bundle for agent synthesis.
  - This command should not produce prose synthesis itself.

- `wiki lint`
  - Read-only.
  - Return structured issues and suggested future fixes.

### Small helper commands

- `wiki tree [--format json|markdown]`
- `wiki show SOURCE`
- `wiki status`

Future TODO:

- `wiki list [CATEGORY] [--recursive/--direct]`
- `wiki list-topics [CATEGORY]`
- `wiki export [--events]`
- repair commands, if repeated manual repair workflows prove they are worth automating

## Implementation Phases

### Phase 0: Backup And Behavior Reference

- Back up the original implementation, for example to `src/wikicli_old/` or an ignored archive directory.
- Back up or copy current tests before replacing them.
- Capture expected JSON behavior for `add`, `index`/`reconcile`, `search`, `synthesize`, and `lint`.
- Treat old code as read-only reference, not as source to refactor.

Review gate:

- Confirm backup location and command behaviors to preserve.

### Phase 1: Compact Skeleton

- Replace `src/wikicli` with the new compact module layout.
- Add `app.py` with `WikiCli`, `CommandResult`, and `Issue`.
- Put dataclasses in concept modules, not in a central model module.
- Implement `cli.py` JSON printing and thin `commands/*.py` adapters.

Review gate:

- Approve `CommandResult`, `WikiCli` methods, and preserved old-output behavior.

### Phase 2: Notebook, Config, Packet

- Rebuild config validation.
- Move path helpers, note discovery, and markdown/frontmatter functions into `notebook.py`.
- Add `packet.py` validation.
- Reject unsafe paths and invalid packets before mutation.

Review gate:

- Approve YAML dependency decision and packet validation behavior.

### Phase 3: Category And Wiki State

- Move tree parsing/rendering into `category.py`.
- Move log replay, catalog state, index rendering, and category page rendering into `wiki.py`.
- Keep log format as simple JSON events in `log.md`.
- Add tests for catalog replay and generated markdown.

Review gate:

- Approve invalid category behavior and generated markdown format.

### Phase 4: Commands And Output

- Make `commands/*.py` thin adapters.
- Add `tree`, `show`, and `status`.
- Standardize result envelopes internally.
- Match old command outputs where required by `SKILL.md`, agents, or behavior-reference tests.

Review gate:

- Approve command output contracts before updating prompts.

### Phase 5: Search And Lint

- Consolidate search behavior in `search.py`.
- Normalize `rg`, `obsidian-cli`, generated-page, tag, and hierarchy matches.
- Make `lint` read-only.
- Add tests for malformed logs, undeclared categories, missing notes, modified notes, and unindexed notes.

Review gate:

- Approve scoring weights and final lint mutation policy.

### Phase 6: Skill Prompt Update

- Update `SKILL.md` and `agents/*.md` to use stable command outputs.
- Run a clean-slate indexing/search/lint flow against a sample notebook.

## Testing Strategy

- Unit tests for config, notebook IO, category parsing, packet validation, wiki state, search, and lint.
- Contract tests for every CLI command's JSON shape.
- Golden markdown tests for `index.md` and category page output.
- Filesystem integration tests for add/index/search/lint flows.
- Behavior-reference tests for old command parity where that behavior is intentionally preserved.
- Determinism tests that run the same command twice and compare normalized output.
- Safety tests for path traversal, absolute packet sources, generated-root overlap, and invalid config.

## Future TODOs

These are intentionally out of scope for the first compact rewrite:

- Atomic file writes.
- Log schema versions and upgrade tooling.
- Rich invalid-log preservation beyond lint reporting.
- Source content hashes and generated metadata blocks.
- A dedicated search backend interface.
- Splitting `notebook.py`, `wiki.py`, or `search.py` if they become too large.
- `list`, `list-topics`, `export`, and repair helper commands.

## Rewrite Notes

Do not migrate file-by-file. Back up the old implementation, then write the new compact package from scratch. The old modules are useful as behavior examples, not as architecture constraints.

Suggested rewrite order:

1. Back up old source and tests.
2. Capture command behavior that must remain stable.
3. Replace `src/wikicli` with the compact module layout.
4. Rebuild tests around the new modules plus preserved CLI behavior.
5. Update skill prompts only after command output is stable.
