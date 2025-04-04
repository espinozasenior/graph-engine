import sys
import os
import json
import asyncio
from typing import Any, Dict, List, Optional
import re # Import regex module

# Explicitly add project root to sys.path BEFORE graph_core import attempt
_THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import server and necessary types from mcp.types
from mcp import server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    TextContent,
    Tool,
)

try:
    # These are project-specific, imported separately
    from graph_core.manager import DependencyGraphManager, DEFAULT_JSON_PATH
    from graph_core.storage.json_storage import JSONGraphStorage
except ImportError as e:
    print(f"Error importing graph_core modules: {e}", file=sys.stderr)
    print("Original sys.path for debug:", sys.path, file=sys.stderr) # Add path print on error
    print("Ensure graph_core is installed or accessible in the Python path.", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
# Use the path provided by env var for testing, otherwise default
# PROJECT_ROOT already calculated above
_env_path = os.environ.get("GRAPH_STORAGE_PATH")
if _env_path and os.path.isabs(_env_path):
    # If env var provides an absolute path, use it directly
    GRAPH_JSON_FULL_PATH = _env_path
    print(f"DEBUG: Using absolute graph path from env var: {GRAPH_JSON_FULL_PATH}", file=sys.stderr)
else:
    # Otherwise, construct path relative to project root (using default or relative env var)
    GRAPH_JSON_PATH = _env_path or DEFAULT_JSON_PATH
    GRAPH_JSON_FULL_PATH = os.path.join(PROJECT_ROOT, GRAPH_JSON_PATH)
    print(f"DEBUG: Using relative graph path: {GRAPH_JSON_PATH} -> {GRAPH_JSON_FULL_PATH}", file=sys.stderr)

# Ensure the directory exists if using the default path relative to root
os.makedirs(os.path.dirname(GRAPH_JSON_FULL_PATH), exist_ok=True)

# --- Dependency Graph Manager Instance ---
try:
    # Pass the path as a positional argument
    storage = JSONGraphStorage(GRAPH_JSON_FULL_PATH) 
    # Load graph data on initialization if the file exists
    if os.path.exists(GRAPH_JSON_FULL_PATH):
        try:
            storage.load_graph()
        except Exception as load_err:
            print(f"Warning: Could not load graph from {GRAPH_JSON_FULL_PATH}. Starting with empty graph. Error: {load_err}", file=sys.stderr)
    else:
        print(f"Info: Graph storage file not found at {GRAPH_JSON_FULL_PATH}. Starting with empty graph.", file=sys.stderr)
        
    graph_manager = DependencyGraphManager(storage=storage)
except Exception as e:
    print(f"Fatal Error initializing DependencyGraphManager: {e}", file=sys.stderr)
    sys.exit(1)

# --- Helper Functions (Updated for Dictionary Access) ---
def _convert_node_to_dict(node_data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts node data dictionary (from storage) to a standardized dict."""
    # node_data is expected to be a dictionary from graph.nodes(data=True)
    # or the result of storage.get_node()
    node_id = node_data.get('id', 'unknown_id') # Use .get() and the correct key 'id'
    return {
        "node_id": node_id, # Keep consistent output key if desired, but fetch using 'id'
        "filepath": node_data.get('filepath'),
        "node_type": node_data.get('node_type'),
        "metadata": node_data.get('metadata', {})
    }

def _convert_edge_to_dict(edge_data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts edge data dictionary (from storage) to a standardized dict."""
    # edge_data is expected to be a dictionary from storage.get_edges_*
    return {
        "source": edge_data.get('source', 'unknown_source'),
        "target": edge_data.get('target', 'unknown_target'),
        "edge_type": edge_data.get('type'), # Use .get() and the correct key 'type'
        "metadata": edge_data.get('metadata', {})
    }

# Function to explicitly reload storage for testing
def _reload_graph_storage_for_testing():
    """Reloads graph data from the configured JSON file. For testing purposes only."""
    global storage # Access the global storage object
    try:
        # Print path for debugging
        print(f"DEBUG: Reloading graph for testing from: {GRAPH_JSON_FULL_PATH}", file=sys.stderr)
        
        # Check if file actually exists - if not, this is likely a test issue
        if not os.path.exists(GRAPH_JSON_FULL_PATH):
            print(f"ERROR: Test graph file not found at {GRAPH_JSON_FULL_PATH}!", file=sys.stderr)
            print(f"Current os.environ['GRAPH_STORAGE_PATH'] = {os.environ.get('GRAPH_STORAGE_PATH', 'NOT SET')}", file=sys.stderr)
            
        if os.path.exists(GRAPH_JSON_FULL_PATH):
            storage.load_graph() # Call the existing load method
            # Count loaded nodes and edges for debugging
            node_count = len(storage.graph.nodes)
            edge_count = len(storage.graph.edges) 
            print(f"DEBUG: Successfully loaded {node_count} nodes and {edge_count} edges", file=sys.stderr)
        else:
            # Clear existing data if file is gone during test run?
            storage.nodes = {}
            storage.edges = {}
            storage.file_to_nodes = {}
            print(f"DEBUG: Test graph file not found on reload: {GRAPH_JSON_FULL_PATH}. Cleared storage.", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Error reloading graph for testing: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

# --- MCP Tool Handlers (Correct argument access) ---
async def handle_get_node_info(request: CallToolRequest) -> CallToolResult:
    """Handles the 'get_node_info' MCP tool call."""
    try:
        # Access arguments via request.params.arguments
        arguments = request.params.arguments or {} # Use .arguments attribute, provide default dict
        node_id = arguments.get("node_id")
        if not node_id or not isinstance(node_id, str):
            raise ValueError("Missing or invalid 'node_id' argument.")
            
        node = graph_manager.storage.get_node(node_id)
        if node:
            node_data = _convert_node_to_dict(node)
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(node_data))])
        else:
            # Return error within MCP result structure
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Node '{node_id}' not found")]
            )
    except Exception as e:
        print(f"Error in handle_get_node_info: {e}", file=sys.stderr)
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

