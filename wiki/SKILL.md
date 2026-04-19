---
name: wiki
description: Build and maintain organized knowledge from raw source notes into a formal wiki with category-organized indexes, hierarchy summaries, delegated search, synthesis, and linting. Use this whenever the user wants to turn notes into a browsable knowledge base, organize an Obsidian notebook into categories, regenerate a wiki index, search across synthesized categories, create a synthesized topic summary, or validate wiki integrity.
---

# Wiki

This skill formalizes a notebook into a generated wiki workspace for easier indexing, organization, and retrieval.

## What This Skill Owns

- Source notes stay in the notebook.
- Generated wiki artifacts live in a separate wiki root.
- The approved category tree lives at the top of `index.md` and is the classification reference.
- User preferences live in the `RULES.md` file to guide or override categorization decisions.
- Category, subcategory, and topic layers each get a generated markdown synthesis page.
- Search combines `obsidian-cli search-content` when available, tag-aware note matching, and generated index/category search.
- `log.md` is the persistent record of adds, removals, and lint runs.
- Layer labels are written deterministically as `layer1: ...`, `layer2: ...`, `layer3: ...`, and deeper when needed, so prompts and search can target a specific depth.

## Retrieval-First Principles

Use these principles when indexing or searching:

- Taxonomy should optimize for how a user will try to find a note later, not for academic purity alone.
- Prefer consolidating semantically overlapping branches when they lead to the same retrieval behavior.
- For dense concept families like frameworks, optimizers, or evaluation loops, keep sibling notes clustered unless there is a strong browsing reason to split them.
- Search should infer nearby concepts, aliases, tags, and hierarchy cues instead of depending on the exact phrase the user typed.
- Good answers should return note path, hierarchy, and a short evidence snippet, not just a title match.

## Dispatch

Choose one of these six subagent workflows before touching the script:

1. `agents/setup.md`
Use when the task is to establish the wiki for the first time by proposing an initial category tree.

1. `agents/add.md`
Use for targeted note ingestion or when the user wants to add a few notes into the wiki.

2. `agents/index.md`
Use for notebook-wide or folder-wide indexing, incremental refreshes, and rebuilds.

3. `agents/search.md`
Use when the user wants answers or browsing help from the generated wiki.

4. `agents/synthesize.md`
Use when the user wants a synthesized presentation of a topic assembled from matching notes. The agent can save valuable syntheses back into the user's notebook as new source notes to compound knowledge over time.

5. `agents/lint.md`
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
  "search": {
    "lexical_limit": 8
  }
}
```

`include_roots` are resolved relative to `notebook_root` unless absolute.

Model choice is not part of the backend config. Subagents should inherit the active model from the invoking skill/session.

## Hierarchy Shape

The generated wiki should default to three hierarchy layers before note leaves, but may add deeper layers when a branch gets crowded or a concept is clearly dense enough to deserve a finer split.

Rule of thumb:
- Keep each level to roughly 5-10 children.
- Prefer broad, durable buckets over narrow one-off branches.
- Prefer real topics over generic buckets like `Research`, `Papers`, `General`, or `Misc`.
- Do not shoehorn notes into an existing branch when they point to a clearer topical subtree.
- Treat fallback branches as explicit review queues, not as real long-term categories.
- Expand the tree only when a concept clearly does not fit an existing branch.
- If a branch grows past roughly 12 direct children, or multiple notes form a clear dense cluster, add another layer instead of leaving an overloaded bucket.
- Consolidate overlapping systems buckets when they reflect the same browsing intent.
- Prefix each category row with its depth marker so the tree stays machine- and prompt-friendly.

Small example:

```text
- layer1: [Computer Science](Computer Science)
  - layer2: [Artificial Intelligence](Artificial Intelligence)
    - layer3: [AI Agents](AI Agents)
      - layer4: [Optimization](Optimization)
        - Note 1 on DSPy
        - Note 2 on GEPA
```

## Operating Rules

- Let subagents interpret notes and queries.
- Let `src/wikicli` own deterministic operations like file IO, category-page regeneration, log updates, indexing, delegated search, and lint checks.
- Keep the approved category tree at the top of `index.md` as the classification reference for `add` and first-time `index`.
- Keep `index.md` focused on the category tree itself. Do not regenerate a second browse-by-category section below it.
- Prefer `index` for broad refreshes and `add` for small targeted updates.
- `index` detects missing source notes, reports modified notes via source `mtime`, and rebuilds generated views.
- For notebook-wide indexing, classify new notes with subagents in parallel when feasible, but cap concurrency at 8 notes at a time.
- For broad or ambiguous note sets, have subagents propose better topical branches instead of forcing notes into a weak existing category.
- For taxonomy disputes, prefer the branch that would make future search queries easier to succeed.
- When a concept shows up across projects, papers, and inbox notes, cluster it consistently unless there is a strong reason to preserve source-folder distinctions.
- Use packet mode when a subagent has already normalized note classification data:

```bash
uv run wiki add --packet /tmp/wiki_packets.json
uv run wiki index
```

- Keep three layers as the default floor, not a hard ceiling. Add deeper layers when a branch becomes crowded or needs a finer conceptual split.
- Use the approved category tree from the top of `index.md` when classifying new notes. Add new subtrees only when the existing tree is clearly insufficient.
- When the notebook mixes `AI Systems` and `Machine Learning Systems`, prefer consolidating them under a shared `Artificial Intelligence` subtree when that matches how the user retrieves notes.
- Use the deterministic `layer1:`, `layer2:`, `layer3:`, and deeper `layerN:` labels when referring to branches in prompts, searches, or follow-up edits.
- Search responses should include hierarchy for each returned note whenever the backend can resolve it.
- Search responses should favor semantic matches with direct evidence over literal-but-weak text matches.
- Treat source notes as references; do not rewrite them in place.
- When changing this skill, always test it with a clean-slate subagent run rather than relying only on the current session context.
