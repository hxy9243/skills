from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from zettel_eval.logging import append_log, ensure_parent, write_json

if TYPE_CHECKING:
    import dspy

csv.field_size_limit(sys.maxsize)


@dataclass(slots=True)
class OptimizationExample:
    dataset_slug: str
    source_note_id: str
    seed_note: str
    retrieved_notes: list[Any]
    target_note_ids: list[str]
    method: str
    params: dict[str, Any]
    retrieval_condition: str


def build_optimizer_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--retrieval-metrics", type=Path, default=None, help="Explicit Phase 2 retrieval_metrics.csv path.")
    parser.add_argument("--processed-root", type=Path, default=Path("datasets/processed"))
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    parser.add_argument("--task-model", required=True, help="DSPy task model, for example openai/gpt-4o-mini.")
    parser.add_argument("--judge-model", default=None, help="Optional dedicated judge model. Defaults to task model.")
    parser.add_argument("--prompt-model", default=None, help="Optional prompt model for MIPRO.")
    parser.add_argument("--optimizer", choices=("mipro", "bootstrap"), default="mipro")
    parser.add_argument("--iterations", type=int, default=20, help="Maximum optimization iterations or trials.")
    parser.add_argument("--train-size", type=int, default=24, help="Maximum number of retrieval examples to use.")
    parser.add_argument("--seed", type=int, default=7)
    return parser


def run_optimization_from_args(args: argparse.Namespace) -> Path:
    import dspy

    from zettel_eval.pipeline.dspy_program import BrainstormPipeline, export_predictor_prompt
    from zettel_eval.pipeline.judge import LLMJudgeMetric

    metrics_path = args.retrieval_metrics or discover_retrieval_metrics(args.output_root)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = args.output_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    append_log(run_dir / "run.log", f"Starting Phase 3 optimization setup using metrics from {metrics_path}")

    examples = load_phase2_examples(
        metrics_path=metrics_path,
        processed_root=args.processed_root,
        max_examples=args.train_size,
    )
    if len(examples) < 2:
        msg = "Need at least two Phase 2 examples to split into train and validation sets."
        raise ValueError(msg)

    trainset, valset = split_examples(examples)
    append_log(run_dir / "run.log", f"Loaded {len(examples)} examples ({len(trainset)} train / {len(valset)} val)")

    task_lm = dspy.LM(model=args.task_model, temperature=1.0, max_tokens=16000, cache=False)
    judge_lm = dspy.LM(model=args.judge_model or args.task_model, temperature=1.0, max_tokens=16000, cache=False)
    prompt_lm = dspy.LM(model=args.prompt_model, temperature=1.0, max_tokens=16000, cache=False) if args.prompt_model else None
    dspy.configure(lm=task_lm)

    student = BrainstormPipeline()
    metric = LLMJudgeMetric(judge_lm=judge_lm, log_file=run_dir / "filter_eval.csv")
    optimizer = build_optimizer(
        optimizer_name=args.optimizer,
        metric=metric,
        prompt_lm=prompt_lm,
        task_lm=task_lm,
        run_dir=run_dir,
        iterations=args.iterations,
        seed=args.seed,
    )

    write_json(
        run_dir / "config.json",
        {
            "optimizer": args.optimizer,
            "iterations": args.iterations,
            "task_model": args.task_model,
            "judge_model": args.judge_model or args.task_model,
            "prompt_model": args.prompt_model,
            "retrieval_metrics": str(metrics_path),
            "processed_root": str(args.processed_root),
            "train_size": args.train_size,
            "seed": args.seed,
            "train_examples": [serialize_example(example) for example in trainset],
            "val_examples": [serialize_example(example) for example in valset],
        },
    )

    compiled = compile_program(
        optimizer=optimizer,
        student=student,
        trainset=to_dspy_examples(trainset),
        valset=to_dspy_examples(valset),
        optimizer_name=args.optimizer,
        iterations=args.iterations,
        seed=args.seed,
    )

    best_filter_prompt = export_predictor_prompt(compiled.filter_notes)
    best_synthesis_prompt = export_predictor_prompt(compiled.synthesize)
    filter_path = args.output_root / "best_filter_prompt.txt"
    synthesis_path = args.output_root / "best_synthesis_prompt.txt"
    ensure_parent(filter_path)
    filter_path.write_text(best_filter_prompt, encoding="utf-8")
    synthesis_path.write_text(best_synthesis_prompt, encoding="utf-8")
    (run_dir / "best_filter_prompt.txt").write_text(best_filter_prompt, encoding="utf-8")
    (run_dir / "best_synthesis_prompt.txt").write_text(best_synthesis_prompt, encoding="utf-8")

    append_log(run_dir / "run.log", f"Saved optimized filter prompt to {filter_path}")
    append_log(run_dir / "run.log", f"Saved optimized synthesis prompt to {synthesis_path}")
    return run_dir


def discover_retrieval_metrics(output_root: Path) -> Path:
    latest_link = output_root / "runs" / "latest" / "retrieval_metrics.csv"
    if latest_link.exists():
        return latest_link

    run_candidates = sorted((output_root / "runs").glob("*/retrieval_metrics.csv"))
    if run_candidates:
        return run_candidates[-1]

    fallback = output_root / "retrieval_metrics.csv"
    if fallback.exists():
        return fallback

    msg = "Could not locate a Phase 2 retrieval_metrics.csv artifact."
    raise FileNotFoundError(msg)


