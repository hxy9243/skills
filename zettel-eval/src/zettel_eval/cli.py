from __future__ import annotations

import argparse
from pathlib import Path

from zettel_eval.config import load_dataset_config, load_retrieval_config
from zettel_eval.logging import append_log
from zettel_eval.retrieval.search import evaluate_processed_datasets


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zettel-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ingest", help="Run Phase 0 ingestion over configured datasets.")
    subparsers.add_parser("validate", help="Run Phase 1 dataset validation and ground truth generation.")
    subparsers.add_parser("benchmark", help="Run Phase 2 retrieval benchmarks.")
    subparsers.add_parser("pipeline", help="Run Phases 0-2 end to end.")

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


def _run_pipeline() -> int:
    _run_ingest()
    _run_validate()
    _run_benchmark()
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "ingest":
        return _run_ingest()
    if args.command == "validate":
        return _run_validate()
    if args.command == "benchmark":
        return _run_benchmark()
    if args.command == "pipeline":
        return _run_pipeline()

    parser.error(f"Unknown command: {args.command}")
    return 2
