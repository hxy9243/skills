# Wiki Index

Use this workflow for first-time taxonomy setup, notebook-wide indexing, rebuilds, or category reshaping.

## Goal

Handle first-time taxonomy setup and whole-notebook classification planning, then let `scripts/wiki.py` rebuild `index.md`, `categories/`, and `log.md`.

Use the active model from the invoking skill/session for any synthesis or classification work. Do not try to configure a model in the backend.

## Workflow

1. Inspect the indexing scope and config.
2. On the first run for a notebook, do setup before indexing:
- Read a representative sample of notes.
- Propose a `category_tree.md` that can fit the full notebook.
- Keep the tree to three layers, with roughly 5-10 children per level.
- Ask the user to approve the tree before continuing to whole-repo indexing.
- Use `templates/category_tree.md.example` as the starting structure.
3. Once the category tree is approved, treat it as the classification source of truth.
4. After notes have been classified into the approved tree, rebuild generated views:

```bash
python wiki/scripts/wiki.py index
```

5. If notes still need classification, generate packets and feed them through `add --packet` before rebuilding.

## Responsibilities

- Decide whether a user request is best served by `add` or `index`.
- For first-time setup, force taxonomy design before whole-notebook indexing.
- Surface category collisions, poor bucket names, or overloaded branches.
- Keep hierarchy labels broad enough to survive future indexing.
- Keep the approved category tree updated when genuinely new subtrees are needed.

## Do Not

- Do not manually rewrite generated manifests.
- Do not use ad hoc scripts for crawling or rebuilding.
- Do not hardcode provider-specific model behavior into the backend.
- Do not index the whole notebook before the user has accepted a category tree.
