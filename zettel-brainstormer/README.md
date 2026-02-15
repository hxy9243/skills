# Zettel Brainstormer

An AI-powered skill for expanding **Zettelkasten** notes into comprehensive writing drafts.

## Overview

This skill provides a **two-stage pipeline** to transform your atomic notes into a coherent draft:
1.  **Preprocess**: Scans a seed note, extracts wikilinks, finds similar notes via tags, filters for relevance using an LLM, and generates a structured outline.
2.  **Draft**: Consumes the outline and context to generate a high-quality Markdown draft using a Pro LLM (e.g., GPT-4o, Claude 3.5 Sonnet).

## Documentation

**👉 See [SKILL.md](SKILL.md) for full installation, configuration, and usage instructions.**

## Quick Start

### Prerequisites
-   Python 3.10+
-   `OPENAI_API_KEY` (or OpenRouter key) set in environment.

### Installation
```bash
# Clone repository
git clone https://github.com/hxy9243/skills.git
cd skills/zettel-brainstormer
```

### Usage
```bash
# 1. Generate Outline (and filter context)
python3 scripts/preprocess.py \
  --input "path/to/my-seed-note.md" \
  --output "outline.json" \
  --zettel-dir "path/to/my-vault" \
  --filter --threshold 5

# 2. Generate Draft
python3 scripts/draft.py \
  --outline "outline.json" \
  --out "draft.md"
```

## License
MIT
