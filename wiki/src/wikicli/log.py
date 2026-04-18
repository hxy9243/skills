from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wikicli.config import WikiConfig
from wikicli.fs import ensure_layout
from wikicli.text import slugify


SYSTEM_NOTE_NAMES = {"dashboard", "dashboard-index", "index", "readme", "summary", "log"}


def utc_now() -> str:
    """
    Get the current UTC timestamp formatted as an ISO 8601 string.
    
    Returns:
        str: The timestamp string ending in 'Z'.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_log_event(config: WikiConfig, event: dict[str, Any]) -> None:
    """
    Append a new event packet to the end of the log.md file.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        event (dict[str, Any]): The event data to log (e.g. add/remove action).
    """
    ensure_layout(config)
    with config.log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {json.dumps(event, ensure_ascii=True, sort_keys=True)}\n")


def read_log_events(config: WikiConfig) -> list[dict[str, Any]]:
    """
    Read and parse all valid JSON events from the log.md file.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        
    Returns:
        list[dict[str, Any]]: A list of parsed event dictionaries.
    """
    if not config.log_path.exists():
        return []
    events = []
    for line in config.log_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- {"):
            continue
        try:
            events.append(json.loads(stripped[2:]))
        except json.JSONDecodeError:
            continue
    return events


def active_catalog(config: WikiConfig) -> dict[str, dict[str, Any]]:
    """
    Replay the log events to build the current state of indexed notes.
    
    Iterates through all events. 'add' events insert or update a note in the catalog,
    while 'remove' events delete it.
    
    Args:
        config (WikiConfig): The active wiki configuration.
        
    Returns:
        dict[str, dict[str, Any]]: A dictionary mapping source relative paths to note data.
    """
    catalog: dict[str, dict[str, Any]] = {}
    for event in read_log_events(config):
        source = event.get("source")
        if not source:
            continue
        if event.get("action") == "add":
            catalog[source] = {
                "title": event["title"],
                "summary": event["summary"],
                "category_path": event["category_path"],
                "tags": event.get("tags", []),
                "source": source,
                "source_mtime_ns": event.get("source_mtime_ns"),
                "updated_at": event["timestamp"],
            }
        elif event.get("action") == "remove":
            catalog.pop(source, None)
    return catalog


def is_system_note(source: str) -> bool:
    """
    Determine if a source file path is a reserved system note.
    
    Args:
        source (str): The relative path to the note.
        
    Returns:
        bool: True if the note is a system note (e.g., index.md, summary.md).
    """
    return slugify(Path(source).stem) in SYSTEM_NOTE_NAMES
