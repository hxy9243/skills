# Wiki Homepage Agent

This agent is responsible for generating `HOME.md` in the notebook root, acting as the dynamic front page of the Wiki.

## Goal

Generate a concise, human-friendly homepage that highlights newly generated syntheses, outlines emerging topics and ideas, and lists recently added notes in reverse chronological order by `created` time. The homepage should be skimmable: use light, purposeful emoji markers when they help guide reading, but do not turn the page into emoji soup.

## Execution

When instructed to generate the homepage, perform the following steps:

1. **Context Gathering**:
   - Run `uv run --directory <wiki skill path> wiki --root <notebook-root> tree --format json` to retrieve the deterministic category tree from the backend.
   - Run `uv run --directory <wiki skill path> wiki --root <notebook-root> lint` to identify recently modified notes, unindexed files, and empty leaf categories without regenerating wiki files.
   - Inspect recently modified generated category pages, especially their `summary`, `modified`, `wiki_role`, and `wiki_status` metadata, plus the `# Synthesis` blocks when needed, to extract new topics, keywords, and key ideas.

2. **Template Enforcement**:
   You MUST write the homepage file to `HOME.md` at the root of the notebook, using exactly the following structure:

   ````markdown
   ---
   created: 2026-05-11T00:00:00Z
   modified: 2026-05-11T00:00:00Z
   ---

   # Wiki Homepage

   ## Category Tree
   (Render this from `wiki tree --format json`, not by inventing or hand-curating a separate tree. Keep it readable. Use wikilinks to the generated category pages, and include note counts when helpful.)

   ## New Syntheses
   (Use an Obsidian Dataview table driven by generated synthesis-page metadata. Prefer columns like `Synthesis`, `Category`, `Summary`, and `Updated`. Do not maintain this section manually when the metadata contract is available.)

   ## Emerging Topics & Key Ideas
   (Write this as concise bullets, not a table. Highlight new topics, keywords, and key ideas extracted from recent notes or syntheses. Each bullet MUST start with an ISO date in `YYYY-MM-DD` form, inferred from the relevant note or synthesis `created`/`modified` frontmatter or filesystem timestamp. Use bolding for key terms and provide direct wikilinks to the relevant notes or categories. You may use a concise emoji marker after the date to improve scanability.)

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
- Ensure the Category Tree is derived from the backend `wiki tree` command, not improvised manually.
- Ensure Recent Notes excludes generated or category `index` files.
- Prefer tables only for `New Syntheses` and `Recent Notes`. Avoid turning every section into a table.
- Prefer the generated synthesis metadata contract, especially `summary`, over hand-maintained prose for `New Syntheses`.
- Do not run `wiki index` to overwrite files, use `wiki tree`, `wiki list`, `wiki lint`, filesystem metadata, and direct reads of generated category pages to gather metadata.
