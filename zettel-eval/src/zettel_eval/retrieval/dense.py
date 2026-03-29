from __future__ import annotations

import math

from zettel_eval.retrieval.bm25 import tokenize


def _hash_vector(tokens: list[str], dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    if not tokens:
        return vector
    for token in tokens:
        vector[hash(token) % dimensions] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


class DenseRetriever:
    def __init__(self, notes: dict[str, str], dimensions: int = 256) -> None:
        self.dimensions = dimensions
        self.note_vectors = {
            note_id: _hash_vector(tokenize(text), dimensions)
            for note_id, text in notes.items()
        }

    def search(self, query: str, exclude_ids: set[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        exclude_ids = exclude_ids or set()
        query_vector = _hash_vector(tokenize(query), self.dimensions)
        scores = [
            (note_id, _cosine(query_vector, vector))
            for note_id, vector in self.note_vectors.items()
            if note_id not in exclude_ids
        ]
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:limit]
