# Zettel Eval: Evaluation Execution Plan

## Instructions for the LLM Agent
- Reuse the implementation from the implementation plan. Do not rewrite working Phase 0-2 logic unless execution shows a concrete defect.
- Save all execution logs and result tables as plaintext (`.log`) or CSV (`.csv`) under `output/`.
- Treat dataset quality and leakage diagnostics as part of the evaluation, not optional cleanup.

---

### Step 1: Bootstrap
- Initialize the `uv` environment and install the project dependencies.
- Verify all required API keys, model endpoints, and external tools are available before starting long-running jobs.

### Step 2: Ingest Public Note Websites
- Run the Phase 0 ingestion pipeline against the fixed website manifest from the implementation plan.
- Crawl the target websites, extract Markdown with Defuddle, classify internal versus external links, canonicalize note IDs, and emit normalized notes under `datasets/raw/<dataset_slug>/notes/`.
- Save dataset metadata to `datasets/raw/<dataset_slug>/metadata.json`.

### Step 3: Validate Datasets And Build Ground Truth
- Run the Phase 1 validation pipeline on each ingested dataset.
- Reject datasets that fail the minimum note-count or link-density thresholds.
- For accepted datasets, generate `corpus.csv` and `ground_truth.csv`.
- Record the dataset statistics, degree distribution, and manual inspection outcome in evaluation logs.

### Step 4: Run Retrieval Benchmarks
- Run Phase 2 note-level retrieval evaluation where each hidden outgoing internal link is one example.
- Benchmark BM25, dense embedding retrieval, ColBERT, and hybrid retrieval.
- Search over the predefined hyperparameter space on the dev dataset only, then evaluate the selected configurations on the held-out test dataset or leave-one-dataset-out folds.
- Log `Recall@5`, `Recall@10`, and `MRR` for every method and dataset.

### Step 5: Run Leakage Diagnostics
- Execute both retrieval conditions:
  - anchor-preserved
  - anchor-masked
- Compare performance across the two conditions and flag cases where lexical cues appear to dominate retrieval quality.
- If per-dataset discrepancy is large, stop and inspect the dataset characteristics before continuing to downstream evaluation.

### Step 6: Summarize Retrieval Results
- Generate a Markdown report at `output/EVALUATION_SUMMARY.md`.
- Include:
  - accepted versus rejected datasets and reasons
  - per-dataset retrieval metrics
  - macro averages
  - selected hyperparameters
  - leakage diagnostic results
  - notes on any large cross-dataset discrepancies

### Step 7: Gate Downstream Work
- Only proceed to Phase 3 and Phase 4 prompt optimization after retrieval evaluation is stable and the dataset quality looks credible.
- If the retrieval benchmark is too noisy or too weak, stop and revise the data or retrieval setup before running judge-based prompt optimization.
