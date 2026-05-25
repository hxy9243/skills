# Wiki Lint

Use this workflow when the user wants validation, cleanup guidance, or confidence that the generated wiki is coherent.

## Goal

Run deterministic checks first, perform a semantic health check of the wiki content, and actively execute all necessary repair actions to restore structural and semantic coherence.

Use the active model from the invoking skill/session to summarize findings and execute remediation, but keep all validation logic in the `wikicli` python package and rely on search tools for semantic checks.

## Workflow

### Phase 1: Deterministic Lint

1. Run:

```bash
uv run --directory <wiki skill path> wiki --root <notebook-root> lint
# To focus on specific issues, use the --filter flag (e.g. --filter unindexed)
```

2. Read the text report.
3. Group findings by severity and type:
- missing source notes
- notes modified since their last recorded add event
- unindexed notes
- notes assigned to an invalid category
- empty leaf categories with no indexed notes

### Phase 2: Semantic Lint

After structural validation, perform a content-aware health check:

1. Read `index.md` to understand the category tree structure.
2. Inspect a subset (or all, if small) of the generated category synthesis pages (`categories/*/index.md`) and cross-reference them with recently modified or relevant notes.
3. If a category synthesis page is empty, missing its `## Synthesis` body, or contains only placeholder text, invoke `agents/synthesize.md` for that exact category before continuing semantic lint. Treat the newly synthesized category page as the current source of truth for subsequent checks.
4. Actively look for:
   - **Contradictions**: Conflicting statements between different category pages, or between a category synthesis and its underlying source notes.
   - **Stale Claims**: Statements in the synthesis pages that have been superseded by newer notes (check dates or recent log entries).
   - **Missing Cross-references**: Important concepts mentioned in the text that should be explicitly linked (`[[Concept]]`) to their respective pages.
   - **Orphan Pages**: Identify notes that are in the catalog but have zero inbound links from other notes or category pages. You can use `rg "\[\[Note Title\]\]"` to verify if a note is linked elsewhere.
   - **Cascading Synthesis Gaps**: If there are new or recently modified notes in a sub-category, verify if their new topics or insights have been incorporated into the synthesis of that category, and recursively rolled up to its parent levels (all the way up to `HOME.md`).
   - **Missing Parent Links**: Check that every non-root `index.md` synthesis page has a `parent: "[[path/to/parent/index.md|Parent Category]]"` property in its frontmatter correctly pointing to its parent category.

### Phase 3: Cascading Rollup

When semantic lint identifies important new or changed knowledge in a category, propagate the change upward instead of stopping at the leaf page:

1. Start with the most specific affected category.
2. Invoke `agents/synthesize.md` for that category if its synthesis is missing, empty, stale, or does not reflect the important change.
3. Re-run `agents/synthesize.md` for each parent category in order, using the updated child category page as part of the evidence considered by the parent synthesis.
4. Continue until the root category boundary is reached.
5. If there is no more specific sub-category to update, or after all affected parent categories have been updated, invoke `agents/homepage.md` so `HOME.md` reflects the propagated change.
6. Treat `HOME.md` as agent-owned output. Do not rely on the deterministic Python backend to write or repair it.

### Phase 4: Execute Remediation

Do not stop after identifying issues or simply proposing a remediation plan. Actively execute the necessary repairs to restore both structural and semantic coherence:

1. **Rebuild Indexes**: If the deterministic report flags that indices are out of sync or category pages need rebuilding, run:
   ```bash
   uv run --directory <wiki skill path> wiki --root <notebook-root> index
   ```
2. **Reclassify/Add Notes**: If notes exist but are unclassified, or if notes have been modified and need their classification refreshed or re-logged, run the `agents/add.md` workflow for those notes (or invoke the corresponding `wiki add` command).
3. **Handle Deleted Notes**: If there are missing source notes (i.e. logged entries pointing to deleted files), remove their references from `log.md` and rebuild the indexes to reflect the deletion.
4. **Fix Semantic Gaps & Contradictions**:
   - For empty or placeholder syntheses, invoke `agents/synthesize.md` for the affected category.
   - For contradictory or stale statements, trace the source notes to determine the ground truth, update the source notes if necessary, and re-run `agents/synthesize.md` for the category.
5. **Resolve Orphan Pages & Cross-references**:
   - Edit the relevant notes/category pages to add missing `[[Concept]]` or `[[Note Title]]` wiki links, ensuring all pages are well-connected.
6. **Propagate Cascading Rollups**:
   - If changes were made to sub-category syntheses, invoke `agents/synthesize.md` upward for each parent category sequentially, then invoke `agents/homepage.md` to refresh `HOME.md` as the final human-facing pass.
7. **Prune Empty Categories**: Remove empty leaf categories from the approved tree in `index.md` and delete their generated folders/files, unless there is a specific reason to keep them.

Once remediation is complete, provide the user with a concise summary of the executed actions and the resolved issues.
