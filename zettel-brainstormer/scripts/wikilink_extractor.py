#!/usr/bin/env python3
"""
Wikilink extractor for zettel-brainstormer.
Extracts [[wikilinks]] from notes and follows them N levels deep, up to M total links.

Usage: wikilink_extractor.py --seed note.md --depth 2 --max 10 --zettel-dir ~/zettelkasten
"""
import re
import argparse
from pathlib import Path
from typing import Set, List, Dict

def extract_wikilinks(content: str) -> List[str]:
    """Extract all [[wikilinks]] from markdown content"""
    pattern = r'\[\[([^\]]+)\]\]'
    return re.findall(pattern, content)

def find_note_path(link_name: str, zettel_dir: Path) -> Path:
    """Find the actual file path for a wikilink name"""
    # Try exact match first
    exact = zettel_dir / f"{link_name}.md"
    if exact.exists():
        return exact
    
    # Try case-insensitive search
    for note in zettel_dir.rglob("*.md"):
        if note.stem.lower() == link_name.lower():
            return note
    
    return None

def extract_links_recursive(
    seed_path: Path,
    zettel_dir: Path,
    max_depth: int,
    max_links: int
) -> Dict[str, dict]:
    """
    Recursively extract wikilinks up to max_depth levels, collecting up to max_links total.
    Returns dict: {note_path: {'level': int, 'links': [str], 'content': str}}
    """
    visited = {}
    to_process = [(seed_path, 0)]  # (path, current_depth)
    
    while to_process and len(visited) < max_links:
        current_path, depth = to_process.pop(0)
        
        if current_path in visited or depth > max_depth:
            continue
        
        # Read content
        try:
            content = current_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Warning: Could not read {current_path}: {e}")
            continue
        
        # Extract links
        links = extract_wikilinks(content)
        
        visited[current_path] = {
            'level': depth,
            'links': links,
            'content': content
        }
        
        # Add linked notes to process queue (if we haven't hit max depth)
        if depth < max_depth and len(visited) < max_links:
            for link in links:
                linked_path = find_note_path(link, zettel_dir)
                if linked_path and linked_path not in visited:
                    to_process.append((linked_path, depth + 1))
    
    return visited

def format_link_graph(links_data: Dict[Path, dict]) -> str:
    """Format the extracted links into a readable summary"""
    output = []
    output.append("# Extracted Wikilink Graph\n")
    
    # Group by level
    by_level = {}
    for path, data in links_data.items():
        level = data['level']
        if level not in by_level:
            by_level[level] = []
        by_level[level].append((path, data))
    
    for level in sorted(by_level.keys()):
        output.append(f"\n## Level {level}\n")
        for path, data in by_level[level]:
            output.append(f"- **{path.stem}** ({len(data['links'])} outgoing links)")
            if data['links']:
                output.append(f"  - Links to: {', '.join(data['links'][:5])}")
                if len(data['links']) > 5:
                    output.append(f"    ... and {len(data['links']) - 5} more")
    
    output.append(f"\n**Total notes extracted:** {len(links_data)}")
    return '\n'.join(output)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description="Extract wikilinks from zettelkasten notes")
    p.add_argument('--seed', required=True, help="Seed note path")
    p.add_argument('--depth', type=int, default=2, help="Max depth to follow links")
    p.add_argument('--max', type=int, default=10, help="Max total notes to extract")
    p.add_argument('--zettel-dir', required=True, help="Zettelkasten directory")
    p.add_argument('--output', help="Output file (default: print to stdout)")
    args = p.parse_args()
    
    seed_path = Path(args.seed).expanduser()
    zettel_dir = Path(args.zettel_dir).expanduser()
    
    if not seed_path.exists():
        print(f"Error: Seed note not found: {seed_path}")
        exit(1)
    
    if not zettel_dir.exists():
        print(f"Error: Zettelkasten directory not found: {zettel_dir}")
        exit(1)
    
    # Extract links
    links_data = extract_links_recursive(seed_path, zettel_dir, args.depth, args.max)
    
    # Format output
    summary = format_link_graph(links_data)
    
    if args.output:
        Path(args.output).write_text(summary, encoding='utf-8')
        print(f"Wrote link graph to {args.output}")
    else:
        print(summary)
    
    # Also write full extracted content to a separate file if output is specified
    if args.output:
        content_file = Path(args.output).with_suffix('.content.txt')
        full_content = []
        for path, data in links_data.items():
            full_content.append(f"\n{'='*60}\n")
            full_content.append(f"# {path.stem} (Level {data['level']})\n")
            full_content.append(f"{'='*60}\n\n")
            full_content.append(data['content'])
        
        content_file.write_text('\n'.join(full_content), encoding='utf-8')
        print(f"Wrote full content to {content_file}")
