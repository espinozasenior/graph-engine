"""
MCP Integration for Graph Engine

This module provides MCP (Machine-Callable Program) integration for the Graph Engine,
allowing LLMs to interact with the code graph in smaller, more digestible chunks.
"""

import sys
import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Set, Union, Literal

from mcp.types import (
    CallToolRequest,
    CallToolResult,
    TextContent,
    Tool,
)

from graph_core.manager import DependencyGraphManager
from graph_core.storage.json_storage import JSONGraphStorage


class GraphEngineMCP:
    """
    MCP integration for the Graph Engine.
    
    This class provides methods for interacting with the code graph via MCP,
    allowing LLMs to fetch graph data in smaller, more manageable chunks.
    """
    
    def __init__(self, graph_manager: Optional[DependencyGraphManager] = None):
        """
        Initialize the MCP integration with a graph manager.
        
        Args:
            graph_manager: An instance of DependencyGraphManager. If None, a new
                instance will be created using the default JSON storage path.
        """
        self.graph_manager = graph_manager or self._create_default_graph_manager()
        
    def _create_default_graph_manager(self) -> DependencyGraphManager:
        """
        Create a default graph manager using environment variables or defaults.
        
        Returns:
            A new DependencyGraphManager instance
        """
        from graph_core.manager import DependencyGraphManager, DEFAULT_JSON_PATH
        
        # Use path from environment variable or default
        json_path = os.environ.get("GRAPH_STORAGE_PATH", DEFAULT_JSON_PATH)
        
        # If path is relative, make it relative to the project root
        if not os.path.isabs(json_path):
            project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            json_path = os.path.join(project_root, json_path)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        # Create storage and manager
        storage = JSONGraphStorage(json_path)
        
        # Load storage if file exists
        if os.path.exists(json_path):
            try:
                storage.load_graph()
            except Exception as e:
                print(f"Warning: Could not load graph from {json_path}. Starting with empty graph. Error: {e}", 
                      file=sys.stderr)
        
        return DependencyGraphManager(storage=storage)
    
    # --- Core Graph Data Access Methods ---
    
    def list_nodes(self, filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List nodes in the graph with optional filtering.
        
        Args:
            filters: Optional dictionary of filters to apply (e.g., {'node_type': 'function'})
            limit: Maximum number of nodes to return
            
        Returns:
            List of node dictionaries
        """
        all_nodes = self.graph_manager.storage.get_all_nodes()
        
        # Apply filters if provided
        if filters:
            filtered_nodes = []
            for node in all_nodes:
                match = True
                for key, value in filters.items():
                    if key not in node or node[key] != value:
                        match = False
                        break
                if match:
                    filtered_nodes.append(self._convert_node_to_dict(node))
                    if len(filtered_nodes) >= limit:
                        break
            return filtered_nodes
        else:
            # Just apply limit
            return [self._convert_node_to_dict(node) for node in all_nodes[:limit]]
    
    def get_node_details(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific node.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            Node dictionary or None if not found
        """
        node = self.graph_manager.storage.get_node(node_id)
        if node:
            return self._convert_node_to_dict(node)
        return None
    
    def search_nodes(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for nodes matching a keyword in ID or filepath.
        
        Args:
            keyword: The search term to look for
            limit: Maximum number of results to return
            
        Returns:
            List of matching node dictionaries
        """
        all_nodes = self.graph_manager.storage.get_all_nodes()
        matched_nodes = []
        
        for node in all_nodes:
            if (keyword.lower() in node.get('id', '').lower() or 
                (node.get('filepath') and keyword.lower() in node['filepath'].lower())):
                matched_nodes.append(self._convert_node_to_dict(node))
                if len(matched_nodes) >= limit:
                    break
                    
        return matched_nodes
    
    def list_edges_for_node(self, node_id: str, 
                          direction: Literal["incoming", "outgoing", "both"] = "both") -> List[Dict[str, Any]]:
        """
        List edges connected to a specific node.
        
        Args:
            node_id: The ID of the node
            direction: Which edges to include:
                       "incoming" - edges where this node is the target
                       "outgoing" - edges where this node is the source
                       "both" - all edges connected to this node (default)
            
        Returns:
            List of edge dictionaries
        """
        # Check if node exists
        if not self.graph_manager.storage.get_node(node_id):
            return []
            
        # Get all edges connected to this node
        all_edges = self.graph_manager.storage.get_edges_for_nodes([node_id])
        
        if direction == "both":
            return [self._convert_edge_to_dict(edge) for edge in all_edges]
        
        filtered_edges = []
        for edge in all_edges:
            if direction == "incoming" and edge['target'] == node_id:
                filtered_edges.append(self._convert_edge_to_dict(edge))
            elif direction == "outgoing" and edge['source'] == node_id:
                filtered_edges.append(self._convert_edge_to_dict(edge))
                
        return filtered_edges
    
    def get_nodes_by_type(self, node_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get nodes of a specific type.
        
        Args:
            node_type: The type of nodes to retrieve (e.g., 'function', 'class')
            limit: Maximum number of nodes to return
            
        Returns:
            List of matching node dictionaries
        """
        return self.list_nodes(filters={'node_type': node_type}, limit=limit)
    
    def get_nodes_by_filepath(self, filepath: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get nodes from a specific file.
        
        Args:
            filepath: The path of the file
            limit: Maximum number of nodes to return
            
        Returns:
            List of matching node dictionaries
        """
        nodes = self.graph_manager.storage.get_nodes_for_file(filepath)
        return [self._convert_node_to_dict(node) for node in nodes[:limit]]
    
    def find_functions_calling(self, function_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find functions that call a specific function.
        
        Args:
            function_id: The ID of the function to find callers for
            limit: Maximum number of results to return
            
        Returns:
            List of function node dictionaries that call the specified function
        """
        # Get edges where target is the specified function and type is 'calls'
        edges = self.list_edges_for_node(function_id, direction="incoming")
        caller_ids = [edge['source'] for edge in edges if edge['edge_type'] == 'calls']
        
        # Get node details for each caller
        callers = []
        for caller_id in caller_ids[:limit]:
            node = self.get_node_details(caller_id)
            if node and node['node_type'] == 'function':
                callers.append(node)
                
        return callers
    
    def find_functions_called_by(self, function_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find functions that are called by a specific function.
        
        Args:
            function_id: The ID of the calling function
            limit: Maximum number of results to return
            
        Returns:
            List of function node dictionaries that are called by the specified function
        """
        # Get edges where source is the specified function and type is 'calls'
        edges = self.list_edges_for_node(function_id, direction="outgoing")
        callee_ids = [edge['target'] for edge in edges if edge['edge_type'] == 'calls']
        
        # Get node details for each callee
        callees = []
        for callee_id in callee_ids[:limit]:
            node = self.get_node_details(callee_id)
            if node and node['node_type'] == 'function':
                callees.append(node)
                
        return callees
    
    def find_functions_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find functions that match a keyword in their name or parameters.
        
        Args:
            keyword: The keyword to search for
            limit: Maximum number of results to return
            
        Returns:
            List of function node dictionaries matching the keyword
        """
        # Get all nodes of type 'function'
        function_nodes = self.get_nodes_by_type('function')
        
        # Filter by keyword
        matches = []
        for node in function_nodes:
            # Check name
            if keyword.lower() in node.get('name', '').lower():
                matches.append(node)
                continue
                
            # Check parameters (if available)
            if 'parameters' in node:
                for param in node['parameters']:
                    if isinstance(param, str) and keyword.lower() in param.lower():
                        matches.append(node)
                        break
            
            if len(matches) >= limit:
                break
                
        return matches[:limit]
    
    def find_functions_calling_filepath(self, filepath: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find functions that call any function defined in the specified filepath.
        
        Args:
            filepath: The filepath to search for
            limit: Maximum number of results to return
            
        Returns:
            List of function node dictionaries that call functions in the specified filepath
        """
        # Get all nodes in the specified filepath
        file_nodes = self.get_nodes_by_filepath(filepath)
        
        # Filter to function nodes
        function_nodes = [node for node in file_nodes if node['node_type'] == 'function']
        
        # Get all callers of these functions
        callers = []
        caller_ids = set()  # To avoid duplicates
        
        for function in function_nodes:
            function_callers = self.find_functions_calling(function['node_id'])
            for caller in function_callers:
                if caller['node_id'] not in caller_ids:
                    callers.append(caller)
                    caller_ids.add(caller['node_id'])
                    
                    if len(callers) >= limit:
                        break
            
            if len(callers) >= limit:
                break
                
        return callers
    
    # --- Helper Methods ---
    
    def _convert_node_to_dict(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a node data dictionary to a standardized format for output.
        
        Args:
            node_data: The raw node data from storage
            
        Returns:
            A standardized node dictionary
        """
        # Create a copy to avoid modifying the original
        result = {
            "node_id": node_data.get('id', 'unknown_id'),
            "node_type": node_data.get('node_type'),
            "filepath": node_data.get('filepath'),
        }
        
        # Add specific fields based on node type
        if node_data.get('node_type') == 'function':
            result.update({
                "name": node_data.get('name'),
                "parameters": node_data.get('parameters', []),
                "start_line": node_data.get('start_point', [0, 0])[0] + 1 if 'start_point' in node_data else None,
                "end_line": node_data.get('end_point', [0, 0])[0] + 1 if 'end_point' in node_data else None,
            })
        elif node_data.get('node_type') == 'class':
            result.update({
                "name": node_data.get('name'),
                "methods": node_data.get('methods', []),
                "start_line": node_data.get('start_point', [0, 0])[0] + 1 if 'start_point' in node_data else None,
                "end_line": node_data.get('end_point', [0, 0])[0] + 1 if 'end_point' in node_data else None,
            })
        elif node_data.get('node_type') == 'import':
            result.update({
                "module": node_data.get('module'),
                "names": node_data.get('names', []),
                "line": node_data.get('start_point', [0, 0])[0] + 1 if 'start_point' in node_data else None,
            })
            
        # Include a filtered set of metadata, avoiding large fields
        metadata = {}
        for key, value in node_data.items():
            if key not in result and key not in ['id', 'body', 'code'] and not isinstance(value, (set, list, dict)) or len(str(value)) < 100:
                metadata[key] = value
                
        if metadata:
            result["metadata"] = metadata
            
        return result

    def _convert_edge_to_dict(self, edge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert an edge data dictionary to a standardized format for output.
        
        Args:
            edge_data: The raw edge data from storage
            
        Returns:
            A standardized edge dictionary
        """
        return {
            "source": edge_data.get('source', 'unknown_source'),
            "target": edge_data.get('target', 'unknown_target'),
            "edge_type": edge_data.get('type'),
            "metadata": {k: v for k, v in edge_data.items() 
                        if k not in ['source', 'target', 'type', 'id']}
        }

    # --- MCP Tool Handlers ---
    
    async def handle_list_nodes(self, request: CallToolRequest) -> CallToolResult:
        """
        MCP handler for listing nodes.
        
        Args:
            request: The MCP tool call request
            
        Returns:
            MCP tool call result
        """
        try:
            arguments = request.params.arguments or {}
            
            # Extract filters if provided
            filters = arguments.get("filters")
            limit = arguments.get("limit", 10)
            
            if not isinstance(limit, int) or limit <= 0:
                limit = 10
                
            nodes = self.list_nodes(filters=filters, limit=limit)
            
            # Return as JSON string
            result_json = json.dumps({"nodes": nodes})
            return CallToolResult(content=[TextContent(type="text", text=result_json)])
            
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error listing nodes: {str(e)}")]
            )
    
    async def handle_get_node_details(self, request: CallToolRequest) -> CallToolResult:
        """
        MCP handler for getting node details.
        
        Args:
            request: The MCP tool call request
            
        Returns:
            MCP tool call result
        """
        try:
            arguments = request.params.arguments or {}
            node_id = arguments.get("node_id")
            
            if not node_id or not isinstance(node_id, str):
                raise ValueError("Missing or invalid 'node_id' argument")
                
            node = self.get_node_details(node_id)
            
            if node:
                return CallToolResult(content=[TextContent(type="text", text=json.dumps(node))])
            else:
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Node '{node_id}' not found")]
                )
                
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error getting node details: {str(e)}")]
            )
    
    async def handle_search_nodes(self, request: CallToolRequest) -> CallToolResult:
        """
        MCP handler for searching nodes.
        
        Args:
            request: The MCP tool call request
            
        Returns:
            MCP tool call result
        """
        try:
            arguments = request.params.arguments or {}
            keyword = arguments.get("keyword")
            limit = arguments.get("limit", 10)
            
            if not keyword or not isinstance(keyword, str):
                raise ValueError("Missing or invalid 'keyword' argument")
                
            if not isinstance(limit, int) or limit <= 0:
                limit = 10
                
            nodes = self.search_nodes(keyword=keyword, limit=limit)
            
            # Return as JSON string
            result_json = json.dumps({"nodes": nodes})
            return CallToolResult(content=[TextContent(type="text", text=result_json)])
            
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error searching nodes: {str(e)}")]
            )
    
    async def handle_list_edges_for_node(self, request: CallToolRequest) -> CallToolResult:
        """
        MCP handler for listing edges for a node.
        
        Args:
            request: The MCP tool call request
            
        Returns:
            MCP tool call result
        """
        try:
            arguments = request.params.arguments or {}
            node_id = arguments.get("node_id")
            direction = arguments.get("direction", "both")
            
            if not node_id or not isinstance(node_id, str):
                raise ValueError("Missing or invalid 'node_id' argument")
                
            if direction not in ["incoming", "outgoing", "both"]:
                direction = "both"
                
            # Check if node exists
            if not self.graph_manager.storage.get_node(node_id):
                return CallToolResult(
                    isError=True,
                    content=[TextContent(type="text", text=f"Node '{node_id}' not found")]
                )
                
            edges = self.list_edges_for_node(node_id=node_id, direction=direction)
            
            # Return as JSON string
            result_json = json.dumps({"edges": edges})
            return CallToolResult(content=[TextContent(type="text", text=result_json)])
            
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error listing edges: {str(e)}")]
            )

    async def handle_find_functions_by_keyword(self, request: CallToolRequest) -> CallToolResult:
        """
        MCP handler for finding functions by keyword.
        
        Args:
            request: The MCP tool call request
            
        Returns:
            MCP tool call result
        """
        try:
            arguments = request.params.arguments or {}
            keyword = arguments.get("keyword")
            limit = arguments.get("limit", 10)
            
            if not keyword or not isinstance(keyword, str):
                raise ValueError("Missing or invalid 'keyword' argument")
                
            if not isinstance(limit, int) or limit <= 0:
                limit = 10
                
            functions = self.find_functions_by_keyword(keyword=keyword, limit=limit)
            
            # Return as JSON string
            result_json = json.dumps({"functions": functions})
            return CallToolResult(content=[TextContent(type="text", text=result_json)])
            
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error finding functions by keyword: {str(e)}")]
            )
    
    async def handle_find_functions_calling_filepath(self, request: CallToolRequest) -> CallToolResult:
        """
        MCP handler for finding functions that call functions in a specific filepath.
        
        Args:
            request: The MCP tool call request
            
        Returns:
            MCP tool call result
        """
        try:
            arguments = request.params.arguments or {}
            filepath = arguments.get("filepath")
            limit = arguments.get("limit", 10)
            
            if not filepath or not isinstance(filepath, str):
                raise ValueError("Missing or invalid 'filepath' argument")
                
            if not isinstance(limit, int) or limit <= 0:
                limit = 10
                
            functions = self.find_functions_calling_filepath(filepath=filepath, limit=limit)
            
            # Return as JSON string
            result_json = json.dumps({"functions": functions})
            return CallToolResult(content=[TextContent(type="text", text=result_json)])
            
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error finding functions calling filepath: {str(e)}")]
            )
    
    # --- MCP Tool Definitions ---
    
    def get_tools(self) -> List[Tool]:
        """
        Get the list of MCP tools provided by this class.
        
        Returns:
            List of MCP Tool objects
        """
        return [
            Tool(
                name="list_nodes",
                description="List nodes in the graph with optional filtering.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "description": "Optional filters to apply (e.g., {'node_type': 'function'})"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of nodes to return",
                            "default": 10
                        }
                    }
                },
                handler=self.handle_list_nodes
            ),
            Tool(
                name="get_node_details",
                description="Get detailed information about a specific node.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "The ID of the node to retrieve"
                        }
                    },
                    "required": ["node_id"]
                },
                handler=self.handle_get_node_details
            ),
            Tool(
                name="search_nodes",
                description="Search for nodes matching a keyword in ID or filepath.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "The search term to look for"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["keyword"]
                },
                handler=self.handle_search_nodes
            ),
            Tool(
                name="list_edges_for_node",
                description="List edges connected to a specific node.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "The ID of the node"
                        },
                        "direction": {
                            "type": "string",
                            "description": "Which edges to include: 'incoming', 'outgoing', or 'both'",
                            "enum": ["incoming", "outgoing", "both"],
                            "default": "both"
                        }
                    },
                    "required": ["node_id"]
                },
                handler=self.handle_list_edges_for_node
            ),
            Tool(
                name="find_functions_by_keyword",
                description="Find functions that match a keyword in their name or parameters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "The keyword to search for in function names or parameters"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["keyword"]
                },
                handler=self.handle_find_functions_by_keyword
            ),
            Tool(
                name="find_functions_calling_filepath",
                description="Find functions that call any function defined in the specified filepath.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "The filepath to find callers for"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10
                        }
                    },
                    "required": ["filepath"]
                },
                handler=self.handle_find_functions_calling_filepath
            )
        ] 