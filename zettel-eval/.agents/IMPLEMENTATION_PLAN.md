# Zettel Eval: Implementation Plan

## Environment & Tooling
- **Language:** Python
- **Package Manager:** `uv`
- **Telemetry Format:** All logging must use plaintext files (`.log`) and CSVs (`.csv`). Avoid opaque databases (no SQLite) to ensure easy manual inspection.
- **Output Directory:** All generated scripts, optimized prompts, and experiment results must be saved to a dedicated `output/` directory within the skill folder.

---

### Phase 1: Dataset & Ground Truth (The "Hide-the-Link" Trick)
**Goal:** Create a clean, self-labeled dataset for testing retrieval algorithms without manual annotation.
**Method:**
1. Download a dense, public Obsidian vault (e.g., Andy Matuschak's working notes).
2. Parse Markdown files. Extract all outgoing wikilinks (`[[Link|Alias]]`).
3. Strip wikilink brackets from the body text (keep alias if present).
4. Save the stripped text into `corpus.csv` and a `ground_truth.csv` (mapping Source Note ID -> Target Note ID).

### Phase 2: Retrieval Evaluation (Benchmarking IR)
**Goal:** Measure search engine ability to find hidden links (Recall@K).
**Method:**
1. Feed stripped notes into Baseline (Dense `text-embedding-3-small`), Hybrid (Dense + BM25 via RRF), and Heavyweight (ColBERT).
2. Calculate `Recall@10` and `MRR`.
**Telemetry:** Log every query, retrieved IDs, and scores to `retrieval_metrics.csv`.

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