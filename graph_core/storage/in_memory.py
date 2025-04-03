"""
In-Memory Graph Storage Module

This module provides an in-memory implementation of a graph storage system
using networkx for storing and manipulating code structure data.
"""

import logging
from typing import Dict, List, Any, Set, Optional

import networkx as nx

# Set up logging
logger = logging.getLogger(__name__)


class InMemoryGraphStorage:
    """
    An in-memory implementation of a graph storage system using networkx.
    
    This class provides methods to add, update, and remove nodes and edges
    representing code structures, with tracking of which nodes came from which files.
    """
    
    def __init__(self):
        """Initialize the in-memory graph storage."""
        self.graph = nx.MultiDiGraph()
        self.file_nodes: Dict[str, Set[str]] = {}  # Maps filepath to set of node IDs
    
    def add_or_update_file(self, filepath: str, parse_result: Dict[str, List[Dict[str, Any]]], content_hash: Optional[str] = None):
        """
        Add or update nodes and edges from a parse result.
        Handles adding file tracking and content hash to nodes.
        Implicitly creates nodes referenced in edges if they don't exist.

        Args:
            filepath: Path of the file being processed
            parse_result: Dictionary containing nodes and edges to add
            content_hash: Optional hash of the file content.
        """
        # Remove existing data associated *only* with this specific file first
        # This is safer than removing all nodes listed in file_nodes[filepath]
        # as some might be shared and still valid.
        self.remove_file(filepath)

        self.file_nodes[filepath] = set()
        file_module_node_id = None
        nodes_to_add = parse_result.get('nodes', [])
        edges_to_add = parse_result.get('edges', [])

        # --- Find the module node ID first --- 
        for node in nodes_to_add:
            if node.get('type') == 'module' and node.get('filepath') == filepath:
                file_module_node_id = node['id']
                break

        # --- Add/Update nodes, manage 'files' attribute and apply hash --- 
        for node in nodes_to_add:
            node_id = node['id']
            attrs = node.copy()
            existing_files = set()

            # Check if node already exists
            if self.graph.has_node(node_id):
                existing_attrs = self.graph.nodes[node_id]
                existing_files = set(existing_attrs.get('files', []))
                # Preserve existing hash if needed
                if node_id == file_module_node_id and content_hash and 'content_hash' not in attrs:
                     if 'content_hash' in existing_attrs:
                           attrs['content_hash'] = existing_attrs['content_hash'] # Keep old hash if new one not provided
            
            # Add current filepath to the set of files for this node
            existing_files.add(filepath)
            attrs['files'] = list(existing_files) # Update the files attribute
            
            # Add content hash if applicable
            if node_id == file_module_node_id and content_hash:
                attrs['content_hash'] = content_hash
            
            # Add/Update the node in the graph. add_node updates attributes if node exists.
            self.graph.add_node(node_id, **attrs)
            self.file_nodes[filepath].add(node_id) # Track node belongs to this file

        # Warning if hash was provided but no module node found
        if content_hash and not file_module_node_id:
            logger.warning(f"Content hash provided for {filepath}, but no corresponding module node found in parse result.")

        # Add edges, using edge type as the key for MultiDiGraph
        # Allow implicit node creation by add_edge
        for edge in edges_to_add:
            source = edge.get('source')
            target = edge.get('target')
            edge_type = edge.get('type', 'unknown') # Use 'unknown' if type missing
            
            if not source or not target:
                logger.warning(f"Skipping edge due to missing source/target: {edge}")
                continue
                
            edge_attrs = edge.copy()
            edge_attrs.pop('source', None)
            edge_attrs.pop('target', None)
            edge_attrs.pop('type', None) # Type is used as key
            
            # Let add_edge handle node creation if needed
            self.graph.add_edge(source, target, key=edge_type, **edge_attrs)

    def remove_file(self, filepath: str):
        """
        Removes nodes exclusively associated with the given file 
        and all edges connected to those exclusively removed nodes.
        Updates the 'files' attribute for nodes shared with other files.
        
        Args:
            filepath: Path of the file to remove
        """
        if filepath not in self.file_nodes:
            # logger.debug(f"File {filepath} not found in storage for removal.") # Too verbose
            return
        
        node_ids_in_file = self.file_nodes.pop(filepath, set()).copy() # Remove from tracking immediately
        nodes_to_remove_completely = set()

        # Identify nodes solely associated with this file by updating 'files' attribute
        for node_id in node_ids_in_file:
            if self.graph.has_node(node_id):
                node_attrs = self.graph.nodes[node_id]
                files_attr = node_attrs.get('files')
                
                if isinstance(files_attr, list):
                    files_set = set(files_attr)
                    if filepath in files_set:
                        files_set.remove(filepath)
                        # If the set is now empty, mark node for complete removal
                        if not files_set:
                            nodes_to_remove_completely.add(node_id)
                        else:
                            # Otherwise, just update the attribute in the graph
                            self.graph.nodes[node_id]['files'] = list(files_set)
                    else:
                        # Filepath was expected but not found in the list
                        logger.warning(f"File {filepath} not found in files attribute for node {node_id} during removal, though tracked in file_nodes.")
                        # If it was the *only* file tracked in file_nodes, still remove the node
                        if len(node_ids_in_file) == 1 and list(node_ids_in_file)[0] == node_id: # Check if this was the only node ID for the file
                              nodes_to_remove_completely.add(node_id)
                else:
                    # files attribute missing or wrong type - Mark for removal if tracked
                    logger.warning(f"Node {node_id} has missing or invalid 'files' attribute ({files_attr}). Marking for removal as it was tracked for {filepath}.")
                    nodes_to_remove_completely.add(node_id)
            else:
                 logger.warning(f"Node {node_id} listed in file_nodes for {filepath} but not found in graph during removal step.")

        # Remove edges connected to nodes being completely removed
        # This handles edges defined across files where one endpoint is removed
        edges_to_remove = set()
        for node_id in nodes_to_remove_completely:
            # Need keys=True for MultiDiGraph edge iteration
            if self.graph.has_node(node_id): # Check again in case of prior removal issues
                 edges_to_remove.update(self.graph.in_edges(node_id, keys=True))
                 edges_to_remove.update(self.graph.out_edges(node_id, keys=True))
        
        # Perform edge removal
        for u, v, k in edges_to_remove:
            if self.graph.has_edge(u, v, key=k):
                self.graph.remove_edge(u, v, key=k)

        # Perform node removal
        for node_id in nodes_to_remove_completely:
            if self.graph.has_node(node_id):
                self.graph.remove_node(node_id)

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes in the graph, including their ID."""
        return [dict(data, id=node_id) for node_id, data in self.graph.nodes(data=True)]
    
    def get_all_edges(self) -> List[Dict[str, Any]]:
        """Get all edges from the graph, including source, target, and type (key)."""
        # Include source, target, and key (as type) in the returned dictionary
        return [
            dict(data, source=u, target=v, type=key) 
            for u, v, key, data in self.graph.edges(data=True, keys=True)
        ]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific node by ID, including its ID."""
        if self.graph.has_node(node_id):
            node_data = self.graph.nodes[node_id].copy()
            node_data['id'] = node_id # Ensure ID is in the returned dict
            return node_data
        return None
    
    def get_edges_for_nodes(self, node_ids: List[str]) -> List[Dict[str, Any]]:
        """Get all edges connected to the given nodes, including source, target, and type (key)."""
        edges = []
        processed_edges = set() # To avoid duplicates (u,v,k)
        for node_id in node_ids:
            if self.graph.has_node(node_id):
                # Get outgoing edges
                for u, v, key, data in self.graph.out_edges(node_id, data=True, keys=True):
                    edge_tuple = (u, v, key)
                    if edge_tuple not in processed_edges:
                        edges.append(dict(data, source=u, target=v, type=key))
                        processed_edges.add(edge_tuple)
                # Get incoming edges
                for u, v, key, data in self.graph.in_edges(node_id, data=True, keys=True):
                    edge_tuple = (u, v, key)
                    if edge_tuple not in processed_edges:
                         edges.append(dict(data, source=u, target=v, type=key))
                         processed_edges.add(edge_tuple)
        return edges
    
    def get_node_count(self) -> int:
        """
        Get the total number of nodes in the graph.
        
        Returns:
            Number of nodes
        """
        return self.graph.number_of_nodes()
    
    def get_edge_count(self) -> int:
        """
        Get the total number of edges in the graph.
        
        Returns:
            Number of edges
        """
        return self.graph.number_of_edges()

    def get_file_content_hash(self, filepath: str) -> Optional[str]:
        """Retrieve the stored content hash for a file."""
        # Find the primary module node for the file
        for node_id in self.file_nodes.get(filepath, set()):
            if self.graph.has_node(node_id):
                node = self.graph.nodes[node_id]
                # Check if it's the module node and has the hash
                if node.get('type') == 'module' and node.get('filepath') == filepath and 'content_hash' in node:
                    return node['content_hash']
        # Alternative: Could retrieve from a separate self.file_hashes dict
        return None 