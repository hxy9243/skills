from __future__ import annotations

from collections import Counter, defaultdict
import math
import re


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class BM25Retriever:
    def __init__(self, notes: dict[str, str], k1: float = 1.2, b: float = 0.75) -> None:
        self.notes = notes
        self.k1 = k1
        self.b = b
        self.doc_tokens = {note_id: tokenize(text) for note_id, text in notes.items()}
        self.doc_lengths = {note_id: len(tokens) for note_id, tokens in self.doc_tokens.items()}
        self.avg_doc_length = sum(self.doc_lengths.values()) / max(len(self.doc_lengths), 1)
        self.term_doc_freq: dict[str, int] = defaultdict(int)
        for tokens in self.doc_tokens.values():
            for term in set(tokens):
                self.term_doc_freq[term] += 1

    def search(self, query: str, exclude_ids: set[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        exclude_ids = exclude_ids or set()
        query_terms = tokenize(query)
        total_docs = max(len(self.doc_tokens), 1)
        scores: list[tuple[str, float]] = []
        for note_id, tokens in self.doc_tokens.items():
            if note_id in exclude_ids:
                continue
            tf = Counter(tokens)
            doc_len = max(self.doc_lengths[note_id], 1)
            score = 0.0
            for term in query_terms:
                df = self.term_doc_freq.get(term, 0)
                if df == 0:
                    continue
                idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
                freq = tf.get(term, 0)
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                score += idf * numerator / max(denominator, 1e-9)
            scores.append((note_id, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:limit]