def _metric_score(row: dict[str, str]) -> float:
    return sum(float(row[name]) for name in ("map", "hit_rate_at_5", "hit_rate_at_10", "mrr"))


def _load_corpus(processed_root: Path, dataset_slug: str) -> dict[str, str]:
    corpus_path = processed_root / dataset_slug / "corpus.csv"
    with corpus_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["note_id"]: row["text"] for row in reader}


def load_phase2_examples(
    *,
    metrics_path: Path,
    processed_root: Path,
    max_examples: int,
) -> list[OptimizationExample]:
    with metrics_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        return []

    best_by_group: dict[tuple[str, str, str], float] = {}
    for row in rows:
        key = (row["dataset_slug"], row["method"], row["params"])
        best_by_group.setdefault(key, 0.0)
        best_by_group[key] += _metric_score(row)

    chosen_groups: dict[str, tuple[str, str]] = {}
    for dataset_slug, method, params in best_by_group:
        current = chosen_groups.get(dataset_slug)
        score = best_by_group[(dataset_slug, method, params)]
        if current is None or score > best_by_group[(dataset_slug, current[0], current[1])]:
            chosen_groups[dataset_slug] = (method, params)

    corpora: dict[str, dict[str, str]] = {}
    examples: list[OptimizationExample] = []
    for row in rows:
        dataset_slug = row["dataset_slug"]
        selected = chosen_groups.get(dataset_slug)
        if selected != (row["method"], row["params"]):
            continue
        corpora.setdefault(dataset_slug, _load_corpus(processed_root, dataset_slug))
        corpus = corpora[dataset_slug]
        seed_note = corpus.get(row["source_note_id"], "").strip()
        if not seed_note:
            continue
        retrieved_ids = json.loads(row["retrieved_ids"])[:10]
        retrieved_notes = [
            _retrieved_note(note_id=note_id, text=corpus[note_id])
            for note_id in retrieved_ids
            if note_id in corpus
        ]
        if not retrieved_notes:
            continue
        examples.append(
            OptimizationExample(
                dataset_slug=dataset_slug,
                source_note_id=row["source_note_id"],
                seed_note=seed_note,
                retrieved_notes=retrieved_notes,
                target_note_ids=json.loads(row["target_note_ids"]),
                method=row["method"],
                params=json.loads(row["params"]),
                retrieval_condition=row["retrieval_condition"],
            )
        )

    examples.sort(
        key=lambda example: (
            example.dataset_slug,
            example.source_note_id,
            example.retrieval_condition,
        )
    )
    return examples[:max_examples]


def split_examples(examples: list[OptimizationExample]) -> tuple[list[OptimizationExample], list[OptimizationExample]]:
    if len(examples) < 2:
        return examples, []
    val_size = max(1, len(examples) // 5)
    trainset = examples[:-val_size]
    valset = examples[-val_size:]
    if not trainset:
        trainset = examples[:-1]
        valset = examples[-1:]
    return trainset, valset


def serialize_example(example: OptimizationExample) -> dict[str, Any]:
    return {
        "dataset_slug": example.dataset_slug,
        "source_note_id": example.source_note_id,
        "retrieval_condition": example.retrieval_condition,
        "method": example.method,
        "params": example.params,
        "target_note_ids": example.target_note_ids,
        "retrieved_note_ids": [note.note_id for note in example.retrieved_notes],
    }


def to_dspy_examples(examples: list[OptimizationExample]) -> list[dspy.Example]:
    import dspy

    from zettel_eval.pipeline.dspy_program import format_retrieved_notes

    return [
        dspy.Example(
            seed_note=example.seed_note,
            retrieved_notes=format_retrieved_notes(example.retrieved_notes),
            target_note_ids=json.dumps(example.target_note_ids),
            dataset_slug=example.dataset_slug,
            source_note_id=example.source_note_id,
            retrieval_condition=example.retrieval_condition,
        ).with_inputs("seed_note", "retrieved_notes")
        for example in examples
    ]


def build_optimizer(
    *,
    optimizer_name: str,
    metric: Any,
    prompt_lm: Any,
    task_lm: Any,
    run_dir: Path,
    iterations: int,
    seed: int,
) -> Any:
    import dspy

    if optimizer_name == "bootstrap":
        return dspy.BootstrapFewShotWithRandomSearch(
            metric=metric,
            num_candidate_programs=iterations,
            max_rounds=1,
            max_bootstrapped_demos=1,
            max_labeled_demos=1,
        )

    return dspy.MIPROv2(
        metric=metric,
        prompt_model=prompt_lm or task_lm,
        task_model=task_lm,
        max_bootstrapped_demos=1,
        max_labeled_demos=1,
        auto=None,
        num_candidates=7,
        num_threads=1,
        seed=seed,
        verbose=False,
        log_dir=str(run_dir / "optimizer_logs"),
    )


def compile_program(
    *,
    optimizer: Any,
    student: Any,
    trainset: list[dspy.Example],
    valset: list[dspy.Example],
    optimizer_name: str,
    iterations: int,
    seed: int,
) -> Any:
    if optimizer_name == "bootstrap":
        return optimizer.compile(student, trainset=trainset, valset=valset)

    return optimizer.compile(
        student,
        trainset=trainset,
        valset=valset,
        num_trials=iterations,
        minibatch=False,
        seed=seed,
        requires_permission_to_run=False,
    )


def _retrieved_note(*, note_id: str, text: str) -> Any:
    from zettel_eval.pipeline.dspy_program import RetrievedNote

    return RetrievedNote(note_id=note_id, text=text)
