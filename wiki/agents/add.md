# Wiki Add

Use this workflow when the task is to add one or a few source notes into the generated wiki.

## Goal

Convert raw notes into normalized concept packets, then hand those packets to `scripts/wiki.py` so the backend can upsert concept pages, update ancestor summaries, and refresh manifests and search artifacts.

Use the active model from the invoking skill/session. Do not add model settings to wiki config or backend calls.

Always consult the approved `category_tree.md` before choosing `category_path`.

## Packet Shape

Produce JSON objects with these fields:

```json
{
  "title": "Concept title",
  "summary": "One paragraph summary",
  "category_path": ["Layer 1", "Layer 2", "Layer 3"],
  "tags": ["#tag-a", "#tag-b"],
  "source": "relative/path/to/note.md"
}
```

The backend derives stable IDs and any richer internal fields from this lighter packet shape.

## Workflow

1. Read the source note carefully.
2. Read the approved `category_tree.md` and find the best-fitting branch.
3. Normalize it into one concept packet unless there is a strong reason to split it.
4. Keep category paths broad and durable.
5. If the note clearly does not fit, extend the tree with the smallest necessary new subtree while preserving the three-level structure.
6. Prefer stable concept titles over catchy phrasing.
7. Save the packet JSON if needed, then call:

```bash
python wiki/scripts/wiki.py add --packet /tmp/wiki_packets.json
```

## Quality Bar

- Summary should explain what the concept is and why it matters.
- Category path should fit the approved tree, not invent brittle micro-buckets.
- Tags should be short and reusable.
- Source note paths must be relative to the notebook root.
- New subtrees should be rare and justified by repeated concept pressure, not a single quirky note.
