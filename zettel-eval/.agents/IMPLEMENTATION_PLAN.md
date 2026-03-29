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
  - Phase 3: End-to-end DSPy optimization of the LLM reasoning pipeline (Filtering + Synthesis) based on the final brainstorm quality.
- Configuration lives in checked-in files, while per-run outputs live under `output/` and `datasets/`.

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
  pipeline/
    dspy_program.py
    judge.py
  reports/
    retrieval_report.py

configs/
  datasets.yaml
  retrieval.yaml

output/
  runs/
    <run_id>/
```

---

### Phase 0 & 1: Ingestion, Validation & Ground Truth
**Goal:** Convert public note websites into a clean, self-labeled dataset (excluding notes with >10 internal links). Strip internal link markup to create `corpus.csv` and `ground_truth.csv`.

### Phase 2: Retrieval Evaluation (Benchmarking IR)
**Goal:** Measure note-level retrieval quality (BM25, Dense, Hybrid, ColBERT) on hidden-link reconstruction using `MAP`, `HitRate@5`, `HitRate@10`, and `MRR`.

### Phase 3: End-to-End LLM Pipeline Optimization (DSPy)
**Goal:** Instead of isolating the relevance filter and the final synthesis, we optimize the entire reasoning chain end-to-end. The ultimate goal is a high-quality brainstorm, so the optimization should be driven by evaluating the *final output*.

**Method:**
1. **The DSPy Program:** Create a `BrainstormPipeline` module in DSPy that takes a `Seed Note` and `Retrieved Notes` (from Phase 2's best retriever) and runs:
   - *Step A (Filter/Process):* Summarize each retrieved note and decide if/how it connects to the seed.
   - *Step B (Synthesize):* Draft the final brainstorm essay using the filtered notes.
2. **The Evaluator (LLM-as-a-Judge):** A strong model (e.g., GPT-4o / Gemini 1.5 Pro) grades the *final synthesized brainstorm* against a strict rubric (0-5 scale per dimension, or binary pass/fail):
   - **Innovation & Insight:** Does the synthesis generate a novel, surprising connection or insight, or is it just a bland summary?
   - **Groundedness (No Hallucination):** Are all factual claims and ideas backed by the provided source notes?
   - **Logical Coherence (No Coerced Logic):** Do the connections flow naturally, or did the model force a strained, illogical link between unrelated notes?
3. **The Optimization:** Use DSPy's optimizers (e.g., `MIPRO` or `BootstrapFewShotWithRandomSearch`) to jointly optimize the prompts for Step A and Step B. The optimizer will mutate the instructions and few-shot examples to maximize the Judge's score on the final output over a training set of seed notes.
4. **Artifact Output:** Export the final, optimized prompt instructions for the Filter and Synthesis steps into `output/best_filter_prompt.txt` and `output/best_synthesis_prompt.txt`.
