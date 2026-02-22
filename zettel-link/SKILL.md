---
name: zettel-link
description: This skill maintains the Note Embeddings for Zettelkasten, to search notes, retrieve notes, and discover connections between notes.
---

# Zettel Link Skill

This skill provides a suite of idempotent Python scripts to audit and improve an Obsidian vault. All scripts live in `scripts/` and are designed to be installed in the agent's skill directory.

## Dependencies

- uv 0.10.0+
- Python 3.10+
- Optional: [Ollama](https://ollama.com) with `mxbai-embed-large` (for local embedding  only)

## Overview of Commands

- `uv run scripts/config.py`: Configure the embedding model and other settings.
- `uv run scripts/embed.py`: Embed notes via Ollama, cache to `.embeddings/`
- `uv run scripts/link.py`: Find conceptually related notes regardless of shared vocabulary, using local vector embeddings.
- `uv run scripts/search.py`: Search notes via Ollama, cache to `.embeddings/`

## Workflow

### Step 0 - Setup and Config

If the `config/config.json` file does not exist, create it with the following command:

```bash
uv run scripts/config.py
```

It will create a `config/config.json` file, for example:

```json
{
    "model": "mxbai-embed-large",
    "provider": {
        "name": "ollama",
        "host": "http://localhost:11434"
    },
    "max_length": 8192,
    "cache_dir": ".embeddings",
    "default_threshold": 0.65,
    "top_k": 5
}
```

### Step 1 - Create Embeddings

```bash
uv run scripts/embed.py --config config/config.json --input <directory>
```

It will create a `<directory>/.embeddings/embeddings.json` file with the embedding cache.

### Step 2 - Semantic Search

```bash
uv run scripts/search.py --config config/config.json --input <directory> --query "<query>"
```

It will embed the query and compare it with the cached embeddings of all notes. It will return the top-k most similar notes.

### Step 3 - Semantic Connection Discovery

Find conceptually related notes regardless of shared vocabulary, using local vector embeddings.

```bash
uv run scripts/link.py --config config/config.json --input <directory>
```

It will create a `<directory>/.embeddings/links.json` file with the link cache.

**How it works:**
- Each note is converted to a vector via the given embedding model.
- Cosine similarity is computed for all pairs.

**Tuning:**

**Cache location:** `<directory>/.embeddings/embeddings.pkl` — delete to force full re-embed.

## Agent Instructions
