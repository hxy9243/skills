from __future__ import annotations

from pathlib import Path
import json
import random

from zettel_eval.datasets.models import NoteRecord


def write_manual_inspection_report(dataset_slug: str, notes: list[NoteRecord], output_path: Path) -> None:
    rng = random.Random(0)
    samples = []
    all_links = [
        {
            "source_note_id": note.note_id,
            "target_note_id": link.target_note_id,
            "anchor_text": link.anchor_text,
            "href": link.href,
            "is_internal": link.is_internal,
        }
        for note in notes
        for link in note.outgoing_links
    ]
    for sample in rng.sample(all_links, k=min(50, len(all_links))):
        samples.append(sample)
    report = {
        "dataset_slug": dataset_slug,
        "sample_size": len(samples),
        "status": "manual_review_required",
        "samples": samples,
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
