from __future__ import annotations

import sys
import os
import csv
from pathlib import Path
import random

import dspy

from zettel_eval.pipeline.dspy_program import BrainstormPipeline, FilterRetrievedNotes, SynthesizeBrainstorm, format_retrieved_notes
from zettel_eval.pipeline.elo_judge import PairwiseEloJudge
from zettel_eval.pipeline.optimize import discover_retrieval_metrics, load_phase2_examples


def update_elo(rating_a, rating_b, score_a, k=32):
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))
    
    new_rating_a = rating_a + k * (score_a - expected_a)
    new_rating_b = rating_b + k * ((1.0 - score_a) - expected_b)
    
    return new_rating_a, new_rating_b


def run_tournament(output_root: Path, processed_root: Path, opt_run_dir: Path, task_model: str, judge_model: str, matches: int):
    print("Setting up DSPy LMs...", flush=True)
    task_lm = dspy.LM(model=task_model, temperature=1.0, max_tokens=16000, cache=False)
    judge_lm = dspy.LM(model=judge_model, temperature=1.0, max_tokens=16000, cache=False)
    dspy.configure(lm=task_lm)

    baseline = BrainstormPipeline()
    optimized = BrainstormPipeline()
    
    # We load the newly optimized synthesis prompt
    synth_prompt = (opt_run_dir / "best_synthesis_prompt.txt").read_text()
    
    class OptSynth(SynthesizeBrainstorm):
        __doc__ = synth_prompt
        
    optimized.synthesize = dspy.Predict(OptSynth)

    print(f"Loading {matches} random seed notes from the benchmark corpus...", flush=True)
    metrics_path = discover_retrieval_metrics(output_root)
    
    examples = load_phase2_examples(metrics_path=metrics_path, processed_root=processed_root, max_examples=100)
    random.seed(42)
    sample = random.sample(examples, min(matches, len(examples)))

    judge_log = output_root / "runs" / "tournament.csv"
    judge = PairwiseEloJudge(judge_lm=judge_lm, log_file=judge_log)
    
    print(f"Running Elo tournament... Logging to {judge_log}\n", flush=True)

    elo_baseline = 1200.0
    elo_optimized = 1200.0

    for i, ex in enumerate(sample, 1):
        print(f"Match {i}/{matches}: Seed '{ex.source_note_id}'", flush=True)
        
        formatted_notes = format_retrieved_notes(ex.retrieved_notes)

        res_base = baseline(seed_note=ex.seed_note, retrieved_notes=formatted_notes)
        res_opt = optimized(seed_note=ex.seed_note, retrieved_notes=formatted_notes)
        
        essay_base = res_base.brainstorm_essay
        essay_opt = res_opt.brainstorm_essay

        is_opt_a = random.choice([True, False])
        
        if is_opt_a:
            winner, rationale = judge.compare(
                seed_note=ex.seed_note, retrieved_notes=formatted_notes,
                essay_a=essay_opt, essay_b=essay_base
            )
            score_opt = 1.0 if winner == "A" else (0.5 if winner == "TIE" else 0.0)
        else:
            winner, rationale = judge.compare(
                seed_note=ex.seed_note, retrieved_notes=formatted_notes,
                essay_a=essay_base, essay_b=essay_opt
            )
            score_opt = 1.0 if winner == "B" else (0.5 if winner == "TIE" else 0.0)

        score_base = 1.0 - score_opt
        elo_optimized, elo_baseline = update_elo(elo_optimized, elo_baseline, score_opt)

        winner_str = "Optimized" if score_opt == 1.0 else ("Baseline" if score_base == 1.0 else "TIE")
        print(f"  🏆 Winner: {winner_str}", flush=True)
        print(f"  🧠 Rationale: {rationale}", flush=True)
        print(f"  📈 Current Elo - Optimized: {int(elo_optimized)} | Baseline: {int(elo_baseline)}\n", flush=True)

    print("--- Final Tournament Results ---", flush=True)
    print(f"Optimized Pipeline Final Elo: {int(elo_optimized)}", flush=True)
    print(f"Baseline Pipeline Final Elo:  {int(elo_baseline)}", flush=True)
    
    return elo_optimized, elo_baseline
