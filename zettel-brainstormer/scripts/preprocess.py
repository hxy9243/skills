#!/usr/bin/env python3
"""
Preprocess script for writing-brainstormer.
Calls openrouter kimi-k2.5 (via CLI or HTTP) to extract headlines, key points, and search queries.
Writes JSON: {"headlines":[], "points":[], "queries":[]}

Usage: preprocess.py --input note.md --output outline.json
"""
import sys, json, argparse, subprocess, shlex
from pathlib import Path
from config_manager import ConfigManager

def simple_read(path):
    return Path(path).read_text(encoding='utf-8')

def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2), encoding='utf-8')

# NOTE: This is a lightweight stub. Integrate with your OpenRouter CLI/API as needed.
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()

    # Load configuration to ensure setup is complete
    config = ConfigManager.load()

    text = simple_read(args.input)

    # Very simple heuristic extraction as fallback
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = lines[0] if lines else ''
    points = []
    for l in lines[1:40]:
        if len(l) > 40 and len(points) < 12:
            points.append(l[:300])

    outline = {
        'headlines': [title] if title else [],
        'points': points,
        'queries': [f"{title} background", f"{title} criticism", f"{title} examples"]
    }

    write_json(args.output, outline)
    print('Wrote', args.output)
