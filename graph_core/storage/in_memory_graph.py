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
        self.graph = nx.DiGraph()
        self.file_nodes = {}  # Maps filepath to set of node IDs from that file
    
    def add_or_update_file(self, filepath: str, parse_result: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Add or update nodes and edges from a parse result.
        
        If the file already exists in the graph, its previous nodes and edges are removed
        before adding the new ones.
        
        Args:
            filepath: The path of the file being added or updated
            parse_result: A dictionary containing 'nodes' and 'edges' lists from a parser
            
        Raises:
            KeyError: If the parse_result doesn't have the expected structure
        """
        if 'nodes' not in parse_result or 'edges' not in parse_result:
            logger.error(f"Invalid parse result format for {filepath}")
            raise KeyError("Parse result must contain 'nodes' and 'edges' keys")
        
        # If the file already exists, remove its nodes and edges
        if filepath in self.file_nodes:
            self.remove_file(filepath)
        
        # Keep track of nodes from this file
        node_ids = set()
        
        # Add nodes
        for node in parse_result['nodes']:
            node_id = node['id']
            node_ids.add(node_id)
            
            # Add the node to the graph with all its attributes
            node_attrs = node.copy()
            
            # Handle existing nodes - merge the 'files' set instead of replacing
            if node_id in self.graph:
                existing_attrs = self.graph.nodes[node_id]
                if 'files' in existing_attrs:
                    # Create a new set with existing files plus the current file
                    files_set = existing_attrs['files'].copy()
                    files_set.add(filepath)
                    node_attrs['files'] = files_set
                else:
                    node_attrs['files'] = {filepath}
            else:
                node_attrs['files'] = {filepath}
            
            self.graph.add_node(node_id, **node_attrs)
        
        # Store the set of node IDs for this file
        self.file_nodes[filepath] = node_ids
        
        # Add edges
        for edge in parse_result['edges']:
            source = edge['source']
            target = edge['target']
            
            # If source or target is the filepath itself, this is a module-level reference
            # Replace it with a file-specific node ID to avoid conflicts
            if source == filepath:
                source = f"module:{filepath}"
                if source not in self.graph:
                    self.graph.add_node(source, id=source, type='module', filepath=filepath, files={filepath})
                    self.file_nodes[filepath].add(source)
            
            if target == filepath:
                target = f"module:{filepath}"
                if target not in self.graph:
                    self.graph.add_node(target, id=target, type='module', filepath=filepath, files={filepath})
                    self.file_nodes[filepath].add(target)
            
            # Add the edge with all its attributes
            edge_attrs = edge.copy()
            edge_attrs['file'] = filepath
            
            self.graph.add_edge(source, target, **edge_attrs)
    
    def remove_file(self, filepath: str) -> None:
        """
        Remove all nodes and edges associated with a file.
        
        Args:
            filepath: The path of the file to remove
        """
        if filepath not in self.file_nodes:
            logger.warning(f"No nodes found for file {filepath}")
            return
        
        nodes_to_remove = []
        for node_id in self.file_nodes[filepath]:
            # Get the node attributes
            if node_id in self.graph:
                node_attrs = self.graph.nodes[node_id]
                
                # Remove this file from the node's files set
                if 'files' in node_attrs:
                    node_attrs['files'].discard(filepath)
                    
                    # If the node isn't in any more files, mark it for removal
                    if not node_attrs['files']:
                        nodes_to_remove.append(node_id)
        
        # Remove edges where this file is the source
        edges_to_remove = []
        for u, v, attrs in self.graph.edges(data=True):
            if attrs.get('file') == filepath:
                edges_to_remove.append((u, v))
        
        # Remove the edges and nodes
        for edge in edges_to_remove:
            self.graph.remove_edge(*edge)
        
        for node_id in nodes_to_remove:
            self.graph.remove_node(node_id)
        
        # Remove the file from our tracking
        del self.file_nodes[filepath]
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all nodes in the graph.
        
        Returns:
            List of dictionaries representing nodes
        """
        return [
            {**attrs, 'id': node_id}
            for node_id, attrs in self.graph.nodes(data=True)
        ]
    
    def get_all_edges(self) -> List[Dict[str, Any]]:
        """
        Get all edges in the graph.
        
        Returns:
            List of dictionaries representing edges
        """
        return [
            {**attrs, 'source': u, 'target': v}
            for u, v, attrs in self.graph.edges(data=True)
        ]
    
    def get_node_count(self) -> int:
        """
        Get the total number of nodes in the graph.
        
        Returns:
            int: The number of nodes
        """
        return self.graph.number_of_nodes()
    
    def get_edge_count(self) -> int:
        """
        Get the total number of edges in the graph.
        
        Returns:
            int: The number of edges
        """
        return self.graph.number_of_edges()
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific node by ID.
        
        Args:
            node_id: The ID of the node to get
            
        Returns:
            A dictionary representing the node, or None if not found
        """
        if node_id in self.graph:
            return {**self.graph.nodes[node_id], 'id': node_id}
        return None
        
    def get_edges_for_nodes(self, node_ids: Set[str]) -> List[Dict[str, Any]]:
        """
        Get all edges connected to any of the specified nodes.
        
        Args:
            node_ids: A set of node IDs to find edges for
            
        Returns:
            A list of dictionaries representing edges where at least one endpoint is in node_ids
        """
        edges = []
        
        # Check each node in the provided set
        for node_id in node_ids:
            if node_id not in self.graph:
                continue
                
            # Get outgoing edges (where node is the source)
            for _, target, attrs in self.graph.out_edges(node_id, data=True):
                edges.append({**attrs, 'source': node_id, 'target': target})
                
            # Get incoming edges (where node is the target)
            for source, _, attrs in self.graph.in_edges(node_id, data=True):
                edges.append({**attrs, 'source': source, 'target': node_id})
        
        # Remove duplicates if a node is both source and target in the set
        unique_edges = []
        seen_edges = set()
        
        for edge in edges:
            edge_key = (edge['source'], edge['target'])
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                unique_edges.append(edge)
        
        return unique_edges 