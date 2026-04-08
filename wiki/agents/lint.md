# Wiki Lint

Use this workflow when the user wants validation, cleanup guidance, or confidence that the generated wiki is coherent.

## Goal

Run deterministic checks first, then turn the result into a short remediation plan.

Use the active model from the invoking skill/session if you summarize findings, but keep all validation logic in `scripts/wiki.py`.

## Workflow

1. Run:

```bash
uv run wiki lint --log
```

2. Read the JSON report.
3. Group findings by severity:
- broken or missing generated artifacts
- notes modified since their last recorded add event
- notes that are missing from the approved category tree
- unindexed notes
- missing source notes or broken category coverage

4. Recommend the smallest repair action that restores coherence.

## Preferred Remediation Guidance

- Suggest `index` when generated category pages or `index.md` need rebuilding, or when removed notes need to be recorded.
- Suggest `add --packet` when a note was modified and should be reclassified or refreshed in the log.
- Suggest `add --packet` when notes exist but have not been classified.
- Call out missing source notes explicitly when logged entries point to deleted files.
