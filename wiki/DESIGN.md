# Wiki Design

## Purpose

The `wiki` skill turns a notebook into a generated, category-driven wiki.

The design goal is to keep the system simple:

- source notes remain the source of truth
- generated wiki files live under a separate wiki root such as `_WIKI/`
- model-driven categorization and synthesis stay in the skill prompts
- deterministic file handling, rendering, search delegation, and linting stay in `scripts/wiki.py`

## Generated Files

The generated wiki workspace is intentionally small.

- `index.md`
  The main category tree. This is both the human-facing navigation page and the classification reference used by `add` and `index`.
- `log.md`
  Append-only operational history for adds, removals, and lint runs.
- `categories/`
  One generated synthesis page per category branch.
- `config.json`
  Notebook-local configuration for include roots, excludes, generated root, and category overrides.

## Tree Model

The tree uses three category layers by default, but can grow deeper when a branch gets crowded or a concept needs a finer split.

Example:

```text
- layer1: [Computer Science](categories/computer-science/index.md)
  - layer2: [Artificial Intelligence](categories/computer-science/artificial-intelligence/index.md)
    - layer3: [AI Agents](categories/computer-science/artificial-intelligence/ai-agents/index.md)
      - layer4: [Optimization](categories/computer-science/artificial-intelligence/ai-agents/optimization/index.md)
        - [[00_Inbox/AI Agent/Example.md]]
```

Design rules:

- aim for roughly 5-10 children per layer
- prefer topic branches over generic buckets like `Research`, `Papers`, `General`, or `Misc`
- prefer retrieval-first clustering over strict folder mirroring or academic taxonomy purity
- do not shoehorn notes into an existing branch if the note clearly points to a better subtree
- use fallback branches only as review queues, not as stable long-term categories
- add a deeper layer when a branch grows past roughly 12 direct children or has obvious subclusters
- consolidate overlapping systems branches when they serve the same browsing intent

## Core Workflow

### First-Time Setup

1. Inspect a representative slice of the notebook.
2. Propose a category tree that starts simple and deepens only where needed.
3. Put that tree at the top of `index.md`.
4. Get approval before whole-repo indexing.

### Ongoing Indexing

1. Read the approved tree from `index.md`.
2. For each new or changed note, classify it into the approved category path.
3. For larger batches, spawn note-level classification subagents in parallel.
4. Cap parallel classification at 8 workers.
5. Run indexing to record removals, report modified notes via source `mtime`, and rebuild `index.md` and `categories/`.

### Search

1. Search notes via `obsidian-cli search-content` when available.
2. Combine that with tag-aware matching and category-path/index matches.
3. Search generated wiki docs for category context.
4. Use the search subagent to synthesize an answer from the retrieved material.
5. Return hierarchy and short evidence with note-level hits whenever possible.

### Lint

1. Check for missing source notes.
2. Check for unindexed notes.
3. Check for category placements that no longer exist in the approved tree.
4. Optionally append findings to `log.md`.

## Command Reference

### `add`

Use `add` for a small number of notes.

It accepts either direct note paths or pre-built packet JSON from a subagent.

Behavior:

- normalize note metadata
- write add events to `log.md`
- rebuild the category tree and category pages
- preserve exact category placement from the packet when provided

Example:

```bash
python wiki/scripts/wiki.py add /absolute/path/to/note.md
python wiki/scripts/wiki.py add --packet /tmp/wiki_packets.json
```

### `index`

Use `index` for broad refreshes and source-of-truth scans.

Behavior:

- crawl configured include roots
- skip excluded and generated files
- record removed notes in `log.md`
- report notes whose source `mtime` differs from the last recorded add event
- detect notes not yet in the active catalog
- render the category tree in `index.md`
- regenerate category synthesis pages under `categories/`

Example:

```bash
python wiki/scripts/wiki.py index
```

### `search`

Use `search` to retrieve notes and generated category context.

Behavior:

- use `obsidian-cli search-content`
- combine with `rg`, tag-aware note matching, and hierarchy/index matches
- include generated category-page matches
- return hierarchy with each resolved note match when possible
- return structured JSON for the search subagent to interpret

Example:

```bash
python wiki/scripts/wiki.py search "agent memory"
```

### `lint`

Use `lint` to validate the current wiki state.

Behavior:

- report missing source notes
- report modified notes using stored source `mtime`
- report unindexed notes
- report catalog entries whose category path is no longer in the approved tree
- optionally append findings to `log.md`

Example:

```bash
python wiki/scripts/wiki.py lint
python wiki/scripts/wiki.py lint --log
```

## Config Model

Config resolution order:

1. `--config <path>`
2. `<generated_root>/config.json`
3. `~/.wiki/config.json`
4. built-in defaults

Important config fields:

- `notebook_root`
- `include_roots`
- `exclude_globs`
- `generated_root`
- `category_overrides`
- `category_prefix_overrides`
- `search.lexical_limit`

Use exact overrides for one-off notes and prefix overrides for stable folder-level branches.

## Deterministic vs Model-Driven Work

Keep this boundary intact.

Model-driven:

- propose the first category tree
- classify ambiguous notes
- decide when the tree needs a new subtree
- improve category-page synthesis
- answer search questions from retrieved context

Deterministic:

- read config
- crawl notes
- parse the approved tree
- render `index.md`
- render `categories/`
- write `log.md`
- run search backends
- lint for drift and missing notes

## Why This Shape

This design intentionally avoids a heavy manifest/indexing system.

The wiki stays legible because:

- the category tree is plain markdown
- category pages are plain markdown
- the config is plain JSON
- the log is append-only markdown

That keeps the generated wiki easy to inspect, easy to repair manually, and easy for agents to read in later turns.
