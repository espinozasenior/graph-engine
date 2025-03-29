#!/usr/bin/env python3
"""
Graph Manager Runner

This script integrates the file watcher with the dependency graph manager
to build and maintain a code dependency graph.
"""

import os
import sys
import argparse
import logging
from typing import Optional

from graph_core.storage.in_memory_graph import InMemoryGraphStorage
from graph_core.manager import DependencyGraphManager
from graph_core.watchers.file_watcher import start_file_watcher, stop_file_watcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run the dependency graph manager with file watching.'
    )
    parser.add_argument(
        '--watch-dir', '-w',
        default='src',
        help='Directory to watch for file changes. Default: src/'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if watch directory exists
    if not os.path.isdir(args.watch_dir):
        logger.error(f"Watch directory does not exist: {args.watch_dir}")
        return 1
    
    try:
        # Create the graph storage
        logger.info("Initializing graph storage...")
        storage = InMemoryGraphStorage()
        
        # Create the graph manager
        logger.info("Creating dependency graph manager...")
        manager = DependencyGraphManager(storage)
        
        # Process existing files
        logger.info(f"Processing existing files in {args.watch_dir}...")
        for root, _, files in os.walk(args.watch_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    logger.debug(f"Processing existing file: {filepath}")
                    manager.on_file_event('created', filepath)
        
        # Start the file watcher
        logger.info(f"Starting file watcher on directory: {args.watch_dir}")
        print(f"Watching directory: {args.watch_dir}")
        print("Press Ctrl+C to stop...")
        
        # Wire the watcher callback to the manager's on_file_event method
        start_file_watcher(
            callback=manager.on_file_event,
            watch_dir=args.watch_dir
        )
        
        # Main loop - the watcher will call the callback when files change
        # Since start_file_watcher is blocking, we won't reach here until it's stopped
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        stop_file_watcher()
    except Exception as e:
        logger.exception(f"Error running graph manager: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main()) 