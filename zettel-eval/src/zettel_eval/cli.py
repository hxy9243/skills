from __future__ import annotations

import argparse
from pathlib import Path

from zettel_eval.config import load_dataset_config, load_retrieval_config
from zettel_eval.logging import append_log
from zettel_eval.pipeline.optimize import build_optimizer_parser, run_optimization_from_args
from zettel_eval.retrieval.search import evaluate_processed_datasets


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zettel-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: datasets
    datasets_parser = subparsers.add_parser("datasets", help="Manage and validate Zettelkasten datasets.")
    ds_subparsers = datasets_parser.add_subparsers(dest="subcommand", required=True)
    ds_subparsers.add_parser("ingest", help="Run Phase 0 ingestion over configured datasets.")
    ds_subparsers.add_parser("validate", help="Run Phase 1 dataset validation and ground truth generation.")

    # Subcommand: retrieval
    retrieval_parser = subparsers.add_parser("retrieval", help="Run Retrieval engine benchmarks.")
    rt_subparsers = retrieval_parser.add_subparsers(dest="subcommand", required=True)
    rt_subparsers.add_parser("benchmark", help="Run Phase 2 retrieval benchmarks.")

    # Subcommand: optimizer
    optimizer_parser = subparsers.add_parser("optimizer", help="Optimize LLM reasoning prompts.")
    opt_subparsers = optimizer_parser.add_subparsers(dest="subcommand", required=True)
    
    # 1. dspy (absolute)
    opt_subparsers.add_parser(
        "dspy",
        help="Run Phase 3 absolute DSPy optimization.",
        parents=[build_optimizer_parser()],
    )
    
    # 2. pairwise (gepa)
    pw_parser = opt_subparsers.add_parser("pairwise", help="Run Phase 3 custom Pairwise Elo Hill-Climbing optimization.")
    pw_parser.add_argument("--processed-root", type=Path, default=Path("datasets/processed"))
    pw_parser.add_argument("--output-root", type=Path, default=Path("output"))
    pw_parser.add_argument("--task-model", required=True, help="DSPy task model, e.g. openai/gpt-5.1-codex-mini.")
    pw_parser.add_argument("--judge-model", required=True, help="Dedicated judge model, e.g. openai/gpt-5.4.")
    pw_parser.add_argument("--iterations", type=int, default=10, help="Maximum optimization iterations.")
    
    # 3. tournament
    tour_parser = opt_subparsers.add_parser("tournament", help="Run Phase 4 Elo A/B tournament between Baseline and Optimized prompts.")
    tour_parser.add_argument("--processed-root", type=Path, default=Path("datasets/processed"))
    tour_parser.add_argument("--output-root", type=Path, default=Path("output"))
    tour_parser.add_argument("--task-model", required=True, help="DSPy task model, e.g. openai/gpt-5.1-codex-mini.")
    tour_parser.add_argument("--judge-model", required=True, help="Dedicated judge model, e.g. openai/gpt-5.4.")
    tour_parser.add_argument("--matches", type=int, default=10, help="Number of head-to-head matches.")
    tour_parser.add_argument("--run-dir", type=Path, required=True, help="Path to the optimization run directory containing the best prompts.")

    return parser


def _run_ingest() -> int:
    from zettel_eval.ingest.writer import run_ingest_phase
    dataset_config = load_dataset_config()
    run_ingest_phase(dataset_config)
    return 0


def _run_validate() -> int:
    from zettel_eval.validate.ground_truth import run_validate_phase
    dataset_config = load_dataset_config()
    run_validate_phase(dataset_config)
    return 0


def _run_benchmark() -> int:
    dataset_config = load_dataset_config()
    retrieval_config = load_retrieval_config()
    metrics_path = evaluate_processed_datasets(
        processed_root=dataset_config.processed_dir,
        output_root=dataset_config.output_dir,
        retrieval_config=retrieval_config,
    )
    append_log(Path("output") / "benchmark.log", f"Benchmark metrics written to {metrics_path}")
    return 0


def _run_optimize_dspy(args: argparse.Namespace) -> int:
    run_dir = run_optimization_from_args(args)
    append_log(Path("output") / "pipeline.log", f"Optimization artifacts written to {run_dir}")
    return 0

def _run_optimize_pairwise(args: argparse.Namespace) -> int:
    from zettel_eval.pipeline.pairwise_opt import run_pairwise_optimization
    run_dir = run_pairwise_optimization(
        output_root=args.output_root,
        processed_root=args.processed_root,
        task_model=args.task_model,
        judge_model=args.judge_model,
        iterations=args.iterations
    )
    append_log(Path("output") / "pipeline.log", f"Pairwise Optimization artifacts written to {run_dir}")
    return 0

def _run_optimize_tournament(args: argparse.Namespace) -> int:
    from zettel_eval.pipeline.tournament import run_tournament
    elo_opt, elo_base = run_tournament(
        output_root=args.output_root,
        processed_root=args.processed_root,
        opt_run_dir=args.run_dir,
        task_model=args.task_model,
        judge_model=args.judge_model,
        matches=args.matches
    )
    append_log(Path("output") / "pipeline.log", f"Tournament concluded. Optimized Elo: {int(elo_opt)}, Baseline Elo: {int(elo_base)}")
    return 0

def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "datasets":
        if args.subcommand == "ingest":
            return _run_ingest()
        elif args.subcommand == "validate":
            return _run_validate()
            
    elif args.command == "retrieval":
        if args.subcommand == "benchmark":
            return _run_benchmark()
            
    elif args.command == "optimizer":
        if args.subcommand == "dspy":
            return _run_optimize_dspy(args)
        elif args.subcommand == "pairwise":
            return _run_optimize_pairwise(args)
        elif args.subcommand == "tournament":
            return _run_optimize_tournament(args)

    parser.error(f"Unknown command/subcommand: {args.command} {args.subcommand}")
    return 2
