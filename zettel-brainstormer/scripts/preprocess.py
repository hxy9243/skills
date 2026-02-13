#!/usr/bin/env python3
"""
Preprocess script for zettel-brainstormer.
Extracts headlines, key points, search queries, wikilinked docs, and tag-similar docs.
Writes JSON: {
  "headlines": [],
  "points": [],
  "queries": [],
  "linked_docs": [{"path": str, "level": int, "content": str}],
  "tag_similar_docs": [{"path": str, "tags": [str], "content": str}]
}

Usage: preprocess.py --input note.md --output outline.json
"""
import sys, json, argparse, re
from pathlib import Path
from typing import Set, List, Dict, Tuple
from config_manager import ConfigManager

def simple_read(path):
    return Path(path).read_text(encoding='utf-8')

def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2), encoding='utf-8')

from obsidian_utils import extract_links_recursive

# --- Tag extraction and similarity logic ---

def extract_tags(content: str) -> Set[str]:
    """
    Extract tags from markdown content.
    Supports: #tag, tags: [tag1, tag2], and YAML frontmatter tags.
    """
    tags = set()

    # Inline #tags
    inline_tags = re.findall(r'#([\w\-]+)', content)
    tags.update(inline_tags)

    # YAML frontmatter tags
    frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        fm = frontmatter_match.group(1)
        # Look for tags: [...] or tags: tag1, tag2
        tags_match = re.search(r'tags:\s*\[([^\]]+)\]', fm)
        if tags_match:
            yaml_tags = [t.strip().strip('"\'') for t in tags_match.group(1).split(',')]
            tags.update(yaml_tags)
        else:
            tags_match = re.search(r'tags:\s*(.+)', fm)
            if tags_match:
                yaml_tags = [t.strip() for t in tags_match.group(1).split(',')]
                tags.update(yaml_tags)

    return tags

def find_tag_similar_docs(
    seed_tags: Set[str],
    zettel_dir: Path,
    seed_path: Path,
    max_similar: int = 5
) -> List[Dict]:
    """
    Find notes with overlapping tags.
    Returns list of dicts: [{'path': str, 'tags': [str], 'content': str, 'overlap': int}]
    """
    similar = []

    for note_path in zettel_dir.rglob("*.md"):
        if note_path == seed_path:
            continue

        try:
            content = note_path.read_text(encoding='utf-8')
            note_tags = extract_tags(content)
            overlap = len(seed_tags & note_tags)

            if overlap > 0:
                similar.append({
                    'path': str(note_path),
                    'tags': sorted(list(note_tags)),
                    'content': content,
                    'overlap': overlap
                })
        except Exception as e:
            print(f"Warning: Could not read {note_path}: {e}", file=sys.stderr)
            continue

    # Sort by overlap descending, take top max_similar
    similar.sort(key=lambda x: x['overlap'], reverse=True)
    return [
        {'path': s['path'], 'tags': s['tags'], 'content': s['content']}
        for s in similar[:max_similar]
    ]

# --- Main preprocessing logic ---

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Input note path')
    p.add_argument('--output', required=True, help='Output JSON path')
    args = p.parse_args()

    # Load configuration
    config = ConfigManager.load()
    zettel_dir = Path(config.get('zettel_dir', '~/Documents/Obsidian/Zettelkasten')).expanduser()
    link_depth = config.get('link_depth', 2)
    max_links = config.get('max_links', 10)

    seed_path = Path(args.input).expanduser()
    if not seed_path.exists():
        print(f"Error: Input note not found: {seed_path}", file=sys.stderr)
        sys.exit(1)

    text = simple_read(seed_path)

    # Extract basic info (headlines, points)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = lines[0] if lines else ''
    points = []
    for l in lines[1:40]:
        if len(l) > 40 and len(points) < 12:
            points.append(l[:300])

    # Extract wikilinked documents
    linked_docs = []
    if zettel_dir.exists():
        raw_linked_docs = extract_links_recursive(seed_path, zettel_dir, link_depth, max_links)
        linked_docs = [
            {'path': str(path), 'level': data['level'], 'content': data['content']}
            for path, data in raw_linked_docs.items()
        ]
        print(f"Extracted {len(linked_docs)} linked documents (depth={link_depth}, max={max_links})", file=sys.stderr)
    else:
        print(f"Warning: Zettelkasten directory not found: {zettel_dir}", file=sys.stderr)

    # Extract tag-similar documents
    tag_similar_docs = []
    if zettel_dir.exists():
        seed_tags = extract_tags(text)
        if seed_tags:
            tag_similar_docs = find_tag_similar_docs(seed_tags, zettel_dir, seed_path, max_similar=5)
            print(f"Found {len(tag_similar_docs)} tag-similar documents (seed tags: {sorted(seed_tags)})", file=sys.stderr)
        else:
            print(f"No tags found in seed note", file=sys.stderr)

    outline = {
        'headlines': [title] if title else [],
        'points': points,
        'queries': [f"{title} background", f"{title} criticism", f"{title} examples"],
        'linked_docs': linked_docs,
        'tag_similar_docs': tag_similar_docs
    }

    write_json(args.output, outline)
    print(f'Wrote {args.output}', file=sys.stderr)
