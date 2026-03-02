# Changelog

## 2026-03-02

- Refactored workflow into 4 explicit stages: Retrieval, Preprocess, Draft, Publish.
- Updated skill instructions to require relevance filtering before draft synthesis.
- Added `scripts/compile_preprocess.py` to build a relevance-filtered draft packet and citation list.
- Updated retrieval guidance to:
  - read note count from config,
  - prioritize `zettel-link` semantic retrieval when available,
  - then use local wikilink/tag retrieval.
- Updated agent prompts in `agents/` to align with the stage boundaries and citation requirements.
- Removed deprecated `scripts/draft_prompt.py` and stale cache artifacts.
- Removed redundant sample file `examples/sample-seed-note.md`.
