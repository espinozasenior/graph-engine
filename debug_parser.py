#!/usr/bin/env python
"""
Debug script to check if the TreeSitterParser is correctly extracting nodes.
"""
import os
import sys
from pathlib import Path

# Import the TreeSitterParser
from graph_core.analyzer.treesitter_parser.tree_sitter_parser import TreeSitterParser
from graph_core.analyzer import get_parser_for_file

# Set up simple logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_parse_file(filepath):
    """Parse a file and print the results for debugging."""
    print(f"\n{'='*80}\nParsing file: {filepath}\n{'='*80}")
    
    try:
        # Get appropriate parser
        parser = get_parser_for_file(filepath)
        if not parser:
            print(f"No parser found for {filepath}")
            return
        
        # Parse the file
        result = parser.parse_file(filepath)
        
        # Print the results
        print(f"\nFound {len(result['nodes'])} nodes:")
        for i, node in enumerate(result['nodes']):
            print(f"{i+1}. {node['type']}: {node.get('name', 'unnamed')} (ID: {node['id']})")
            # Debug: print all node attributes
            for key, value in node.items():
                if key not in ['id', 'type', 'name']:
                    print(f"   - {key}: {value}")
        
        print(f"\nFound {len(result['edges'])} edges:")
        for i, edge in enumerate(result['edges']):
            print(f"{i+1}. {edge['source']} --[{edge.get('type', 'unknown')}]--> {edge['target']}")
    
    except Exception as e:
        print(f"Error parsing {filepath}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Parse sample files
    files_to_parse = [
        "src/sample.py",
        "src/sample.js",
        "src/sample.tsx",
        "src/nested_example.py"
    ]
    
    for file in files_to_parse:
        if os.path.exists(file):
            debug_parse_file(file)
        else:
            print(f"File not found: {file}") 