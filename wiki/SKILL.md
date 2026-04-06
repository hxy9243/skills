---
name: wiki
description: Build and maintain a formal notebook wiki with concept pages, hierarchy summaries, incremental indexing, semantic search, and linting. Use this whenever the user wants to turn notes into a browsable knowledge base, organize an Obsidian notebook into categories, regenerate a wiki index, search across synthesized concepts, or validate wiki integrity.
---

# Wiki

This skill formalizes a notebook into a generated wiki workspace. Keep model-driven interpretation in the subagents and keep deterministic processing in `scripts/wiki.py`.

## What This Skill Owns

- Source notes stay in the notebook.
- Generated wiki artifacts live in a separate wiki root.
- Concept pages are the leaf knowledge objects.
- Category, subcategory, and topic layers each get a generated markdown synthesis page.
- Search uses persisted lexical and semantic indexes.
- Incremental indexing is the default operating mode.

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
  },
  "model": {
    "provider": "inherit-from-skill",
    "chat_model": "inherit-from-skill",
    "embedding_model": "inherit-from-skill"
  }
}
```

Environment overrides:
- `WIKI_CONFIG_PATH`
- `WIKI_NOTEBOOK_ROOT`
- `WIKI_INCLUDE_ROOTS`
- `WIKI_EXCLUDE_GLOBS`
- `WIKI_GENERATED_ROOT`

`include_roots` are resolved relative to `notebook_root` unless absolute.

## Generated Artifacts

The Python backend maintains:
- `concepts/`: generated concept pages
- `hierarchy/`: generated category synthesis pages
- `manifests/concepts.json`: normalized concept records
- `manifests/hierarchy.json`: hierarchy node records
- `manifests/sources.json`: source-note fingerprints
- `search/index.json`: persisted lexical and semantic search data
- `state/state.json`: incremental state
- `index.md`: top-level browse entrypoint

## Operating Rules

- Let subagents interpret notes and queries.
- Let `scripts/wiki.py` own file IO, manifests, hierarchy regeneration, indexing, search ranking, and lint checks.
- Prefer `index` for broad refreshes and `add` for small targeted updates.
- Use packet mode when a subagent has already normalized concept data:

```bash
python wiki/scripts/wiki.py add --packet /tmp/wiki_packets.json
```

- Keep the hierarchy at exactly three layers before concept leaves.
- Treat source notes as references; do not rewrite them in place.
