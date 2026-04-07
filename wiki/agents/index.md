# Wiki Index

Use this workflow for first-time taxonomy setup, notebook-wide indexing, rebuilds, or category reshaping.

## Goal

Handle first-time taxonomy setup and whole-notebook classification planning, then let `scripts/wiki.py` index source notes against the log and rebuild the tree-focused `index.md`, `categories/`, and `log.md`.

Use the active model from the invoking skill/session for any synthesis or classification work. Do not try to configure a model in the backend.

## Workflow

1. Inspect the indexing scope and config.
2. On the first run for a notebook, do setup before indexing:
- Read a representative sample of notes.
- Propose a category tree that can fit the full notebook.
- Start with three layers, with roughly 5-10 children per level, then add deeper layers when a branch is crowded or conceptually dense.
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
python wiki/scripts/wiki.py index
```

7. Review the generated category pages for touched branches. Use subagents to refine the synthesis at each layer when you need a better intro, topics-covered list, or search/Q&A framing than the deterministic baseline.
8. If notes still need classification, generate packets and feed them through `add --packet` before rebuilding.

## Responsibilities

- Decide whether a user request is best served by `add` or `index`.
- For first-time setup, force taxonomy design before whole-notebook indexing.
- Surface category collisions, poor bucket names, or overloaded branches.
- Replace broad catch-all branches when the underlying notes naturally split into clearer topical branches.
- Split overloaded branches when they exceed roughly 12 direct children or when the notes form obvious subclusters.
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