async def handle_search_nodes(request: CallToolRequest) -> CallToolResult:
    """Handles the 'search_nodes' MCP tool call."""
    try:
        # Access arguments via request.params.arguments
        arguments = request.params.arguments or {} # Use .arguments attribute, provide default dict
        query = arguments.get("query")
        limit = arguments.get("limit", 10) # Default limit
        if not query or not isinstance(query, str):
             raise ValueError("Missing or invalid 'query' argument.")
        if not isinstance(limit, int) or limit <= 0:
            limit = 10 # Reset to default if invalid

        # Get nodes directly as dictionaries from storage
        all_nodes = graph_manager.storage.get_all_nodes()
        matched_nodes_data = []
        for node_dict in all_nodes:
            match = False
            # Use .get() for safer access and check against 'id'
            if query.lower() in node_dict.get('id', '').lower():
                match = True
            elif node_dict.get('filepath') and query.lower() in node_dict['filepath'].lower():
                match = True

            if match:
                 # Pass the dictionary directly
                 matched_nodes_data.append(_convert_node_to_dict(node_dict))

            if len(matched_nodes_data) >= limit:
                break

        # Return JSON string within TextContent
        result_json = json.dumps({"nodes": matched_nodes_data})
        return CallToolResult(content=[TextContent(type="text", text=result_json)])

    except Exception as e:
        print(f"Error in handle_search_nodes: {e}", file=sys.stderr)
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

async def handle_list_edges(request: CallToolRequest) -> CallToolResult:
    """Handles the 'list_edges' MCP tool call."""
    try:
        # Access arguments via request.params.arguments
        arguments = request.params.arguments or {} # Use .arguments attribute, provide default dict
        node_id = arguments.get("node_id")
        if not node_id or not isinstance(node_id, str):
            raise ValueError("Missing or invalid 'node_id' argument.")

        if not graph_manager.storage.get_node(node_id):
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Node '{node_id}' not found")]
            )
             
        edges = graph_manager.storage.get_edges_for_nodes([node_id])
        edge_data = [_convert_edge_to_dict(edge) for edge in edges]
        
        # Return JSON string within TextContent
        result_json = json.dumps({"edges": edge_data})
        return CallToolResult(content=[TextContent(type="text", text=result_json)])

    except Exception as e:
        print(f"Error in handle_list_edges: {e}", file=sys.stderr)
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

# --- MCP Tool Definitions ---
GET_NODE_INFO_TOOL = Tool(
    name="get_node_info",
    description="Retrieve information about a specific node by its ID.",
    inputSchema={
        "type": "object",
        "properties": {
            "node_id": {"type": "string", "description": "The unique identifier of the node."}
        },
        "required": ["node_id"]
    },
    handler=handle_get_node_info
)

SEARCH_NODES_TOOL = Tool(
    name="search_nodes",
    description="Search for nodes based on a query string (e.g., in name or filepath).",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query string."},
            "limit": {"type": "integer", "description": "Maximum number of results to return.", "default": 10}
        },
        "required": ["query"]
    },
    handler=handle_search_nodes
)

LIST_EDGES_TOOL = Tool(
    name="list_edges",
    description="List all incoming and outgoing edges connected to a specific node.",
    inputSchema={
        "type": "object",
        "properties": {
            "node_id": {"type": "string", "description": "The unique identifier of the node."}
        },
        "required": ["node_id"]
    },
    handler=handle_list_edges
)

# --- Natural Language Interpretation --- 

