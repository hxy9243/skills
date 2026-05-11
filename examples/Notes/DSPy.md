---
category: "Computer Science > AI Systems > Agents"
---
# DSPy

DSPy treats prompts and model calls as optimizable programs. The note is useful for examples about agent pipelines, prompt optimization, and deterministic wiki packet ingestion.


uv run --project wiki wiki --config examples/_WIKI/config.json status
uv run --project wiki wiki --config examples/_WIKI/config.json tree
uv run --project wiki wiki --config examples/_WIKI/config.json add --packet "$(python -m json.tool --compact examples/_WIKI/packets/dspy.json)"
uv run --project wiki wiki --config examples/_WIKI/config.json add --packet "$(python -m json.tool --compact examples/_WIKI/packets/memory-state.json)"
uv run --project wiki wiki --config examples/_WIKI/config.json index
uv run --project wiki wiki --config examples/_WIKI/config.json reconcile
uv run --project wiki wiki --config examples/_WIKI/config.json search "prompt optimization agents" --limit 3
uv run --project wiki wiki --config examples/_WIKI/config.json show Notes/DSPy.md
uv run --project wiki wiki --config examples/_WIKI/config.json synthesize --tag '#agents' --limit 5
uv run --project wiki wiki --config examples/_WIKI/config.json lint
