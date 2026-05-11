# Wiki Lint

Use this workflow when the user wants validation, cleanup guidance, or confidence that the generated wiki is coherent.

## Goal

Run deterministic checks first, then perform a semantic health check of the wiki content. Turn the combined results into a short remediation plan.

Use the active model from the invoking skill/session if you summarize findings, but keep all validation logic in the `wikicli` python package and rely on search tools for semantic checks.

## Workflow

### Phase 1: Deterministic Lint

1. Run:

```bash
uv run wiki lint
# To focus on specific issues, use the --filter flag (e.g. --filter unindexed)
```

2. Read the text report.
3. Group findings by severity and type:
- missing source notes
- notes modified since their last recorded add event
- unindexed notes
- notes assigned to an invalid category

### Phase 2: Semantic Lint

After structural validation, perform a content-aware health check:

1. Read `index.md` to understand the category tree structure.
2. Inspect a subset (or all, if small) of the generated category synthesis pages (`categories/*/index.md`) and cross-reference them with recently modified or relevant notes.
3. Actively look for:
   - **Contradictions**: Conflicting statements between different category pages, or between a category synthesis and its underlying source notes.
   - **Stale Claims**: Statements in the synthesis pages that have been superseded by newer notes (check dates or recent log entries).
   - **Missing Cross-references**: Important concepts mentioned in the text that should be explicitly linked (`[[Concept]]`) to their respective pages.
   - **Orphan Pages**: Identify notes that are in the catalog but have zero inbound links from other notes or category pages. You can use `rg "\[\[Note Title\]\]"` to verify if a note is linked elsewhere.

### Phase 3: Remediation Plan

Recommend the smallest repair action that restores both structural and semantic coherence.

## Preferred Remediation Guidance

- Suggest `index` when generated category pages or `index.md` need rebuilding, or when removed notes need to be recorded.
- Suggest `add --json` when a note was modified and should be reclassified or refreshed in the log.
- Suggest `add --json` when notes exist but have not been classified.
- Call out missing source notes explicitly when logged entries point to deleted files.
- For semantic issues, suggest specific edits to the source notes or recommend re-running the `synthesize` agent for specific categories to resolve contradictions or stale claims.