async def interpret_llm_request(request_text: str) -> Dict[str, Any]:
    """Interprets a natural language request and maps it to graph operations.
    
    Args:
        request_text: The natural language query from the LLM.
        
    Returns:
        A dictionary containing the result (data or error message).
    """
    # Make debug output more readable
    print(f"\nDEBUG: Processing request: '{request_text}'", file=sys.stderr)
    
    request_text_lower = request_text.lower()
    response: Dict[str, Any] = {"status": "error", "message": "Could not understand the request."} # Default error

    # --- Intent Recognition and Argument Extraction --- 
    
    # Pattern 1: Get Node Info (e.g., "info about node1", "details for my_function", "what is class A?")
    match_info = re.search(r"(?:info about|details for|what is|describe)(?:\s+|[\s`])(node[0-9a-zA-Z_-]+|[a-zA-Z0-9_-]+)", request_text_lower, re.IGNORECASE)
    if match_info:
        node_id = match_info.group(1).strip().replace('`', '')
        print(f"DEBUG: Intent=get_node_info, node_id='{node_id}'", file=sys.stderr)
        request = CallToolRequest(method="tools/call", params={"name": "get_node_info", "arguments": {"node_id": node_id}})
        result: CallToolResult = await handle_get_node_info(request)
        if result.isError:
            response["message"] = result.content[0].text
        else:
            try:
                data = json.loads(result.content[0].text)
                response = {"status": "success", "type": "node_info", "data": data}
            except json.JSONDecodeError:
                 response["message"] = "Failed to parse node info result."
        return response

    # Pattern 2: List Edges (e.g., "edges for node1", "connections to `my_func`", "what calls X?", "references for Y")
    match_edges = re.search(r"(?:edges for|connections to|connections from|calls to|references for|what calls|what uses|related to)(?:\s+|[\s`])(node[0-9a-zA-Z_-]+|[a-zA-Z0-9_-]+)", request_text_lower, re.IGNORECASE)
    if match_edges:
        node_id = match_edges.group(1).strip().replace('`', '')
        print(f"DEBUG: Intent=list_edges, node_id='{node_id}'", file=sys.stderr)
        request = CallToolRequest(method="tools/call", params={"name": "list_edges", "arguments": {"node_id": node_id}})
        result: CallToolResult = await handle_list_edges(request)
        if result.isError:
            response["message"] = result.content[0].text
        else:
            try:
                data = json.loads(result.content[0].text)
                response = {"status": "success", "type": "edge_list", "data": data}
            except json.JSONDecodeError:
                 response["message"] = "Failed to parse edge list result."
        return response

    # Pattern 3: Search Nodes (e.g., "search for function X", "find nodes matching Y", "look for Z in path/to/file.py")
    match_search = re.search(r"(?:search for|find nodes matching|find|look for) +(.+)", request_text_lower, re.IGNORECASE)
    # Basic limit extraction (optional)
    limit = 10
    match_limit = re.search(r"limit(?:ed to)? +(\d+)", request_text_lower, re.IGNORECASE)
    if match_limit:
        try:
            limit = int(match_limit.group(1))
        except ValueError:
            pass # Ignore invalid limit
            
    if match_search:
        query = match_search.group(1).strip()
        # Refine query if limit was mentioned
        if match_limit:
             query = re.sub(r"limit(?:ed to)? +\d+", "", query, flags=re.IGNORECASE).strip()
             query = re.sub(r" with $", "", query, flags=re.IGNORECASE).strip() # Remove trailing ' with '
             
        print(f"DEBUG: Intent=search_nodes, query='{query}', limit={limit}", file=sys.stderr)
        request = CallToolRequest(method="tools/call", params={"name": "search_nodes", "arguments": {"query": query, "limit": limit}})
        result: CallToolResult = await handle_search_nodes(request)
        # Search always returns success status code, check results list length
        try:
            data = json.loads(result.content[0].text)
            response = {"status": "success", "type": "search_results", "data": data}
        except json.JSONDecodeError:
            response["message"] = "Failed to parse search results."
        return response

    # If no pattern matched
    print(f"DEBUG: Intent=unknown, request='{request_text}'", file=sys.stderr)
    return response

# --- Main Server Logic ---
async def main():
    mcp_server = server.Server(
        tools=[GET_NODE_INFO_TOOL, SEARCH_NODES_TOOL, LIST_EDGES_TOOL],
        # No resources or prompts defined in this version
        prompts=[],
        resources=[]
    )
    # Use stdio for communication as per MCP standard practice
    await server.stdio_main(mcp_server)

# Example usage (for testing purposes, can be removed later)
async def test_interpreter():
    print("--- Testing Interpreter ---")
    test_queries = [
        "info about `node1`",
        "what is node2",
        "describe nodeX", # Should fail
        "edges for node1",
        "connections to node2",
        "what calls node3?",
        "references for node4", # Should fail
        "search for file1.py",
        "find nodes matching node",
        "look for class",
        "find node with limit 5", # Test limit
        "gibberish request"
    ]
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = await interpret_llm_request(query)
        print(f"Result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    print(f"Starting MCP Graph Engine Server using graph: {GRAPH_JSON_FULL_PATH}", file=sys.stderr)
    # asyncio.run(main()) # Comment out main server run for testing interpreter
    
    # Run the test interpreter function if this script is run directly
    # Ensure test graph exists for this test
    test_graph_path = os.environ.get("GRAPH_STORAGE_PATH")
    if not test_graph_path or not os.path.exists(test_graph_path):
         print("WARNING: Test graph JSON not found. Interpreter tests might fail or give empty results.", file=sys.stderr)
         print(f"Expected at: {test_graph_path}", file=sys.stderr)
         # Optionally create a dummy one here if needed for standalone testing
    else: 
        # Reload storage just in case if test file exists
        _reload_graph_storage_for_testing()
        
    asyncio.run(test_interpreter()) # Run the test function 