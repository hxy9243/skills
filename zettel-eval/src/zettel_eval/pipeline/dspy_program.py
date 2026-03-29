from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

import dspy


@dataclass(slots=True)
class RetrievedNote:
    note_id: str
    text: str


@dataclass(slots=True)
class FilteredConnection:
    note_id: str
    relevance_score: float
    keep: bool
    connection_summary: str
    evidence_quote: str


class FilterRetrievedNotes(dspy.Signature):
    """Review the retrieved notes, keep only the ones that genuinely help the seed note, and return strict JSON."""

    seed_note = dspy.InputField(desc="The seed note that needs to be expanded into a brainstorm essay.")
    retrieved_notes = dspy.InputField(desc="A numbered list of retrieved notes with note ids and full text.")
    filtered_notes_json = dspy.OutputField(
        desc=(
            "A JSON array. Each item must have note_id, relevance_score (0-1), keep (boolean), "
            "connection_summary, and evidence_quote."
        )
    )


class SynthesizeBrainstorm(dspy.Signature):
    """Write a grounded brainstorm essay that uses only the seed note and the filtered notes."""

    seed_note = dspy.InputField(desc="The seed note that anchors the brainstorm.")
    filtered_notes = dspy.InputField(
        desc="JSON describing the filtered supporting notes and why they matter."
    )
    brainstorm_essay = dspy.OutputField(
        desc=(
            "A polished brainstorm essay with specific cross-note connections, explicit grounding, "
            "and logically coherent claims."
        )
    )


def format_retrieved_notes(notes: Iterable[RetrievedNote]) -> str:
    chunks: list[str] = []
    for index, note in enumerate(notes, start=1):
        chunks.append(f"[{index}] note_id={note.note_id}\n{note.text.strip()}")
    return "\n\n".join(chunks)


def _coerce_json_payload(raw_text: str, default: Any) -> Any:
    text = raw_text.strip()
    if not text:
        return default
    candidates = [text]
    if "```json" in text:
        candidates.extend(segment.split("```", 1)[0].strip() for segment in text.split("```json")[1:])
    elif "```" in text:
        candidates.extend(segment.split("```", 1)[0].strip() for segment in text.split("```")[1:])

    start_positions = [i for i, char in enumerate(text) if char in "[{"]
    end_positions = [i for i, char in enumerate(text) if char in "]}"]
    if start_positions and end_positions:
        for start in start_positions:
            for end in reversed(end_positions):
                if end > start:
                    candidates.append(text[start : end + 1])
                    break

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return default


def parse_filtered_connections(raw_text: str) -> list[FilteredConnection]:
    payload = _coerce_json_payload(raw_text, default=[])
    if not isinstance(payload, list):
        return []

    connections: list[FilteredConnection] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        note_id = str(item.get("note_id", "")).strip()
        if not note_id:
            continue
        relevance_score = item.get("relevance_score", 0.0)
        try:
            normalized_score = max(0.0, min(1.0, float(relevance_score)))
        except (TypeError, ValueError):
            normalized_score = 0.0
        keep_raw = item.get("keep", normalized_score >= 0.5)
        keep = keep_raw if isinstance(keep_raw, bool) else str(keep_raw).strip().lower() in {"1", "true", "yes"}
        connections.append(
            FilteredConnection(
                note_id=note_id,
                relevance_score=normalized_score,
                keep=keep,
                connection_summary=str(item.get("connection_summary", "")).strip(),
                evidence_quote=str(item.get("evidence_quote", "")).strip(),
            )
        )

    connections.sort(key=lambda item: item.relevance_score, reverse=True)
    return connections


def filtered_connections_to_json(connections: Iterable[FilteredConnection]) -> str:
    return json.dumps([asdict(connection) for connection in connections], indent=2, ensure_ascii=True)


def export_predictor_prompt(predictor: Any) -> str:
    signature = predictor.signature
    lines = [signature.instructions.strip()]
    demos = getattr(predictor, "demos", []) or []
    if demos:
        lines.append("")
        lines.append("Few-shot examples:")
        for index, demo in enumerate(demos, start=1):
            lines.append(f"Example {index}:")
            for field in signature.input_fields:
                value = getattr(demo, field, None)
                if value is not None:
                    lines.append(f"{field}:")
                    lines.append(str(value).strip())
            for field in signature.output_fields:
                value = getattr(demo, field, None)
                if value is not None:
                    lines.append(f"{field}:")
                    lines.append(str(value).strip())
            lines.append("")
    return "\n".join(lines).strip() + "\n"


class BrainstormPipeline(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.filter_notes = dspy.Predict(FilterRetrievedNotes)
        self.synthesize = dspy.Predict(SynthesizeBrainstorm)

    def forward(self, seed_note: str, retrieved_notes: str | list[RetrievedNote]) -> dspy.Prediction:
        formatted_notes = (
            format_retrieved_notes(retrieved_notes)
            if isinstance(retrieved_notes, list)
            else str(retrieved_notes)
        )
        filter_prediction = self.filter_notes(seed_note=seed_note, retrieved_notes=formatted_notes)
        parsed_connections = parse_filtered_connections(filter_prediction.filtered_notes_json)
        kept_connections = [item for item in parsed_connections if item.keep]
        if not kept_connections:
            kept_connections = parsed_connections[:3]
        filtered_json = filtered_connections_to_json(kept_connections)
        synthesis_prediction = self.synthesize(seed_note=seed_note, filtered_notes=filtered_json)
        return dspy.Prediction(
            filtered_notes_json=filtered_json,
            brainstorm_essay=synthesis_prediction.brainstorm_essay,
        )
