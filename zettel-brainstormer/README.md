Zettel Brainstormer — public package

This package contains the zettel-brainstormer skill.

Overview
- Two-stage pipeline: preprocess (configurable, e.g. OpenRouter kimi-k2.5) -> draft (pro model, configurable) -> optional humanizer.
- Scripts provided are safe by default: they run in "stub" mode unless environment variables are set to enable real API calls.

Quick start (safe mode)
1. Inspect the sample input: examples/sample-note.md
2. Run preprocess:
   ./scripts/preprocess.py --input examples/sample-note.md --output /tmp/outline.json
3. Run draft:
   ./scripts/draft.py --outline /tmp/outline.json --model openai/gpt-5.2 --out /tmp/draft.md

Enabling real API calls
- To enable OpenRouter/OpenAI calls, set the environment variables OPENROUTER_API_KEY and OPENAI_API_KEY and also set REAL_API=1 in the environment. The scripts will refuse to run with live credentials otherwise.

License
- MIT. See LICENSE file.
