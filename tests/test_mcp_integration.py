import pytest
import json
import os
import sys
import asyncio
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

# Setup environment variable *before* importing the modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEST_GRAPH_FILENAME = "test_mcp_graph.json"
TEST_STORAGE_PATH = os.path.join(PROJECT_ROOT, 'tests', TEST_GRAPH_FILENAME)
os.environ["GRAPH_STORAGE_PATH"] = TEST_STORAGE_PATH

from mcp.types import CallToolRequest, TextContent
from graph_core.mcp_integration import GraphEngineMCP
from graph_core.storage.json_storage import JSONGraphStorage
from graph_core.manager import DependencyGraphManager

@pytest.fixture(scope="module", autouse=True)
def manage_test_graph_file():
    """Creates and cleans up the test graph JSON file."""
    # Clean up any old test graph file before starting
    if os.path.exists(TEST_STORAGE_PATH):
        os.remove(TEST_STORAGE_PATH)
        
    # Ensure the directory exists
    os.makedirs(os.path.dirname(TEST_STORAGE_PATH), exist_ok=True)
    
    # Create a dummy graph file for testing
    dummy_graph_data = {
        "nodes": [
            {"id": "node1", "filepath": "src/file1.py", "node_type": "function", "name": "function1", 
             "parameters": ["param1", "param2"], "start_point": [9, 0], "end_point": [14, 10]},
            {"id": "node2", "filepath": "src/file2.py", "node_type": "class", "name": "Class2", 
             "methods": ["method1", "method2"], "start_point": [5, 0], "end_point": [25, 10]},
            {"id": "node3", "filepath": "src/file1.py", "node_type": "variable", "name": "var3", 
             "start_point": [3, 0], "end_point": [3, 10]},
            {"id": "function:file1.function1", "filepath": "src/file1.py", "node_type": "function", 
             "name": "function1", "parameters": ["param1", "param2"]},
            {"id": "function:file1.function2", "filepath": "src/file1.py", "node_type": "function", 
             "name": "function2", "parameters": ["arg1"]},
            {"id": "function:file2.search_keyword", "filepath": "src/file2.py", "node_type": "function", 
             "name": "search_keyword", "parameters": ["keyword", "options"]}
        ],
        "edges": [
            {"source": "node1", "target": "node2", "type": "calls", "metadata": {}},
            {"source": "node3", "target": "node1", "type": "references", "metadata": {}},
            {"source": "function:file1.function1", "target": "function:file1.function2", "type": "calls", "metadata": {}},
            {"source": "function:file2.search_keyword", "target": "function:file1.function2", "type": "calls", "metadata": {}}
        ],
        "file_nodes": {
            "src/file1.py": ["node1", "node3", "function:file1.function1", "function:file1.function2"],
            "src/file2.py": ["node2", "function:file2.search_keyword"]
        }
    }
    with open(TEST_STORAGE_PATH, 'w') as f:
        json.dump(dummy_graph_data, f)

    # Let tests run
    yield

    # Clean up the test graph file after tests run
    if os.path.exists(TEST_STORAGE_PATH):
        os.remove(TEST_STORAGE_PATH)


@pytest.fixture
def mcp_integration():
    """Returns a GraphEngineMCP instance configured to use the test graph file."""
    # Create a fresh instance for each test to ensure clean state
    json_storage = JSONGraphStorage(TEST_STORAGE_PATH)
    
    # Force reload the graph from file
    if os.path.exists(TEST_STORAGE_PATH):
        json_storage.load_graph()
    
    graph_manager = DependencyGraphManager(storage=json_storage)
    
    return GraphEngineMCP(graph_manager=graph_manager)


