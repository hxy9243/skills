from __future__ import annotations

import re
from urllib.parse import urlparse


NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def canonical_note_id(url: str) -> str:
    parsed = urlparse(url)
    parts = [segment for segment in parsed.path.split("/") if segment]
    raw = "-".join(parts) if parts else parsed.netloc
    slug = NON_ALNUM_RE.sub("-", raw.lower()).strip("-")
    return slug or "index"


def markdown_filename(note_id: str) -> str:
    return f"{note_id}.md"
