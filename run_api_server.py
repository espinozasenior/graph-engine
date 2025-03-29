#!/usr/bin/env python3
"""
API Server Runner

This script runs the FastAPI server that exposes the dependency graph API.
It can be run alongside the graph manager to provide HTTP access to the graph data.
"""

import os
import sys
import argparse
import logging
import threading
import time
import uvicorn

from graph_core.storage.in_memory_graph import InMemoryGraphStorage
from graph_core.manager import DependencyGraphManager
from graph_core.watchers.file_watcher import start_file_watcher
from graph_core.api import create_app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run the Graph Engine API server.'
    )
    parser.add_argument(
        '--host', default='127.0.0.1',
        help='Host to bind the server to. Default: 127.0.0.1'
    )
    parser.add_argument(
        '--port', type=int, default=8000,
        help='Port to bind the server to. Default: 8000'
    )
    parser.add_argument(
        '--watch-dir', '-w', default='src',
        help='Directory to watch for file changes. Default: src/'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose logging'
    )
    return parser.parse_args()


def start_watcher(manager, watch_dir):
    """Start the file watcher in a separate thread."""
    logger.info(f"Starting file watcher on directory: {watch_dir}")
    
    try:
        # Process existing files first
        for root, _, files in os.walk(watch_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    logger.debug(f"Processing existing file: {filepath}")
                    manager.on_file_event('created', filepath)
        
        # Start watching for changes
        start_file_watcher(
            callback=manager.on_file_event,
            watch_dir=watch_dir
        )
    except Exception as e:
        logger.exception(f"Error in file watcher: {str(e)}")


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
        
        # Start the file watcher in a separate thread
        watcher_thread = threading.Thread(
            target=start_watcher,
            args=(manager, args.watch_dir),
            daemon=True  # Make thread exit when main thread exits
        )
        watcher_thread.start()
        
        # Create the FastAPI app
        logger.info("Creating FastAPI application...")
        app = create_app(manager)
        
        # Run the API server
        logger.info(f"Starting API server at http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.exception(f"Error running API server: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main()) 