class TestGraphEngineMCP:
    """Tests for the GraphEngineMCP class."""
    
    def test_init(self, mcp_integration):
        """Test that the GraphEngineMCP initializes properly."""
        assert mcp_integration is not None
        assert mcp_integration.graph_manager is not None
        assert mcp_integration.graph_manager.storage is not None
    
    def test_list_nodes_no_filter(self, mcp_integration):
        """Test listing nodes without filters."""
        nodes = mcp_integration.list_nodes(limit=10)
        assert len(nodes) > 0
        assert "node_id" in nodes[0]
        assert "node_type" in nodes[0]
        assert "filepath" in nodes[0]
    
    def test_list_nodes_with_filter(self, mcp_integration):
        """Test listing nodes with filters."""
        # Filter by node type
        nodes = mcp_integration.list_nodes(filters={"node_type": "function"})
        assert len(nodes) > 0
        assert all(node["node_type"] == "function" for node in nodes)
        
        # Filter by filepath
        nodes = mcp_integration.list_nodes(filters={"filepath": "src/file2.py"})
        assert len(nodes) > 0
        assert all(node["filepath"] == "src/file2.py" for node in nodes)
    
    def test_get_node_details_found(self, mcp_integration):
        """Test getting details for an existing node."""
        node = mcp_integration.get_node_details("node1")
        assert node is not None
        assert node["node_id"] == "node1"
        assert node["node_type"] == "function"
        assert node["filepath"] == "src/file1.py"
        assert "name" in node
        assert "parameters" in node
        assert "start_line" in node
        assert "end_line" in node
    
    def test_get_node_details_not_found(self, mcp_integration):
        """Test getting details for a non-existent node."""
        node = mcp_integration.get_node_details("nonexistent_node")
        assert node is None
    
    def test_search_nodes(self, mcp_integration):
        """Test searching for nodes by keyword."""
        # Search by node ID
        nodes = mcp_integration.search_nodes("node1")
        assert len(nodes) > 0
        assert any(node["node_id"] == "node1" for node in nodes)
        
        # Search by filepath
        nodes = mcp_integration.search_nodes("file1.py")
        assert len(nodes) > 0
        assert all("file1.py" in node["filepath"] for node in nodes)
        
        # Search with limit
        nodes = mcp_integration.search_nodes("node", limit=1)
        assert len(nodes) == 1
    
    def test_list_edges_for_node_both_directions(self, mcp_integration):
        """Test listing edges for a node in both directions."""
        edges = mcp_integration.list_edges_for_node("node1")
        assert len(edges) == 2  # node1 -> node2 and node3 -> node1
        
        # Check edge properties
        assert any(edge["source"] == "node1" and edge["target"] == "node2" for edge in edges)
        assert any(edge["source"] == "node3" and edge["target"] == "node1" for edge in edges)
    
    def test_list_edges_for_node_outgoing(self, mcp_integration):
        """Test listing outgoing edges for a node."""
        edges = mcp_integration.list_edges_for_node("node1", direction="outgoing")
        assert len(edges) == 1  # Only node1 -> node2
        assert edges[0]["source"] == "node1"
        assert edges[0]["target"] == "node2"
    
    def test_list_edges_for_node_incoming(self, mcp_integration):
        """Test listing incoming edges for a node."""
        edges = mcp_integration.list_edges_for_node("node1", direction="incoming")
        assert len(edges) == 1  # Only node3 -> node1
        assert edges[0]["source"] == "node3"
        assert edges[0]["target"] == "node1"
    
    def test_get_nodes_by_type(self, mcp_integration):
        """Test getting nodes by type."""
        nodes = mcp_integration.get_nodes_by_type("function")
        assert len(nodes) > 0
        assert all(node["node_type"] == "function" for node in nodes)
    
    def test_get_nodes_by_filepath(self, mcp_integration):
        """Test getting nodes by filepath."""
        nodes = mcp_integration.get_nodes_by_filepath("src/file1.py")
        assert len(nodes) > 0
        assert all(node["filepath"] == "src/file1.py" for node in nodes)
    
    def test_find_functions_calling(self, mcp_integration):
        """Test finding functions that call a specific function."""
        callers = mcp_integration.find_functions_calling("function:file1.function2")
        assert len(callers) > 0
        assert any(caller["node_id"] == "function:file1.function1" for caller in callers)
        assert any(caller["node_id"] == "function:file2.search_keyword" for caller in callers)
    
    def test_find_functions_called_by(self, mcp_integration):
        """Test finding functions called by a specific function."""
        callees = mcp_integration.find_functions_called_by("function:file1.function1")
        assert len(callees) > 0
        assert any(callee["node_id"] == "function:file1.function2" for callee in callees)
        
    def test_find_functions_by_keyword(self, mcp_integration):
        """Test finding functions that match a keyword in their name or parameters."""
        # Find by function name
        functions = mcp_integration.find_functions_by_keyword("search")
        assert len(functions) > 0
        assert any(function["name"] == "search_keyword" for function in functions)
        
        # Find by parameter name
        functions = mcp_integration.find_functions_by_keyword("keyword")
        assert len(functions) > 0
        assert any(function["name"] == "search_keyword" for function in functions)
        
        # Test with limit
        functions = mcp_integration.find_functions_by_keyword("function", limit=1)
        assert len(functions) == 1
    
    def test_find_functions_calling_filepath(self, mcp_integration):
        """Test finding functions that call functions in a specific filepath."""
        # Find functions calling functions in file1.py
        functions = mcp_integration.find_functions_calling_filepath("src/file1.py")
        assert len(functions) > 0
        assert any(function["node_id"] == "function:file2.search_keyword" for function in functions)
        
        # Test with non-existent filepath
        functions = mcp_integration.find_functions_calling_filepath("nonexistent_file.py")
        assert len(functions) == 0
        
        # Test with limit
        functions = mcp_integration.find_functions_calling_filepath("src/file1.py", limit=1)
        assert len(functions) <= 1


