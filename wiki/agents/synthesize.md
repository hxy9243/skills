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

1. Discover the notes.
   - If synthesizing an ad-hoc topic, use search:
     ```bash
     uv run --directory <wiki skill path> wiki --root <notebook-root> search "user topic"
     ```
   - If synthesizing an entire category, use list recursively:
     ```bash
     uv run --directory <wiki skill path> wiki --root <notebook-root> list "Category > Path" --recursive
     ```

2. Expand the topic mentally before judging the results.
   - Include aliases, adjacent methods, likely frameworks, and overlapping vocabulary.
   - Example: `prompt optimization` may imply `DSPy`, `MIPRO`, `GEPA`, `OPRO`, prompt tuning, harness optimization, and evaluation loops.

3. Gather the strongest note set.
   - Prefer notes with direct evidence in the title, body, tags, or category path.
   - Include category-page hits when they help explain the branch better than any single note.
   - If the topic is broad, also run a narrower follow-up search on the top two or three nearby terms.

4. Cross-reference and analyze the notes.
   - **Chronological Evolution**: Pay close attention to the creation dates (in filenames or frontmatter) of the notes. Trace how the topic's focus, technology, or sentiment has evolved over time.
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
   - Start with `## Emerging Topics & Key Ideas` as the first content section. Use up to 10 concise bullets to highlight the most important new topics, keywords, connections, contradictions, trends, or key ideas discovered in the note set. Each bullet should include direct wikilinks to the relevant notes or category pages when available.
   - Then add `## Synthesis`.
   - **Contextual Framing (5W1H)**: Begin the synthesis body with a short framing paragraph that defines the topic using the 5W1H framework (Who, What, When, Where, Why, How) to capture human intent and prevent generic summaries.
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

You must produce a **textbook-level** deep dive. Do not generate shallow bullet summaries. Your synthesis should read like an authoritative, comprehensive chapter that explains the topic inside-out, heavily backed by inline references to the source notes.

Do **not** use an "Outline" section. Start the content with `## Emerging Topics & Key Ideas`, then use `## Synthesis` followed by logical sub-sections.

Good synthesis responses usually include:

- `Deep Synthesis (The Core)`
  - Use Markdown headers (`###` or `####`) for structural sub-sections, rather than bold text.
  - **Chronological Evolution**: A walkthrough of how the concepts and focuses have shifted over time based on note dates.
  - **Comprehensive Concept Walkthroughs**: Clear, detailed explanations of the underlying mechanisms, classic architectures, and definitions. Do not skip major themes present in the note set.
  - **In-Depth Analysis**: Detailed exploration of paradigms, frameworks, and state-of-the-art developments.
  - **Tradeoffs & Failure Modes**: Explicit discussion of edge cases, limitations, and architectural tradeoffs.
  - **Inline Citations**: Every major claim must be explicitly backed by an inline reference linking to the original source note.
- `Key Topics & Terminologies`
  - A structured list defining the core vocabularies and concepts introduced in the synthesis. **Every term must include an inline citation** to the note that defines it.
- `Insights & Visualizations`
  - Deep analytical insights, connections, and common themes.
  - Presentations like Markdown tables or Mermaid graphs/flowcharts **only if strictly necessary and genuinely helpful for understanding**.
- `Gaps or weak coverage`
  - missing concepts, contradictions, or thin areas in the note set.
- `References`
  - all notes materially used (note path and brief evidence cue).

## Quality Bar

- Search or list first. Do not synthesize from memory alone.
- For standalone synthesis output, include `## Emerging Topics & Key Ideas` as the first content section before `## Synthesis`, limited to 10 bullets. For generated category-page edits, keep the backend-owned page shape and merge those ideas into the `## Synthesis` body unless the page already has a dedicated emerging-topics section.
- **Density & Depth**: The output must be substantial. Provide a meaningful, inside-out walkthrough of the topic, not just a surface-level gloss. Be exhaustive and ensure all major topics discovered in the notes are represented.
- **No Tags**: Do not include hashtag tags (`#tag`) within the synthesis text. Keep them empty or remove them.
- **Headers Over Bold**: Use markdown heading syntax for sub-sections rather than bold text.
- Favor recurring patterns across notes over isolated claims.
- Keep the output highly grounded. Heavily use inline references with Obsidian wiki syntax (`[[Note Title]]`) when backing up claims.
- Prefer a coherent conceptual map over a bag of excerpts.
- Explicitly distinguish note-supported conclusions from your own inference.
- Always include a final `References` section.

