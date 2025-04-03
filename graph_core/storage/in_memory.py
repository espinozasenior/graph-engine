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
    
    def add_or_update_file(self, filepath: str, parse_result: Dict[str, List[Dict[str, Any]]]):
        """
        Add or update nodes and edges from a parse result.
        
        Args:
            filepath: Path of the file being processed
            parse_result: Dictionary containing nodes and edges to add
        """
        # First remove existing nodes for this file
        self.remove_file(filepath)
        
        # Keep track of nodes for this file
        self.file_nodes[filepath] = set()
        
        # Add nodes
        for node in parse_result.get('nodes', []):
            node_id = node['id']
            
            # Add the node with all its attributes
            attrs = node.copy()
            
            # Track which files this node is in
            if node_id in self.graph:
                # Node already exists, update its files
                existing_attrs = self.graph.nodes[node_id]
                files = set(existing_attrs.get('files', []))
                files.add(filepath)
                attrs['files'] = list(files)
            else:
                # New node
                attrs['files'] = [filepath]
            
            self.graph.add_node(node_id, **attrs)
            self.file_nodes[filepath].add(node_id)
        
        # Add edges
        for edge in parse_result.get('edges', []):
            source = edge['source']
            target = edge['target']
            
            # Add the edge with its attributes
            attrs = edge.copy()
            attrs.pop('source', None)
            attrs.pop('target', None)
            attrs['file'] = filepath
            
            self.graph.add_edge(source, target, **attrs)
    
    def remove_file(self, filepath: str):
        """
        Remove all nodes and edges associated with the given file.
        
        Args:
            filepath: Path of the file to remove
        """
        if filepath not in self.file_nodes:
            return
        
        node_ids = self.file_nodes[filepath].copy()
        
        # Remove or update nodes
        for node_id in node_ids:
            if node_id in self.graph:
                # Get the node's files
                attrs = self.graph.nodes[node_id]
                files = set(attrs.get('files', []))
                
                # Remove this file
                if filepath in files:
                    files.remove(filepath)
                
                if files:
                    # Node is still in other files, update its files list
                    attrs['files'] = list(files)
                else:
                    # Node is not in any files, remove it
                    self.graph.remove_node(node_id)
        
        # Remove edges for this file
        edges_to_remove = []
        for u, v, attrs in self.graph.edges(data=True):
            if attrs.get('file') == filepath:
                edges_to_remove.append((u, v))
        
        for u, v in edges_to_remove:
            self.graph.remove_edge(u, v)
        
        # Remove file from tracking
        del self.file_nodes[filepath]
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all nodes in the graph.
        
        Returns:
            List of node dictionaries
        """
        result = []
        for node_id, attrs in self.graph.nodes(data=True):
            node_data = attrs.copy()
            node_data['id'] = node_id
            result.append(node_data)
        return result
    
    def get_all_edges(self) -> List[Dict[str, Any]]:
        """
        Get all edges in the graph.
        
        Returns:
            List of edge dictionaries
        """
        result = []
        for u, v, attrs in self.graph.edges(data=True):
            edge_data = attrs.copy()
            edge_data['source'] = u
            edge_data['target'] = v
            result.append(edge_data)
        return result
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific node by its ID.
        
        Args:
            node_id: ID of the node to retrieve
            
        Returns:
            Node dictionary or None if not found
        """
        if node_id in self.graph:
            node_data = self.graph.nodes[node_id].copy()
            node_data['id'] = node_id
            return node_data
        return None
    
    def get_edges_for_nodes(self, node_ids: Set[str]) -> List[Dict[str, Any]]:
        """
        Get all edges connected to the given nodes.
        
        Args:
            node_ids: Set of node IDs to get edges for
            
        Returns:
            List of edge dictionaries
        """
        result = []
        
        for node_id in node_ids:
            if node_id not in self.graph:
                continue
            
            # Get outgoing edges
            for _, target, attrs in self.graph.out_edges(node_id, data=True):
                edge_data = attrs.copy()
                edge_data['source'] = node_id
                edge_data['target'] = target
                result.append(edge_data)
            
            # Get incoming edges
            for source, _, attrs in self.graph.in_edges(node_id, data=True):
                edge_data = attrs.copy()
                edge_data['source'] = source
                edge_data['target'] = node_id
                result.append(edge_data)
        
        return result
    
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