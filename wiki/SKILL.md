---
name: wiki
description: Build and maintain a formal notebook wiki with concept pages, hierarchy summaries, incremental indexing, semantic search, and linting. Use this whenever the user wants to turn notes into a browsable knowledge base, organize an Obsidian notebook into categories, regenerate a wiki index, search across synthesized concepts, or validate wiki integrity.
---

# Wiki

This skill formalizes a notebook into a generated wiki workspace. Keep model-driven interpretation in the subagents and keep deterministic processing in `scripts/wiki.py`.

## What This Skill Owns

- Source notes stay in the notebook.
- Generated wiki artifacts live in a separate wiki root.
- The approved category tree is the classification reference.
- Category, subcategory, and topic layers each get a generated markdown synthesis page.
- Search delegates to `obsidian-cli search` when available, with `rg` fallback.
- `log.md` is the persistent record of adds, removals, and lint runs.

## Dispatch

Choose one of these four subagent workflows before touching the script:

1. `agents/add.md`
Use for targeted note ingestion or when the user wants to add a few notes into the wiki.

2. `agents/index.md`
Use for notebook-wide or folder-wide indexing, incremental refreshes, and rebuilds.

3. `agents/search.md`
Use when the user wants answers or browsing help from the generated wiki.

4. `agents/lint.md`
Use when the user wants validation, cleanup guidance, or integrity checks.

## Config Contract

The backend loads config from `~/.wiki/config.json` by default, or from `--config <path>`.

Use [`templates/config.json.example`](/home/kevin/Workspace/skills/wiki/templates/config.json.example) as the starting template.

Supported config fields:

```json
{
  "notebook_root": "/absolute/path/to/notebook",
  "include_roots": [".", "Projects"],
  "exclude_globs": ["_WIKI/**", ".obsidian/**", "Templates/**"],
  "generated_root": "/absolute/path/to/notebook/_WIKI",
  "search": {
    "lexical_limit": 8,
    "semantic_limit": 8
  }
}
```

`include_roots` are resolved relative to `notebook_root` unless absolute.

Model choice is not part of the backend config. Subagents should inherit the active model from the invoking skill/session.

## Hierarchy Shape

The generated wiki always uses exactly three hierarchy layers before concept leaves.

Rule of thumb:
- Keep each level to roughly 5-10 children.
- Prefer broad, durable buckets over narrow one-off branches.
- Expand the tree only when a concept clearly does not fit an existing branch.

Small example:

```text
Computer Science
  AI Systems
    Memory
      State.md
      Context Windows.md
    Agents
      Tool Use.md
      Workflow Delegation.md
```

## First-Time Setup

Before indexing a notebook for the first time, establish an approved category tree.

1. Read through a representative slice of the notes.
2. Propose a three-level category tree that can absorb the notebook's concepts.
3. Save the proposal as `category_tree.md`, usually at `<generated_root>/category_tree.md`.
4. Ask the user to approve or edit that tree before running a full-repo index.

Use [`templates/category_tree.md.example`](/home/kevin/Workspace/skills/wiki/templates/category_tree.md.example) as the starting template.

Do not index the whole notebook until the user has accepted a category tree.

## Generated Artifacts

The Python backend maintains:
- `index.md`: top-level browse entrypoint across the whole wiki
- `log.md`: append-only record of adds, removals, and lint runs
- `category_tree.md`: approved classification tree for the notebook
- `categories/`: generated synthesis pages for each category node

## Operating Rules

- Let subagents interpret notes and queries.
- Let `scripts/wiki.py` own file IO, category-page regeneration, log updates, index rebuilding, delegated search, and lint checks.
- Keep an approved `category_tree.md` as the classification reference for `add` and first-time `index`.
- Prefer `index` for broad refreshes and `add` for small targeted updates.
- Use packet mode when a subagent has already normalized concept data:

```bash
python wiki/scripts/wiki.py add --packet /tmp/wiki_packets.json
```

- Keep the hierarchy at exactly three layers before concept leaves.
- Use the approved category tree when classifying new notes. Add new subtrees only when the existing tree is clearly insufficient.
- Treat source notes as references; do not rewrite them in place.
