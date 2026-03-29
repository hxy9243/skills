# Zettel Eval: Implementation Plan

## Environment & Tooling
- **Language:** Python
- **Package Manager:** `uv`
- **Telemetry Format:** All logging must use plaintext files (`.log`) and CSVs (`.csv`). Avoid opaque databases (no SQLite) to ensure easy manual inspection.
- **Output Directory:** All generated scripts, optimized prompts, and experiment results must be saved to a dedicated `output/` directory within the skill folder.

## Overall Architecture
- The system should be organized as a staged offline evaluation pipeline:
  - Phase 0 ingests live websites into normalized local Markdown datasets.
  - Phase 1 validates dataset quality and emits retrieval-ready corpora plus ground truth.
  - Phase 2 runs retrieval benchmarks and hyperparameter search over the accepted datasets.
  - Later phases consume the accepted retrieval outputs rather than reimplementing earlier steps.
- Each phase should be executable independently from the command line, but should also compose into one end-to-end pipeline.
- Each phase should read explicit input artifacts from disk and write explicit output artifacts to disk so runs are reproducible and restartable.
- Configuration should live in checked-in files, while per-run outputs should live under `output/` and `datasets/`.

## Physical Source Layout
Use a source tree like this:

```text
src/zettel_eval/
  cli.py
  config.py
  logging.py
  datasets/
    manifest.py
    models.py
  ingest/
    crawl.py
    defuddle.py
    links.py
    canonicalize.py
    writer.py
  validate/
    stats.py
    inspect.py
    ground_truth.py
  retrieval/
    bm25.py
    dense.py
    colbert.py
    hybrid.py
    metrics.py
    search.py
  reports/
    retrieval_report.py

configs/
  datasets.yaml
  retrieval.yaml

datasets/
  raw/
    <dataset_slug>/
      notes/
      metadata.json
  processed/
    <dataset_slug>/
      corpus.csv
      ground_truth.csv
      dataset_stats.json

output/
  retrieval_metrics.csv
  runs/
    <run_id>/
      config.json
      run.log
      summary.md
```

### Module Responsibilities
- `cli.py`: top-level entrypoints for each phase and end-to-end execution.
- `config.py`: load and validate dataset and retrieval configuration.
- `datasets/models.py`: typed models for notes, links, examples, and dataset metadata.
- `ingest/*`: crawl websites, extract Markdown, classify links, canonicalize note IDs, and write normalized datasets.
- `validate/*`: compute dataset statistics, run acceptance checks, and generate `corpus.csv` plus `ground_truth.csv`.
- `retrieval/*`: build indexes, run retrieval methods, tune hyperparameters, and compute retrieval metrics.
- `reports/*`: write Markdown summaries and machine-readable run artifacts.

---

### Phase 0: Website Ingestion & Canonicalization
**Goal:** Convert public note websites into a local, normalized Markdown dataset while preserving the internal link graph.
**Method:**
1. Start from a fixed manifest of live public note websites. Initial candidates:
   - Andy Matuschak's About these notes: `https://notes.andymatuschak.org/About_these_notes`
   - Steph Ango: `https://stephango.com/`
   - SuperMemo Guru: `https://supermemo.guru/wiki/SuperMemo_Guru`
   - Jethro's Braindump: `https://braindump.jethro.dev`
   - Mental Nodes: `https://www.mentalnodes.com/`
2. Crawl same-origin note pages from each seed URL and save the raw page URL manifest locally.
3. Use Defuddle to extract Markdown from each page:
   - `defuddle parse <url> --md`
4. Distinguish internal links from external links:
   - Internal links point to another page in the same dataset/site.
   - External links point outside the dataset and should not become note-level ground-truth targets.
5. Canonicalize internal links into a stable local note-ID format and rewrite them into normalized local Markdown links.
6. Save one local Markdown file per canonical note in a dataset directory, plus metadata needed to reconstruct provenance and the link graph.
7. Emit dataset-level metadata:
   - source site URL
   - crawl date
   - page URL to local note ID mapping
   - internal link graph
   - external link list
**Artifact Output:** Save normalized notes under `datasets/raw/<dataset_slug>/notes/` and metadata under `datasets/raw/<dataset_slug>/metadata.json`.

### Phase 1: Dataset Validation & Ground Truth (The "Hide-the-Link" Trick)
**Goal:** Accept only datasets with enough scale and link density, then create self-labeled ground truth for retrieval evaluation.
**Method:**
1. Evaluate each ingested dataset against minimum acceptance criteria:
   - At least 100 notes.
   - More than 50% of notes have at least one incoming or outgoing internal link.
   - The total number of unique bidirectional internal note-note links is at least 2x the total number of notes.
   - Link connectivity should not be overly concentrated in a tiny number of hub pages; report the degree distribution and flag datasets where the top 10% of notes account for more than 50% of total internal-link degree.