## Do Not

- Do not just list notes without integrating them.
- Do not overfit to literal phrase matches when the topic is clearly broader.
- Do not flatten disagreements or tradeoffs into fake consensus.
- Do not present external facts as though they came from the notebook.
- Do not rewrite source notes in place.

# Result Output

For a synthesis for a category already in the tree, the Python backend owns the generated category page skeleton. It creates and refreshes `path/to/category/index.md`, including frontmatter, layer path, subcategories, and references. Your primary job is to update the category page's narrative `## Synthesis` section, and to preserve or improve any existing rich prose.

Before editing a generated category page:

1. Run `uv run --directory <wiki skill path> wiki --root <notebook-root> list "Category > Path" --recursive --include-body` to retrieve the relevant source notes.
2. Read the existing generated category page directly.
3. Keep the backend-owned structure intact unless the user explicitly requests a full page rewrite.
4. Replace or revise only the `## Synthesis` body when possible. If there is already a substantial synthesis, merge new ideas into it organically rather than replacing it wholesale.
5. Leave deterministic sections such as `## Layer Path`, `## Subcategories`, and `## References` to the backend unless you are correcting a clear backend defect.

Generated category pages normally follow this backend-owned structure:

```markdown
---
category: "Computer Science > ... > Target Category"
parent: "[[path/to/parent/index.md|Parent Category]]"
created: 2026-05-11T00:00:00Z
modified: 2026-05-11T00:00:00Z
summary: "One or two sentences that highlight the subject of the category itself, not a list of note titles or references."
tags: []
---
# layer[X]: Target Category

## Layer Path
- layer1: Computer Science
...
- layer[X]: Target Category

## Subcategories
(List the subcategories returned by `wiki list`, linked to their index.md files, e.g., `- [layer[X+1]: Subcategory](subcategory/index.md)`. If none, omit this section entirely. IMPORTANT: For non-leaf categories, make sure this subcategory list is at the very top of the page, immediately after the Layer Path.)

## Synthesis
(Agent-maintained deep textbook-level synthesis goes here...)

## References
(Backend-maintained note references.)
```

If it is a top-level synthesis for the entire wiki or notebook, invoke `agents/homepage.md` and write the result to `HOME.md` at the notebook root. Do not add a `parent` property to the homepage frontmatter.

For generated category syntheses, the `summary` frontmatter is mandatory. It should be compact, human-facing, and Dataview-friendly: one or two sentences that explain why the category matters or what it covers. Do not turn the summary into a roll call of note titles.

If the topic is not covered in the category tree, propose the smallest necessary tree addition first. After the tree is accepted and regenerated with `wiki index`, synthesize into the generated page. Do not create free-floating generated category pages that are absent from the approved tree.

If the result is not necessarily matching a category (e.g. a synthesis across different categories) you can save the results into a new note in the appropriate category.

## Compound Knowledge

If the synthesis represents a highly valuable new concept, deep analysis, or comparison, or if the user explicitly asks to save the synthesis, you should offer to file it back into the wiki as a new source note. This allows explorations to compound over time.

To save a synthesis:
1. Create a new markdown file in the user's notebook (e.g., alongside related source notes or in a `Syntheses/` folder).
2. **Rich Frontmatter**: Include rich YAML frontmatter to fully leverage Obsidian tools like Dataview and Graph View. You must include `date`, `modified`, `tags`, `source_count` (number of notes synthesized), and `entity_links` (direct wikilinks to the core notes used). Always update the `modified` timestamp when updating an existing synthesis.
3. When necessary, use rich representations to better present your ideas, like a mermaid flowchart, table, or lists.
4. Write the synthesized content into the file.
5. Build a single add packet for the new note, then run `uv run --directory <wiki skill path> wiki --root <notebook-root> add --json '<json-packet>'` to index it back into the wiki.
