from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from wikicli.config import load_config
from wikicli.fs import gather_source_files, normalize_path
from wikicli.log import active_catalog
from wikicli.render import combined_notes, suggest_unindexed_packets
from wikicli.text import STOPWORDS, tokenize


def register_parser(subparsers) -> None:
    parser = subparsers.add_parser("search", help="Search notes via obsidian-cli or rg, plus generated docs.")
    parser.add_argument("query", help="Query string.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum matches per result set.")
    parser.set_defaults(func=run)


def obsidian_search(config, query: str):
    if not shutil.which("obsidian-cli"):
        return None
    try:
        result = subprocess.run(
            ["obsidian-cli", "search-content", query, "--vault", config.notebook_root.name],
            cwd=str(config.notebook_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode not in {0, 1}:
        return None
    return [{"backend": "obsidian-cli", "raw": line.strip()} for line in result.stdout.splitlines() if line.strip()]


def rg_search(root: Path, query: str):
    try:
        result = subprocess.run(["rg", "-n", "-i", query, str(root)], capture_output=True, text=True, check=False)
    except OSError:
        return []
    matches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path, _, remainder = line.partition(":")
        line_no, _, text = remainder.partition(":")
        matches.append({"path": path, "line": line_no or "1", "text": text.strip()})
    return matches


def generated_search(config, query: str):
    matches = []
    for item in rg_search(config.generated_root, query):
        try:
            rel = normalize_path(Path(item["path"]).resolve().relative_to(config.generated_root))
        except ValueError:
            rel = item["path"]
        matches.append({"path": rel, "line": item["line"], "text": item["text"]})
    return matches


def query_terms(query: str):
    return [term for term in tokenize(query) if term not in STOPWORDS]


def rg_content_search(config, query: str):
    matches = []
    generated_root = config.generated_root.resolve()
    for item in rg_search(config.notebook_root, query):
        path = Path(item["path"]).resolve()
        if path == generated_root or generated_root in path.parents:
            continue
        try:
            source = normalize_path(path.relative_to(config.notebook_root))
        except ValueError:
            continue
        matches.append({"source": source, "line": item["line"], "snippet": item["text"], "match_reason": "content"})
    return matches


def tag_search(notes, query: str):
    terms = set(query_terms(query))
    if not terms:
        return []
    matches = []
    for note in notes:
        tags = note.get("tags", [])
        tag_tokens = {token.lstrip("#") for tag in tags for token in tokenize(tag)}
        overlap = sorted(terms & tag_tokens)
        if overlap:
            matches.append({"source": note["source"], "tags": tags, "snippet": f"Matched tags: {', '.join('#' + token for token in overlap)}", "match_reason": "tags"})
    return matches


def hierarchy_search(notes, query: str):
    terms = set(query_terms(query))
    if not terms:
        return []
    matches = []
    for note in notes:
        hierarchy_tokens = set(tokenize(" ".join(note.get("category_path", []))))
        overlap = sorted(terms & hierarchy_tokens)
        if overlap:
            matches.append({"source": note["source"], "snippet": f"Matched hierarchy terms: {', '.join(overlap)}", "match_reason": "hierarchy"})
    return matches


def enrich_note_matches(raw_matches, note_lookup):
    merged = {}
    for item in raw_matches:
        source = item.get("source")
        if not source:
            continue
        note = note_lookup.get(source, {})
        enriched = merged.setdefault(source, {
            "source": source,
            "title": note.get("title", Path(source).stem),
            "hierarchy": note.get("category_path", []),
            "tags": note.get("tags", []),
            "match_reasons": [],
            "snippets": [],
        })
        reason = item.get("match_reason")
        if reason and reason not in enriched["match_reasons"]:
            enriched["match_reasons"].append(reason)
        snippet = item.get("snippet")
        if snippet and snippet not in enriched["snippets"]:
            enriched["snippets"].append(snippet)
        line = item.get("line")
        if line and "line" not in enriched:
            enriched["line"] = line
    return list(merged.values())


def run(args) -> int:
    config = load_config(args.config)
    catalog = active_catalog(config)
    current_files = {normalize_path(path.relative_to(config.notebook_root)) for path in gather_source_files(config)}
    notes = combined_notes(catalog, suggest_unindexed_packets(config, sorted(current_files - set(catalog))))
    note_lookup = {note["source"]: note for note in notes}

    obsidian_matches = obsidian_search(config, args.query)
    backend = "obsidian-cli"
    if not obsidian_matches:
        backend = "rg"
        obsidian_matches = []
    structured_note_matches = enrich_note_matches(
        [
            *rg_content_search(config, args.query),
            *tag_search(notes, args.query),
            *hierarchy_search(notes, args.query),
        ],
        note_lookup,
    )
    generated_matches = generated_search(config, args.query)
    print(json.dumps({
        "query": args.query,
        "notes_backend": backend,
        "obsidian_matches": obsidian_matches[: args.limit],
        "note_matches": structured_note_matches[: args.limit],
        "tag_matches": tag_search(notes, args.query)[: args.limit],
        "hierarchy_matches": hierarchy_search(notes, args.query)[: args.limit],
        "generated_matches": generated_matches[: args.limit],
    }, indent=2))
    return 0 if obsidian_matches or structured_note_matches or generated_matches else 1
