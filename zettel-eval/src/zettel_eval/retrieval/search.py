from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import csv
import json
import math

from zettel_eval.config import RetrievalConfig
from zettel_eval.logging import append_log, ensure_parent, write_csv, write_json
from zettel_eval.retrieval.bm25 import BM25Retriever
from zettel_eval.retrieval.colbert import ColBERTRetriever
from zettel_eval.retrieval.dense import DenseRetriever
from zettel_eval.retrieval.hybrid import HybridRetriever
from zettel_eval.retrieval.metrics import RetrievalExample, recall_at_k, reciprocal_rank
from zettel_eval.reports.retrieval_report import build_summary_report


@dataclass(slots=True)
class NoteRecord:
    note_id: str
    text: str


def load_corpus(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["note_id"]: row["text"] for row in reader}


def load_ground_truth(path: Path) -> list[RetrievalExample]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            RetrievalExample(
                dataset_slug=row["dataset_slug"],
                source_note_id=row["source_note_id"],
                target_note_id=row["target_note_id"],
                query_text=row["query_text"],
                retrieval_condition=row["retrieval_condition"],
            )
            for row in reader
        ]


def _grid(grid: dict[str, list]) -> list[dict]:
    if not grid:
        return [{}]
    keys = list(grid.keys())
    values = [grid[key] for key in keys]
    return [dict(zip(keys, combo, strict=True)) for combo in product(*values)]


def _build_retriever(method: str, notes: dict[str, str], params: dict):
    if method == "bm25":
        return BM25Retriever(notes=notes, k1=float(params.get("k1", 1.2)), b=float(params.get("b", 0.75)))
    if method == "dense":
        return DenseRetriever(notes=notes, dimensions=int(params.get("dimensions", 256)))
    if method == "colbert":
        return ColBERTRetriever(notes=notes, dimensions=int(params.get("dimensions", 64)))
    if method == "hybrid":
        return HybridRetriever(
            bm25=BM25Retriever(notes=notes, k1=float(params.get("k1", 1.2)), b=float(params.get("b", 0.75))),
            dense=DenseRetriever(notes=notes, dimensions=int(params.get("dimensions", 256))),
            alpha=float(params.get("alpha", 0.5)),
        )
    msg = f"Unknown retrieval method: {method}"
    raise ValueError(msg)


