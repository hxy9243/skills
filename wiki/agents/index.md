# Wiki Index

Use this workflow for first-time taxonomy setup, notebook-wide indexing, rebuilds, or category reshaping.

## Goal

Handle first-time taxonomy setup and whole-notebook classification planning, then let the `wikicli` python package index source notes against the log and rebuild the tree-focused `index.md`, `categories/`, and `log.md`.

Use the active model from the invoking skill/session for any synthesis or classification work. Do not try to configure a model in the backend.

## Workflow

1. Inspect the indexing scope and config.
2. On the first run for a notebook, do setup before indexing:
- Read a representative sample of notes.
- Propose a category tree that can fit the full notebook.
- Start with three layers, with roughly 5-10 children per level, then add deeper layers when a branch is crowded or conceptually dense.
- Prefer a retrieval-first tree: group notes the way a user would expect to search or browse for them later.
- Prefer topic-shaped branches over generic buckets like `Research`, `General`, `Papers`, or `Misc`.
- Do not shoehorn notes into an existing branch when the note clearly deserves a better subtree.
- If a note still does not fit, place it in a review queue branch and revisit the tree. Do not leave it in a broad catch-all permanently.
- If two parallel branches mostly hold the same kind of notes, consolidate them under a shared parent instead of preserving accidental distinctions.
- Put that tree at the top of `index.md`, above a `---` separator.
- Ask the user to approve the tree before continuing to whole-repo indexing.
- Use `templates/category_tree.md.example` as the starting tree block, then paste it into the top of `index.md`.
3. Once the category tree in `index.md` is approved, treat it as the classification source of truth.
4. For each new or changed note, spawn a classification subagent to determine its best category path against the approved tree.
5. Parallelize that note-classification work when the batch is large, but cap concurrency at 8 subagents at a time so runs stay tractable.
6. After notes have been classified into the approved tree, rebuild generated views:

```bash
uv run --directory <wiki skill path> wiki --root <notebook-root> index
```

7. **Cascading Bottom-Up Synthesis**: After rebuilding, ensure that synthesis is rolled up at *each* category level. For any given category level, read the synthesis notes of its immediate depth-1 children to construct and update the synthesis of the current level. Repeat this process up to the root to create and update a `HOME.md` file that represents the top-level synthesis of the entire wiki.
8. If notes still need classification, generate packets and feed them through `add --json` before rebuilding.

## Responsibilities

- Decide whether a user request is best served by `add` or `index`.
- For first-time setup, force taxonomy design before whole-notebook indexing.
- Surface category collisions, poor bucket names, or overloaded branches.
- Replace broad catch-all branches when the underlying notes naturally split into clearer topical branches.
- Split overloaded branches when they exceed roughly 12 direct children or when the notes form obvious subclusters.
- Consolidate parallel branches when users would search them as one idea cluster.
- Prefer concept consistency across source folders. A topic family should usually live in one subtree even if notes came from projects, inbox, and subject folders.
- Run `uv run --directory <wiki skill path> wiki --root <notebook-root> lint` to discover all unindexed notes.
- If there are unindexed notes, read the approved category tree at the top of `index.md` and any custom rules in `RULES.md` to guide classification.
- Keep hierarchy labels broad enough to survive future indexing.
- Keep the approved category tree in `index.md` updated when genuinely new subtrees are needed.
- Use the deterministic `layer1:`, `layer2:`, `layer3:`, and deeper `layerN:` labels when proposing or editing branch names.
- For bulk indexing, use note-level subagents as the classification workers and keep the run bounded to 8 concurrent workers.

## Do Not

- Do not keep a second category-tree file beside `index.md`.
- Do not use ad hoc scripts for crawling or rebuilding.
- Do not hardcode provider-specific model behavior into the backend.
- Do not index the whole notebook before the user has accepted a category tree.
- Do not keep notes in a generic branch just because it already exists. Create or propose a better branch when the topic warrants it.
