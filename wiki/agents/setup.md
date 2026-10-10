# Wiki Setup

Use this workflow when the task is to establish the wiki for the first time by proposing an initial category tree.

## Goal

Before indexing a notebook for the first time, establish an approved category tree that can absorb the notebook's concepts and match how the user will naturally browse or search them later.

## Workflow

1. Read through a representative slice of the notes.
2. Propose a category tree that can absorb the notebook's concepts and match how the user will naturally browse or search them later.
3. Put the approved category tree at the top of `index.md`, above a markdown separator `---`.
4. Ask the user to approve or edit that top section before running a full-repo index.

Use [`templates/category_tree.md.example`](../templates/category_tree.md.example) as the starting tree block, then paste it into the top of `index.md`.

Do not index the whole notebook until the user has accepted a category tree.

Save exceptions and rules into `RULES.md` in the wiki root.

## Generated Artifacts

The Python backend maintains:
- `config.json`: notebook-local wiki config stored under the generated wiki root (auto-discovered by `wikicli` by default)
- `index.md`: top-level category tree across the whole wiki, with all discovered non-system notes placed under their current branch and operational sections below a separator
- `log.md`: append-only record of adds, removals, and lint runs
- `categories/`: generated synthesis pages for each category node, with a brief intro, topics covered, references, and search cues



## Preservation Contract

All wiki workflows are additive by default. Keep existing source notes, YAML values and comments, category summaries, synthesis prose, extra sections, tree annotations, and homepage content. Add missing information without duplicating it; do not replace, normalize, prune, rename, or delete existing information unless the user explicitly requests that specific change. Surface conflicting categories for review rather than reclassifying silently.

The backend adds missing metadata and navigation/reference lines. It refreshes only owned fields: `wiki_note_count` (including descendant notes), `wiki_child_count` (direct children), `wiki_kind`, `wiki_depth`, and the standard `wiki_status` values `active`/`empty`. Custom `wiki_status` values and plain `status` fields are preserved. `modified` changes only when page content, referenced source content, catalog information, or owned metadata changes; a source mtime-only touch or unchanged run does not change it. `wiki_content_hash` records the comparison baseline. The first run on a legacy page establishes that baseline without changing `modified` unless that run changes page content or owned metadata. Authored summaries, other YAML, comments, and prose remain untouched. Old placeholders and stale links are retained for review. Orphan pages remain on disk and are reported; `HOME.md` is never written by the backend. `lint --filter empty_summary` warns about missing, null, empty, or whitespace-only summaries on existing approved category pages without editing them.

Source metadata updates preserve the original text and add only a missing property. Conflicting values, malformed or ambiguous YAML, output-path collisions, and symlink writes fail safely. `log.md` is append-only. Repeating the same operation must not duplicate material or rewrite unchanged files. Concurrent edits detected during a prepared write cause an error; stop and retry after other writers finish. Complex or ambiguous YAML shapes in backend-owned fields fail safely before mutation rather than being normalized.
