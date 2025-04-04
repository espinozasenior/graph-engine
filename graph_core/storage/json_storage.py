"""
JSON Graph Storage Module

This module provides a JSON file-based implementation of a graph storage system
for storing and manipulating code structure data.
"""

import os
import json
import logging
import networkx as nx
import threading
import time
import random
import hashlib
from typing import Dict, List, Any, Set, Optional

# Set up logging
logger = logging.getLogger(__name__)


class JSONGraphStorage:
    """
    A JSON file-based implementation of a graph storage system.
    
    This class provides methods to add, update, and remove nodes and edges
    representing code structures, with tracking of which nodes came from which files.
    Data is persisted to a JSON file on disk.
    """
    
    def __init__(self, json_path: str):
        """
        Initialize the JSON graph storage.
        
        Args:
            json_path: Path to the JSON file where the graph will be stored
        """
        self.json_path = json_path
        self.graph = nx.MultiDiGraph()
        self.file_nodes = {}  # Maps filepath to list of node IDs
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._lock_file = f"{json_path}.lock"  # Path to the lock file
        
        # Load existing graph if the file exists
        self.load_graph()
    
    def load_graph(self) -> None:
        """
        Load the graph from the JSON file.
        
        If the file doesn't exist, an empty graph is initialized.
        """
        with self._lock:
            # Reset the graph
            self.graph.clear()
            self.file_nodes = {}
            
            # If the file doesn't exist yet, don't try to load it
            if not os.path.exists(self.json_path):
                logger.info(f"JSON file {self.json_path} doesn't exist yet - using empty graph")
                return
            
            try:
                # Acquire a read lock to ensure we don't read a partially written file
                lock_acquired = self._acquire_file_lock()
                
                # Load the data from the JSON file
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load nodes
                for node_data in data.get('nodes', []):
                    node_id = node_data.pop('id')
                    self.graph.add_node(node_id, **node_data)
                
                # Load edges
                for edge_data in data.get('edges', []):
                    source = edge_data.pop('source')
                    target = edge_data.pop('target')
                    edge_type = edge_data.pop('type')
                    self.graph.add_edge(source, target, key=edge_type, **edge_data)
                
                # Load file node mappings (convert lists to sets for internal representation)
                file_nodes = data.get('file_nodes', {})
                for file_path, node_ids in file_nodes.items():
                    self.file_nodes[file_path] = set(node_ids)
                
                # Count loaded nodes and edges
                node_count = self.graph.number_of_nodes()
                edge_count = self.graph.number_of_edges()
                file_count = len(self.file_nodes)
                
                logger.info(f"Loaded graph from {self.json_path} - {node_count} nodes, {edge_count} edges, {file_count} files")
                
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {self.json_path}: {e}")
                # If JSON is invalid, start with an empty graph
                self.graph.clear()
                self.file_nodes = {}
            except (IOError, OSError) as e:
                logger.error(f"Error loading graph from {self.json_path}: {e}")
                # If file can't be read, start with an empty graph
                self.graph.clear()
                self.file_nodes = {}
            finally:
                # Always release the lock if we acquired it
                if lock_acquired:
                    self._release_file_lock()
    
    def _acquire_file_lock(self, max_attempts: int = 10, delay_base: float = 0.1) -> bool:
        """
        Acquire a lock on the file for writing.
        
        Uses a separate lock file with the process ID to ensure exclusive access.
        Implements exponential backoff with jitter for retries.
        
        Args:
            max_attempts: Maximum number of attempts to acquire the lock
            delay_base: Base delay between attempts (will be increased exponentially)
            
        Returns:
            True if lock was acquired, False otherwise
        """
        pid = os.getpid()
        temp_lock_file = f"{self._lock_file}.{pid}"
        
        for attempt in range(max_attempts):
            try:
                # Try to create a temporary lock file
                if not os.path.exists(os.path.dirname(temp_lock_file)):
                    os.makedirs(os.path.dirname(temp_lock_file), exist_ok=True)
                
                with open(temp_lock_file, 'w') as f:
                    f.write(str(pid))
                
                # Try to create a hard link to the actual lock file
                # This will fail if the lock file already exists
                try:
                    # Atomically create lock file if it doesn't exist
                    os.link(temp_lock_file, self._lock_file)
                    logger.debug(f"Acquired file lock: {self._lock_file}")
                    return True
                except FileExistsError:
                    # Lock file exists, check if it's stale (older than 60 seconds)
                    if os.path.exists(self._lock_file):
                        lock_age = time.time() - os.path.getmtime(self._lock_file)
                        if lock_age > 60:  # 60 seconds
                            logger.warning(f"Found stale lock file (age: {lock_age:.1f}s). Breaking lock.")
                            os.remove(self._lock_file)
                            continue  # Try again immediately
                
                # If we can't acquire the lock, wait with exponential backoff and jitter
                delay = delay_base * (2 ** attempt) * (0.5 + random.random())
                logger.debug(f"Failed to acquire lock, retry in {delay:.2f}s (attempt {attempt+1}/{max_attempts})")
                time.sleep(delay)
            
            finally:
                # Clean up the temporary lock file
                if os.path.exists(temp_lock_file):
                    os.remove(temp_lock_file)
        
        logger.error(f"Failed to acquire file lock after {max_attempts} attempts")
        return False
    
    def _release_file_lock(self) -> None:
        """Release the file lock."""
        try:
            if os.path.exists(self._lock_file):
                os.remove(self._lock_file)
                logger.debug(f"Released file lock: {self._lock_file}")
        except Exception as e:
            logger.error(f"Error releasing file lock: {e}")
    
    def _convert_for_json(self, value):
        """
        Convert a value to be JSON serializable.
        
        Args:
            value: The value to convert
            
        Returns:
            A JSON serializable version of the value
        """
        if isinstance(value, set):
            return list(value)
        elif isinstance(value, dict):
            return {k: self._convert_for_json(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._convert_for_json(v) for v in value]
        else:
            return value

    def save_graph(self) -> None:
        """
        Save the graph data to the JSON file.
        
        This method writes all nodes, edges, and file-node mappings to the JSON file.
        The operation is atomic, using a temporary file and rename to avoid data corruption.
        """
        lock_acquired = self._acquire_file_lock()
        if not lock_acquired:
            logger.warning(f"Could not acquire lock to save graph to {self.json_path}")
            return
        
        try:
            # Create the dictionary to export
            data = {
                'nodes': [],
                'edges': [],
                'file_nodes': {}
            }
            
            # Add nodes with their attributes
            for node_id, attrs in self.graph.nodes(data=True):
                node_data = {'id': node_id}
                node_data.update(attrs)
                # Convert sets to lists for JSON serialization
                node_data = self._convert_for_json(node_data)
                data['nodes'].append(node_data)
            
            # Add edges with their attributes
            for source, target, key, attrs in self.graph.edges(data=True, keys=True):
                edge_data = {
                    'source': source,
                    'target': target,
                    'type': key
                }
                edge_data.update(attrs)
                # Convert sets to lists for JSON serialization
                edge_data = self._convert_for_json(edge_data)
                data['edges'].append(edge_data)
            
            # Convert file_nodes mapping to proper format
            for file_path, node_ids in self.file_nodes.items():
                data['file_nodes'][file_path] = list(node_ids)
            
            # Write to a temporary file first, then rename for atomic update
            temp_file = f"{self.json_path}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Rename the temp file to the actual file (atomic operation)
            # This prevents data corruption if the process is interrupted during writing
            os.replace(temp_file, self.json_path)
            
            logger.info(f"Saved graph to {self.json_path}")
        except (IOError, OSError) as e:
            logger.error(f"Error saving graph to {self.json_path}: {e}")
        finally:
            # Always release the lock, even if an error occurred
            if lock_acquired:
                self._release_file_lock()
    
    def add_or_update_file(self, filepath: str, parse_result: Dict[str, List[Dict[str, Any]]], content_hash: Optional[str] = None):
        """
        Add or update nodes and edges from a parse result.

        Args:
            filepath: Path of the file being processed
            parse_result: Dictionary containing nodes and edges to add
            content_hash: Optional hash of the file content.
        """
        with self._lock:
            # Remove existing nodes associated *only* with this file first
            # (keeps shared nodes)
            self._remove_file_nodes_and_edges(filepath)

            # Track nodes for this file
            self.file_nodes[filepath] = set()
            file_module_node_id = None

            # --- Pass 1: Find module node ID --- 
            for node_data in parse_result.get('nodes', []):
                if node_data.get('type') == 'module' and node_data.get('filepath') == filepath:
                    file_module_node_id = node_data['id']
                    break

            # --- Pass 2: Add/Update nodes --- 
            for node_data in parse_result.get('nodes', []):
                node_id = node_data['id']
                node_attrs = node_data.copy()

                # Add content hash if it's the module node
                if node_id == file_module_node_id and content_hash:
                    node_attrs['content_hash'] = content_hash

                if self.graph.has_node(node_id):
                    node = self.graph.nodes[node_id]
                    files = set(node.get('files', []))
                    files.add(filepath)
                    node_attrs['files'] = list(files)
                    # Preserve existing hash if needed
                    if node_id == file_module_node_id and 'content_hash' not in node_attrs and 'content_hash' in node:
                         node_attrs['content_hash'] = node['content_hash']
                else:
                    node_attrs['files'] = [filepath]

                self.graph.add_node(node_id, **node_attrs)
                self.file_nodes[filepath].add(node_id)

            if content_hash and not file_module_node_id:
                 logger.warning(f"No module node found for {filepath} to store content hash.")

            # Process edges (logic remains similar, ensuring nodes exist)
            for edge_data in parse_result.get('edges', []):
                source = edge_data['source']
                target = edge_data['target']
                edge_type = edge_data.get('type', 'default') # Use get with default

                # Ensure source/target nodes exist (might have been created above)
                if not self.graph.has_node(source):
                     # This might happen if the parse result is inconsistent
                     logger.warning(f"Edge source node {source} not found for file {filepath}, skipping edge.")
                     continue
                if not self.graph.has_node(target):
                     if target.startswith('module:'): # Auto-create missing module targets
                         self.graph.add_node(target, type='module', name=target.split(':')[1], files=[filepath])
                         if filepath in self.file_nodes: self.file_nodes[filepath].add(target)
                     else:
                         logger.warning(f"Edge target node {target} not found for file {filepath}, skipping edge.")
                         continue

                attrs = edge_data.copy()
                attrs.pop('source', None)
                attrs.pop('target', None)
                attrs.pop('type', None) # Pop type as it's used as key
                attrs['file'] = filepath

                # Add edge using type as key
                self.graph.add_edge(source, target, key=edge_type, **attrs)

            # Save the updated graph
            self.save_graph()

            logger.info(f"Added/updated file {filepath} with {len(parse_result.get('nodes', []))} "
                        f"nodes and {len(parse_result.get('edges', []))} edges")

    def _remove_file_nodes_and_edges(self, filepath: str):
        """Internal helper to remove nodes/edges specific to a file."""
        if filepath not in self.file_nodes:
            return # Nothing to remove

        file_node_ids = set(self.file_nodes.get(filepath, set())) # Make a copy
        nodes_to_remove_completely = set()

        # Update or mark nodes for removal
        for node_id in file_node_ids:
            if self.graph.has_node(node_id):
                node = self.graph.nodes[node_id]
                files = set(node.get('files', []))
                if filepath in files:
                    files.remove(filepath)
                
                if not files:
                    # If no other file uses this node, mark for complete removal
                    nodes_to_remove_completely.add(node_id)
                else:
                    # Otherwise, just update the files list
                    node['files'] = list(files)
        
        # Remove edges associated with the file
        # Need to iterate carefully as graph changes
        edges_to_remove = []
        for u, v, k, data in self.graph.edges(data=True, keys=True):
            if data.get('file') == filepath:
                edges_to_remove.append((u, v, k))
            # Also remove edges connected to nodes being completely removed
            elif u in nodes_to_remove_completely or v in nodes_to_remove_completely:
                # Avoid duplicates if edge also had the file attribute
                if data.get('file') != filepath: 
                    edges_to_remove.append((u, v, k))
        
        # Remove identified edges (use set to avoid duplicates)
        for u, v, k in set(edges_to_remove):
            if self.graph.has_edge(u, v, key=k):
                self.graph.remove_edge(u, v, key=k)

        # Remove nodes marked for complete removal
        for node_id in nodes_to_remove_completely:
            if self.graph.has_node(node_id):
                self.graph.remove_node(node_id)

        # Remove file from tracking
        if filepath in self.file_nodes:
            del self.file_nodes[filepath]

    def remove_file(self, filepath: str) -> None:
        """
        Remove all nodes and edges specific to the given file and save.
        
        Args:
            filepath: Path of the file to remove
        """
        with self._lock:
            self._remove_file_nodes_and_edges(filepath)
            # Save the updated graph after removal
            self.save_graph()
            logger.info(f"Removed data specific to file {filepath} and saved graph")
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all nodes in the graph with their attributes.
        
        Returns:
            List of node dictionaries with id and attributes
        """
        with self._lock:
            result = []
            for node_id, attrs in self.graph.nodes(data=True):
                node_data = {'id': node_id}
                node_data.update(attrs)
                result.append(node_data)
            return result
    
    def get_all_edges(self) -> List[Dict[str, Any]]:
        """
        Get all edges in the graph with their attributes.
        
        Returns:
            List of edge dictionaries with source, target, type and attributes
        """
        with self._lock:
            result = []
            for source, target, key, attrs in self.graph.edges(data=True, keys=True):
                edge_data = {
                    'source': source,
                    'target': target,
                    'type': key
                }
                edge_data.update(attrs)
                result.append(edge_data)
            return result
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific node by its ID.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            Node dictionary with attributes or None if not found
        """
        with self._lock:
            if not self.graph.has_node(node_id):
                return None
            
            node_data = {'id': node_id}
            node_data.update(self.graph.nodes[node_id])
            return node_data
    
    def get_edges_for_nodes(self, node_ids: Set[str]) -> List[Dict[str, Any]]:
        """
        Get all edges connected to the given nodes.
        
        Args:
            node_ids: Set of node IDs to get edges for
            
        Returns:
            List of edge dictionaries
        """
        with self._lock:
            result = []
            for node_id in node_ids:
                if not self.graph.has_node(node_id):
                    continue
                
                # Get outgoing edges
                for _, target, key, attrs in self.graph.out_edges(node_id, data=True, keys=True):
                    edge_data = {
                        'source': node_id,
                        'target': target,
                        'type': key
                    }
                    edge_data.update(attrs)
                    result.append(edge_data)
                
                # Get incoming edges
                for source, _, key, attrs in self.graph.in_edges(node_id, data=True, keys=True):
                    edge_data = {
                        'source': source,
                        'target': node_id,
                        'type': key
                    }
                    edge_data.update(attrs)
                    result.append(edge_data)
            
            return result
    
    def get_nodes_for_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Get all nodes associated with a specific file.
        
        Args:
            filepath: Path of the file to get nodes for
            
        Returns:
            List of node dictionaries
        """
        with self._lock:
            result = []
            if filepath not in self.file_nodes:
                return result
            
            for node_id in self.file_nodes[filepath]:
                if self.graph.has_node(node_id):
                    node_data = {'id': node_id}
                    node_data.update(self.graph.nodes[node_id])
                    result.append(node_data)
            
            return result
    
    def get_edges_for_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Get all edges associated with a specific file.
        
        Args:
            filepath: Path of the file to get edges for
            
        Returns:
            List of edge dictionaries
        """
        with self._lock:
            result = []
            for source, target, key, attrs in self.graph.edges(data=True, keys=True):
                if attrs.get('file') == filepath:
                    edge_data = {
                        'source': source,
                        'target': target,
                        'type': key
                    }
                    edge_data.update(attrs)
                    result.append(edge_data)
            
            return result
    
    def get_node_count(self) -> int:
        """
        Get the total number of nodes in the graph.
        
        Returns:
            Number of nodes
        """
        with self._lock:
            return self.graph.number_of_nodes()
    
    def get_edge_count(self) -> int:
        """
        Get the total number of edges in the graph.
        
        Returns:
            Number of edges
        """
        with self._lock:
            return self.graph.number_of_edges()
    
    def get_file_content_hash(self, filepath: str) -> Optional[str]:
        """Retrieve the stored content hash for a file."""
        with self._lock:
            # Find the primary module node for the file
            for node_id in self.file_nodes.get(filepath, set()):
                if self.graph.has_node(node_id):
                    node = self.graph.nodes[node_id]
                    # Check if it's the module node and has the hash
                    if node.get('type') == 'module' and node.get('filepath') == filepath and 'content_hash' in node:
                        return node['content_hash']
        return None

# Helper function for hashing (can be placed here or in a utils module)
def calculate_content_hash(content: bytes) -> str:
    """Calculates the SHA-256 hash of the given content."""
    return hashlib.sha256(content).hexdigest() 