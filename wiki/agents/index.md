# Wiki Index

Use this workflow for first-time taxonomy setup, notebook-wide indexing, rebuilds, or category reshaping.

## Goal

Handle first-time taxonomy setup and whole-notebook classification planning, then let the `wikicli` python package index source notes against the log and rebuild the tree-focused `index.md`, `categories/`, and `log.md`.

Use the active model from the invoking skill/session for any synthesis or classification work. Do not try to configure a model in the backend.

## Workflow

1. Inspect the indexing scope and config.
2. On the first run for a notebook, do setup before indexing:
- Read a representative sample of notes.
- Propose a category tree that can fit the full notebook.
- Apply the taxonomy rules from `SKILL.md` under `Hierarchy Shape`; do not duplicate or override those limits here.
- Put that tree at the top of `index.md`, above a `---` separator.
- Ask the user to approve the tree before continuing to whole-repo indexing.
- Use `templates/category_tree.md.example` as the starting tree block, then paste it into the top of `index.md`.
3. Once the category tree in `index.md` is approved, treat it as the classification source of truth.
4. For each new or changed note, spawn a classification subagent to determine its best category path against the approved tree.
5. Parallelize that note-classification work when the batch is large, but cap concurrency at 8 subagents at a time so runs stay tractable.
6. Before rebuilding generated views, inspect important existing category pages, especially branches with hand-maintained multi-paragraph syntheses. Treat those synthesis bodies as durable content, not disposable generated filler.
7. After notes have been classified into the approved tree, rebuild generated views:

```bash
uv run --directory <wiki skill path> wiki --root <notebook-root> index
```

8. **Cascading Bottom-Up Synthesis**: After rebuilding, ensure that synthesis is rolled up at *each* category level. For any given category level, read the synthesis notes of its immediate depth-1 children to construct and update the synthesis of the current level.
9. Repeat that rollup process upward until the root boundary is reached.
10. After category rollups are complete, invoke `agents/homepage.md` as the final homepage-writing step so `HOME.md` reflects the updated wiki state.
11. When a category page already has a substantial `## Synthesis` section, preserve and update that body organically instead of replacing it with the short metadata `summary`. New ideas should be woven into the existing prose rather than dropped in as a full rewrite, unless the user explicitly wants a full resynthesis.
12. Keep this synthesis work in the skill workflow, not in the deterministic Python backend. `wiki.py` should update metadata, references, and structure, while the agent owns narrative synthesis edits and the final `HOME.md` synthesis.
13. If notes still need classification, generate packets and feed them through `add --json` before rebuilding.

## Responsibilities

- Decide whether a user request is best served by `add` or `index`.
- For first-time setup, force taxonomy design before whole-notebook indexing.
- Surface category collisions, poor bucket names, or overloaded branches.
- Apply the shared taxonomy hygiene rules from `SKILL.md` consistently, including branch splitting, consolidation, and review queue handling.
- Run `uv run --directory <wiki skill path> wiki --root <notebook-root> lint` to discover all unindexed notes.
- If there are unindexed notes, read the approved category tree at the top of `index.md` and any custom rules in `RULES.md` to guide classification.
- Keep hierarchy labels broad enough to survive future indexing.
- Keep the approved category tree in `index.md` updated when genuinely new subtrees are needed.
- Preserve existing rich category synthesis pages during rebuild-oriented workflows. Do not treat a one or two sentence summary as a full synthesis replacement.
- When synthesis needs to evolve, revise the existing prose in place. Prefer organic integration of new material over detached appendices or complete rewrites.
- Use the deterministic `layer1:`, `layer2:`, `layer3:`, and deeper `layerN:` labels when proposing or editing branch names.
- For bulk indexing, use note-level subagents as the classification workers and keep the run bounded to 8 concurrent workers.

## Do Not

- Do not keep a second category-tree file beside `index.md`.
- Do not use ad hoc scripts for crawling or rebuilding.
- Do not hardcode provider-specific model behavior into the backend.
- Do not index the whole notebook before the user has accepted a category tree.
- Do not keep notes in a generic branch just because it already exists. Create or propose a better branch when the topic warrants it.
