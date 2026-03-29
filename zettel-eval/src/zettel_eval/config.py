from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class DatasetSeed:
    slug: str
    seed_url: str


@dataclass(slots=True)
class DatasetConfig:
    seeds: list[DatasetSeed] = field(default_factory=list)
    raw_dir: Path = Path("datasets/raw")
    processed_dir: Path = Path("datasets/processed")
    output_dir: Path = Path("output")
    max_pages_per_dataset: int = 150


@dataclass(slots=True)
class RetrievalMethodConfig:
    enabled: bool = True
    top_k_values: list[int] = field(default_factory=lambda: [5, 10])
    grid: dict[str, list[Any]] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalConfig:
    benchmark_metrics: list[str] = field(default_factory=lambda: ["recall@5", "recall@10", "mrr"])
    split_mode: str = "dataset"
    lexical_conditions: list[str] = field(default_factory=lambda: ["anchor_preserved", "anchor_masked"])
    methods: dict[str, RetrievalMethodConfig] = field(default_factory=dict)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        msg = f"Expected mapping in config file: {path}"
        raise ValueError(msg)
    return data


def load_dataset_config(path: Path | str = Path("configs/datasets.yaml")) -> DatasetConfig:
    raw = _read_yaml(Path(path))
    seeds = [
        DatasetSeed(slug=item["slug"], seed_url=item["seed_url"])
        for item in raw.get("datasets", [])
    ]
    return DatasetConfig(
        seeds=seeds,
        raw_dir=Path(raw.get("raw_dir", "datasets/raw")),
        processed_dir=Path(raw.get("processed_dir", "datasets/processed")),
        output_dir=Path(raw.get("output_dir", "output")),
        max_pages_per_dataset=int(raw.get("max_pages_per_dataset", 150)),
    )


def load_retrieval_config(path: Path | str = Path("configs/retrieval.yaml")) -> RetrievalConfig:
    raw = _read_yaml(Path(path))
    methods: dict[str, RetrievalMethodConfig] = {}
    for name, data in raw.get("methods", {}).items():
        methods[name] = RetrievalMethodConfig(
            enabled=bool(data.get("enabled", True)),
            top_k_values=list(data.get("top_k_values", [5, 10])),
            grid=dict(data.get("grid", {})),
        )
    return RetrievalConfig(
        benchmark_metrics=list(raw.get("benchmark_metrics", ["recall@5", "recall@10", "mrr"])),
        split_mode=str(raw.get("split_mode", "dataset")),
        lexical_conditions=list(raw.get("lexical_conditions", ["anchor_preserved", "anchor_masked"])),
        methods=methods,
    )
