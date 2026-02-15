# Zettel Brainstormer

An AI-powered skill for expanding **Zettelkasten** notes into comprehensive writing drafts.

## Overview

This skill provides a **3-stage pipeline** to transform your atomic notes into a coherent draft:
1.  **Find Links**: Scans a seed note, extracts wikilinks, finds similar notes via tags, and generates a list of file paths.
2.  **Preprocess**: Reads the files and context to generate a high-quality Markdown outline using subagent.
3.  **Draft**: Reads the outline and context to generate a high-quality Markdown draft using a Pro LLM.

## Documentation

**👉 See [SKILL.md](SKILL.md) for full installation, configuration, and usage instructions.**

## Quick Start

### Prerequisites
-   Python 3.10+
-   Your favorite AI Agent system (OpenCode, Cursor, OpenClaw, etc.)
-   Optionally, `OPENAI_API_KEY` (or OpenRouter key) set in environment.

### Installation
```bash
# Clone repository
npx skills install https://github.com/hxy9243/skills/blob/main/zettel-brainstormer/
```

### Usage

1. Prompt your AI Agent to configure the skill.
2. Prompt your AI Agent to run the skill.


## License
MIT
