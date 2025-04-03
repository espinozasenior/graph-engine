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
        
        If the file doesn't exist or is invalid, an empty graph is initialized.
        """
        with self._lock:
            if not os.path.exists(self.json_path):
                logger.info(f"JSON file {self.json_path} does not exist. Creating a new graph.")
                return
            
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Clear existing graph
                self.graph.clear()
                self.file_nodes.clear()
                
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
                
                # Load file_nodes mapping
                self.file_nodes = data.get('file_nodes', {})
                
                logger.info(f"Loaded graph with {self.graph.number_of_nodes()} nodes and "
                            f"{self.graph.number_of_edges()} edges")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading graph from {self.json_path}: {e}")
                # Initialize empty graph as fallback
                self.graph.clear()
                self.file_nodes.clear()
    
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
    
    def save_graph(self) -> None:
        """
        Save the graph to the JSON file.
        
        Creates the parent directories if they don't exist.
        Uses file locking to ensure safe concurrent access from multiple processes.
        """
        with self._lock:
            # Acquire file lock for cross-process safety
            lock_acquired = self._acquire_file_lock()
            if not lock_acquired:
                logger.warning("Could not acquire file lock. Saving without lock (may cause data corruption if multiple processes are writing).")
            
            try:
                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(os.path.abspath(self.json_path)), exist_ok=True)
                
                # Prepare data in a serializable format
                data = {
                    'nodes': [],
                    'edges': [],
                    'file_nodes': self.file_nodes
                }
                
                # Add nodes with their attributes
                for node_id, attrs in self.graph.nodes(data=True):
                    node_data = {'id': node_id}
                    node_data.update(attrs)
                    data['nodes'].append(node_data)
                
                # Add edges with their attributes
                for source, target, key, attrs in self.graph.edges(data=True, keys=True):
                    edge_data = {
                        'source': source,
                        'target': target,
                        'type': key
                    }
                    edge_data.update(attrs)
                    data['edges'].append(edge_data)
                
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
    
    def add_or_update_file(self, filepath: str, parse_result: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Add or update nodes and edges for a file in the graph.
        
        Args:
            filepath: Path of the file being processed
            parse_result: Dictionary containing nodes and edges to add
        """
        with self._lock:
            # Remove existing nodes for this file
            self.remove_file(filepath)
            
            # Track nodes for this file
            self.file_nodes[filepath] = []
            
            # Add nodes
            for node_data in parse_result.get('nodes', []):
                node_id = node_data['id']
                
                # If node already exists, update its files list
                if self.graph.has_node(node_id):
                    node = self.graph.nodes[node_id]
                    files = set(node.get('files', []))
                    files.add(filepath)
                    node['files'] = list(files)
                # Otherwise add a new node
                else:
                    node_attrs = node_data.copy()
                    node_attrs['files'] = [filepath]
                    self.graph.add_node(node_id, **node_attrs)
                
                # Track this node for the file
                self.file_nodes[filepath].append(node_id)
            
            # Process edges and ensure module nodes exist
            for edge_data in parse_result.get('edges', []):
                source = edge_data['source']
                target = edge_data['target']
                edge_type = edge_data['type']
                
                # If target is a module node and doesn't exist yet, create it
                if target.startswith('module:') and not self.graph.has_node(target):
                    self.graph.add_node(target, type='module', name=target.split(':')[1], files=[filepath])
                    # Add to file nodes tracking if not already there
                    if target not in self.file_nodes[filepath]:
                        self.file_nodes[filepath].append(target)
                
                # Add necessary attributes for tracking
                attrs = edge_data.copy()
                attrs.pop('source', None)
                attrs.pop('target', None)
                attrs.pop('type', None)
                attrs['file'] = filepath
                
                self.graph.add_edge(source, target, key=edge_type, **attrs)
            
            # Save the updated graph
            self.save_graph()
            
            logger.info(f"Added/updated file {filepath} with {len(parse_result.get('nodes', []))} "
                        f"nodes and {len(parse_result.get('edges', []))} edges")
    
    def remove_file(self, filepath: str) -> None:
        """
        Remove all nodes and edges associated with the given file.
        
        Args:
            filepath: Path of the file to remove
        """
        with self._lock:
            if filepath not in self.file_nodes:
                logger.info(f"No nodes found for file {filepath}")
                return
            
            # Get list of nodes for this file
            file_node_ids = set(self.file_nodes[filepath])
            
            # For each node associated with this file
            for node_id in file_node_ids:
                if self.graph.has_node(node_id):
                    node = self.graph.nodes[node_id]
                    
                    # Update files list
                    files = set(node.get('files', []))
                    if filepath in files:
                        files.remove(filepath)
                    
                    if files:
                        # Node is still used by other files, update its files list
                        node['files'] = list(files)
                    else:
                        # Node is not used by any other file, remove it
                        self.graph.remove_node(node_id)
            
            # Remove edges associated with the file
            edges_to_remove = []
            for source, target, key, attrs in self.graph.edges(data=True, keys=True):
                if attrs.get('file') == filepath:
                    edges_to_remove.append((source, target, key))
            
            for source, target, key in edges_to_remove:
                self.graph.remove_edge(source, target, key)
            
            # Remove file from tracking
            del self.file_nodes[filepath]
            
            # Save the updated graph
            self.save_graph()
            
            logger.info(f"Removed file {filepath} and its associated nodes/edges")
    
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