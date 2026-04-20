# wiki

The `wiki` skill turns an Obsidian-style note collection into a lightweight generated wiki rooted in category pages, with search and topic-synthesis workflows on top of the indexed notes.

## Install

```bash
npx skills install wiki
```

## Quick Start

You can interact with the wiki natively through the agent using natural language.

1. **First-time setup**: Ask the agent to "set up the wiki" or "index the notebook for the first time" to generate your initial category tree.
   - *Example*: "@wiki set up the wiki for my current notebook"
   - *Example*: "@wiki read through my notes and propose a category tree"
2. **Add a note**: Say "add this note to the wiki" to classify and ingest one note into the established categories.
   - *Example*: "@wiki add `Notes/Delegation.md` to the wiki"
3. **Search notes**: Ask "search my notes for X" to get direct, evidence-backed answers with hierarchy context.
   - *Example*: "@wiki search my notes for chain-of-thought prompting"
   - *Example*: "@wiki what do my notes say about distributed consensus algorithms?"
4. **Synthesize**: Ask "synthesize a topic brief on Y" to cross-reference multiple notes into a cohesive summary.
   - *Example*: "@wiki synthesize what my notes say about reasoning prompts in LLMs"
   - *Example*: "@wiki create a topic brief for the 'AI Agents' category"
5. **Automation (Dream & Cron Jobs)**: You can configure the agent's background `dream` or `cron` workflows to automatically add new notes, synthesize weekly roundups, and run `lint` to maintain the wiki without manual intervention.
   - *Example Dream Task*: "Look for unindexed notes in the workspace and classify them into the wiki."
   - *Example Cron Task*: "Run `@wiki lint` every night to ensure the wiki integrity is preserved."

## What It Generates

- `index.md`: the approved category tree and note placement index
- `log.md`: append-only add/remove/lint history
- `categories/`: one generated synthesis page per category node
- `config.json`: notebook-local configuration, typically stored under `_WIKI/`
- `RULES.md`: category rules, notes, exceptions and overrides from user.

## Commands

```bash
uv run wiki add --packet '{"title":"Delegation","summary":"Delegate work to smaller agents for bounded tasks.","category":"Computer Science > AI Systems > Agents","tags":["#agents"],"source":"Notes/Delegation.md"}'
uv run wiki index
uv run wiki search "query"
uv run wiki synthesize --category "Computer Science > Artificial Intelligence > AI Agents"
uv run wiki lint
```

## Testing

To run the full suite of unit and integration tests for the Python backend:

```bash
uv run python -m unittest discover tests/
```

## Skill Use Example

### Example category tree in `index.md`

```text
- layer1: [[Computer Science]]
  - layer2: [[Artificial Intelligence]]
    - layer3: [[LLM]]
      - [[20_Subjects/Computer Science/Papers/Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.md]]
      - [[20_Subjects/Computer Science/Papers/Least-to-Most Prompting Enables Complex Reasoning in Large Language Models.md]]
```

## Search

input

> Search my notes for chain-of-thought prompting.

output

```
Assistant: I found the strongest hit in
[[20_Subjects/Computer Science/Papers/Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.md]]
under [[Computer Science]] > [[Artificial Intelligence]] > [[LLM]].

It matches because the note explicitly covers reasoning in large language models and sits in the same concept branch as related prompting papers.
```

## Synthesis

input

> Synthesize what my notes say about reasoning prompts in LLMs.

output

```text
Assistant: Your notes treat reasoning prompts as a family of techniques for improving multi-step problem solving in LLMs.

The core cluster here is:
- [[20_Subjects/Computer Science/Papers/Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.md]]
- [[20_Subjects/Computer Science/Papers/Least-to-Most Prompting Enables Complex Reasoning in Large Language Models.md]]

Together they suggest a progression from eliciting intermediate reasoning to structuring harder problems into smaller ordered steps.

References:
- [[20_Subjects/Computer Science/Papers/Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.md]]
- [[20_Subjects/Computer Science/Papers/Least-to-Most Prompting Enables Complex Reasoning in Large Language Models.md]]
```

**Compound Knowledge**: You can ask the agent to "save this synthesis" to permanently file it back into your notebook as a new source note, allowing your explorations to compound over time.

## Config Resolution

The backend resolves config in this order:

1. `--config <path>`
2. `<generated_root>/config.json`
3. `~/.wiki/config.json`
4. built-in defaults

Use [`templates/config.json.example`](./templates/config.json.example) as the starter template.

## Category Rules

If the user has specific classification preferences, they should be documented in `RULES.md` in the wiki root. Subagents should consult `RULES.md` alongside the approved category tree when classifying notes.

- Keep three layers as the default starting point, but add deeper layers when a branch gets crowded or conceptually dense.
- Aim for roughly 5-10 children per layer.
- Prefer durable topic branches over generic buckets like `Research`, `Papers`, `General`, or `Misc`.
- Do not shoehorn notes into an existing branch when the note clearly points to a better topic-shaped subtree.
- Treat fallback branches as review queues only. Reclassify them into topic branches as soon as the right subtree is clear.
- Split branches once they pass roughly 12 direct children or clearly contain subclusters.
- Consolidate overlapping systems buckets when they represent the same browsing intent.
- Prefer retrieval-first grouping over folder-first grouping. Notes from different source folders can still belong in the same concept subtree.

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
