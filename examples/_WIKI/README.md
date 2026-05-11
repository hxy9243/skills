# Wiki CLI Example Workspace

This directory is a generated wiki root for the example notebook in `examples/`.

The packet fixtures mirror `wikicli.packet.parse_packet`:

- required strings: `title`, `summary`, `category`, `source`
- optional string lists: `tags`, `search_terms`
- rejected shape example: `packets/invalid-list.json`

Run commands from the repository root:

```bash
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
uv run --project wiki wiki --config examples/_WIKI/config.json add --packet "$(python -m json.tool --compact examples/_WIKI/packets/invalid-list.json)"
```

There is no separate `render` subcommand. `add`, `index`, and `reconcile` rebuild `index.md` and `categories/`.
