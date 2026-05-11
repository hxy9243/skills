# Wiki Homepage Agent

This agent is responsible for generating the root `HOME.md` (or `MAIN.md`) of the notebook, acting as the dynamic front page of the Wiki.

## Goal

Generate a comprehensive homepage that provides a complete category tree, highlights newly generated syntheses, outlines emerging topics and ideas, and lists recently added notes in reverse chronological order by `created` time. The homepage should be skimmable: use light, purposeful emoji markers in section entries when they help guide reading.

## Execution

When instructed to generate the homepage, perform the following steps:

1. **Context Gathering**:
   - Run `uv run wiki list "" --recursive` to retrieve the entire category tree.
   - Run `uv run wiki lint` to identify recently modified notes or unindexed files without regenerating wiki files.
   - Inspect recently modified `index.md` files (specifically the `# Synthesis` blocks) to extract new topics, keywords, and key ideas.

2. **Template Enforcement**:
   You MUST write the homepage file to `HOME.md` at the root of the notebook, using exactly the following structure:

   ````markdown
   ---
   created: 2026-05-11T00:00:00Z
   modified: 2026-05-11T00:00:00Z
   ---

   # Wiki Homepage

   ## Category Tree
   (Generate a hierarchical bulleted list of all categories up to the leaf category. Use wikilinks to link to their respective `index.md` files, e.g., `- [[_WIKI/categories/computer-science/index.md|Computer Science]]`).

   ## New Syntheses
   (Provide a synthesized summary of the most recently generated or updated category pages. Each bullet MUST start with an ISO date in `YYYY-MM-DD` form, inferred from the category page `modified` frontmatter or filesystem modified time when frontmatter is absent. Briefly describe what knowledge was synthesized and link to the category `index.md` files. You may use a concise emoji marker after the date to improve scanability.)

   ## Emerging Topics & Key Ideas
   (Highlight new topics, keywords, and key ideas extracted from recent notes or syntheses. Each bullet MUST start with an ISO date in `YYYY-MM-DD` form, inferred from the relevant note or synthesis `created`/`modified` frontmatter or filesystem timestamp. Use bolding for key terms and provide direct wikilinks to the relevant notes or categories. You may use a concise emoji marker after the date to improve scanability.)

   ## Recent Notes
   (Use the following exact Obsidian Dataview block to list the 50 most recently created notes. `SORT date(created) DESC` is required so the notes are reverse chronological by parsed created date. Exclude all `index` files from this list):

   ```dataview
   TABLE created, category
   WHERE category != null AND file.name != "index"
   SORT date(created) DESC
   LIMIT 50
   ```

   ````

## Constraints

- Do not include the `parent` property in the frontmatter, as this is the root node.
- Ensure the Category Tree accurately reflects the filesystem hierarchy of `_WIKI/categories`.
- Ensure Recent Notes excludes generated or category `index` files.
- Do not run `wiki index` to overwrite files; use `wiki list`, `wiki lint`, filesystem metadata, and direct reads of generated category pages to gather metadata.
