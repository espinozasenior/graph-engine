"""
Dependency Graph Manager Module

This module provides a manager for handling file events and keeping
the dependency graph updated accordingly.
"""

import os
import logging
import threading
import time
from typing import List, Optional, Dict, Any, Callable

from graph_core.analyzer import get_parser_for_file
from graph_core.storage.in_memory_graph import InMemoryGraphStorage
from graph_core.dynamic.import_hook import initialize_hook, get_function_calls, FunctionCallEvent

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
        
        # Python instrumentation
        self.instrumentation_active = False
        self.instrumentation_thread = None
        self.instrumentation_watch_dir = None
        self.instrumentation_poll_interval = 0.5  # Default polling interval in seconds
    
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
            source_node = self.storage.get_node(source_id)
            target_node = self.storage.get_node(target_id)
            
            # Create or update edge
            if source_node and target_node:
                # Try to find the existing edge
                edges = self.storage.get_all_edges()
                edge = None
                
                for e in edges:
                    if e.get('source') == source_id and e.get('target') == target_id:
                        edge = e
                        break
                
                if edge:
                    # Update existing edge
                    if 'dynamic_call_count' in edge:
                        edge['dynamic_call_count'] += 1
                    else:
                        edge['dynamic_call_count'] = 1
                    edge['dynamic'] = True
                else:
                    # Create new edge
                    edge = {
                        'source': source_id,
                        'target': target_id,
                        'type': 'calls',
                        'dynamic': True,
                        'dynamic_call_count': 1
                    }
                
                # Add or update the edge in storage
                self.storage.graph.add_edge(source_id, target_id, **{k: v for k, v in edge.items() 
                                                                  if k not in ['source', 'target']})
                logger.debug(f"Added/updated dynamic call edge: {source_id} -> {target_id} (count: {edge.get('dynamic_call_count', 1)})")
        
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
        node = self.storage.get_node(function_id)
        if node:
            # Update dynamic call count attribute
            if 'dynamic_call_count' in node:
                node['dynamic_call_count'] += increment
            else:
                node['dynamic_call_count'] = increment
            
            # Update the node in storage
            attrs = {k: v for k, v in node.items() if k != 'id'}
            self.storage.graph.add_node(function_id, **attrs)
            logger.debug(f"Updated call count for {function_id}: {node['dynamic_call_count']}")
    
    def start_python_instrumentation(self, watch_dir: str = 'src', poll_interval: float = 0.5) -> None:
        """
        Start Python instrumentation using the import hook.
        
        This method initializes the import hook to track function calls in Python modules
        and starts a background thread to process function call events.
        
        Args:
            watch_dir: Directory to monitor for Python files (default: 'src')
            poll_interval: How frequently to check for new events in seconds (default: 0.5)
        """
        if self.instrumentation_active:
            logger.warning("Python instrumentation is already active")
            return
        
        # Store the watch directory and poll interval
        self.instrumentation_watch_dir = os.path.abspath(watch_dir)
        self.instrumentation_poll_interval = poll_interval
        
        # Initialize the import hook
        logger.info(f"Initializing Python instrumentation for directory: {self.instrumentation_watch_dir}")
        initialize_hook(self.instrumentation_watch_dir)
        
        # Start the event processing thread
        self.instrumentation_active = True
        self.instrumentation_thread = threading.Thread(
            target=self._process_function_call_events,
            daemon=True
        )
        self.instrumentation_thread.start()
        
        logger.info("Python instrumentation started")
    
    def stop_python_instrumentation(self) -> None:
        """
        Stop Python instrumentation.
        
        This method stops the background thread processing function call events.
        Note: This does not remove the import hook from sys.meta_path - it just stops collecting events.
        """
        if not self.instrumentation_active:
            logger.warning("Python instrumentation is not active")
            return
        
        # Stop the event processing thread
        self.instrumentation_active = False
        if self.instrumentation_thread and self.instrumentation_thread.is_alive():
            self.instrumentation_thread.join(timeout=2.0)
        
        logger.info("Python instrumentation stopped")
    
    def _process_function_call_events(self) -> None:
        """
        Process function call events from the import hook queue.
        
        This method runs in a background thread and periodically checks for new function call
        events, updating the graph with dynamic call information.
        """
        logger.debug("Function call event processing thread started")
        
        while self.instrumentation_active:
            try:
                # Get function call events
                events = get_function_calls()
                
                # Process each event if there are any
                if events:
                    logger.debug(f"Processing {len(events)} function call events")
                    for event in events:
                        self._process_function_call_event(event)
                
                # Sleep for the poll interval
                time.sleep(self.instrumentation_poll_interval)
            except Exception as e:
                logger.error(f"Error processing function call events: {str(e)}", exc_info=True)
        
        logger.debug("Function call event processing thread stopped")
    
    def _process_function_call_event(self, event: FunctionCallEvent) -> None:
        """
        Process a single function call event.
        
        Args:
            event: The function call event to process
        """
        try:
            logger.debug(f"Processing event: {event.module_name}.{event.function_name}")
            
            # Create a function ID from the event
            module_parts = event.module_name.split('.')
            func_parts = event.function_name.split('.')
            
            # Handle potential repetition in function name format (e.g., outer_function.outer_function)
            # The format from instrumentation is: parent.child.child where the last repetition is the actual function
            
            # Extract the actual function name (last part)
            func_name = func_parts[-1]
            function_id = f"function:{module_parts[-1]}.{func_name}"
            
            # Update function call count
            self.update_function_call_count(function_id)
            
            # If this is a nested function call (has a parent)
            if len(func_parts) > 1:
                # Extract parent function name - go back 2 steps if we have repeating names
                # e.g., for 'outer.inner.inner', parent is 'outer'
                parent_index = -2
                parent_name = func_parts[parent_index]
                
                # If parent name is the same as function name, go back one more step
                # This handles cases like 'outer.outer.inner.inner'
                if parent_name == func_name and len(func_parts) > 2:
                    parent_index -= 1
                    parent_name = func_parts[parent_index]
                
                parent_id = f"function:{module_parts[-1]}.{parent_name}"
                
                # Avoid self-references
                if parent_id != function_id:
                    # Process as a call event
                    logger.debug(f"Adding call edge: {parent_id} -> {function_id}")
                    self.process_dynamic_event('call', parent_id, function_id)
            
            logger.debug(f"Processed function call event: {event.module_name}.{event.function_name}")
        except Exception as e:
            logger.error(f"Error processing function call event {event}: {str(e)}", exc_info=True)
    
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