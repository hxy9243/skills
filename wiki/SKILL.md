---
name: wiki
description: Manage an LLM-driven knowledge base (Karpathy pattern). Parses raw notes, infers taxonomy categories, updates index.md, and writes structured concept nodes to _WIKI/nodes/.
metadata:
  openclaw:
    install:
      script: |
        npm install
---

# Wiki Skill 📚

This skill implements the **Wiki Pattern** (conceptualized by Andrej Karpathy) for OpenClaw. It shifts the burden of maintaining a Zettelkasten or knowledge base from the human to the LLM. 

Instead of dumping files and relying on query-time embeddings (RAG), this skill *ingests* raw files, extracts concepts, infers a 3-layer taxonomy (`Category -> Subcategory -> Topic`), and maintains a highly structured, semantic Markdown index (`index.md`) alongside clean concept nodes.

## Features
- **Semantic Ingestion**: Uses an LLM to read a raw source, extract the core concept, and infer its place in your ontology.
- **Auto-Indexing**: Automatically places new concepts into a hierarchical `index.md` file.
- **Bookkeeping**: Automatically logs actions to `log.md` and moves raw files to an archive directory.
- **Linting**: Finds orphan nodes that are missing from the index.

## Configuration

You can use the `config` command to generate a local `~/.wiki.json` settings file:

```bash
node ~/.openclaw/skills/wiki/index.js config --api-key "sk-..."
```


By default, the skill assumes your Obsidian vault is located at `~/Documents/kevinhusnotes`. You can override these paths by setting environment variables in your OpenClaw environment or local `.env` file:

- `WIKI_ROOT`: Path to the compiled wiki directory (Default: `~/Documents/kevinhusnotes/_WIKI`)
- `INBOX_DIR`: Path to raw staging (Default: `~/Documents/kevinhusnotes/00_Inbox`)
- `RAW_ARCHIVE_DIR`: Path to archive raw sources (Default: `~/Documents/kevinhusnotes/30_Resources/Raw`)
- `OPENAI_API_KEY`: Required for the ingestion LLM call.

## Commands

Run the CLI tool via Node:

```bash
# Ingest a raw markdown file into the wiki
node ~/.openclaw/skills/wiki/index.js add ~/Documents/kevinhusnotes/00_Inbox/some_raw_file.md

# Lint the wiki for orphan nodes
node ~/.openclaw/skills/wiki/index.js lint

# Search the semantic index
node ~/.openclaw/skills/wiki/index.js search "Agent"
```

## How it works

1. **Add**: The script passes the raw file text and your current `index.md` to an LLM. The LLM returns a structured JSON object containing the `title`, `description`, `l1`, `l2`, `l3` taxonomy levels, and the synthesized `content`.
2. **Compile**: A new node is created in `_WIKI/nodes/` using a standardized YAML frontmatter format.
3. **Index & Log**: The script parses `index.md`, injects the new link under the correct heading, and writes to `log.md`.
