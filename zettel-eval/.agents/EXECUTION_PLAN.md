# Zettel Eval: Execution Plan

## Instructions for the LLM Agent
- **Do not rewrite core evaluation logic** if the scripts from the Implementation Plan already exist. Use them to drive the experimental workflow end-to-end.
- Ensure all execution logs are piped to plaintext (`.log`) or CSV (`.csv`) in the `output/runs/` timestamped directory.

---

### Step 1: Bootstrap & Ingest
- Initialize the `uv` environment.
- Run the data extraction script over the target Obsidian vault to generate `corpus.csv` and `ground_truth.csv` (excluding menu notes with >10 internal links).

### Step 2: Benchmark Retrieval Engines
- Execute the evaluation harness against Baseline, Hybrid, and ColBERT architectures.
- Ensure IR metrics (`MAP`, `HitRate@5`, `HitRate@10`, `MRR`) are calculated at the per-note target level.
- Save metrics to `retrieval_metrics.csv` and generate `summary.md`.

### Step 3: End-to-End Pairwise LLM Optimization (GEPA)
- Run the Pairwise Hill-Climbing optimization loop (`run_pairwise_opt.py`) to create the ideal prompt for drafting the final brainstorm synthesis end-to-end.
- **Dataset:** Use the top 10 retrieval results from Step 2.
- **Evaluation Rubric (LLM-as-a-Judge):** Grade the final synthesis blinded (Essay A vs B) on:
  1. **Innovation & Insight:** Does it generate a novel, surprising connection?
  2. **Groundedness (No Hallucination):** Are all claims backed by the source notes?
  3. **Logical Coherence (No Coerced Logic):** Do the connections make sense, or are they forced/strained?
- **Credit Assignment Rule:** Lock the Filter Prompt and mutate the Synthesis Prompt (or vice versa). DO NOT mutate both simultaneously.
- Iterate and log prompt mutations.
- Export the final, optimized plain-text instructions that openclaw subagents can execute natively.

### Step 4: Summarize & Visualize
- Run the `run_tournament.py` script to pit the final Optimized Prompt against the initial Baseline Prompt in a 10-match Elo-rated tournament.
- Generate a comprehensive Markdown summary report and output visualizations (e.g., using `matplotlib` or `seaborn` saved as PNGs) tracking the Elo trajectory (`plot_elo.py`).

### Step 5: Apply to Zettel-Brainstormer (Update the Skill)
- Once the optimized prompts have stabilized and the evaluation is complete, the final step is to **update the actual skill**.
- Copy the contents of `output/runs/latest/best_filter_prompt.txt` and `best_synthesis_prompt.txt`.
- Apply these optimized prompts to the source code of the target agent (e.g., `~/.openclaw/skills/zettel-brainstormer/SKILL.md` or its associated prompt files).
- Commit the optimized skill back to the repository with a message detailing the performance uplift.
