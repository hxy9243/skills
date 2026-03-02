# Preprocess Agent

## Goal
Analyze one candidate note and determine relevance to the seed note.

## Model Tier
- Use `agent_models.preprocess` from config.
- Resolve to `models.fast` by default for cost-efficient extraction.
- Use `models.deep` only when a note is dense, ambiguous, or highly technical.

## Input
- Seed note topic and key intent
- One candidate note content
- Candidate note path

## Required Output (Markdown)
1. `Relevance Score`: integer `0-10`
2. `Title`: candidate note title
3. `Filepath`: absolute path
4. `Summary`: 1-2 sentences
5. `Key Points`: concise bullets that add non-duplicated value
6. `Evidence`: 1-2 short direct quotes when useful
7. `Relevance Verdict`: `relevant` or `irrelevant`

## Relevance Rules
- Mark `irrelevant` when the note does not materially help the seed topic.
- Penalize weak thematic overlap and generic filler.
- Favor concrete claims, mechanisms, examples, and counterpoints.

## Format Rule
If irrelevant, keep output short but still include score, filepath, and verdict.
