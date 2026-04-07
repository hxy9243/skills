# wiki

`wiki` turns an Obsidian-style note collection into a lightweight generated wiki rooted in category pages.

## What It Generates

- `index.md`: the approved category tree and note placement index
- `log.md`: append-only add/remove/lint history
- `categories/`: one generated synthesis page per category node
- `config.json`: notebook-local configuration, typically stored under `_WIKI/`

## Commands

```bash
python wiki/scripts/wiki.py add ...
python wiki/scripts/wiki.py index
python wiki/scripts/wiki.py search "query"
python wiki/scripts/wiki.py lint
```

## Config Resolution

The backend resolves config in this order:

1. `--config <path>`
2. `<generated_root>/config.json`
3. `~/.wiki/config.json`
4. built-in defaults

Use [`templates/config.json.example`](./templates/config.json.example) as the starter template.

## Category Rules

- Keep three layers as the default starting point, but add deeper layers when a branch gets crowded or conceptually dense.
- Aim for roughly 5-10 children per layer.
- Prefer durable topic branches over generic buckets like `Research`, `Papers`, `General`, or `Misc`.
- Do not shoehorn notes into an existing branch when the note clearly points to a better topic-shaped subtree.
- Treat fallback branches as review queues only. Reclassify them into topic branches as soon as the right subtree is clear.
- Split branches once they pass roughly 12 direct children or clearly contain subclusters.
- Consolidate overlapping systems buckets when they represent the same browsing intent.
- Use `category_overrides` for exact note placements and `category_prefix_overrides` for stable folder-level rules.

## Workflow

- `agents/index.md` owns first-run taxonomy design and bulk indexing.
- `agents/add.md` classifies targeted notes against the approved tree in `index.md`.
- `agents/search.md` combines content search, tag search, and hierarchy/index search.
- `agents/lint.md` checks for modified notes, missing notes, and branches that no longer match the tree.

When changing this skill, verify it with a clean-slate subagent run instead of relying only on the current session context.
