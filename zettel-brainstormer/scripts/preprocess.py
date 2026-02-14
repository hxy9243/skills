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
from llm_utils import call_llm


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

def generate_queries(title, points, model_name):
    if not model_name:
        return [f"{title} background", f"{title} criticism", f"{title} examples"]

    system_prompt = "You are a research assistant. Generate 3 specific search queries."
    user_prompt = f"""
    Topic: {title}
    Key Points: {json.dumps(points)}

    Task: Generate 3 specific search queries to find supporting evidence, counter-arguments, or missing context.
    Output format: JSON list of strings (e.g. ["query 1", "query 2", "query 3"])
    """
    response = call_llm(system_prompt, user_prompt, model_name)
    if not response:
        return [f"{title} background", f"{title} criticism", f"{title} examples"]

    try:
        # cleanup markdown json codes if present
        cleaned = response.replace('```json', '').replace('```', '').strip()
        queries = json.loads(cleaned)
        if isinstance(queries, list):
            return queries[:3]
        return [f"{title} background", f"{title} criticism", f"{title} examples"]
    except:
        return [f"{title} background", f"{title} criticism", f"{title} examples"]

# --- Filter Logic ---

def check_relevance(doc_content, title, points, model_name):
    """
    Ask LLM to score relevance 0-10.
    """
    system_prompt = "You are a research assistant. Evaluate the relevance of a document to a draft topic."
    user_prompt = f"""
    Draft Title: {title}
    Key Points: {json.dumps(points)}

    Document Content:
    {doc_content[:2000]}

    Task: Is this document relevant to the draft?
    Reply with ONLY a single number from 0 to 10.
    0 = Completely irrelevant
    10 = Crucial, directly supports the points
    """

    response = call_llm(system_prompt, user_prompt, model_name)
    try:
        score = int(response.strip())
        return score
    except:
        return 5 # Default on error

def summarize_doc(doc_content, title, model_name):
    """
    Summarize document to < 300 words.
    """
    system_prompt = "You are a research assistant. Summarize the following text."
    user_prompt = f"""
    Context: We are writing about "{title}".

    Document:
    {doc_content[:8000]}

    Task: Summarize the key information relevant to the topic in under 200 words.
    """

    response = call_llm(system_prompt, user_prompt, model_name)
    return response if response else doc_content[:1000] + "..."

def process_docs(docs_list, title, points, model_name, relevance_threshold=5, max_length=2000):
    filtered = []
    for doc in docs_list:
        content = doc.get('content', '')
        path = doc.get('path', 'unknown')

        # 1. Check Relevance
        score = check_relevance(content, title, points, model_name)
        if score < relevance_threshold:
            print(f"Skipping {Path(path).stem} (Score: {score})", file=sys.stderr)
            continue

        print(f"Keeping {Path(path).stem} (Score: {score})", file=sys.stderr)

        # 2. Summarize if too long
        if len(content) > max_length:
            print(f"Summarizing {Path(path).stem}...", file=sys.stderr)
            summary = summarize_doc(content, title, model_name)
            doc['content'] = f"**Summary (Relevance: {score}/10)**:\n{summary}"
        else:
            doc['content'] = f"**Relevance: {score}/10**\n\n{content}"

        filtered.append(doc)
    return filtered

# --- Main preprocessing logic ---

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Input note path')
    p.add_argument('--output', required=True, help='Output JSON path')
    p.add_argument('--zettel-dir', help='Override Zettelkasten directory')
    # Filter args
    p.add_argument('--filter', action='store_true', help='Enable LLM-based relevance filtering')
    p.add_argument('--threshold', type=int, default=4, help='Relevance score threshold (0-10)')
    p.add_argument('--max-length', type=int, default=2000, help='Max content length before summarization')

    args = p.parse_args()

    # Load configuration
    config = ConfigManager.load()
    if args.zettel_dir:
        zettel_dir = Path(args.zettel_dir).expanduser()
    else:
        zettel_dir = Path(config.get('zettel_dir', '~/Documents/Obsidian/Zettelkasten')).expanduser()
    link_depth = config.get('link_depth', 2)
    max_links = config.get('max_links', 10)
    # Use preprocess model for queries and filtering
    preprocess_model = config.get('preprocess_model', 'openrouter/x-ai/kimi-k2.5')

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

    # Generate queries
    print(f"Generating queries using {preprocess_model}...", file=sys.stderr)
    queries = generate_queries(title, points, preprocess_model)

    # Apply filtering if enabled
    if args.filter:
        print(f"Filtering docs (threshold={args.threshold}, max_len={args.max_length}) using {preprocess_model}...", file=sys.stderr)
        linked_docs = process_docs(linked_docs, title, points, preprocess_model, args.threshold, args.max_length)
        tag_similar_docs = process_docs(tag_similar_docs, title, points, preprocess_model, args.threshold, args.max_length)

    outline = {
        'headlines': [title] if title else [],
        'points': points,
        'queries': queries,
        'linked_docs': linked_docs,
        'tag_similar_docs': tag_similar_docs
    }

    write_json(args.output, outline)
    print(f'Wrote {args.output}', file=sys.stderr)
