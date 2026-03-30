# Zettel Eval: Implementation Plan

## Environment & Tooling
- **Language:** Python
- **Package Manager:** `uv`
- **Telemetry Format:** All logging must use plaintext files (`.log`) and CSVs (`.csv`).
- **Output Directory:** All generated scripts, optimized prompts, and experiment results must be saved to a dedicated `output/` directory.

## Overall Architecture
- The system is organized as a staged offline evaluation pipeline:
  - Phase 0: Ingests live websites into normalized local Markdown datasets.
  - Phase 1: Validates dataset quality and emits retrieval-ready corpora plus ground truth.
  - Phase 2: Runs retrieval benchmarks and hyperparameter search over the accepted datasets.
  - Phase 3: End-to-End Pairwise Elo Optimization (GEPA-style). Replaces standard scalar DSPy optimizers to enable A/B pairwise LLM-as-a-Judge evaluations.
- Configuration lives in checked-in files, while per-run outputs live under `output/` and `datasets/`.

## Physical Source Layout
Use a source tree like this:

```text
src/zettel_eval/
  cli.py
  config.py
  logging.py
  datasets/
  ingest/
  validate/
  retrieval/
  pipeline/
    dspy_program.py
    elo_judge.py
  reports/

configs/
  datasets.yaml
  retrieval.yaml

output/
  retrieval_metrics.csv
  runs/
    <run_id>/
```

---

### Phase 0 & 1: Ingestion, Validation & Ground Truth
**Goal:** Convert public note websites into a clean, self-labeled dataset. Exclude notes with >10 internal links (hub/menu notes) to prevent suppressing @K metrics. Strip internal link markup to create `corpus.csv` and `ground_truth.csv` (mapping Source Note ID -> Target Note IDs as a set).

### Phase 2: Retrieval Evaluation (Benchmarking IR)
**Goal:** Measure note-level retrieval quality (BM25, Dense, Hybrid, ColBERT) on hidden-link reconstruction using `MAP`, `HitRate@5`, `HitRate@10`, and `MRR`. 
**Method:** Treat target links as a set per note, not independent queries. Use `nomic-embed-text` and `text-embedding-3-small` with local LRU caching to minimize API costs.

### Phase 3: End-to-End Pairwise LLM Optimization (GEPA)
**Goal:** Optimize the prompt used by the subagent to summarize/filter notes, and the prompt used to synthesize the final brainstorm. 
**Method (Pairwise Hill-Climbing):**
Standard DSPy optimizers rely on noisy absolute 1-100 grading. We bypass this by building a custom Pairwise Elo Optimizer:
1. **The Credit Assignment Strategy:** Lock the Filter Prompt and mutate the Synthesis Prompt (or vice versa). If you mutate both simultaneously, the judge cannot determine which mutation caused the win/loss.
2. **The Proposal:** A Pro LLM (e.g., `gpt-5.4`) reviews the current "Champion" prompt and previous match feedback, and proposes a new "Challenger" prompt.
3. **The Arena:** Generate final essays using both the Champion and Challenger pipelines on 5-10 random seed notes.
4. **The Pairwise Judge:** The Judge LLM reads Essay A and Essay B side-by-side (blinded) and outputs `winner: A|B|TIE` with a 1-sentence justification, based on:
   - **Innovation & Insight:** Novel, surprising connections.
   - **Groundedness:** No hallucinations; explicit evidence citations.
   - **Logical Coherence:** Natural flow, no coerced logic.
5. **The Hill Climb:** If the Challenger wins the majority of matches, it dethrones the Champion and the baseline updates.
6. **Artifact Output:** Export the final, optimized prompt instructions into `output/runs/<run_id>/best_filter_prompt.txt` and `best_synthesis_prompt.txt`.
