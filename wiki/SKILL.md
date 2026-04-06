---
name: wiki
description: Build and maintain a formal notebook wiki with category-organized indexes, hierarchy summaries, delegated search, and linting. Use this whenever the user wants to turn notes into a browsable knowledge base, organize an Obsidian notebook into categories, regenerate a wiki index, search across synthesized categories, or validate wiki integrity.
---

# Wiki

This skill formalizes a notebook into a generated wiki workspace. Keep model-driven interpretation in the subagents and keep deterministic processing in `scripts/wiki.py`.

## What This Skill Owns

- Source notes stay in the notebook.
- Generated wiki artifacts live in a separate wiki root.
- The approved category tree lives at the top of `index.md` and is the classification reference.
- Category, subcategory, and topic layers each get a generated markdown synthesis page.
- Search delegates to `obsidian-cli search-content` when available, with `rg` fallback.
- `log.md` is the persistent record of adds, removals, and lint runs.
- Layer labels are written deterministically as `layer1: ...`, `layer2: ...`, and `layer3: ...` so prompts and search can target a specific depth.

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

The backend resolves config in this order:

1. `--config <path>`
2. `<generated_root>/config.json`
3. `~/.wiki/config.json`
4. built-in defaults

Prefer keeping the active notebook config in `_WIKI/config.json`, next to `index.md` and `log.md`.

Use [`templates/config.json.example`](/home/kevin/Workspace/skills/wiki/templates/config.json.example) as the starting template.

Supported config fields:

```json
{
  "notebook_root": "/absolute/path/to/notebook",
  "include_roots": [".", "Projects"],
  "exclude_globs": ["_WIKI/**", ".obsidian/**", "Templates/**"],
  "generated_root": "/absolute/path/to/notebook/_WIKI",
  "category_overrides": {
    "00_Inbox/Some Note.md": ["Computer Science", "AI Systems", "Agents"]
  },
  "search": {
    "lexical_limit": 8
  }
}
```

`include_roots` are resolved relative to `notebook_root` unless absolute.
Use `category_overrides` for notebook-specific placements that should survive future rebuilds.

Model choice is not part of the backend config. Subagents should inherit the active model from the invoking skill/session.

## Hierarchy Shape

The generated wiki always uses exactly three hierarchy layers before note leaves.

Rule of thumb:
- Keep each level to roughly 5-10 children.
- Prefer broad, durable buckets over narrow one-off branches.
- Expand the tree only when a concept clearly does not fit an existing branch.
- Add layer to each layer of category for better future 

Small example:

```text
- layer1: Computer Science
  - layer2: AI Systems
    - layer3: Agents
      - Note 1 on AI Agent
      - Note 2 on AI Agent
```

## First-Time Setup

Before indexing a notebook for the first time, establish an approved category tree.

1. Read through a representative slice of the notes.
2. Propose a three-level category tree that can absorb the notebook's concepts.
3. Put the approved category tree at the top of `index.md`, above a markdown separator `---`.
4. Ask the user to approve or edit that top section before running a full-repo index.

Use [`templates/category_tree.md.example`](/home/kevin/Workspace/skills/wiki/templates/category_tree.md.example) as the starting tree block, then paste it into the top of `index.md`.

Do not index the whole notebook until the user has accepted a category tree.

## Generated Artifacts

The Python backend maintains:
- `config.json`: notebook-local wiki config stored under the generated wiki root
- `index.md`: top-level category tree across the whole wiki, with all discovered non-system notes placed under their current branch and operational sections below a separator
- `log.md`: append-only record of adds, removals, and lint runs
- `categories/`: generated synthesis pages for each category node, with a brief intro, topics covered, references, and search cues

## Operating Rules

- Let subagents interpret notes and queries.
- Let `scripts/wiki.py` own file IO, category-page regeneration, log updates, index rebuilding, delegated search, and lint checks.
- Keep the approved category tree at the top of `index.md` as the classification reference for `add` and first-time `index`.
- Keep `index.md` focused on the category tree itself. Do not regenerate a second browse-by-category section below it.
- Prefer `index` for broad refreshes and `add` for small targeted updates.
- Use packet mode when a subagent has already normalized note classification data:

```bash
python wiki/scripts/wiki.py add --packet /tmp/wiki_packets.json
```

- Keep the hierarchy at exactly three layers before note leaves.
- Use the approved category tree from the top of `index.md` when classifying new notes. Add new subtrees only when the existing tree is clearly insufficient.
- Use the deterministic `layer1:`, `layer2:`, and `layer3:` labels when referring to branches in prompts, searches, or follow-up edits.
- Treat source notes as references; do not rewrite them in place.
- When changing this skill, always test it with a clean-slate subagent run rather than relying only on the current session context.