def evaluate_processed_datasets(
    processed_root: Path,
    output_root: Path,
    retrieval_config: RetrievalConfig,
) -> Path:
    ensure_parent(output_root / "placeholder")
    run_dir = output_root / "runs" / "latest"
    run_dir.mkdir(parents=True, exist_ok=True)
    append_log(run_dir / "run.log", "Starting retrieval benchmark run.")

    if not processed_root.exists():
        metrics_path = output_root / "retrieval_metrics.csv"
        write_csv(
            metrics_path,
            [],
            fieldnames=[
                "dataset_slug",
                "method",
                "retrieval_condition",
                "source_note_id",
                "target_note_id",
                "recall_at_5",
                "recall_at_10",
                "mrr",
                "params",
                "retrieved_ids",
            ],
        )
        summary_path = run_dir / "summary.md"
        summary_path.write_text("No processed datasets were available for benchmarking.\n", encoding="utf-8")
        append_log(run_dir / "run.log", f"Processed dataset directory not found: {processed_root}")
        return metrics_path

    metrics_rows: list[dict] = []
    summary_rows: list[dict] = []
    all_dataset_scores: dict[str, dict[str, float]] = {}

    for dataset_dir in sorted(path for path in processed_root.iterdir() if path.is_dir()):
        corpus_path = dataset_dir / "corpus.csv"
        ground_truth_path = dataset_dir / "ground_truth.csv"
        if not corpus_path.exists() or not ground_truth_path.exists():
            append_log(run_dir / "run.log", f"Skipping {dataset_dir.name}: missing corpus or ground truth.")
            continue

        notes = load_corpus(corpus_path)
        examples = load_ground_truth(ground_truth_path)
        if not notes or not examples:
            append_log(run_dir / "run.log", f"Skipping {dataset_dir.name}: empty corpus or ground truth.")
            continue

        dataset_aggregate: dict[str, list[float]] = {}

        for method_name, method_config in retrieval_config.methods.items():
            if not method_config.enabled:
                continue
            best_score = -math.inf
            best_summary: dict | None = None

            for params in _grid(method_config.grid):
                retriever = _build_retriever(method_name, notes, params)
                recall5_values: list[float] = []
                recall10_values: list[float] = []
                mrr_values: list[float] = []

                for example in examples:
                    ranked = retriever.search(example.query_text, exclude_ids={example.source_note_id}, limit=max(method_config.top_k_values))
                    ranked_ids = [item[0] for item in ranked]
                    recall5 = recall_at_k(ranked_ids, example.target_note_id, 5)
                    recall10 = recall_at_k(ranked_ids, example.target_note_id, 10)
                    mrr = reciprocal_rank(ranked_ids, example.target_note_id)
                    recall5_values.append(recall5)
                    recall10_values.append(recall10)
                    mrr_values.append(mrr)
                    metrics_rows.append(
                        {
                            "dataset_slug": dataset_dir.name,
                            "method": method_name,
                            "retrieval_condition": example.retrieval_condition,
                            "source_note_id": example.source_note_id,
                            "target_note_id": example.target_note_id,
                            "recall_at_5": f"{recall5:.4f}",
                            "recall_at_10": f"{recall10:.4f}",
                            "mrr": f"{mrr:.4f}",
                            "params": json.dumps(params, sort_keys=True),
                            "retrieved_ids": json.dumps(ranked_ids[:10]),
                        }
                    )

                avg_recall5 = sum(recall5_values) / len(recall5_values)
                avg_recall10 = sum(recall10_values) / len(recall10_values)
                avg_mrr = sum(mrr_values) / len(mrr_values)
                score = avg_recall10 + avg_mrr
                if score > best_score:
                    best_score = score
                    best_summary = {
                        "dataset_slug": dataset_dir.name,
                        "method": method_name,
                        "recall_at_5": avg_recall5,
                        "recall_at_10": avg_recall10,
                        "mrr": avg_mrr,
                        "params": params,
                    }

            if best_summary is None:
                continue
            summary_rows.append(
                {
                    "dataset_slug": best_summary["dataset_slug"],
                    "method": best_summary["method"],
                    "recall_at_5": f'{best_summary["recall_at_5"]:.4f}',
                    "recall_at_10": f'{best_summary["recall_at_10"]:.4f}',
                    "mrr": f'{best_summary["mrr"]:.4f}',
                    "params": json.dumps(best_summary["params"], sort_keys=True),
                }
            )
            dataset_aggregate[method_name] = [
                best_summary["recall_at_5"],
                best_summary["recall_at_10"],
                best_summary["mrr"],
            ]

        all_dataset_scores[dataset_dir.name] = {
            key: sum(values) / len(values) for key, values in dataset_aggregate.items()
        }

    metrics_path = output_root / "retrieval_metrics.csv"
    write_csv(
        metrics_path,
        metrics_rows,
        fieldnames=[
            "dataset_slug",
            "method",
            "retrieval_condition",
            "source_note_id",
            "target_note_id",
            "recall_at_5",
            "recall_at_10",
            "mrr",
            "params",
            "retrieved_ids",
        ],
    )
    summary_path = run_dir / "summary.md"
    summary_path.write_text(build_summary_report(summary_rows, all_dataset_scores), encoding="utf-8")
    write_json(run_dir / "config.json", {"methods": list(retrieval_config.methods.keys())})
    append_log(run_dir / "run.log", "Finished retrieval benchmark run.")
    return metrics_path
