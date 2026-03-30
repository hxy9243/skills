from __future__ import annotations
import sys
import csv
csv.field_size_limit(sys.maxsize)

from dataclasses import dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
import json
import math

from zettel_eval.config import RetrievalConfig
from zettel_eval.logging import append_log, ensure_parent, write_csv, write_json
from zettel_eval.retrieval.bm25 import BM25Retriever
from zettel_eval.retrieval.colbert import ColBERTRetriever
from zettel_eval.retrieval.dense import DenseRetriever
from zettel_eval.retrieval.hybrid import HybridRetriever
from zettel_eval.retrieval.metrics import RetrievalExample, hit_rate_at_k, mean_average_precision, mrr_for_targets
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
                target_note_ids=json.loads(row["target_note_ids"]),
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
        return DenseRetriever(notes=notes, dimensions=int(params.get("dimensions", 1536)), model="openai")
    if method == "dense_nomic":
        return DenseRetriever(notes=notes, dimensions=int(params.get("dimensions", 768)), model="nomic")
    if method == "colbert":
        return ColBERTRetriever(notes=notes)
    if method == "hybrid":
        return HybridRetriever(
            bm25=BM25Retriever(notes=notes, k1=float(params.get("k1", 1.2)), b=float(params.get("b", 0.75))),
            dense=DenseRetriever(notes=notes, dimensions=int(params.get("dimensions", 1536)), model="openai"),
            alpha=float(params.get("alpha", 0.5)),
        )
    if method == "hybrid_nomic":
        return HybridRetriever(
            bm25=BM25Retriever(notes=notes, k1=float(params.get("k1", 1.2)), b=float(params.get("b", 0.75))),
            dense=DenseRetriever(notes=notes, dimensions=int(params.get("dimensions", 768)), model="nomic"),
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
    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / "runs" / run_timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    append_log(run_dir / "run.log", "Starting retrieval benchmark run.")
    append_log(run_dir / "run.log", f"Run directory: {run_dir}")

    if not processed_root.exists():
        metrics_path = run_dir / "retrieval_metrics.csv"
        write_csv(
            metrics_path,
            [],
            fieldnames=[
                "dataset_slug",
                "method",
                "retrieval_condition",
                "source_note_id",
                "target_note_ids",
                "map",
                "hit_rate_at_5",
                "hit_rate_at_10",
                "mrr",
                "params",
                "retrieved_ids",
            ],
        )
        _write_run_readme(run_dir, run_timestamp, retrieval_config)
        return metrics_path

    metrics_rows: list[dict] = []
    summary_rows: list[dict] = []
    all_dataset_scores: dict[str, dict[str, float]] = {}

    for dataset_dir in sorted(path for path in processed_root.iterdir() if path.is_dir()):
        corpus_path = dataset_dir / "corpus.csv"
        ground_truth_path = dataset_dir / "ground_truth.csv"
        if not corpus_path.exists() or not ground_truth_path.exists():
            continue

        notes = load_corpus(corpus_path)
        examples = load_ground_truth(ground_truth_path)
        if not notes or not examples:
            continue

        dataset_aggregate: dict[str, list[float]] = {}

        for method_name, method_config in retrieval_config.methods.items():
            if not method_config.enabled:
                continue
            best_score = -math.inf
            best_summary: dict | None = None

            for params in _grid(method_config.grid):
                try:
                    retriever = _build_retriever(method_name, notes, params)
                except Exception as exc:
                    append_log(
                        run_dir / "run.log",
                        f"Skipping method={method_name} params={json.dumps(params, sort_keys=True)}: {exc}",
                    )
                    continue
                map_values: list[float] = []
                hit5_values: list[float] = []
                hit10_values: list[float] = []
                mrr_values: list[float] = []

                # Sample up to 100 queries per dataset per method to save time
                for example in examples[:100]:
                    ranked = retriever.search(example.query_text, exclude_ids={example.source_note_id}, limit=10)
                    ranked_ids = [item[0] for item in ranked]

                    map_score = mean_average_precision(ranked_ids, example.target_note_ids)
                    hit5 = hit_rate_at_k(ranked_ids, example.target_note_ids, 5)
                    hit10 = hit_rate_at_k(ranked_ids, example.target_note_ids, 10)
                    mrr = mrr_for_targets(ranked_ids, example.target_note_ids)

                    map_values.append(map_score)
                    hit5_values.append(hit5)
                    hit10_values.append(hit10)
                    mrr_values.append(mrr)

                    metrics_rows.append(
                        {
                            "dataset_slug": dataset_dir.name,
                            "method": method_name,
                            "retrieval_condition": example.retrieval_condition,
                            "source_note_id": example.source_note_id,
                            "target_note_ids": json.dumps(example.target_note_ids),
                            "map": f"{map_score:.4f}",
                            "hit_rate_at_5": f"{hit5:.4f}",
                            "hit_rate_at_10": f"{hit10:.4f}",
                            "mrr": f"{mrr:.4f}",
                            "params": json.dumps(params, sort_keys=True),
                            "retrieved_ids": json.dumps(ranked_ids[:10]),
                        }
                    )

                avg_map = sum(map_values) / len(map_values)
                avg_hit5 = sum(hit5_values) / len(hit5_values)
                avg_hit10 = sum(hit10_values) / len(hit10_values)
                avg_mrr = sum(mrr_values) / len(mrr_values)

                score = avg_map + avg_hit5 + avg_hit10 + avg_mrr
                if score > best_score:
                    best_score = score
                    best_summary = {
                        "dataset_slug": dataset_dir.name,
                        "method": method_name,
                        "map": avg_map,
                        "hit_rate_at_5": avg_hit5,
                        "hit_rate_at_10": avg_hit10,
                        "mrr": avg_mrr,
                        "params": params,
                    }

            if best_summary is None:
                continue
            summary_rows.append(
                {
                    "dataset_slug": best_summary["dataset_slug"],
                    "method": best_summary["method"],
                    "map": f'{best_summary["map"]:.4f}',
                    "hit_rate_at_5": f'{best_summary["hit_rate_at_5"]:.4f}',
                    "hit_rate_at_10": f'{best_summary["hit_rate_at_10"]:.4f}',
                    "mrr": f'{best_summary["mrr"]:.4f}',
                    "params": json.dumps(best_summary["params"], sort_keys=True),
                }
            )
            dataset_aggregate[method_name] = [
                best_summary["map"],
                best_summary["hit_rate_at_5"],
                best_summary["hit_rate_at_10"],
                best_summary["mrr"],
            ]

        all_dataset_scores[dataset_dir.name] = {
            key: sum(values) / len(values) for key, values in dataset_aggregate.items()
        }

    metrics_path = run_dir / "retrieval_metrics.csv"
    write_csv(
        metrics_path,
        metrics_rows,
        fieldnames=[
            "dataset_slug",
            "method",
            "retrieval_condition",
            "source_note_id",
            "target_note_ids",
            "map",
            "hit_rate_at_5",
            "hit_rate_at_10",
            "mrr",
            "params",
            "retrieved_ids",
        ],
    )
    
    summary_md = "# Retrieval Benchmark Summary\n\n## Best Method Per Dataset\n\n"
    for row in summary_rows:
        summary_md += f"- `{row['dataset_slug']}` / `{row['method']}`: MAP={row['map']}, Hit@5={row['hit_rate_at_5']}, Hit@10={row['hit_rate_at_10']}, MRR={row['mrr']}, params={row['params']}\n"
    summary_md += "\n## Aggregate Diagnostics\n\n"
    for ds_name, methods in all_dataset_scores.items():
        parts = []
        for m, score in methods.items():
            parts.append(f"{m}={score:.4f}")
        summary_md += f"- `{ds_name}`: {', '.join(parts)}\n"

    summary_path = run_dir / "summary.md"
    summary_path.write_text(summary_md, encoding="utf-8")

    _write_run_readme(run_dir, run_timestamp, retrieval_config)
    append_log(run_dir / "run.log", "Finished retrieval benchmark run.")
    return metrics_path


def _write_run_readme(run_dir: Path, run_timestamp: str, retrieval_config: RetrievalConfig) -> None:
    enabled_methods = [
        method_name
        for method_name, method_config in retrieval_config.methods.items()
        if method_config.enabled
    ]
    config_grid = {
        method_name: method_config.grid
        for method_name, method_config in retrieval_config.methods.items()
        if method_config.enabled
    }
    readme = (
        "# Retrieval Benchmark Run\n\n"
        f"- Timestamp: `{run_timestamp}`\n"
        f"- Description: Retrieval benchmark artifacts for the configured benchmark run.\n"
        f"- Enabled methods: `{', '.join(enabled_methods) if enabled_methods else 'none'}`\n\n"
        "## Config Grid\n\n"
        "```json\n"
        f"{json.dumps(config_grid, indent=2, sort_keys=True)}\n"
        "```\n"
    )
    (run_dir / "README.md").write_text(readme, encoding="utf-8")
