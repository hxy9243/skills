# Wiki Setup

Use this workflow when the task is to establish the wiki for the first time by proposing an initial category tree.

## Goal

Before indexing a notebook for the first time, establish an approved category tree that can absorb the notebook's concepts and match how the user will naturally browse or search them later.

## Workflow

1. Read through a representative slice of the notes.
2. Propose a category tree that can absorb the notebook's concepts and match how the user will naturally browse or search them later.
3. Put the approved category tree at the top of `index.md`, above a markdown separator `---`.
4. Ask the user to approve or edit that top section before running a full-repo index.

Use [`templates/category_tree.md.example`](/home/kevin/Workspace/skills/wiki/templates/category_tree.md.example) as the starting tree block, then paste it into the top of `index.md`.

Do not index the whole notebook until the user has accepted a category tree.

Save exceptions and rules into `RULES.md` in the wiki root.

## Generated Artifacts

The Python backend maintains:
- `config.json`: notebook-local wiki config stored under the generated wiki root (auto-discovered by `wikicli` by default)
- `index.md`: top-level category tree across the whole wiki, with all discovered non-system notes placed under their current branch and operational sections below a separator
- `log.md`: append-only record of adds, removals, and lint runs
- `categories/`: generated synthesis pages for each category node, with a brief intro, topics covered, references, and search cues
