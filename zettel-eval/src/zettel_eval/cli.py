from __future__ import annotations

import argparse
import sys
from pathlib import Path

from zettel_eval.config import load_dataset_config, load_retrieval_config
from zettel_eval.logging import append_log


def _build_parser(optimizer_command: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline evaluation pipeline for Zettelkasten datasets.")
    subparsers = parser.add_subparsers(dest="command_group", required=True)

    datasets_parser = subparsers.add_parser("datasets", help="Ingest and validate datasets.")
    datasets_subparsers = datasets_parser.add_subparsers(dest="datasets_command", required=True)
    datasets_subparsers.add_parser("ingest", help="Run Phase 0 ingestion over configured datasets.")
    datasets_subparsers.add_parser("validate", help="Run Phase 1 dataset validation and ground truth generation.")

    retrieval_parser = subparsers.add_parser("retrieval", help="Benchmark retrieval methods.")
    retrieval_subparsers = retrieval_parser.add_subparsers(dest="retrieval_command", required=True)
    retrieval_subparsers.add_parser("benchmark", help="Run Phase 2 retrieval benchmarks.")

    optimizer_parser = subparsers.add_parser("optimizer", help="Run prompt optimization workflows.")
    optimizer_subparsers = optimizer_parser.add_subparsers(dest="optimizer_command", required=True)
    _add_optimizer_subcommands(optimizer_subparsers, optimizer_command)

    return parser


def _add_optimizer_subcommands(
    optimizer_subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    optimizer_command: str | None,
) -> None:
    if optimizer_command == "dspy":
        from zettel_eval.pipeline.optimize import build_optimizer_parser

        optimizer_subparsers.add_parser(
            "dspy",
            help="Run Phase 3 DSPy optimization.",
            parents=[build_optimizer_parser()],
        )
    else:
        optimizer_subparsers.add_parser("dspy", help="Run Phase 3 DSPy optimization.")

    if optimizer_command == "pairwise":
        from zettel_eval.pipeline.pairwise_opt import build_pairwise_parser

        optimizer_subparsers.add_parser(
            "pairwise",
            help="Run pairwise prompt optimization.",
            parents=[build_pairwise_parser()],
        )
    else:
        optimizer_subparsers.add_parser("pairwise", help="Run pairwise prompt optimization.")

    if optimizer_command == "tournament":
        from zettel_eval.pipeline.tournament import build_tournament_parser

        optimizer_subparsers.add_parser(
            "tournament",
            help="Run an Elo tournament between baseline and optimized prompts.",
            parents=[build_tournament_parser()],
        )
    else:
        optimizer_subparsers.add_parser(
            "tournament",
            help="Run an Elo tournament between baseline and optimized prompts.",
        )


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
    from zettel_eval.retrieval.search import evaluate_processed_datasets

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
    from zettel_eval.pipeline.optimize import run_optimization_from_args

    run_dir = run_optimization_from_args(args)
    append_log(Path("output") / "pipeline.log", f"Optimization artifacts written to {run_dir}")
    return 0


def _run_optimize_pairwise(args: argparse.Namespace) -> int:
    from zettel_eval.pipeline.pairwise_opt import run_pairwise_optimization_from_args

    run_dir = run_pairwise_optimization_from_args(args)
    append_log(Path("output") / "pipeline.log", f"Pairwise optimization artifacts written to {run_dir}")
    return 0


def _run_optimize_tournament(args: argparse.Namespace) -> int:
    from zettel_eval.pipeline.tournament import run_tournament_from_args

    run_dir = run_tournament_from_args(args)
    append_log(Path("output") / "pipeline.log", f"Tournament artifacts written to {run_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    optimizer_command = argv[1] if len(argv) >= 2 and argv[0] == "optimizer" else None
    parser = _build_parser(optimizer_command=optimizer_command)
    args = parser.parse_args(argv)

    if args.command_group == "datasets" and args.datasets_command == "ingest":
        return _run_ingest()
    if args.command_group == "datasets" and args.datasets_command == "validate":
        return _run_validate()
    if args.command_group == "retrieval" and args.retrieval_command == "benchmark":
        return _run_benchmark()
    if args.command_group == "optimizer" and args.optimizer_command == "dspy":
        return _run_optimize_dspy(args)
    if args.command_group == "optimizer" and args.optimizer_command == "pairwise":
        return _run_optimize_pairwise(args)
    if args.command_group == "optimizer" and args.optimizer_command == "tournament":
        return _run_optimize_tournament(args)

    parser.error("Unknown command")
    return 2
