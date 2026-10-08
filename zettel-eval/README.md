# Zettel Eval

Dataset ingestion and retrieval evaluation scaffolding for note-heavy public corpora.

## Commands

Use `uv run` or the installed `zettel-eval` entrypoint.

```bash
zettel-eval ingest
zettel-eval validate
zettel-eval benchmark
zettel-eval pipeline
```

## Layout

- `datasets/raw/<dataset_slug>/notes/` stores normalized Markdown notes from Phase 0.
- `datasets/raw/<dataset_slug>/metadata.json` stores crawl provenance and link graph metadata.
- `datasets/processed/<dataset_slug>/` stores validated corpora, ground truth, and inspection reports from Phase 1.
- `output/` stores benchmark logs, summaries, and evaluation artifacts.

## Embedding cache

Dense retrieval caches embeddings in `output/.cache/` relative to this package,
regardless of the current working directory. Set `ZETTEL_EVAL_CACHE_DIR` to use
a different writable directory (for example, when the package is installed in a
read-only location). `~` is expanded; relative overrides use the current working
directory.

Run the cache path regression tests without calling an embedding service:

```bash
PYTHONPATH=src python -m unittest discover tests/
```