class TestGraphEngineMCPHandlers:
    """Tests for the MCP tool handlers."""
    
    @pytest.mark.asyncio
    async def test_handle_list_nodes(self, mcp_integration):
        """Test the list_nodes MCP handler."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "list_nodes", "arguments": {"limit": 5}}
        )
        result = await mcp_integration.handle_list_nodes(request)
        
        assert not result.isError
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        
        data = json.loads(result.content[0].text)
        assert "nodes" in data
        assert len(data["nodes"]) <= 5
    
    @pytest.mark.asyncio
    async def test_handle_get_node_details_found(self, mcp_integration):
        """Test the get_node_details MCP handler for an existing node."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "get_node_details", "arguments": {"node_id": "node1"}}
        )
        result = await mcp_integration.handle_get_node_details(request)
        
        assert not result.isError
        assert len(result.content) == 1
        
        data = json.loads(result.content[0].text)
        assert data["node_id"] == "node1"
    
    @pytest.mark.asyncio
    async def test_handle_get_node_details_not_found(self, mcp_integration):
        """Test the get_node_details MCP handler for a non-existent node."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "get_node_details", "arguments": {"node_id": "nonexistent"}}
        )
        result = await mcp_integration.handle_get_node_details(request)
        
        assert result.isError
        assert "not found" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_handle_search_nodes(self, mcp_integration):
        """Test the search_nodes MCP handler."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "search_nodes", "arguments": {"keyword": "file1.py", "limit": 3}}
        )
        result = await mcp_integration.handle_search_nodes(request)
        
        assert not result.isError
        
        data = json.loads(result.content[0].text)
        assert "nodes" in data
        assert len(data["nodes"]) <= 3
        assert all("file1.py" in node["filepath"] for node in data["nodes"])
    
    @pytest.mark.asyncio
    async def test_handle_list_edges_for_node(self, mcp_integration):
        """Test the list_edges_for_node MCP handler."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "list_edges_for_node", "arguments": {"node_id": "node1", "direction": "both"}}
        )
        result = await mcp_integration.handle_list_edges_for_node(request)
        
        assert not result.isError
        
        data = json.loads(result.content[0].text)
        assert "edges" in data
        assert len(data["edges"]) == 2  # node1 -> node2 and node3 -> node1
    
    @pytest.mark.asyncio
    async def test_handle_list_edges_for_node_not_found(self, mcp_integration):
        """Test the list_edges_for_node MCP handler for a non-existent node."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "list_edges_for_node", "arguments": {"node_id": "nonexistent"}}
        )
        result = await mcp_integration.handle_list_edges_for_node(request)
        
        assert result.isError
        assert "not found" in result.content[0].text
        
    @pytest.mark.asyncio
    async def test_handle_find_functions_by_keyword(self, mcp_integration):
        """Test the find_functions_by_keyword MCP handler."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "find_functions_by_keyword", "arguments": {"keyword": "search", "limit": 5}}
        )
        result = await mcp_integration.handle_find_functions_by_keyword(request)
        
        assert not result.isError
        assert len(result.content) == 1
        
        data = json.loads(result.content[0].text)
        assert "functions" in data
        assert any(function["name"] == "search_keyword" for function in data["functions"])
        
    @pytest.mark.asyncio
    async def test_handle_find_functions_by_keyword_not_found(self, mcp_integration):
        """Test the find_functions_by_keyword MCP handler with no matches."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "find_functions_by_keyword", "arguments": {"keyword": "nonexistent_keyword"}}
        )
        result = await mcp_integration.handle_find_functions_by_keyword(request)
        
        assert not result.isError
        
        data = json.loads(result.content[0].text)
        assert "functions" in data
        assert len(data["functions"]) == 0
        
    @pytest.mark.asyncio
    async def test_handle_find_functions_by_keyword_missing_argument(self, mcp_integration):
        """Test the find_functions_by_keyword MCP handler with a missing keyword argument."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "find_functions_by_keyword", "arguments": {}}
        )
        result = await mcp_integration.handle_find_functions_by_keyword(request)
        
        assert result.isError
        assert "Missing or invalid 'keyword' argument" in result.content[0].text
        
    @pytest.mark.asyncio
    async def test_handle_find_functions_calling_filepath(self, mcp_integration):
        """Test the find_functions_calling_filepath MCP handler."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "find_functions_calling_filepath", "arguments": {"filepath": "src/file1.py"}}
        )
        result = await mcp_integration.handle_find_functions_calling_filepath(request)
        
        assert not result.isError
        
        data = json.loads(result.content[0].text)
        assert "functions" in data
        assert any(function["node_id"] == "function:file2.search_keyword" for function in data["functions"])
        
    @pytest.mark.asyncio
    async def test_handle_find_functions_calling_filepath_not_found(self, mcp_integration):
        """Test the find_functions_calling_filepath MCP handler with no matches."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "find_functions_calling_filepath", "arguments": {"filepath": "nonexistent_file.py"}}
        )
        result = await mcp_integration.handle_find_functions_calling_filepath(request)
        
        assert not result.isError
        
        data = json.loads(result.content[0].text)
        assert "functions" in data
        assert len(data["functions"]) == 0
        
    @pytest.mark.asyncio
    async def test_handle_find_functions_calling_filepath_missing_argument(self, mcp_integration):
        """Test the find_functions_calling_filepath MCP handler with a missing filepath argument."""
        request = CallToolRequest(
            method="tools/call",
            params={"name": "find_functions_calling_filepath", "arguments": {}}
        )
        result = await mcp_integration.handle_find_functions_calling_filepath(request)
        
        assert result.isError
        assert "Missing or invalid 'filepath' argument" in result.content[0].text
    
    def test_get_tools(self, mcp_integration):
        """Test that the get_tools method returns the expected tools."""
        tools = mcp_integration.get_tools()
        
        # Check that we have the expected number of tools
        assert len(tools) == 6
        
        # Check that we have tools with the expected names
        tool_names = [tool.name for tool in tools]
        assert "list_nodes" in tool_names
        assert "get_node_details" in tool_names
        assert "search_nodes" in tool_names
        assert "list_edges_for_node" in tool_names
        assert "find_functions_by_keyword" in tool_names
        assert "find_functions_calling_filepath" in tool_names 