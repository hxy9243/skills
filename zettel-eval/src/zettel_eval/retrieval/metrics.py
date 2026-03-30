from __future__ import annotations

from dataclasses import dataclass
import json

@dataclass(slots=True)
class RetrievalExample:
    dataset_slug: str
    source_note_id: str
    target_note_ids: list[str]
    query_text: str
    retrieval_condition: str

def mean_average_precision(ranked_ids: list[str], target_ids: list[str]) -> float:
    if not target_ids:
        return 0.0

    target_set = set(target_ids)
    hits = 0
    precision_sum = 0.0
    for index, candidate in enumerate(ranked_ids, start=1):
        if candidate not in target_set:
            continue
        hits += 1
        precision_sum += hits / index

    return precision_sum / len(target_set)

def hit_rate_at_k(ranked_ids: list[str], target_ids: list[str], k: int) -> float:
    if not target_ids:
        return 0.0
    target_set = set(target_ids)
    return 1.0 if any(candidate in target_set for candidate in ranked_ids[:k]) else 0.0

def mrr_for_targets(ranked_ids: list[str], target_ids: list[str]) -> float:
    # First relevant item rank
    target_set = set(target_ids)
    for index, candidate in enumerate(ranked_ids, start=1):
        if candidate in target_set:
            return 1.0 / index
    return 0.0
