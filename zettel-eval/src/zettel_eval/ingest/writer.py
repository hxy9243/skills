from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import re

from zettel_eval.config import DatasetConfig
from zettel_eval.datasets.models import DatasetMetadata, LinkRecord, NoteRecord
from zettel_eval.ingest.canonicalize import canonical_note_id, markdown_filename
from zettel_eval.ingest.crawl import crawl_site
from zettel_eval.ingest.defuddle import extract_markdown
from zettel_eval.ingest.links import normalize_url, resolve_href


MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _rewrite_internal_links(markdown: str, source_url: str, note_id_by_url: dict[str, str]) -> tuple[str, list[LinkRecord], set[str]]:
    outgoing: list[LinkRecord] = []
    external_links: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        anchor = match.group(1).strip() or "untitled"
        href = resolve_href(source_url, match.group(2).strip())
        target_note_id = note_id_by_url.get(href)
        is_internal = target_note_id is not None
        outgoing.append(
            LinkRecord(
                source_note_id=note_id_by_url[source_url],
                target_note_id=target_note_id,
                anchor_text=anchor,
                href=href,
                is_internal=is_internal,
            )
        )
        if is_internal:
            return f"[[{target_note_id}|{anchor}]]"
        external_links.add(href)
        return f"[{anchor}]({href})"

    return MARKDOWN_LINK_RE.sub(replace, markdown), outgoing, external_links


def run_ingest_phase(dataset_config: DatasetConfig) -> None:
    for seed in dataset_config.seeds:
        print(f"[ingest] crawling {seed.slug} from {seed.seed_url}")
        dataset_dir = dataset_config.raw_dir / seed.slug
        notes_dir = dataset_dir / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)

        pages = crawl_site(seed.seed_url, max_pages=dataset_config.max_pages_per_dataset)
        print(f"[ingest] discovered {len(pages)} pages for {seed.slug}")
        note_id_by_url = {normalize_url(page.url): canonical_note_id(page.url) for page in pages}
        notes: list[NoteRecord] = []
        external_links: set[str] = set()

        for page in pages:
            source_url = normalize_url(page.url)
            note_id = note_id_by_url[source_url]
            markdown = extract_markdown(source_url, page.html)
            normalized_markdown, outgoing, found_external = _rewrite_internal_links(markdown, source_url, note_id_by_url)
            external_links.update(found_external)
            markdown_path = notes_dir / markdown_filename(note_id)
            markdown_path.write_text(normalized_markdown, encoding="utf-8")
            title = note_id.replace("-", " ").title()
            notes.append(
                NoteRecord(
                    note_id=note_id,
                    source_url=source_url,
                    title=title,
                    markdown_path=str(markdown_path.relative_to(dataset_dir)),
                    text=normalized_markdown,
                    outgoing_links=outgoing,
                )
            )
            print(f"[ingest] wrote {markdown_path}")

        metadata = DatasetMetadata(
            dataset_slug=seed.slug,
            seed_url=seed.seed_url,
            crawl_started_at=datetime.now(UTC).isoformat(),
            note_id_by_url=note_id_by_url,
            notes=notes,
            external_links=sorted(external_links),
        )
        metadata_path = dataset_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata.to_dict(), indent=2), encoding="utf-8")
        print(f"[ingest] wrote {metadata_path}")
