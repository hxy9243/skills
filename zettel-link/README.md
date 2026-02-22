# zettel-link

A suite of Python scripts for semantically searching and linking notes in an Obsidian directory based on embedding similarity.

## Scripts

```
scripts/
├── config.py # Configure the embedding model and other settings.
├── embed.py  # Embed notes via Ollama (e.g. mxbai-embed-large), cached
├── search.py # Search notes via Ollama (e.g. mxbai-embed-large), cached
└── link.py   # Cosine similarity ranking → links.json
```

## Quick Start

Install it via npx skills command:

```bash
npx skills install https://github.com/hxy9243/skills/blob/main/zettel-link/
```

## Requirements

- uv 0.10.0+
- Python 3.10+
- Optional: [Ollama](https://ollama.com) with `mxbai-embed-large` (for local embedding only)

## Idempotency

All scripts are safe to re-run:
- `embed.py` uses content-hash caching,only re-embeds changed notes
