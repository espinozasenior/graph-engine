#!/usr/bin/env python
"""
Run the dependency graph manager with file watching and API server.

This script starts a file watcher to monitor a directory for file changes
and updates the dependency graph accordingly. It also starts a FastAPI server
to provide API access to the graph data.

Supported languages:
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts, .tsx)
"""

import os
import logging
import argparse
import threading
import time
from typing import Callable, Optional

import uvicorn
from graph_core import DependencyGraphManager, create_app
from graph_core.storage.in_memory_graph import InMemoryGraphStorage
from graph_core.watchers.file_watcher import start_file_watcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def start_watcher(callback: Callable[[str, str], None], watch_dir: str) -> threading.Thread:
    """
    Start the file watcher in a background thread.
    
    Args:
        callback: Function to call with event type and file path
        watch_dir: Directory to watch for changes
        
    Returns:
        The started watcher thread
        
    Raises:
        FileNotFoundError: If the watch_dir doesn't exist
    """
    if not os.path.exists(watch_dir):
        raise FileNotFoundError(f"Watch directory not found: {watch_dir}")
    
    # Create and start the watcher thread
    watcher_thread = threading.Thread(
        target=start_file_watcher,
        args=(callback, watch_dir),
        daemon=True  # Make thread exit when main thread exits
    )
    watcher_thread.start()
    logger.info(f"Started file watcher for {watch_dir}")
    
    return watcher_thread


def main() -> None:
    """Run the dependency graph manager with file watching and API server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the dependency graph manager with file watching and API server')
    parser.add_argument('--watch-dir', type=str, default='src', help='Directory to watch for file changes')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to run the API server on')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the API server on')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize the storage and manager
        storage = InMemoryGraphStorage()
        manager = DependencyGraphManager(storage)
        
        # Process existing files in the watch directory
        logger.info(f"Processing existing files in {args.watch_dir}...")
        num_files = manager.process_existing_files(args.watch_dir)
        logger.info(f"Processed {num_files} existing files")
        
        # Start the file watcher in a background thread
        watcher_thread = start_watcher(manager.on_file_event, args.watch_dir)
        
        # Create the FastAPI app
        app = create_app(manager)
        
        # Log available endpoints
        logger.info(f"API will be available at:")
        logger.info(f"  http://{args.host}:{args.port}/graph/nodes")
        logger.info(f"  http://{args.host}:{args.port}/graph/edges")
        
        # Run the API server
        # This will block until the server is stopped
        uvicorn.run(app, host=args.host, port=args.port)
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        logger.info("Shutdown complete")


if __name__ == '__main__':
    main() 