#!/usr/bin/env python3
"""
Unified Graph Engine Server

This script provides a unified server that combines both the MCP Protocol and 
the web frontend for the Graph Engine. It replaces the REST API with MCP for 
backend functionality while still serving the web UI.
"""

import os
import sys
import argparse
import logging
import threading
import asyncio
import json
import uvicorn
from typing import Dict, Any, List, Optional

# Import FastAPI for the web server (frontend only)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse

# Import server and necessary types from MCP
from mcp import server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    TextContent,
    Tool,
)

# Import Graph Engine components
from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.storage.json_storage import JSONGraphStorage
from graph_core.manager import DependencyGraphManager, DEFAULT_JSON_PATH
from graph_core.watchers.file_watcher import start_file_watcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration and Argument Parsing ---

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run the unified Graph Engine Server with MCP and frontend support.'
    )
    parser.add_argument(
        '--host', default='127.0.0.1',
        help='Host to bind the web server to. Default: 127.0.0.1'
    )
    parser.add_argument(
        '--port', type=int, default=8000,
        help='Port to bind the web server to. Default: 8000'
    )
    parser.add_argument(
        '--watch-dir', '-w', default='src',
        help='Directory to watch for file changes. Default: src/'
    )
    parser.add_argument(
        '--storage-path', default=DEFAULT_JSON_PATH,
        help=f'Path to the JSON storage file. Default: {DEFAULT_JSON_PATH}'
    )
    parser.add_argument(
        '--in-memory', action='store_true',
        help='Use in-memory storage instead of JSON file.'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--disable-cors', action='store_true',
        help='Disable CORS middleware for development'
    )
    parser.add_argument(
        '--mcp-only', action='store_true',
        help='Run only the MCP server without the web frontend'
    )
    parser.add_argument(
        '--web-only', action='store_true',
        help='Run only the web server without the MCP server'
    )
    return parser.parse_args()

# --- MCP Server Implementation ---

