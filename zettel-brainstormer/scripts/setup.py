#!/usr/bin/env python3
import json
import os
from pathlib import Path
from config_manager import ConfigManager

def get_input(prompt, default):
    response = input(f"{prompt} [{default}]: ").strip()
    return response if response else default

def main():
    print("🧠 Zettel Brainstormer Setup 🧠")
    print("--------------------------------")

    defaults = ConfigManager.load_defaults()
    config = {}

    # Models
    print("\n--- Model Configuration ---")
    config['pro_model'] = get_input(
        "Pro Model (for drafting)",
        defaults.get('pro_model', 'openai/gpt-5.2')
    )
    config['preprocess_model'] = get_input(
        "Preprocess Model (cheap/fast)",
        defaults.get('preprocess_model', 'openrouter/x-ai/kimi-k2.5')
    )

    # Directories
    print("\n--- Directory Configuration ---")
    # Expand user path for default display if it starts with ~
    default_zettel = defaults.get('zettel_dir', '~/Documents/Obsidian/Zettelkasten')
    config['zettel_dir'] = get_input(
        "Zettelkasten Directory",
        default_zettel
    )

    default_output = defaults.get('output_dir', '~/Documents/Obsidian/Inbox')
    config['output_dir'] = get_input(
        "Output/Inbox Directory",
        default_output
    )

    # Save
    print("\nSaving configuration...")
    ConfigManager.save(config)
    print("Setup complete! You can now use the skill.")

if __name__ == "__main__":
    main()
