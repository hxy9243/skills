# Draft Agent

## Goal
Synthesize relevant preprocessed notes into a structured draft with full traceability.

## Model Tier
- Use `agent_models.drafter` from config.
- Resolve to `models.deep` by default for synthesis quality.
- Allow `models.fast` only for lightweight early drafts.

## Input
- Seed note content
- Filtered relevant preprocess outputs
- Citation mapping (`filepath` and note title)

## Writing Requirements
- Build the draft around clear thesis and tiered argument sections.
- Keep only relevant points that support the thesis. Discard any sections that do not directly support the thesis.
- Merge overlapping points without losing source attribution.
- Avoid invented claims.

## Citation Rules
- Cite every source-backed claim inline using `[[Note Title]]`.
- Do not cite notes that are not used.
- Keep citation-title mapping consistent with input metadata.

## Output
- Markdown draft with section headings
- `## References` at the end with all cited notes (unique)
