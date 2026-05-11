# Wiki Synthesize

Use this workflow when the user wants a synthesized presentation of a topic assembled from the notebook or generated wiki.

## Goal

Search broadly first, cross-reference the strongest matches, extract the core topics and disagreements, then produce a grounded synthesis that reads like a coherent topic brief rather than a search dump.

Keep retrieval in the backend and keep interpretation in the subagent.

## When To Use

Use this workflow when the user asks for any of the following:

- a synthesis of a topic or category
- an outline plus synthesis
- a topic brief from notes
- a cross-note summary
- a distilled view of a concept cluster

Prefer `agents/search.md` when the user mostly wants note discovery or direct Q&A. Prefer this workflow when the user wants a higher-level presentation built from multiple notes.

## Workflow

1. Run search first.

```bash
uv run wiki search "user topic"
```

2. Expand the topic mentally before judging the results.
   - Include aliases, adjacent methods, likely frameworks, and overlapping vocabulary.
   - Example: `prompt optimization` may imply `DSPy`, `MIPRO`, `GEPA`, `OPRO`, prompt tuning, harness optimization, and evaluation loops.

3. Gather the strongest note set.
   - Prefer notes with direct evidence in the title, body, tags, or category path.
   - Include category-page hits when they help explain the branch better than any single note.
   - If the topic is broad, also run a narrower follow-up search on the top two or three nearby terms.

4. Cross-reference the notes.
   - Compare repeated ideas across notes.
   - Separate core agreements from one-off claims.
   - Identify useful distinctions such as method families, tradeoffs, or chronology.
   - Note contradictions, uncertainty, or shallow coverage explicitly.

5. Extract the core topics.
   - Reduce the cluster into a small number of recurring themes.
   - Good theme types:
     - definitions and boundaries
     - method families
     - evaluation patterns
     - best practices
     - tradeoffs and failure modes
     - open questions or gaps

6. Create the synthesized presentation.
   - **Contextual Framing (5W1H)**: Start with a short framing paragraph that defines the topic using the 5W1H framework (Who, What, When, Where, Why, How) to capture human intent and prevent generic summaries.
   - Then present the major themes in a deliberate order.
   - Prefer synthesis over note-by-note recitation.
   - Keep each claim tied to note evidence.
   - Include note paths and short snippets when they materially support the synthesis.
   - Reference the note for your claims, as a part of your narrative.

7. Call out gaps.
   - If the notebook coverage is thin, fragmented, or mostly references external material, say so directly.
8. Always end with references.
   - Include a final `References` section.
   - List every note materially used in the synthesis.
   - Prefer note path plus a short reason or evidence cue.

## Output Shape

Good synthesis responses usually include:

- `Relevant notes`
  - note path
  - hierarchy when available
  - short evidence snippet
- `Outline`
  - a compact structure for the topic
- `Synthesis`
  - the integrated presentation of the topic
- `Gaps or weak coverage`
  - missing concepts
  - contradictions
  - thin areas in the note set
- `References`
  - all notes materially used
  - note path and brief evidence cue

## Quality Bar

- Search first. Do not synthesize from memory alone.
- Favor recurring patterns across notes over isolated claims.
- Keep the output grounded in note evidence.
- Prefer a coherent conceptual map over a bag of excerpts.
- Use category-path context when it helps orient the user.
- Explicitly distinguish note-supported conclusions from your own inference.
- Always include a final `References` section.

## Do Not

- Do not just list notes without integrating them.
- Do not overfit to literal phrase matches when the topic is clearly broader.
- Do not flatten disagreements or tradeoffs into fake consensus.
- Do not present external facts as though they came from the notebook.
- Do not rewrite source notes in place.

# Result Output

By default, if it's a synthesis for a given category in the tree, write the result into the `path/to/category/index.md` file, under the section `## Synthesis`, `## Summary`, or `## Topics Covered`.

If the topic is not covered in the category tree, you can propose and write a new `path/to/category/index.md` file, and add it into the tree structure.

If the result is not necessarily matching a category (e.g. a synthesis across different categories) you can save the results into a new note in the appropriate category.

## Compound Knowledge

If the synthesis represents a highly valuable new concept, deep analysis, or comparison, or if the user explicitly asks to save the synthesis, you should offer to file it back into the wiki as a new source note. This allows explorations to compound over time.

To save a synthesis:
1. Create a new markdown file in the user's notebook (e.g., alongside related source notes or in a `Syntheses/` folder).
2. **Rich Frontmatter**: Include rich YAML frontmatter to fully leverage Obsidian tools like Dataview and Graph View. You must include `date`, `tags`, `source_count` (number of notes synthesized), and `entity_links` (direct wikilinks to the core notes used).
3. When necessary, use rich representations to better present your ideas, like a mermaid flowchart, table, or lists.
4. Write the synthesized content into the file.
5. Build a single add packet for the new note, then run `uv run wiki add --json '<json-packet>'` to index it back into the wiki.
