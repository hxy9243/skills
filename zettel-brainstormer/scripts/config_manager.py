#!/usr/bin/env python3
import json
import sys
from pathlib import Path

CONFIG_FILE = Path(__file__).parent.parent / "config" / "models.json"
EXAMPLE_CONFIG = Path(__file__).parent.parent / "config" / "models.example.json"

class ConfigManager:
    @staticmethod
    def load():
        if not CONFIG_FILE.exists():
            print(f"Error: Configuration file not found at {CONFIG_FILE}")
            print("Please run 'python scripts/setup.py' to configure the skill.")
            sys.exit(1)

        try:
            return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in configuration file at {CONFIG_FILE}")
            sys.exit(1)

    @staticmethod
    def save(config):
        # Ensure config directory exists
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding='utf-8')
        print(f"Configuration saved to {CONFIG_FILE}")

    @staticmethod
    def load_defaults():
        if EXAMPLE_CONFIG.exists():
            return json.loads(EXAMPLE_CONFIG.read_text(encoding='utf-8'))
        return {
            "pro_model": "openai/gpt-5.2",
            "preprocess_model": "openrouter/x-ai/kimi-k2.5",
            "zettel_dir": "~/Documents/Obsidian/Zettelkasten",
            "output_dir": "~/Documents/Obsidian/Inbox"
        }
