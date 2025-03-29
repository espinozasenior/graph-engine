"""
Dependency Graph Manager Module

This module provides a manager for handling file events and keeping
the dependency graph updated accordingly.
"""

import os
import logging
from typing import Optional

from graph_core.analyzer import get_parser_for_file
from graph_core.storage.in_memory_graph import InMemoryGraphStorage

# Set up logging
logger = logging.getLogger(__name__)


class DependencyGraphManager:
    """
    Manages a dependency graph by handling file events and keeping the graph updated.
    
    This class serves as the coordinator between file watchers, parsers, and storage.
    It reacts to file system events, parses code files, and updates the graph accordingly.
    """
    
    def __init__(self, storage: InMemoryGraphStorage):
        """
        Initialize the dependency graph manager.
        
        Args:
            storage: An instance of InMemoryGraphStorage to store the graph data
        """
        self.storage = storage
    
    def on_file_event(self, event_type: str, filepath: str) -> None:
        """
        Handle a file event by updating the graph accordingly.
        
        Args:
            event_type: Type of the event, one of 'created', 'modified', or 'deleted'
            filepath: Path to the file that triggered the event
            
        Raises:
            ValueError: If the event_type is not one of 'created', 'modified', or 'deleted'
        """
        if event_type not in ('created', 'modified', 'deleted'):
            raise ValueError(f"Invalid event type: {event_type}")
        
        # Get file extension
        _, ext = os.path.splitext(filepath)
        
        # Only process Python files
        if ext.lower() != '.py':
            logger.debug(f"Ignoring non-Python file: {filepath}")
            return
        
        try:
            if event_type in ('created', 'modified'):
                # Get the appropriate parser
                parser = get_parser_for_file(filepath)
                if parser is None:
                    logger.warning(f"No parser available for {filepath}")
                    return
                
                # Parse the file
                parse_result = parser.parse_file(filepath)
                
                # Update the storage
                self.storage.add_or_update_file(filepath, parse_result)
                logger.info(f"Updated graph for {event_type} file: {filepath}")
            
            elif event_type == 'deleted':
                # Remove the file from storage
                self.storage.remove_file(filepath)
                logger.info(f"Removed file from graph: {filepath}")
        
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
        except PermissionError:
            logger.error(f"Permission denied when accessing file: {filepath}")
        except Exception as e:
            logger.error(f"Error processing file event for {filepath}: {str(e)}")
            raise 