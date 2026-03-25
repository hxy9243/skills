# Retriever Agent

## Goal
Retrieve candidate supporting notes from a seed note.

## Model Tier
- Use `agent_models.retriever` from config.
- Resolve to `models.fast` by default for retrieval orchestration.
- Use `models.deep` only for complex query reformulation when needed.

## Input
- `seed_note_path`
- `zettel_dir`
- retrieval limits (`link_depth`, `max_links`)

## Procedure
1. Read retrieval limits from config and target candidate count from `retrieval.max_links`.
2. **MANDATORY FIRST STEP:** Always run the `zettel-link` skill (`scripts/search.py`) to retrieve high-quality semantic candidates using the seed note's topic or title. Do not skip this.
3. **THEN:** Run local retrieval (`scripts/find_links.py`) to collect explicit wikilinked and tag-overlap notes.
4. Merge and deduplicate all candidates from both tools.
5. Prioritize semantic candidates from `zettel-link`, then fill remaining slots with local retrieval results up to configured count.
6. Exclude the seed note itself.

## Output
- `candidate_paths`: unique prioritized list of markdown note paths
- `stats`: counts for semantic, wikilink, and tag-similar hits

## Constraints
- Use local vault evidence only.
- Do not score relevance in this stage.
