"""
Simple script to create dummy Tree-sitter language files for testing.
"""
import os
from pathlib import Path

# Create the language directory
lang_dir = Path("graph_core/analyzer/treesitter_parser/languages")
lang_dir.mkdir(parents=True, exist_ok=True)

# Create dummy files for all supported languages
languages = ["python", "javascript", "typescript"]

for lang in languages:
    output_file = lang_dir / f"{lang}.so"
    with open(output_file, "wb") as f:
        f.write(b"DUMMY")
    print(f"Created dummy file: {output_file}")

print("Successfully created all dummy language files.")
print("Note: These files are placeholders and will only allow basic functionality.") 