"""
Dependency Graph Manager Module

This module provides a manager for handling file events and keeping
the dependency graph updated accordingly.
"""

import os
import logging
from typing import List, Optional, Dict, Any

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
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.py', '.js', '.ts', '.tsx']
    
    def __init__(self, storage: InMemoryGraphStorage):
        """
        Initialize the dependency graph manager.
        
        Args:
            storage: An instance of InMemoryGraphStorage to store the graph data
        """
        self.storage = storage
        # Dynamic analysis event handlers
        self.dynamic_event_handlers = []
    
    def register_dynamic_handler(self, handler_func):
        """
        Register a dynamic analysis event handler.
        
        The handler function should accept three parameters:
        - event_type: The type of event ('call', 'import', etc.)
        - source_id: The ID of the source node
        - target_id: The ID of the target node (if applicable)
        
        Args:
            handler_func: Function to call when a dynamic event occurs
        """
        self.dynamic_event_handlers.append(handler_func)
        logger.info(f"Registered dynamic event handler: {handler_func.__name__}")
    
    def process_dynamic_event(self, event_type: str, source_id: str, target_id: Optional[str] = None) -> None:
        """
        Process a dynamic event by updating the graph and notifying handlers.
        
        Args:
            event_type: Type of the event ('call', 'import', etc.)
            source_id: ID of the source node
            target_id: ID of the target node (optional)
        """
        # Update the graph based on the event type
        if event_type == 'call' and target_id is not None:
            # Check if the nodes exist
            source_nodes = self.storage.get_nodes_by_id(source_id)
            target_nodes = self.storage.get_nodes_by_id(target_id)
            
            # Create or update edge
            if source_nodes and target_nodes:
                edge = {
                    'source': source_id,
                    'target': target_id,
                    'type': 'calls',
                    'dynamic': True
                }
                self.storage.add_or_update_edge(edge)
                logger.debug(f"Added/updated dynamic call edge: {source_id} -> {target_id}")
        
        # Notify dynamic event handlers
        for handler in self.dynamic_event_handlers:
            try:
                handler(event_type, source_id, target_id)
            except Exception as e:
                logger.error(f"Error in dynamic event handler {handler.__name__}: {str(e)}")
    
    def update_function_call_count(self, function_id: str, increment: int = 1) -> None:
        """
        Update the call count for a function.
        
        Args:
            function_id: ID of the function node
            increment: Amount to increment the call count by
        """
        nodes = self.storage.get_nodes_by_id(function_id)
        if nodes:
            node = nodes[0]
            # Update dynamic call count attribute
            if 'dynamic_call_count' in node:
                node['dynamic_call_count'] += increment
            else:
                node['dynamic_call_count'] = increment
            
            # Update the node in storage
            self.storage.update_node(function_id, node)
            logger.debug(f"Updated call count for {function_id}: {node['dynamic_call_count']}")
    
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
        ext = ext.lower()
        
        # Only process supported file types
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"Ignoring unsupported file type: {filepath}")
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
    
    def process_existing_files(self, directory: str) -> int:
        """
        Process all existing supported files in a directory.
        
        Args:
            directory: Directory to process
            
        Returns:
            Number of files processed
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not os.path.isdir(directory):
            raise ValueError(f"Not a directory: {directory}")
        
        count = 0
        for root, _, files in os.walk(directory):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in self.SUPPORTED_EXTENSIONS:
                    filepath = os.path.join(root, file)
                    try:
                        self.on_file_event('created', filepath)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error processing file {filepath}: {str(e)}")
        
        logger.info(f"Processed {count} existing files in {directory}")
        return count 