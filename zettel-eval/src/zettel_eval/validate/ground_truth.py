from __future__ import annotations

import csv
import json
from pathlib import Path
import re

from zettel_eval.config import DatasetConfig
from zettel_eval.datasets.models import NoteRecord
from zettel_eval.logging import write_json
from zettel_eval.validate.inspect import write_manual_inspection_report
from zettel_eval.validate.stats import compute_stats


INTERNAL_LINK_RE = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")


def _load_notes(metadata_path: Path) -> list[NoteRecord]:
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    notes: list[NoteRecord] = []
    for item in raw.get("notes", []):
        notes.append(
            NoteRecord(
                note_id=item["note_id"],
                source_url=item["source_url"],
                title=item["title"],
                markdown_path=item["markdown_path"],
                text=item["text"],
                outgoing_links=[],
            )
        )
    return notes


def _load_metadata(metadata_path: Path) -> dict:
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _extract_links(note_text: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2)) for match in INTERNAL_LINK_RE.finditer(note_text)]


def _mask_anchor(text: str, target_note_id: str, anchor_text: str) -> str:
    pattern = re.escape(f"[[{target_note_id}|{anchor_text}]]")
    return re.sub(pattern, "[[MASKED_LINK]]", text)


def run_validate_phase(dataset_config: DatasetConfig) -> None:
    dataset_config.processed_dir.mkdir(parents=True, exist_ok=True)

    for dataset_dir in sorted(path for path in dataset_config.raw_dir.iterdir() if path.is_dir()):
        metadata_path = dataset_dir / "metadata.json"
        if not metadata_path.exists():
            continue

        metadata = _load_metadata(metadata_path)
        notes = _load_notes(metadata_path)
        note_by_id = {note.note_id: note for note in notes}

        for note in notes:
            note_path = dataset_dir / note.markdown_path
            note.text = note_path.read_text(encoding="utf-8")
            note.outgoing_links = [
                type("LinkStub", (), {"target_note_id": target_id, "anchor_text": anchor, "is_internal": True})()
                for target_id, anchor in _extract_links(note.text)
            ]

        stats = compute_stats(notes)
        processed_dir = dataset_config.processed_dir / dataset_dir.name
        processed_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            processed_dir / "dataset_stats.json",
            {
                "note_count": stats.note_count,
                "notes_with_links_ratio": stats.notes_with_links_ratio,
                "unique_bidirectional_links": stats.unique_bidirectional_links,
                "top_10_percent_degree_share": stats.top_10_percent_degree_share,
                "passes_thresholds": stats.passes(),
            },
        )
        write_manual_inspection_report(dataset_dir.name, notes, processed_dir / "inspection_report.json")
        if not stats.passes():
            continue

        corpus_rows = [{"note_id": note.note_id, "text": note.text} for note in notes]
        with (processed_dir / "corpus.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["note_id", "text"])
            writer.writeheader()
            writer.writerows(corpus_rows)

        ground_truth_rows: list[dict] = []
        for note in notes:
            for target_note_id, anchor_text in _extract_links(note.text):
                if target_note_id not in note_by_id:
                    continue
                ground_truth_rows.append(
                    {
                        "dataset_slug": dataset_dir.name,
                        "source_note_id": note.note_id,
                        "target_note_id": target_note_id,
                        "query_text": note.text,
                        "retrieval_condition": "anchor_preserved",
                    }
                )
                ground_truth_rows.append(
                    {
                        "dataset_slug": dataset_dir.name,
                        "source_note_id": note.note_id,
                        "target_note_id": target_note_id,
                        "query_text": _mask_anchor(note.text, target_note_id, anchor_text),
                        "retrieval_condition": "anchor_masked",
                    }
                )

        with (processed_dir / "ground_truth.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "dataset_slug",
                    "source_note_id",
                    "target_note_id",
                    "query_text",
                    "retrieval_condition",
                ],
            )
            writer.writeheader()
            writer.writerows(ground_truth_rows)