# Helper Functions
def _convert_node_to_dict(node_data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts node data dictionary (from storage) to a standardized dict."""
    # node_data is expected to be a dictionary from graph.nodes(data=True)
    # or the result of storage.get_node()
    node_id = node_data.get('id', 'unknown_id')
    return {
        "node_id": node_id,
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
        "edge_type": edge_data.get('type'),
        "metadata": edge_data.get('metadata', {})
    }

# MCP Tool Handlers
async def handle_get_node_info(request: CallToolRequest, graph_manager: DependencyGraphManager) -> CallToolResult:
    """Handles the 'get_node_info' MCP tool call."""
    try:
        arguments = request.params.arguments or {}
        node_id = arguments.get("node_id")
        if not node_id or not isinstance(node_id, str):
            raise ValueError("Missing or invalid 'node_id' argument.")
            
        node = graph_manager.storage.get_node(node_id)
        if node:
            node_data = _convert_node_to_dict(node)
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(node_data))])
        else:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Node '{node_id}' not found")]
            )
    except Exception as e:
        logger.error(f"Error in handle_get_node_info: {e}")
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

async def handle_search_nodes(request: CallToolRequest, graph_manager: DependencyGraphManager) -> CallToolResult:
    """Handles the 'search_nodes' MCP tool call."""
    try:
        arguments = request.params.arguments or {}
        query = arguments.get("query")
        limit = arguments.get("limit", 10)
        if not query or not isinstance(query, str):
             raise ValueError("Missing or invalid 'query' argument.")
        if not isinstance(limit, int) or limit <= 0:
            limit = 10
            
        all_nodes = graph_manager.storage.get_all_nodes()
        matched_nodes_data = []
        for node_dict in all_nodes:
            match = False
            if query.lower() in node_dict.get('id', '').lower():
                match = True
            elif node_dict.get('filepath') and query.lower() in node_dict['filepath'].lower():
                match = True
            
            if match:
                matched_nodes_data.append(_convert_node_to_dict(node_dict))
            
            if len(matched_nodes_data) >= limit:
                break
        
        result_json = json.dumps({"nodes": matched_nodes_data})
        return CallToolResult(content=[TextContent(type="text", text=result_json)])
    except Exception as e:
        logger.error(f"Error in handle_search_nodes: {e}")
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

async def handle_list_edges(request: CallToolRequest, graph_manager: DependencyGraphManager) -> CallToolResult:
    """Handles the 'list_edges' MCP tool call."""
    try:
        arguments = request.params.arguments or {}
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
        
        result_json = json.dumps({"edges": edge_data})
        return CallToolResult(content=[TextContent(type="text", text=result_json)])
    except Exception as e:
        logger.error(f"Error in handle_list_edges: {e}")
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

async def handle_get_all_nodes(request: CallToolRequest, graph_manager: DependencyGraphManager) -> CallToolResult:
    """Handles the 'get_all_nodes' MCP tool call."""
    try:
        # Get optional limit
        arguments = request.params.arguments or {}
        limit = arguments.get("limit", -1)
        if not isinstance(limit, int):
            limit = -1
            
        all_nodes = graph_manager.storage.get_all_nodes()
        if limit > 0:
            all_nodes = all_nodes[:limit]
            
        node_data = [_convert_node_to_dict(node) for node in all_nodes]
        result_json = json.dumps({"nodes": node_data})
        return CallToolResult(content=[TextContent(type="text", text=result_json)])
    except Exception as e:
        logger.error(f"Error in handle_get_all_nodes: {e}")
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

async def handle_get_all_edges(request: CallToolRequest, graph_manager: DependencyGraphManager) -> CallToolResult:
    """Handles the 'get_all_edges' MCP tool call."""
    try:
        # Get optional limit
        arguments = request.params.arguments or {}
        limit = arguments.get("limit", -1)
        if not isinstance(limit, int):
            limit = -1
            
        all_edges = graph_manager.storage.get_all_edges()
        if limit > 0:
            all_edges = all_edges[:limit]
            
        edge_data = [_convert_edge_to_dict(edge) for edge in all_edges]
        result_json = json.dumps({"edges": edge_data})
        return CallToolResult(content=[TextContent(type="text", text=result_json)])
    except Exception as e:
        logger.error(f"Error in handle_get_all_edges: {e}")
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Internal server error: {str(e)}")]
        )

def create_mcp_server(graph_manager: DependencyGraphManager) -> server.Server:
    """Create an MCP server with tools for the graph engine."""
    
    # Define MCP tools using the graph manager
    get_node_info_tool = Tool(
        name="get_node_info",
        description="Retrieve information about a specific node by its ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "The unique identifier of the node."}
            },
            "required": ["node_id"]
        },
        handler=lambda req: handle_get_node_info(req, graph_manager)
    )
    
    search_nodes_tool = Tool(
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
        handler=lambda req: handle_search_nodes(req, graph_manager)
    )
    
    list_edges_tool = Tool(
        name="list_edges",
        description="List all incoming and outgoing edges connected to a specific node.",
        inputSchema={
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "The unique identifier of the node."}
            },
            "required": ["node_id"]
        },
        handler=lambda req: handle_list_edges(req, graph_manager)
    )
    
    # Add tools that replace the REST API endpoints
    get_all_nodes_tool = Tool(
        name="get_all_nodes",
        description="Get all nodes in the graph. Replaces /graph/nodes REST endpoint.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of nodes to return. -1 for all."}
            }
        },
        handler=lambda req: handle_get_all_nodes(req, graph_manager)
    )
    
    get_all_edges_tool = Tool(
        name="get_all_edges",
        description="Get all edges in the graph. Replaces /graph/edges REST endpoint.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of edges to return. -1 for all."}
            }
        },
        handler=lambda req: handle_get_all_edges(req, graph_manager)
    )
    
    # Create the MCP server with tools array parameter
    mcp_server = server.Server(
        tools=[
            get_node_info_tool, 
            search_nodes_tool, 
            list_edges_tool,
            get_all_nodes_tool,
            get_all_edges_tool
        ],
        prompts=[],
        resources=[]
    )
    
    return mcp_server

async def run_mcp_server(graph_manager: DependencyGraphManager) -> None:
    """Run the MCP server in a separate thread."""
    logger.info("Starting MCP server...")
    
    mcp_server = create_mcp_server(graph_manager)
    
    # Run the MCP server using stdio for communication
    await server.stdio_main(mcp_server)

def run_mcp_server_in_thread(graph_manager: DependencyGraphManager) -> threading.Thread:
    """Run the MCP server in a separate thread."""
    async def _run_mcp():
        try:
            await run_mcp_server(graph_manager)
        except Exception as e:
            logger.exception(f"Error in MCP server thread: {e}")
        
    def _thread_target():
        try:
            if sys.platform == 'win32':
                # Windows-specific event loop policy
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(_run_mcp())
        except Exception as e:
            logger.exception(f"Fatal error in MCP server thread: {e}")
    
    thread = threading.Thread(target=_thread_target, daemon=True)
    thread.start()
    logger.info("MCP server thread started")
    return thread

# --- Web Frontend Server Implementation ---

def create_frontend_app(graph_manager: DependencyGraphManager, disable_cors: bool = False) -> FastAPI:
    """Create a FastAPI app for serving the frontend with MCP Bridge API."""
    app = FastAPI(title="Graph Engine UI")
    
    # Add CORS middleware for frontend
    if not disable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # For development only
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS middleware enabled")
    
    # Mount the frontend static files
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    if os.path.exists(frontend_dir):
        app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")
        logger.info(f"Mounted frontend static files from {frontend_dir}")
        
        # Add a redirect from root to frontend
        @app.get("/")
        async def redirect_to_frontend():
            return RedirectResponse(url="/frontend/")
    else:
        logger.warning(f"Frontend directory not found at {frontend_dir}")
    
    # Create bridge API endpoints that call MCP tools internally
    # This allows the existing frontend to work unmodified
    @app.get("/graph/nodes")
    async def get_nodes():
        """Bridge API endpoint that calls the MCP get_all_nodes tool."""
        try:
            # Create a CallToolRequest for direct handler calls
            request = CallToolRequest(
                method="tools/call",
                params={"name": "get_all_nodes", "arguments": {}}
            )
            
            # Call the handler directly instead of creating an MCP server
            result = await handle_get_all_nodes(request, graph_manager)
            
            if result.isError:
                return JSONResponse(
                    status_code=500,
                    content={"error": result.content[0].text}
                )
                
            data = json.loads(result.content[0].text)
            return data["nodes"]
        except Exception as e:
            logger.error(f"Error in bridge API /graph/nodes: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )
    
    @app.get("/graph/edges")
    async def get_edges():
        """Bridge API endpoint that calls the MCP get_all_edges tool."""
        try:
            # Create a CallToolRequest for direct handler calls
            request = CallToolRequest(
                method="tools/call",
                params={"name": "get_all_edges", "arguments": {}}
            )
            
            # Call the handler directly instead of creating an MCP server
            result = await handle_get_all_edges(request, graph_manager)
            
            if result.isError:
                return JSONResponse(
                    status_code=500,
                    content={"error": result.content[0].text}
                )
                
            data = json.loads(result.content[0].text)
            return data["edges"]
        except Exception as e:
            logger.error(f"Error in bridge API /graph/edges: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )
    
    return app

# --- File Watcher ---

def start_watcher(manager: DependencyGraphManager, watch_dir: str) -> None:
    """Start the file watcher in a separate thread."""
    logger.info(f"Starting file watcher on directory: {watch_dir}")
    
    try:
        # File extensions to process
        supported_extensions = ('.py', '.js', '.jsx', '.ts', '.tsx')
        
        # Process existing files first
        for root, _, files in os.walk(watch_dir):
            for file in files:
                if file.endswith(supported_extensions):
                    filepath = os.path.join(root, file)
                    logger.debug(f"Processing existing file: {filepath}")
                    manager.on_file_event('created', filepath)
        
        # Start watching for changes
        start_file_watcher(
            callback=manager.on_file_event,
            watch_dir=watch_dir
        )
    except Exception as e:
        logger.exception(f"Error in file watcher: {str(e)}")

# --- Main Function ---

async def run_web_server(app: FastAPI, host: str, port: int) -> None:
    """Run the web server for the frontend."""
    config = uvicorn.Config(app, host=host, port=port)
    server = uvicorn.Server(config)
    await server.serve()

def create_mcp_server_for_stdio() -> server.Server:
    """Create a simple MCP server for stdio that acknowledges the unified server mode.
    
    This is used as a workaround for the fact that the MCP server will block waiting for
    stdio input, and we are running in a unified server mode where we don't expect direct
    MCP protocol messages via stdio.
    """
    async def handle_echo(request: CallToolRequest) -> CallToolResult:
        """Echo handler that acknowledges the request."""
        try:
            arguments = request.params.arguments or {}
            message = arguments.get("message", "No message provided")
            return CallToolResult(content=[TextContent(type="text", text=f"Unified server received: {message}")])
        except Exception as e:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=f"Error in echo handler: {str(e)}")]
            )
            
    echo_tool = Tool(
        name="echo",
        description="Echo the input message back. For testing the unified server's MCP capabilities.",
        inputSchema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to echo back."}
            }
        },
        handler=handle_echo
    )
    
    # Create the MCP server with tools array parameter
    mcp_server = server.Server(
        tools=[echo_tool],
        prompts=[],
        resources=[]
    )
    
    return mcp_server

async def run_mcp_server_in_unified_mode() -> None:
    """Run a simplified MCP server suitable for the unified server mode."""
    logger.info("Starting simplified MCP server for unified mode...")
    
    mcp_server = create_mcp_server_for_stdio()
    
    # Run the MCP server using stdio for communication
    await server.stdio_main(mcp_server)

async def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if watch directory exists
    if not os.path.isdir(args.watch_dir):
        logger.error(f"Watch directory does not exist: {args.watch_dir}")
        return 1
    
    try:
        # Create the graph storage
        logger.info("Initializing graph storage...")
        if args.in_memory:
            storage = InMemoryGraphStorage()
            logger.info("Using in-memory storage")
        else:
            # Get the storage path
            if os.path.isabs(args.storage_path):
                storage_path = args.storage_path
            else:
                storage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.storage_path)
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            
            storage = JSONGraphStorage(storage_path)
            logger.info(f"Using JSON storage at: {storage_path}")
        
        # Create the graph manager
        logger.info("Creating dependency graph manager...")
        manager = DependencyGraphManager(storage)
        
        # Start the file watcher in a separate thread
        watcher_thread = threading.Thread(
            target=start_watcher,
            args=(manager, args.watch_dir),
            daemon=True
        )
        watcher_thread.start()
        
        # Run the servers based on args
        if args.mcp_only:
            # Run only the MCP server
            logger.info("Running in MCP-only mode")
            
            # Print MCP server information
            print("\n" + "="*80)
            print(" GRAPH ENGINE: MCP SERVER MODE ".center(80, "="))
            print("="*80)
            print(f"MCP Server is running via standard input/output.")
            print(f"Connect to the MCP Server using an MCP client or a compatible tool.")
            print(f"Available MCP Tools:")
            
            # Define tools here directly instead of calling create_mcp_server
            get_node_info_tool = Tool(
                name="get_node_info",
                description="Retrieve information about a specific node by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string", "description": "The unique identifier of the node."}
                    },
                    "required": ["node_id"]
                },
                handler=lambda req: handle_get_node_info(req, manager)
            )
            print(f"  - get_node_info: Retrieve information about a specific node by its ID.")
            
            search_nodes_tool = Tool(
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
                handler=lambda req: handle_search_nodes(req, manager)
            )
            print(f"  - search_nodes: Search for nodes based on a query string.")
            
            list_edges_tool = Tool(
                name="list_edges",
                description="List all incoming and outgoing edges connected to a specific node.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string", "description": "The unique identifier of the node."}
                    },
                    "required": ["node_id"]
                },
                handler=lambda req: handle_list_edges(req, manager)
            )
            print(f"  - list_edges: List all incoming and outgoing edges connected to a specific node.")
            
            get_all_nodes_tool = Tool(
                name="get_all_nodes",
                description="Get all nodes in the graph. Replaces /graph/nodes REST endpoint.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of nodes to return. -1 for all."}
                    }
                },
                handler=lambda req: handle_get_all_nodes(req, manager)
            )
            print(f"  - get_all_nodes: Get all nodes in the graph.")
            
            get_all_edges_tool = Tool(
                name="get_all_edges",
                description="Get all edges in the graph. Replaces /graph/edges REST endpoint.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Maximum number of edges to return. -1 for all."}
                    }
                },
                handler=lambda req: handle_get_all_edges(req, manager)
            )
            print(f"  - get_all_edges: Get all edges in the graph.")
            
            print("="*80 + "\n")
            
            # Create server directly based on mcp_endpoint.py pattern
            mcp_server = server.Server(
                tools=[
                    get_node_info_tool, 
                    search_nodes_tool, 
                    list_edges_tool,
                    get_all_nodes_tool,
                    get_all_edges_tool
                ],
                prompts=[],
                resources=[]
            )
            
            # Run the MCP server
            await server.stdio_main(mcp_server)
            
        elif args.web_only:
            # Run only the web server
            logger.info("Running in web-only mode")
            
            # Create the web app
            app = create_frontend_app(manager, disable_cors=args.disable_cors)
            
            # Get a user-friendly host string
            host_str = args.host if args.host != "0.0.0.0" else "localhost"
            
            print("\n" + "="*80)
            print(" GRAPH ENGINE: WEB SERVER MODE ".center(80, "="))
            print("="*80)
            print(f"Web server running at: http://{host_str}:{args.port}")
            print(f"Frontend UI available at: http://{host_str}:{args.port}/frontend/")
            print(f"REST API endpoints:")
            print(f"  - GET http://{host_str}:{args.port}/graph/nodes - Get all nodes")
            print(f"  - GET http://{host_str}:{args.port}/graph/edges - Get all edges")
            print("="*80 + "\n")
            
            await run_web_server(app, args.host, args.port)
        else:
            # Run both servers
            logger.info("Running both MCP and web servers")
            
            # Create the web app
            app = create_frontend_app(manager, disable_cors=args.disable_cors)
            
            # Get a user-friendly host string
            host_str = args.host if args.host != "0.0.0.0" else "localhost"
            
            # Print unified server information
            print("\n" + "="*80)
            print(" GRAPH ENGINE: UNIFIED SERVER MODE ".center(80, "="))
            print("="*80)
            print(f"Web server running at: http://{host_str}:{args.port}")
            print(f"Frontend UI available at: http://{host_str}:{args.port}/frontend/")
            print(f"REST API endpoints:")
            print(f"  - GET http://{host_str}:{args.port}/graph/nodes - Get all nodes")
            print(f"  - GET http://{host_str}:{args.port}/graph/edges - Get all edges")
            print("\nGraph Manager is using storage: {0}".format(
                f"JSON file at {storage_path}" if not args.in_memory else "In-Memory"
            ))
            print(f"Watching directory: {args.watch_dir} for code changes")
            print("\nNOTE: The MCP server is running in background but is simplified in unified mode.")
            print("      To use full MCP functionality, run with --mcp-only flag.")
            print("\nSimplified MCP Tool available:")
            print(f"  - echo: Echo a message back (for MCP server testing)")
            print("\nPress Ctrl+C to exit.")
            print("="*80 + "\n")
            
            # Start the MCP server in a background thread - use simplified version for unified mode
            def _run_simplified_mcp():
                try:
                    logger.info("Starting simplified MCP server...")
                    
                    # Create server using FastMCP
                    logger.info("Starting simplified MCP server for unified mode...")
                    from mcp.server.fastmcp import FastMCP
                    
                    mcp_server = FastMCP("unified-graph-server")
                    
                    # Register echo tool using decorator
                    @mcp_server.tool()
                    def echo(message: str) -> str:
                        """Echo back a message"""
                        return f"Echo: {message}"
                    
                    # Run the MCP server
                    mcp_server.run(transport='stdio')
                    
                except Exception as e:
                    logger.exception(f"Error in simplified MCP server: {e}")
                    
            def _mcp_thread_target():
                try:
                    _run_simplified_mcp()
                except Exception as e:
                    logger.exception(f"Fatal error in simplified MCP server thread: {e}")
            
            mcp_thread = threading.Thread(target=_mcp_thread_target, daemon=True)
            mcp_thread.start()
            logger.info("Simplified MCP server thread started")
            
            # Create the web app
            app = create_frontend_app(manager, disable_cors=args.disable_cors)
            
            # Run the web server in the main thread
            logger.info(f"Starting web server at http://{host_str}:{args.port}")
            logger.info(f"Frontend available at http://{host_str}:{args.port}/frontend/")
            await run_web_server(app, args.host, args.port)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.exception(f"Error running unified server: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    if sys.platform == 'win32':
        # Windows-specific event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete.")