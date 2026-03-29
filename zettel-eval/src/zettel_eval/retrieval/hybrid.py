from __future__ import annotations


class HybridRetriever:
    def __init__(self, bm25, dense, alpha: float = 0.5) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.alpha = alpha

    def search(self, query: str, exclude_ids: set[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        exclude_ids = exclude_ids or set()
        bm25_scores = dict(self.bm25.search(query, exclude_ids=exclude_ids, limit=max(limit * 3, 20)))
        dense_scores = dict(self.dense.search(query, exclude_ids=exclude_ids, limit=max(limit * 3, 20)))
        candidate_ids = set(bm25_scores) | set(dense_scores)
        if not candidate_ids:
            return []
        max_bm25 = max(bm25_scores.values(), default=1.0) or 1.0
        max_dense = max(dense_scores.values(), default=1.0) or 1.0
        combined = []
        for note_id in candidate_ids:
            bm25_score = bm25_scores.get(note_id, 0.0) / max_bm25
            dense_score = dense_scores.get(note_id, 0.0) / max_dense
            combined.append((note_id, self.alpha * dense_score + (1.0 - self.alpha) * bm25_score))
        combined.sort(key=lambda item: item[1], reverse=True)
        return combined[:limit]
