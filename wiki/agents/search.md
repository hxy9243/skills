# Wiki Search

Use this workflow when the user wants to search, browse, or answer questions from the generated wiki.

## Goal

Interpret the query, expand it into the most likely nearby concepts, let the backend combine content search, tag search, and hierarchy/index search, then use `index.md` and category pages for browse context.

Use the active model from the invoking skill/session for answer synthesis. Retrieval remains delegated in the `wikicli` python package.

## Workflow

1. Run search first:

```bash
uv run wiki search "user query"
```

2. Read note matches from the combined backends: Obsidian content search, tag matches, and hierarchy-aware matches.
3. Expand the query mentally to aliases, nearby terms, and likely related concepts before judging the results.
4. Read generated matches from `index.md` and `categories/`.
5. Use category-path context and the deterministic `layer1:`, `layer2:`, `layer3:`, and deeper `layerN:` labels when they help orient the user.
6. Prefer grounded synthesis over speculative inference.

## What Good Answers Include

- The most relevant concepts
- Their category paths or category pages
- The key distinction or pattern across top matches
- Direct mention of missing coverage when the wiki does not support the answer
- Hierarchy on each returned note when available
- Short evidence from the note body or tags explaining why the result matched

## Do Not

- Do not do retrieval in the prompt alone.
- Do not ignore category-page hits if they explain the branch better than any single note.
- Do not overfit to literal phrase matches when the user is clearly asking for a concept cluster.
