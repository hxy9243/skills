# Skills

A collection of AI agent skills for productivity and knowledge management.

## Available Skills

-   **[Wiki](./wiki/)**: A notebook-to-wiki skill for indexing notes into a category-driven knowledge base with delegated search, topic synthesis, and linting.
-   **[Zettel Brainstormer](./zettel-brainstormer/)**: An AI-powered drafting tool that turns Zettelkasten notes into comprehensive writing drafts using a multi-stage LLM pipeline.
-   **[Zettel Link](./zettel-link/)**: A suite of tools to maintain note embeddings for semantic search and discovering connections between notes.
-   **[Startup Researcher](./startup-researcher/)**: An AI-powered research assistant that generates comprehensive market intelligence reports for startups.
-   **[Podcast Generator](./podcast-generator/)**: A complete pipeline for drafting, narrating (via TTS), and mixing high-quality audio podcasts or briefings with background music.

## Usage

Each skill is a self-contained directory with its own documentation and scripts. Navigate to the skill directory to get started.

## Slash Commands

`commands/<skill>.md` turns a skill into a `/skill` command. The same file works in every supported harness, because they all read the same Markdown shape: `description` and an optional `argument-hint` in the frontmatter, then a body where `$ARGUMENTS` is replaced by what you type after the command. Only the destination directory differs.

| Harness  | Destination                                                                             | Invoked as                     |
| -------- | --------------------------------------------------------------------------------------- | ------------------------------ |
| claude   | `~/.claude/commands/<skill>.md`                                                         | `/skill`                       |
| codex    | `~/.codex/prompts/<skill>.md`                                                           | `/prompts:skill` (deprecated)  |
| opencode | `$XDG_CONFIG_HOME/opencode/commands/<skill>.md` (default `~/.config/opencode/commands`) | `/skill`                       |
| pi       | `$PI_CODING_AGENT_DIR/prompts/<skill>.md` (default `~/.pi/agent/prompts`)               | `/skill`                       |

```bash
# from the repository root
mkdir -p ~/.claude/commands \
         ~/.codex/prompts \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/commands" \
         "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/prompts"
for s in commands/*.md; do
  name=$(basename "$s")
  cp "$s" ~/.claude/commands/"$name"
  cp "$s" ~/.codex/prompts/"$name"
  cp "$s" "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/commands/$name"
  cp "$s" "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/prompts/$name"
done
```

A symlink to the repository file works too and keeps the command in step with the skill, if your harness follows symlinked command files. Reload after copying: OpenCode on save, Pi with `/reload`, Claude Code and Codex at the next session.

Every skill with a `SKILL.md` has a command. `zettel-eval` has none, because it is a standalone Python project rather than a skill.

Two routes that look like they replace this, and do not. A Claude plugin command is namespaced as `/plugin-name:skill`, and a Codex plugin bundles skills rather than prompts, so neither gives a plain `/skill`. The `npx skills` installer places `SKILL.md` files only, never commands. Codex also marks `~/.codex/prompts` deprecated in favour of skills, which it calls with `$skill` or `/skills`.
