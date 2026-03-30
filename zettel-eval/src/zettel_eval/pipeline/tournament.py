from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import datetime
from pathlib import Path

from zettel_eval.pipeline.optimize import discover_retrieval_metrics, load_phase2_examples

csv.field_size_limit(sys.maxsize)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def build_tournament_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--retrieval-metrics", type=Path, default=None, help="Optional Phase 2 retrieval_metrics.csv path.")
    parser.add_argument("--processed-root", type=Path, default=PROJECT_ROOT / "datasets/processed")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "output")
    parser.add_argument("--task-model", default="openai/gpt-5.1-codex-mini")
    parser.add_argument("--judge-model", default="openai/gpt-5.4")
    parser.add_argument("--max-examples", type=int, default=100, help="Maximum Phase 2 examples to load before sampling.")
    parser.add_argument("--matches", type=int, default=10, help="Number of tournament matches.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--optimized-run-dir",
        type=Path,
        default=None,
        help="Explicit pairwise run directory containing best_synthesis_prompt.txt.",
    )
    return parser


def update_elo(rating_a: float, rating_b: float, score_a: float, k: int = 32) -> tuple[float, float]:
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))
    new_rating_a = rating_a + k * (score_a - expected_a)
    new_rating_b = rating_b + k * ((1.0 - score_a) - expected_b)
    return new_rating_a, new_rating_b


def _discover_pairwise_run(output_root: Path) -> Path:
    pairwise_runs = sorted(path for path in (output_root / "runs").glob("pairwise_*") if path.is_dir())
    if pairwise_runs:
        return pairwise_runs[-1]
    msg = "Could not locate a pairwise optimizer run under output/runs."
    raise FileNotFoundError(msg)


def run_tournament_from_args(args: argparse.Namespace) -> Path:
    import dspy

    from zettel_eval.pipeline.dspy_program import BrainstormPipeline, SynthesizeBrainstorm, format_retrieved_notes
    from zettel_eval.pipeline.elo_judge import PairwiseEloJudge

    random.seed(args.seed)

    print("Setting up DSPy LMs...", flush=True)
    task_lm = dspy.LM(model=args.task_model, temperature=1.0, max_tokens=16000, cache=False)
    judge_lm = dspy.LM(model=args.judge_model, temperature=1.0, max_tokens=16000, cache=False)
    dspy.configure(lm=task_lm)

    baseline = BrainstormPipeline()
    optimized = BrainstormPipeline()

    opt_run_dir = args.optimized_run_dir or _discover_pairwise_run(args.output_root)
    synth_prompt = (opt_run_dir / "best_synthesis_prompt.txt").read_text(encoding="utf-8")

    class OptSynth(SynthesizeBrainstorm):
        __doc__ = synth_prompt

    optimized.synthesize = dspy.Predict(OptSynth)

    print(f"Loading {args.matches} random seed notes from the benchmark corpus...", flush=True)
    metrics_path = args.retrieval_metrics or discover_retrieval_metrics(args.output_root)
    examples = load_phase2_examples(
        metrics_path=metrics_path,
        processed_root=args.processed_root,
        max_examples=args.max_examples,
    )
    if not examples:
        msg = "No Phase 2 examples available for the tournament."
        raise ValueError(msg)

    sample = random.sample(examples, min(args.matches, len(examples)))
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    tournament_dir = args.output_root / "runs" / f"tournament_{run_id}"
    tournament_dir.mkdir(parents=True, exist_ok=True)
    judge_log = tournament_dir / "tournament.csv"
    judge = PairwiseEloJudge(judge_lm=judge_lm, log_file=judge_log)

    print(f"Running Elo tournament. Logging to {judge_log}\n", flush=True)
    elo_baseline = 1200.0
    elo_optimized = 1200.0

    for index, example in enumerate(sample, start=1):
        print(f"Match {index}/{len(sample)}: Seed '{example.source_note_id}'", flush=True)
        formatted_notes = format_retrieved_notes(example.retrieved_notes)

        res_base = baseline(seed_note=example.seed_note, retrieved_notes=formatted_notes)
        res_opt = optimized(seed_note=example.seed_note, retrieved_notes=formatted_notes)

        is_optimized_a = random.choice([True, False])
        if is_optimized_a:
            winner, rationale = judge.compare(
                seed_note=example.seed_note,
                retrieved_notes=formatted_notes,
                essay_a=res_opt.brainstorm_essay,
                essay_b=res_base.brainstorm_essay,
            )
            score_opt = 1.0 if winner == "A" else (0.5 if winner == "TIE" else 0.0)
        else:
            winner, rationale = judge.compare(
                seed_note=example.seed_note,
                retrieved_notes=formatted_notes,
                essay_a=res_base.brainstorm_essay,
                essay_b=res_opt.brainstorm_essay,
            )
            score_opt = 1.0 if winner == "B" else (0.5 if winner == "TIE" else 0.0)

        elo_optimized, elo_baseline = update_elo(elo_optimized, elo_baseline, score_opt)
        winner_str = "Optimized" if score_opt == 1.0 else ("Baseline" if score_opt == 0.0 else "Tie")
        print(f"  Winner: {winner_str}", flush=True)
        print(f"  Rationale: {rationale}", flush=True)
        print(
            f"  Current Elo - Optimized: {int(elo_optimized)} | Baseline: {int(elo_baseline)}\n",
            flush=True,
        )

    print("--- Final Tournament Results ---", flush=True)
    print(f"Optimized Pipeline Final Elo: {int(elo_optimized)}", flush=True)
    print(f"Baseline Pipeline Final Elo:  {int(elo_baseline)}", flush=True)
    return tournament_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a baseline-vs-optimized tournament.",
        parents=[build_tournament_parser()],
    )
    args = parser.parse_args()
    run_tournament_from_args(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
