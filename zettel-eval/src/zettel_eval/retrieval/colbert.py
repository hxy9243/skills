from __future__ import annotations

import math

from zettel_eval.retrieval.bm25 import tokenize


def _token_embedding(token: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    index = hash(token) % dimensions
    vector[index] = 1.0
    return vector


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


class ColBERTRetriever:
    """A lightweight late-interaction approximation for offline experimentation."""

    def __init__(self, notes: dict[str, str], dimensions: int = 64) -> None:
        self.dimensions = dimensions
        self.note_token_vectors = {
            note_id: [_token_embedding(token, dimensions) for token in tokenize(text)]
            for note_id, text in notes.items()
        }

    def search(self, query: str, exclude_ids: set[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        exclude_ids = exclude_ids or set()
        query_vectors = [_token_embedding(token, self.dimensions) for token in tokenize(query)]
        scores: list[tuple[str, float]] = []
        for note_id, note_vectors in self.note_token_vectors.items():
            if note_id in exclude_ids:
                continue
            if not note_vectors or not query_vectors:
                scores.append((note_id, 0.0))
                continue
            score = 0.0
            for query_vector in query_vectors:
                score += max(_dot(query_vector, note_vector) for note_vector in note_vectors)
            score /= math.sqrt(len(query_vectors))
            scores.append((note_id, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:limit]
