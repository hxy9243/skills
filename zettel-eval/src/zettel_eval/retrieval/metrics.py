from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RetrievalExample:
    dataset_slug: str
    source_note_id: str
    target_note_id: str
    query_text: str
    retrieval_condition: str


def recall_at_k(ranked_ids: list[str], target_id: str, k: int) -> float:
    return 1.0 if target_id in ranked_ids[:k] else 0.0


def reciprocal_rank(ranked_ids: list[str], target_id: str) -> float:
    for index, candidate in enumerate(ranked_ids, start=1):
        if candidate == target_id:
            return 1.0 / index
    return 0.0
