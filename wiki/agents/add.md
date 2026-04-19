# Wiki Add

Use this workflow when the task is to add one or a few source notes into the generated wiki.

## Goal

Convert raw notes into normalized classification packets, then hand those packets to the `wikicli` python package so the backend can update `index.md`, regenerate category pages, and append to `log.md`.

Use the active model from the invoking skill/session. Do not add model settings to wiki config or backend calls.

Always consult the approved category tree at the top of `index.md` before choosing `category`. Use the deterministic branch labels `layer1:`, `layer2:`, `layer3:`, and deeper `layerN:` labels when referring to parts of the tree.

## Packet Shape

Produce JSON objects with these fields:

```json
{
  "title": "Note title",
  "summary": "One paragraph summary",
  "category": "Layer 1 > Layer 2 > Layer 3",
  "tags": ["#tag-a", "#tag-b"],
  "search_terms": ["search term 1", "search term 2"],
  "source": "relative/path/to/note.md"
}
```

The backend keeps this packet shape lightweight and deterministic.

## Workflow

1. Read the source note carefully.
2. Read the approved category tree from the top of `index.md` and find the best-fitting branch. Check `RULES.md` in the wiki root if it exists to apply any custom user rules.
3. Normalize it into one concept packet unless there is a strong reason to split it.
4. **Entity & Concept Page Maintenance**: Check if there is an existing synthesis or summary source note for the target category. If a concept page already exists for this topic, read it and use your file editing tools to update it by integrating any new information, nuances, or contradictions introduced by the new note.
5. Choose the branch that would make this note easiest to rediscover later through natural search queries.
6. Keep category paths broad and durable, but add a deeper level when a dense concept family is already forming.
7. If the note clearly does not fit, extend the tree with the smallest necessary new subtree rather than forcing a weak placement.
8. Keep concept families consistent across folders. If an AI note in `10_Projects` and an AI note in `20_Subjects` belong together for search, place them together.
9. Prefer stable concept titles over catchy phrasing.
10. Pull reusable tags from frontmatter when available and normalize them into short search-friendly tags.
11. Call the add command with the packet as an inline JSON string:

```bash
uv run wiki add --packet '{"title": "Note title", "summary": "One paragraph summary", "category": "Layer 1 > Layer 2 > Layer 3", "tags": ["#tag-a"], "search_terms": ["search term 1", "search term 2"], "source": "relative/path/to/note.md"}'
```

## Quality Bar

- **Contextual Framing (5W1H)**: The summary must strictly answer: Who is involved? What is the core concept? When/Where does it apply? Why does it matter? How is it implemented or used? This captures human intent and prevents generic summaries.
- Category path should fit the approved tree, not invent brittle micro-buckets.
- Category path should reflect retrieval intent, not just where the note happens to live in the notebook.
- Tags should be short and reusable.
- Search terms should be short and reusable, optimizing for deterministic search.
- Source note paths must be relative to the notebook root.
- New subtrees should be rare and justified by repeated concept pressure, not a single quirky note.
