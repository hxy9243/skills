#!/usr/bin/env python3
"""CLI for maintaining a markdown LLM wiki."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import textwrap
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


HOME = Path.home()
VAULT_ROOT = HOME / "Documents" / "kevinhusnotes"
WIKI_ROOT = VAULT_ROOT / "_WIKI"
NODES_DIR = WIKI_ROOT / "nodes"
INDEX_PATH = WIKI_ROOT / "index.md"
LOG_PATH = WIKI_ROOT / "log.md"
WIKI_RAW_DIR = WIKI_ROOT / "raw"
RESOURCES_RAW_DIR = VAULT_ROOT / "30_Resources" / "Raw"

REQUIRED_SECTIONS = [
    "## Core Ideas",
    "## Related Concepts",
    "## Evolution / Contradictions",
    "## Sources",
]


@dataclass
class NodeSpec:
    title: str
    summary: str
    category: List[str]
    core_ideas: List[str]
    related_concepts: List[str]
    contradictions: List[str]
    source_stem: str
    source_path: Path

    @property
    def filename(self) -> str:
        sanitized = re.sub(r'[\\/:*?"<>|]+', " ", self.title)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return f"{sanitized}.md"

    @property
    def node_path(self) -> Path:
        return NODES_DIR / self.filename


@dataclass
class NodeRecord:
    path: Path
    title: str
    summary: str
    category: List[str]
    source_links: List[str]
    body: str


def ensure_layout() -> None:
    NODES_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_RAW_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.touch(exist_ok=True)
    LOG_PATH.touch(exist_ok=True)


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text
    raw_meta, body = parts[0][4:], parts[1]
    meta: Dict[str, object] = {}
    current_key = None
    for line in raw_meta.splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9_ -]*:\s*$", line):
            current_key = line.split(":", 1)[0].strip()
            meta[current_key] = []
            continue
        if line.startswith("  - ") and current_key:
            value = line[4:].strip().strip("'\"")
            existing = meta.setdefault(current_key, [])
            if isinstance(existing, list):
                existing.append(value)
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("'\"")
            current_key = None
    return meta, body


def summarize_text(text: str, limit: int = 220) -> str:
    clean = re.sub(r"^\W+", "", re.sub(r"\s+", " ", text).strip())
    clean = clean.replace("> ", "").strip()
    if len(clean) <= limit:
        return clean
    clipped = clean[: limit - 3].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def normalize_acronyms(text: str) -> str:
    replacements = {
        "Ai": "AI",
        "Llm": "LLM",
        "Rag": "RAG",
        "Api": "API",
        "Rbac": "RBAC",
    }
    words = text.split()
    return " ".join(replacements.get(word, word) for word in words)


def extract_title(raw_text: str, source_path: Path) -> str:
    for line in raw_text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            if ":" in title:
                return title.split(":", 1)[1].strip()
            return title
    return source_path.stem.replace("_", " ")


def extract_sentences(raw_text: str) -> List[str]:
    body = extract_content_text(raw_text)
    body = re.sub(r"`[^`]+`", "", body)
    body = re.sub(r"\[[^\]]+\]\([^)]+\)", "", body)
    chunks = re.split(r"(?<=[.!?])\s+", body)
    return [c.strip() for c in chunks if len(c.strip()) > 30]


def strip_frontmatter(raw_text: str) -> str:
    _, body = parse_frontmatter(raw_text)
    return body


def extract_content_text(raw_text: str) -> str:
    body = strip_frontmatter(raw_text)
    cleaned_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        if stripped.startswith("# "):
            continue
        if stripped.startswith("@") and "):" in stripped:
            continue
        if stripped.startswith("📅 ") or stripped.startswith("🔗 "):
            continue
        if stripped.startswith("http://") or stripped.startswith("https://"):
            continue
        if set(stripped) == {"─"}:
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def count_keyword_hits(text: str, keyword: str) -> int:
    pattern = r"\b" + re.escape(keyword.lower()).replace(r"\ ", r"\s+") + r"\b"
    return len(re.findall(pattern, text.lower()))


def heuristic_category(text: str, title: str) -> List[str]:
    haystack = f"{title}\n{text}".lower()
    rules = [
        (["memory", "context window", "claude code", "compaction"], ["Computer Science", "AI", "Memory Systems"]),
        (["filesystem", "rag", "retrieval", "docs", "chroma"], ["Computer Science", "AI", "Agent Interfaces"]),
        (["hierarchy", "organization", "middle management", "company", "block"], ["Strategy", "Organizations", "AI-Native Organizations"]),
        (["tweet", "twitter", "x.com"], ["Signal", "Social Media", "Source Notes"]),
    ]
    scored = []
    for keywords, category in rules:
        score = sum(count_keyword_hits(haystack, keyword) for keyword in keywords)
        if score:
            scored.append((score, category))
    if scored:
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]
    return ["General", "Unsorted"]


def title_case_phrase(text: str) -> str:
    small = {"a", "an", "and", "as", "at", "for", "in", "of", "on", "or", "the", "to", "with"}
    words = re.split(r"\s+", text.strip())
    out = []
    for i, word in enumerate(words):
        lower = word.lower()
        if i and lower in small:
            out.append(lower)
        else:
            out.append(lower.capitalize())
    return normalize_acronyms(" ".join(out))


def heuristic_related(text: str) -> List[str]:
    mapping = {
        "RAG": ["rag", "retrieval"],
        "Virtual Filesystem": ["virtual filesystem", "file system", "filesystem"],
        "World Model": ["world model"],
        "Hierarchy": ["hierarchy", "span of control"],
        "Middle Management": ["middle management", "manager"],
        "Session Memory": ["session memory"],
        "Microcompaction": ["microcompact", "compaction"],
        "Tool Result Storage": ["tool result", "persisted-output"],
    }
    lowered = text.lower()
    found = [label for label, keywords in mapping.items() if any(count_keyword_hits(lowered, k) for k in keywords)]
    return found[:6]


def heuristic_core_ideas(text: str) -> List[str]:
    sentences = extract_sentences(text)
    ideas = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(token in lowered for token in [" because ", " instead ", " enables ", " allows ", " replaces ", " uses ", " can "]):
            ideas.append(summarize_text(sentence, 180))
        if len(ideas) >= 4:
            break
    if not ideas:
        ideas = [summarize_text(sentence, 180) for sentence in sentences[:3]]
    return ideas[:4]


def heuristic_summary(text: str, title: str) -> str:
    sentences = extract_sentences(text)
    if sentences:
        return summarize_text(sentences[0], 220)
    return summarize_text(title, 220)


def call_openai_enrich(title: str, text: str) -> Dict[str, object] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    model = os.getenv("LLM_WIKI_MODEL", "gpt-4.1-mini")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    prompt = textwrap.dedent(
        f"""
        Extract a durable concept page from this markdown source.
        Return strict JSON with keys:
        title, summary, category, core_ideas, related_concepts, contradictions.
        category must be an array of 2 or 3 strings.
        core_ideas, related_concepts, contradictions must be arrays of strings.

        Source title: {title}

        Source:
        {text[:16000]}
        """
    ).strip()
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You extract stable wiki nodes from noisy markdown notes and tweets. Output JSON only.",
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        ],
    }
    req = urllib.request.Request(
        f"{base_url}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None
    text_out = body.get("output_text")
    if not text_out:
        outputs = body.get("output", [])
        for item in outputs:
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    text_out = content["text"]
                    break
    if not text_out:
        return None
    try:
        return json.loads(text_out)
    except json.JSONDecodeError:
        return None


def build_node_spec(source_path: Path) -> NodeSpec:
    raw_text = source_path.read_text(encoding="utf-8")
    content_text = extract_content_text(raw_text)
    title = title_case_phrase(extract_title(raw_text, source_path))
    llm = call_openai_enrich(title, raw_text)
    if llm:
        category = [str(part).strip() for part in llm.get("category", []) if str(part).strip()][:3]
        if not category:
            category = heuristic_category(content_text, title)
        return NodeSpec(
            title=str(llm.get("title") or title).strip(),
            summary=summarize_text(str(llm.get("summary") or heuristic_summary(content_text, title)), 220),
            category=category,
            core_ideas=[summarize_text(str(item), 180) for item in llm.get("core_ideas", []) if str(item).strip()][:4] or heuristic_core_ideas(content_text),
            related_concepts=[title_case_phrase(str(item)) for item in llm.get("related_concepts", []) if str(item).strip()][:6] or heuristic_related(content_text),
            contradictions=[summarize_text(str(item), 180) for item in llm.get("contradictions", []) if str(item).strip()][:4],
            source_stem=source_path.stem,
            source_path=source_path,
        )
    return NodeSpec(
        title=title,
        summary=heuristic_summary(content_text, title),
        category=heuristic_category(content_text, title),
        core_ideas=heuristic_core_ideas(content_text),
        related_concepts=heuristic_related(content_text),
        contradictions=[],
        source_stem=source_path.stem,
        source_path=source_path,
    )


def render_node(spec: NodeSpec, existing_created: str | None = None, existing_sources: Iterable[str] = ()) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    created = existing_created or today
    source_links = sorted(set(existing_sources) | {spec.source_stem})
    related = spec.related_concepts or ["None yet."]
    contradictions = spec.contradictions or ["No explicit contradictions captured yet."]
    lines = [
        "---",
        f"Created: '{created}'",
        f"Updated: '{today}'",
        "Tags:",
        "  - '#concept'",
        "  - '#llm-wiki'",
        "Category:",
    ]
    for part in spec.category[:3]:
        lines.append(f"  - {part}")
    lines.extend(
        [
            "---",
            f"# {spec.title}",
            "",
            spec.summary,
            "",
            "## Core Ideas",
        ]
    )
    for idea in spec.core_ideas:
        lines.append(f"- {idea}")
    lines.extend(["", "## Related Concepts"])
    for concept in related:
        if concept == "None yet.":
            lines.append(f"- {concept}")
        else:
            lines.append(f"- [[{concept}]]")
    lines.extend(["", "## Evolution / Contradictions"])
    for item in contradictions:
        lines.append(f"- {item}")
    lines.extend(["", "## Sources"])
    for stem in source_links:
        lines.append(f"- [[{stem}]]")
    lines.append("")
    return "\n".join(lines)


def read_existing_node(path: Path) -> Tuple[str | None, List[str]]:
    if not path.exists():
        return None, []
    text = path.read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(text)
    created = str(meta.get("Created") or "").strip() or None
    sources = re.findall(r"- \[\[([^\]]+)\]\]", text.split("## Sources", 1)[1] if "## Sources" in text else "")
    return created, sources


def parse_node_record(path: Path) -> NodeRecord:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem
    body_after_title = body.split("\n", 2)
    summary = ""
    if len(body_after_title) >= 3:
        summary = body_after_title[2].split("\n## ", 1)[0].strip()
    category = meta.get("Category")
    if isinstance(category, list):
        category_parts = [str(x).strip() for x in category if str(x).strip()]
    elif isinstance(category, str) and category:
        category_parts = [category]
    else:
        category_parts = ["General", "Unsorted"]
    source_links = re.findall(r"- \[\[([^\]]+)\]\]", text.split("## Sources", 1)[1] if "## Sources" in text else "")
    return NodeRecord(path=path, title=title, summary=summary, category=category_parts[:3], source_links=source_links, body=text)


def load_nodes() -> List[NodeRecord]:
    if not NODES_DIR.exists():
        return []
    return sorted((parse_node_record(path) for path in NODES_DIR.glob("*.md")), key=lambda node: node.title.lower())


def render_index(records: Sequence[NodeRecord]) -> str:
    grouped: Dict[str, Dict[str, Dict[str, List[NodeRecord]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for record in records:
        parts = record.category[:3] or ["General", "Unsorted"]
        if len(parts) == 1:
            parts = [parts[0], "General"]
        if len(parts) == 2:
            parts = [parts[0], parts[1], ""]
        grouped[parts[0]][parts[1]][parts[2]].append(record)

    lines = [
        "# LLM Wiki Index",
        "",
        f"_Last regenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        "This catalog is an inferred taxonomy with a maximum depth of 3 layers.",
        "",
    ]
    for top in sorted(grouped):
        lines.extend([f"## {top}", ""])
        for second in sorted(grouped[top]):
            lines.extend([f"### {second}", ""])
            third_map = grouped[top][second]
            for third in sorted(third_map):
                if third:
                    lines.extend([f"#### {third}", ""])
                for record in sorted(third_map[third], key=lambda node: node.title.lower()):
                    lines.append(f"- [[{record.title}]] - {summarize_text(record.summary, 160)}")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def append_log(action: str, source_name: str, category: Sequence[str], pages: Sequence[str]) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"## [{timestamp}] {action} | {source_name}",
        f"- Category: {' -> '.join(category)}",
        f"- Pages touched: {', '.join(f'[[{page}]]' for page in pages)}",
        "",
    ]
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def maybe_archive(path: Path, mode: str) -> Path | None:
    if mode == "none":
        return None
    if mode == "wiki-raw":
        target_dir = WIKI_RAW_DIR
    elif mode == "resources-raw":
        target_dir = RESOURCES_RAW_DIR
    else:
        raise ValueError(f"Unsupported archive mode: {mode}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    shutil.move(str(path), str(target))
    return target


def cmd_add(args: argparse.Namespace) -> int:
    ensure_layout()
    ingested = []
    for file_arg in args.files:
        source_path = Path(file_arg).expanduser().resolve()
        if not source_path.exists():
            print(f"missing file: {source_path}", file=sys.stderr)
            return 1
        spec = build_node_spec(source_path)
        created, existing_sources = read_existing_node(spec.node_path)
        spec.node_path.write_text(render_node(spec, created, existing_sources), encoding="utf-8")
        maybe_archive(source_path, args.archive)
        ingested.append(spec)
        append_log("Ingest", spec.source_stem, spec.category, [spec.title])

    INDEX_PATH.write_text(render_index(load_nodes()), encoding="utf-8")
    for spec in ingested:
        print(json.dumps({
            "source": spec.source_stem,
            "title": spec.title,
            "category": spec.category,
            "node": str(spec.node_path),
        }, ensure_ascii=True))
    return 0


def cmd_lint(_: argparse.Namespace) -> int:
    ensure_layout()
    issues = []
    records = load_nodes()
    seen_titles = set()
    indexed_links = set(re.findall(r"\[\[([^\]]+)\]\]", INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""))
    for record in records:
        lowered = record.title.lower()
        if lowered in seen_titles:
            issues.append(f"duplicate title: {record.title}")
        seen_titles.add(lowered)
        if len(record.category) > 3:
            issues.append(f"category deeper than 3: {record.title}")
        if record.title not in indexed_links:
            issues.append(f"missing from index: {record.title}")
        for section in REQUIRED_SECTIONS:
            if section not in record.body:
                issues.append(f"missing section {section}: {record.title}")
        if not record.summary:
            issues.append(f"missing summary: {record.title}")
    print(json.dumps({"nodes": len(records), "issues": issues}, ensure_ascii=True, indent=2))
    return 1 if issues else 0


def cmd_search(args: argparse.Namespace) -> int:
    ensure_layout()
    query = args.query.lower()
    matches = []
    for record in load_nodes():
        haystack = "\n".join([record.title, record.summary, " -> ".join(record.category), record.body]).lower()
        if query in haystack:
            matches.append({
                "title": record.title,
                "category": record.category,
                "path": str(record.path),
                "summary": summarize_text(record.summary, 160),
            })
    print(json.dumps({"query": args.query, "matches": matches}, ensure_ascii=True, indent=2))
    return 0 if matches else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain the _WIKI knowledge base.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Ingest raw markdown files into the wiki.")
    add_parser.add_argument("files", nargs="+", help="Raw markdown files to ingest.")
    add_parser.add_argument(
        "--archive",
        choices=["none", "wiki-raw", "resources-raw"],
        default="none",
        help="Archive processed raw files after ingest.",
    )
    add_parser.set_defaults(func=cmd_add)

    lint_parser = subparsers.add_parser("lint", help="Validate wiki nodes and index coverage.")
    lint_parser.set_defaults(func=cmd_lint)

    search_parser = subparsers.add_parser("search", help="Search wiki nodes.")
    search_parser.add_argument("query", help="Case-insensitive search string.")
    search_parser.set_defaults(func=cmd_search)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
