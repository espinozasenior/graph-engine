"""
Demonstration of JSONGraphStorage usage.

This script shows how to use the JSONGraphStorage class to persist
a dependency graph to a JSON file.
"""

import logging
import os
import sys
from pathlib import Path

from graph_core import DependencyGraphManager, JSONGraphStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Main demonstration function.
    """
    # Set the JSON file path
    json_path = os.path.join(os.path.dirname(__file__), 'graph_data.json')
    logger.info(f"Using JSON storage at: {json_path}")
    
    # Create the JSONGraphStorage
    storage = JSONGraphStorage(json_path)
    
    # Create a manager instance with the JSON storage
    manager = DependencyGraphManager(storage)
    
    # Process existing files in the src directory
    watch_dir = "src"
    if os.path.exists(watch_dir):
        logger.info(f"Processing existing files in {watch_dir} directory...")
        count = manager.process_existing_files(watch_dir)
        logger.info(f"Processed {count} files in {watch_dir} directory")
    else:
        logger.warning(f"Directory {watch_dir} not found, skipping file processing")
    
    # Print some stats
    logger.info(f"Graph statistics:")
    logger.info(f"  Nodes: {storage.get_node_count()}")
    logger.info(f"  Edges: {storage.get_edge_count()}")
    logger.info(f"  Files: {len(storage.file_nodes)}")
    
    # Show where the JSON file was saved
    if os.path.exists(json_path):
        size_kb = os.path.getsize(json_path) / 1024
        logger.info(f"JSON file saved at: {json_path} ({size_kb:.2f} KB)")
    else:
        logger.warning(f"JSON file was not created at: {json_path}")

if __name__ == "__main__":
    main() 