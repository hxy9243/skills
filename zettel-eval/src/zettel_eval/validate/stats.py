from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from zettel_eval.datasets.models import NoteRecord


@dataclass(slots=True)
class DatasetStats:
    note_count: int
    notes_with_links_ratio: float
    unique_bidirectional_links: int
    top_10_percent_degree_share: float

    def passes(self) -> bool:
        return (
            self.note_count >= 100
            and self.notes_with_links_ratio > 0.5
            and self.unique_bidirectional_links >= 2 * self.note_count
            and self.top_10_percent_degree_share <= 0.5
        )


def compute_stats(notes: list[NoteRecord]) -> DatasetStats:
    incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    undirected_edges: set[tuple[str, str]] = set()

    for note in notes:
        for link in note.outgoing_links:
            if not link.is_internal or not link.target_note_id:
                continue
            outgoing[note.note_id].add(link.target_note_id)
            incoming[link.target_note_id].add(note.note_id)
            edge = tuple(sorted((note.note_id, link.target_note_id)))
            undirected_edges.add(edge)

    note_count = len(notes)
    notes_with_links = [
        note.note_id
        for note in notes
        if incoming.get(note.note_id) or outgoing.get(note.note_id)
    ]
    degree_values = sorted(
        [
            len(incoming.get(note.note_id, set())) + len(outgoing.get(note.note_id, set()))
            for note in notes
        ],
        reverse=True,
    )
    top_count = max(1, round(note_count * 0.1)) if note_count else 1
    total_degree = sum(degree_values) or 1
    top_share = sum(degree_values[:top_count]) / total_degree

    return DatasetStats(
        note_count=note_count,
        notes_with_links_ratio=len(notes_with_links) / note_count if note_count else 0.0,
        unique_bidirectional_links=len(undirected_edges),
        top_10_percent_degree_share=top_share,
    )
