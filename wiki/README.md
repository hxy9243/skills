# wiki

`wiki` turns an Obsidian-style note collection into a lightweight generated wiki rooted in category pages, with search and topic-synthesis workflows on top of the indexed notes.

## What It Generates

- `index.md`: the approved category tree and note placement index
- `log.md`: append-only add/remove/lint history
- `categories/`: one generated synthesis page per category node
- `config.json`: notebook-local configuration, typically stored under `_WIKI/`

## Commands

```bash
uv run wiki add ...
uv run wiki index
uv run wiki search "query"
uv run wiki synthesize --category "Computer Science > Artificial Intelligence > AI Agents"
uv run wiki lint
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
- Prefer retrieval-first grouping over folder-first grouping. Notes from different source folders can still belong in the same concept subtree.
- Use `category_overrides` for exact note placements and `category_prefix_overrides` for stable folder-level rules.

## Workflow

- `agents/index.md` owns first-run taxonomy design and bulk indexing.
- `agents/add.md` classifies targeted notes against the approved tree in `index.md`.
- `agents/search.md` combines content search, tag search, and hierarchy/index search.
- `agents/synthesize.md` searches, cross-references, extracts core topics, and produces a synthesized presentation with references at the end.
- `agents/lint.md` checks for modified notes, missing notes, and branches that no longer match the tree.

## Synthesis Workflow

Use synthesis when the user wants a topic brief built from multiple notes rather than just search hits.

- Search first to gather the strongest note set.
- Cross-reference the notes to identify recurring ideas, distinctions, and contradictions.
- Extract the core topics into a compact outline.
- Produce a synthesized presentation grounded in note evidence.
- Always include references at the end for every materially used note.

When changing this skill, verify it with a clean-slate subagent run instead of relying only on the current session context.