2. Perform manual corpus inspection before accepting a dataset:
   - Sample at least 50 extracted links per corpus.
   - Check whether links usually resolve to real notes.
   - Check whether links are mostly semantic/contentful rather than navigational boilerplate.
   - Discard the corpus if link quality is too poor for meaningful note-retrieval evaluation.
3. For accepted datasets, parse the local normalized Markdown files and extract all outgoing internal links.
4. Strip internal link markup from the body text while preserving the anchor text or alias when present.
5. Save the stripped text into `corpus.csv` and a `ground_truth.csv` (mapping Source Note ID -> Target Note ID).
**Implementation**
This step should be deterministic and you should be able to implement all the steps in Python.

Save the output into `datasets/` as versioned ground-truth artifacts.

### Phase 2: Retrieval Evaluation (Benchmarking IR)
**Goal:** Measure note-level retrieval quality on hidden-link reconstruction.
**Method:**
1. Evaluate note-level retrieval only. Each hidden outgoing internal link is one evaluation example. If a source note has 5 distinct outgoing internal links, it contributes 5 examples.
2. Benchmark multiple retrieval families:
   - BM25 lexical baseline
   - Dense embedding retrieval (for example `text-embedding-3-small`)
   - ColBERT-based retrieval
   - Hybrid retrieval (dense + lexical/BM25 fusion, e.g. RRF)
3. Retrieval searches over all notes in the same dataset except the source note itself.
4. Use dataset-level splits, not within-dataset random splits, to avoid leakage across heavily interlinked notes:
   - If 4 or more datasets pass validation, reserve 1 dataset for dev, 1 for test, and use the remaining datasets for training or method development as needed.
   - If only 3 datasets pass validation, use leave-one-dataset-out evaluation and report the average and variance across folds.
   - Never tune on the final test dataset.
5. Tune retrieval hyperparameters to optimize retrieval score on the dev split. This phase is not just a fixed benchmark; part of the evaluation is to measure how retrieval strategies and parameter choices change performance.
6. At minimum, tune:
   - whole-note versus chunked-note indexing
   - chunk size and overlap when chunking is enabled
   - top-K retrieval depth
   - BM25 parameters
   - hybrid fusion weights or RRF parameters
   - ColBERT indexing/search parameters
7. Define a fixed search budget per retrieval family and save the chosen hyperparameters in the experiment artifacts.
8. Calculate `Recall@5`, `Recall@10`, and `MRR`.
9. Report per-dataset scores and macro averages. If the score discrepancy across datasets is large, stop and inspect the dataset characteristics before proceeding to downstream phases.
10. Run two retrieval conditions to measure lexical leakage:
   - Anchor-preserved: remove link markup but keep alias/anchor text.
   - Anchor-masked: remove both link markup and alias/anchor text, replacing it with minimal neutral text.
11. Compare retrieval performance across the two conditions to estimate how much the benchmark depends on lexical cues rather than conceptual retrieval.
**Telemetry:** Log every example, retrieval condition, retrieved IDs, scores, and chosen hyperparameters to `retrieval_metrics.csv`.

### Phase 3: Filter Evaluation (LLM-as-a-Judge & DSPy)
**Goal:** Optimize the extraction layer (why a retrieved note is relevant to the seed).
**Method:**
1. LLM-as-a-Judge (Gemini 1.5 Pro/GPT-4o) evaluates Filter output.
2. **Rubric (Binary 0/1):** Grounding (No hallucinations) and Relevance.
3. **Optimization Constraints (DSPy):**
   - **Max Iterations:** 30 prompt variants.
   - **Early Stopping:** Stop if the Judge's pass rate hits >95% or if there is no improvement over 5 consecutive rounds.
**Telemetry:** Record prompt mutations to `filter_prompts.log`. Log pass/fail rates to `filter_eval.csv`.
**Artifact Output:** Save the winning prompt to `output/best_filter_prompt.txt`.

### Phase 4: Synthesis Evaluation (Pairwise Elo Rating)
**Goal:** Test strength, coherence, and novelty of the final synthesized argument.
**Method:**
1. Generate final output using Prompt A and Prompt B. Feed both to the Judge.
2. **Rubric:** Novelty, Citation Density, Coherence. Output: A, B, or TIE.
3. **Optimization Constraints (GEPA):**
   - **Max Matches:** 50 pairwise comparisons.
   - **Early Stopping:** Stop when the Elo rating of the top prompt stabilizes (change < 10 points over 5 matches).
**Telemetry:** Log all pairwise matchups and justifications to `elo_matches.log`. Log the Elo trajectory to `elo_ratings.csv`.
**Artifact Output:** Save the winning prompt to `output/best_synthesis_prompt.txt`.
