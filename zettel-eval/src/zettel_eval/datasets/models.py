from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class LinkRecord:
    source_note_id: str
    target_note_id: str | None
    anchor_text: str
    href: str
    is_internal: bool


@dataclass(slots=True)
class NoteRecord:
    note_id: str
    source_url: str
    title: str
    markdown_path: str
    text: str
    outgoing_links: list[LinkRecord] = field(default_factory=list)


@dataclass(slots=True)
class DatasetMetadata:
    dataset_slug: str
    seed_url: str
    crawl_started_at: str
    note_id_by_url: dict[str, str]
    notes: list[NoteRecord]
    external_links: list[str]

    def to_dict(self) -> dict:
        return asdict(self)
