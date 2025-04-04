#!/usr/bin/env python
"""
Generate Graph Snapshot

This script creates a snapshot of the code dependency graph by processing
files in a specified directory and saving the result to a JSON file.

Usage:
    python generate_graph_snapshot.py --src-dir <source_directory> --output <output_file>

Example:
    python generate_graph_snapshot.py --src-dir src --output graph_snapshot.json
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, Any

from graph_core.manager import DependencyGraphManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def generate_snapshot(src_dir: str, output_file: str) -> Dict[str, Any]:
    """
    Generate a snapshot of the code dependency graph.
    
    Args:
        src_dir: Directory containing source files to process
        output_file: Path to save the JSON snapshot
        
    Returns:
        Dictionary containing the graph snapshot data
    """
    if not os.path.exists(src_dir):
        raise FileNotFoundError(f"Source directory not found: {src_dir}")
    
    if not os.path.isdir(src_dir):
        raise ValueError(f"Not a directory: {src_dir}")
    
    # Create a manager with in-memory storage
    logger.info(f"Creating dependency graph manager")
    manager = DependencyGraphManager()
    
    # Process existing files
    logger.info(f"Processing files in {src_dir}")
    file_count = manager.process_existing_files(src_dir)
    logger.info(f"Processed {file_count} files")
    
    # Get all nodes and edges
    logger.info("Extracting graph data")
    nodes = list(manager.storage.get_all_nodes())
    edges = list(manager.storage.get_all_edges())
    
    # Create the snapshot data
    snapshot = {
        'nodes': [dict(node) for node in nodes],
        'edges': [dict(edge) for edge in edges],
        'metadata': {
            'file_count': file_count,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }
    }
    
    # Write to output file
    logger.info(f"Writing snapshot to {output_file}")
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    logger.info(f"Snapshot complete: {len(nodes)} nodes, {len(edges)} edges")
    return snapshot

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate a snapshot of the code dependency graph')
    parser.add_argument('--src-dir', required=True, help='Source directory containing code files')
    parser.add_argument('--output', required=True, help='Output file path for the JSON snapshot')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        generate_snapshot(args.src_dir, args.output)
        return 0
    except Exception as e:
        logger.error(f"Error generating snapshot: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 