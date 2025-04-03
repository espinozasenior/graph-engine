"""
Dependency Graph Manager Module

This module provides a manager for handling file events and keeping
the dependency graph updated accordingly.
"""

import os
import logging
import threading
import time
from typing import List, Optional, Dict, Any, Callable, Set, Tuple, Union, Literal
from collections import deque

from graph_core.analyzer import get_parser_for_file
from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.storage.json_storage import JSONGraphStorage
from graph_core.dynamic.import_hook import initialize_hook, get_function_calls, FunctionCallEvent
from graph_core.watchers.rename_detection import detect_renames, RenameEvent, match_functions

# Set up logging
logger = logging.getLogger(__name__)

# Default JSON file path
DEFAULT_JSON_PATH = os.path.join("data", "graph_data.json")


class DependencyGraphManager:
    """
    Manages a dependency graph by handling file events and keeping the graph updated.
    
    This class serves as the coordinator between file watchers, parsers, and storage.
    It reacts to file system events, parses code files, and updates the graph accordingly.
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = ['.py', '.js', '.ts', '.tsx']
    
    # How long (in seconds) to keep track of deleted files for rename detection
    RENAME_DETECTION_WINDOW = 2.0
    
    def __init__(self, 
                 storage: Optional[Union[InMemoryGraphStorage, JSONGraphStorage]] = None,
                 storage_type: Literal["memory", "json"] = "memory",
                 json_path: str = DEFAULT_JSON_PATH):
        """
        Initialize the dependency graph manager.
        
        Args:
            storage: An instance of InMemoryGraphStorage or JSONGraphStorage to store the graph data.
                If not provided, a new storage instance will be created based on storage_type.
            storage_type: The type of storage to use if storage is not provided.
                "memory" for in-memory storage, "json" for JSON file storage.
            json_path: Path to the JSON file when using JSONGraphStorage.
                Only used if storage_type is "json" and storage is not provided.
        """
        # Create the storage if not provided
        if storage is None:
            if storage_type == "json":
                # Ensure the directory exists
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                storage = JSONGraphStorage(json_path)
                logger.info(f"Created JSONGraphStorage with path: {json_path}")
            else:
                storage = InMemoryGraphStorage()
                logger.info("Created InMemoryGraphStorage")
        else:
            if isinstance(storage, JSONGraphStorage):
                logger.info(f"Using provided JSONGraphStorage with path: {storage.json_path}")
            else:
                logger.info("Using provided InMemoryGraphStorage")
                
        self.storage = storage
        self.is_json_storage = isinstance(storage, JSONGraphStorage)
        
        # Dynamic analysis event handlers
        self.dynamic_event_handlers = []
        
        # Python instrumentation
        self.instrumentation_active = False
        self.instrumentation_thread = None
        self.instrumentation_watch_dir = None
        self.instrumentation_poll_interval = 0.5  # Default polling interval in seconds
        self.exclude_patterns = None
        self.include_patterns = None
        self.cache_dir = None
        
        # Buffers for tracking potential file renames
        # Each entry is (timestamp, filepath)
        self.deleted_files = deque(maxlen=100)
        self.created_files = deque(maxlen=100)
        
        # Keep track of renamed files for history
        self.rename_history = {}  # Maps new_path -> old_path
    
    @classmethod
    def create_with_json_storage(cls, json_path: str = DEFAULT_JSON_PATH) -> 'DependencyGraphManager':
        """
        Create a DependencyGraphManager with JSONGraphStorage.
        
        Args:
            json_path: Path to the JSON file for storage
            
        Returns:
            A new DependencyGraphManager instance with JSONGraphStorage
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        storage = JSONGraphStorage(json_path)
        return cls(storage=storage)
    
    @classmethod
    def create_with_memory_storage(cls) -> 'DependencyGraphManager':
        """
        Create a DependencyGraphManager with InMemoryGraphStorage.
        
        Returns:
            A new DependencyGraphManager instance with InMemoryGraphStorage
        """
        storage = InMemoryGraphStorage()
        return cls(storage=storage)
        
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
    
    def process_dynamic_event(self, event_type: str, source_id: str, target_id: str = None) -> bool:
        """
        Process a dynamic event such as a function call or import.
        
        Args:
            event_type: Type of the event ('call', 'import')
            source_id: ID of the source node
            target_id: ID of the target node (optional)
            
        Returns:
            bool: True if the event was processed successfully, False otherwise
        """
        try:
            success = False
            
            if event_type == 'call':
                if target_id is None:
                    logger.warning(f"Target ID is required for 'call' events")
                    return False
                    
                # Get the source and target nodes
                source_node = self.storage.get_node(source_id)
                target_node = self.storage.get_node(target_id)
                
                if source_node is None or target_node is None:
                    logger.warning(f"Source node {source_id} or target node {target_id} not found")
                    return False
                
                # Check if an edge already exists
                existing_edges = self.storage.get_edges_for_nodes([source_id])
                existing_edge = None
                
                for edge in existing_edges:
                    if (edge['source'] == source_id and 
                        edge['target'] == target_id and 
                        edge['type'] == 'calls'):
                        existing_edge = edge
                        break
                
                # Update the existing edge or add a new one
                current_time = time.time()
                
                if existing_edge:
                    # Update the existing edge
                    edge_id = existing_edge['id']
                    
                    # Increment the call count
                    call_count = existing_edge.get('dynamic_call_count', 0) + 1
                    
                    # Update the edge with networkx
                    self.storage.graph[source_id][target_id]['dynamic_call_count'] = call_count
                    self.storage.graph[source_id][target_id]['dynamic'] = True
                    self.storage.graph[source_id][target_id]['last_call_time'] = current_time
                    
                    logger.debug(f"Updated dynamic edge: {source_id} -> {target_id}, calls: {call_count}")
                else:
                    # Add a new edge
                    edge_data = {
                        'id': f"edge:{source_id}:{target_id}:calls",
                        'source': source_id,
                        'target': target_id,
                        'type': 'calls',
                        'dynamic': True,
                        'dynamic_call_count': 1,
                        'first_call_time': current_time,
                        'last_call_time': current_time
                    }
                    
                    # Add the edge to the graph
                    self.storage.graph.add_edge(
                        source_id, 
                        target_id, 
                        **edge_data
                    )
                    
                    logger.debug(f"Added dynamic edge: {source_id} -> {target_id}")
                
                # Save graph if using JSON storage
                if self.is_json_storage:
                    self.storage.save_graph()
                    logger.debug(f"Graph saved to JSON after dynamic call event: {source_id} -> {target_id}")
                
                success = True
                
            elif event_type == 'import':
                # TODO: Implement import tracking
                logger.warning(f"Import tracking not yet implemented")
                success = False
                
            else:
                logger.warning(f"Unknown dynamic event type: {event_type}")
                success = False
            
            # Notify all registered event handlers
            for handler in self.dynamic_event_handlers:
                try:
                    handler(event_type, source_id, target_id)
                except Exception as e:
                    logger.error(f"Error in dynamic event handler {handler.__name__}: {str(e)}")
                    
            return success
                
        except Exception as e:
            logger.error(f"Error processing dynamic event: {str(e)}")
            return False
    
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
            
            # Save the graph if using JSONGraphStorage
            if self.is_json_storage:
                self.storage.save_graph()
    
    def detect_renames(self) -> List[RenameEvent]:
        """
        Detect if any recently deleted files have been renamed to match recently created files.
        
        This method checks for renames by comparing the similarity of files that were recently
        deleted and created within the RENAME_DETECTION_WINDOW timeframe.
        
        Returns:
            A list of RenameEvent objects representing detected renames
        """
        current_time = time.time()
        
        # Get recently deleted files that are still within the window
        recent_deleted = [
            filepath for timestamp, filepath in self.deleted_files
            if current_time - timestamp <= self.RENAME_DETECTION_WINDOW
        ]
        
        # Get recently created files that are still within the window
        recent_created = [
            filepath for timestamp, filepath in self.created_files
            if current_time - timestamp <= self.RENAME_DETECTION_WINDOW
        ]
        
        # If we have both deleted and created files, check for renames
        if recent_deleted and recent_created:
            logger.debug(f"Checking for renames among {len(recent_deleted)} deleted and {len(recent_created)} created files")
            
            # Use the rename detection module to detect renames
            rename_events = detect_renames(recent_deleted, recent_created)
            
            if rename_events:
                logger.info(f"Detected {len(rename_events)} file rename(s)")
                
                # Remove the files involved in renames from the buffers
                for event in rename_events:
                    # Update rename history
                    self.rename_history[event.new_path] = event.old_path
                    
                    # Filter out the renamed files from our buffers
                    self.deleted_files = deque(
                        [(ts, path) for ts, path in self.deleted_files if path != event.old_path],
                        maxlen=100
                    )
                    self.created_files = deque(
                        [(ts, path) for ts, path in self.created_files if path != event.new_path],
                        maxlen=100
                    )
            
            return rename_events
        
        return []
    
    def start_python_instrumentation(
        self, 
        watch_dir: str = 'src', 
        poll_interval: float = 0.5,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        cache_dir: Optional[str] = None
    ) -> None:
        """
        Start Python instrumentation using the import hook.
        
        This method initializes the import hook to track function calls in Python modules
        and starts a background thread to process function call events.
        
        Args:
            watch_dir: Directory to monitor for Python files (default: 'src')
            poll_interval: How frequently to check for new events in seconds (default: 0.5)
            exclude_patterns: List of regex patterns for modules to exclude from instrumentation
            include_patterns: List of regex patterns for modules to include in instrumentation
            cache_dir: Directory to store cached transformations (default: ~/.instrumentation_cache)
        """
        if self.instrumentation_active:
            logger.warning("Python instrumentation is already active")
            return
        
        # Store the watch directory and poll interval
        self.instrumentation_watch_dir = os.path.abspath(watch_dir)
        self.instrumentation_poll_interval = poll_interval
        
        # Initialize the import hook
        logger.info(f"Initializing Python instrumentation for directory: {self.instrumentation_watch_dir}")
        
        # Store these in case we need to restart the instrumentation
        self.exclude_patterns = exclude_patterns
        self.include_patterns = include_patterns
        self.cache_dir = cache_dir
        
        initialize_hook(
            self.instrumentation_watch_dir,
            exclude_patterns=exclude_patterns,
            include_patterns=include_patterns,
            cache_dir=cache_dir
        )
        
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
    
    def update_node_filepath(self, old_path: str, new_path: str) -> bool:
        """
        Update the filepath property of all nodes associated with the old path.
        
        This is used when a file has been renamed, to preserve node continuity
        rather than deleting and recreating nodes.
        
        Args:
            old_path: The original filepath
            new_path: The new filepath after rename
            
        Returns:
            True if any nodes were updated, False otherwise
        """
        # Find all nodes associated with the old filepath
        if old_path not in self.storage.file_nodes:
            logger.warning(f"No nodes found for file {old_path}")
            return False
        
        # Update the filepath for each node
        updated = False
        for node_id in self.storage.file_nodes.get(old_path, set()):
            node = self.storage.get_node(node_id)
            if node:
                # Update filepath and add rename history
                node['filepath'] = new_path
                if 'rename_history' not in node:
                    node['rename_history'] = []
                node['rename_history'].append(old_path)
                
                # Update the node in storage
                attrs = {k: v for k, v in node.items() if k != 'id'}
                self.storage.graph.add_node(node_id, **attrs)
                updated = True
        
        # Update file_nodes tracking
        if old_path in self.storage.file_nodes:
            nodes = self.storage.file_nodes[old_path]
            self.storage.file_nodes[new_path] = nodes
            del self.storage.file_nodes[old_path]
        
        # Record the rename in the history
        if updated:
            self.rename_history[new_path] = old_path
            logger.info(f"Updated filepath for nodes from {old_path} to {new_path}")
            
            # Save the graph if using JSONGraphStorage
            if self.is_json_storage:
                self.storage.save_graph()
        
        return updated
    
    def update_function_names(self, old_ast: Dict[str, List[Dict[str, Any]]], new_ast: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """
        Update node names for functions that have been renamed but have similar bodies.
        
        Args:
            old_ast: The AST nodes and edges from the old version of the file
            new_ast: The AST nodes and edges from the new version of the file
            
        Returns:
            A dictionary mapping old function IDs to new function IDs of renamed functions
            
        Note:
            This method modifies the storage directly, updating node names instead of 
            removing and recreating nodes when a function is renamed.
        """
        try:
            # Match functions between old and new ASTs
            function_matches = match_functions(old_ast, new_ast)
            
            if not function_matches:
                return {}
            
            logger.info(f"Detected {len(function_matches)} renamed functions")
            
            # Track which functions were successfully updated
            updated_functions = {}
            
            # Process each matched function
            for old_id, new_id in function_matches.items():
                # Get the nodes from old and new ASTs
                old_func = next((node for node in old_ast.get('nodes', []) if node.get('id') == old_id), None)
                new_func = next((node for node in new_ast.get('nodes', []) if node.get('id') == new_id), None)
                
                if not old_func or not new_func:
                    continue
                
                # Get the old node from storage
                node = self.storage.get_node(old_id)
                if not node:
                    continue
                
                old_name = node.get('name', '')
                new_name = new_func.get('name', '')
                
                # Update the node's name and other relevant properties
                node['name'] = new_name
                
                # Create a rename history if it doesn't exist
                if 'rename_history' not in node:
                    node['rename_history'] = []
                
                # Add the old name to the rename history
                node['rename_history'].append(old_name)
                
                # Update any other properties that might have changed
                for key in ['parameters', 'body', 'start_point', 'end_point']:
                    if key in new_func:
                        node[key] = new_func[key]
                
                # Update the node in storage
                attrs = {k: v for k, v in node.items() if k != 'id'}
                self.storage.graph.add_node(old_id, **attrs)
                
                # Record the update
                updated_functions[old_id] = new_id
                logger.info(f"Updated function name: {old_name} -> {new_name} (id: {old_id})")
            
            # Save the graph if using JSONGraphStorage and there were updates
            if updated_functions and self.is_json_storage:
                self.storage.save_graph()
                
            return updated_functions
            
        except Exception as e:
            logger.error(f"Error updating function names: {str(e)}", exc_info=True)
            return {}
    
    def _handle_file_created(self, filepath: str) -> None:
        """
        Handle 'created' file event.
        
        Args:
            filepath: Path to the file that was created
        """
        # Get file extension
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        
        # Only process supported file types
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"Ignoring unsupported file type: {filepath}")
            return
            
        # Add to created files buffer for rename detection
        self.created_files.append((time.time(), filepath))
        
        # Check for renames
        rename_events = self.detect_renames()
        
        # If this file was part of a rename, update the nodes instead of creating new ones
        renamed = False
        for event in rename_events:
            if event.new_path == filepath:
                # Update the filepath for all nodes from the old file
                renamed = self.update_node_filepath(event.old_path, filepath)
                break
        
        # If not a rename, process as a new file
        if not renamed:
            # Get the appropriate parser
            parser = get_parser_for_file(filepath)
            if parser is None:
                logger.warning(f"No parser available for {filepath}")
                return
            
            # Parse the file
            parse_result = parser.parse_file(filepath)
            
            # Update the storage
            self.storage.add_or_update_file(filepath, parse_result)
            logger.info(f"Updated graph for created file: {filepath}")
    
    def _handle_file_modified(self, filepath: str) -> None:
        """
        Handle 'modified' file event.
        
        Args:
            filepath: Path to the file that was modified
        """
        # Get file extension
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        
        # Only process supported file types
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"Ignoring unsupported file type: {filepath}")
            return
            
        # Get the appropriate parser
        parser = get_parser_for_file(filepath)
        if parser is None:
            logger.warning(f"No parser available for {filepath}")
            return
        
        # Parse the file
        new_ast = parser.parse_file(filepath)
        
        # Get the original AST for this file
        old_ast = {
            'nodes': [],
            'edges': []
        }
        
        if filepath in self.storage.file_nodes:
            # Build the old AST from the storage
            old_node_ids = self.storage.file_nodes.get(filepath, set())
            old_nodes = [self.storage.get_node(node_id) for node_id in old_node_ids]
            old_ast['nodes'] = [node for node in old_nodes if node]
            
            # Get edges connected to these nodes
            old_edges = self.storage.get_edges_for_nodes(old_node_ids)
            old_ast['edges'] = old_edges
            
            # Check for renamed functions
            renamed_functions = self.update_function_names(old_ast, new_ast)
            
            # Remove renamed functions from the new AST to avoid duplicates
            if renamed_functions:
                # Create a lookup set of new_ids that correspond to renamed functions
                renamed_new_ids = set(renamed_functions.values())
                
                # Filter out these nodes from the new AST
                new_ast['nodes'] = [
                    node for node in new_ast['nodes'] 
                    if node.get('id') not in renamed_new_ids
                ]
        
        # Update the storage with the new AST
        self.storage.add_or_update_file(filepath, new_ast)
        logger.info(f"Updated graph for modified file: {filepath}")
    
    def _handle_file_deleted(self, filepath: str) -> None:
        """
        Handle 'deleted' file event.
        
        Args:
            filepath: Path to the file that was deleted
        """
        # Get file extension
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        
        # Only process supported file types
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"Ignoring unsupported file type: {filepath}")
            return
            
        # Add to deleted files buffer for rename detection
        self.deleted_files.append((time.time(), filepath))
        
        # Check for renames
        rename_events = self.detect_renames()
        
        # If this file was not part of a rename, remove it from storage
        renamed = False
        for event in rename_events:
            if event.old_path == filepath:
                renamed = True
                break
        
        if not renamed:
            # Remove the file from storage
            self.storage.remove_file(filepath)
            logger.info(f"Removed file from graph: {filepath}")
    
    def on_file_event(self, event_type: str, filepath: str) -> None:
        """
        Handle file events from the file system watcher.
        
        Args:
            event_type: The type of event ('created', 'modified', 'deleted')
            filepath: The path to the file that triggered the event
        """
        try:
            if event_type == 'created':
                self._handle_file_created(filepath)
            elif event_type == 'modified':
                self._handle_file_modified(filepath)
            elif event_type == 'deleted':
                self._handle_file_deleted(filepath)
            elif event_type == 'renamed':
                # Extract old and new paths from the rename event
                old_path, new_path = filepath
                self.update_node_filepath(old_path, new_path)
            else:
                logging.warning(f"Unknown event type: {event_type} for file {filepath}")
                
            # Save graph if using JSON storage
            if self.is_json_storage:
                self.storage.save_graph()
                logging.debug(f"Graph saved to JSON after {event_type} event for {filepath}")
                
        except Exception as e:
            logging.error(f"Error handling {event_type} event for {filepath}: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
    
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
    
    def clear_instrumentation_cache(self) -> None:
        """
        Clear the instrumentation cache.
        
        This removes all cached transformed code, which will force
        re-instrumentation of modules on next import.
        """
        from graph_core.dynamic.import_hook import clear_transformation_cache
        clear_transformation_cache(self.cache_dir)
        logger.info("Instrumentation cache cleared")
    
    def migrate_to_json_storage(self, json_path: str = DEFAULT_JSON_PATH) -> bool:
        """
        Migrate the current in-memory storage to JSON storage.
        
        Args:
            json_path: Path to save the JSON file to
            
        Returns:
            bool: True if migration was successful, False otherwise
            
        Raises:
            ValueError: If the current storage is already JSON storage
        """
        if self.is_json_storage:
            raise ValueError("Cannot migrate: already using JSON storage")
            
        try:
            # Create a directory for the JSON file if it doesn't exist
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # Create a new JSON storage
            json_storage = JSONGraphStorage(json_path)
            
            # Get all nodes and edges from current storage
            all_nodes = self.storage.get_all_nodes()
            all_edges = self.storage.get_all_edges()
            
            # Add all nodes to the new storage
            for node in all_nodes:
                # Ensure any attributes that might be sets are converted to lists
                for key, value in node.items():
                    if isinstance(value, set):
                        node[key] = list(value)
                json_storage.graph.add_node(node['id'], **{k: v for k, v in node.items() if k != 'id'})
            
            # Add all edges to the new storage
            for edge in all_edges:
                # Ensure any attributes that might be sets are converted to lists
                for key, value in edge.items():
                    if isinstance(value, set):
                        edge[key] = list(value)
                json_storage.graph.add_edge(
                    edge['source'], 
                    edge['target'], 
                    key=edge.get('type', 'default'),  # Add a key parameter for edge type
                    **{k: v for k, v in edge.items() if k not in ['source', 'target', 'type']}
                )
            
            # Copy file_nodes mapping using lists instead of sets
            json_storage.file_nodes = {}
            for filepath, node_ids in self.storage.file_nodes.items():
                json_storage.file_nodes[filepath] = list(node_ids)
            
            # Save the graph data to disk
            json_storage.save_graph()
            
            # Replace the current storage with the new JSON storage
            self.storage = json_storage
            self.is_json_storage = True
            
            logger.info(f"Successfully migrated from in-memory storage to JSON storage at {json_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate to JSON storage: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False 