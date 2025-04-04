import pytest
import json
import os
import sys
import asyncio

# Removed sys.path printing and manipulation - rely on editable install

from mcp.types import CallToolRequest, TextContent

# Setup environment variable *before* importing the module that uses it
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Keep for path construction
TEST_GRAPH_FILENAME = "test_mcp_graph.json"
TEST_STORAGE_PATH = os.path.join(PROJECT_ROOT, 'tests', TEST_GRAPH_FILENAME)
os.environ["GRAPH_STORAGE_PATH"] = TEST_STORAGE_PATH

# Import the module - should be found via editable install
import mcp_integration.mcp_endpoint 

@pytest.fixture(scope="module", autouse=True)
def manage_test_graph_file():
    """Creates and cleans up the test graph JSON file."""
    # Clean up any old test graph file before starting
    if os.path.exists(TEST_STORAGE_PATH):
        os.remove(TEST_STORAGE_PATH)
        
    # Ensure the directory exists
    os.makedirs(os.path.dirname(TEST_STORAGE_PATH), exist_ok=True)
    
    # Create a dummy graph file for testing (Corrected nodes structure)
    dummy_graph_data = {
        "nodes": [
            {"id": "node1", "filepath": "src/file1.py", "node_type": "function", "metadata": {}},
            {"id": "node2", "filepath": "src/file2.py", "node_type": "class", "metadata": {"lines": [10, 25]}},
            {"id": "node3", "filepath": "src/file1.py", "node_type": "variable", "metadata": {}}
        ],
        "edges": [
            {"source": "node1", "target": "node2", "type": "calls", "metadata": {}},
            {"source": "node3", "target": "node1", "type": "references", "metadata": {}}
        ],
        "file_nodes": {
            "src/file1.py": ["node1", "node3"],
            "src/file2.py": ["node2"]
        }
    }
    with open(TEST_STORAGE_PATH, 'w') as f:
        json.dump(dummy_graph_data, f)

    # --- Explicitly reload the graph data AFTER creating the file ---
    mcp_integration.mcp_endpoint._reload_graph_storage_for_testing()
    # -------------------------------------------------------------

    # Let tests run
    yield

    # Clean up the test graph file after tests run
    if os.path.exists(TEST_STORAGE_PATH):
        os.remove(TEST_STORAGE_PATH)
    # Unset environment variable if needed, though test runners often isolate envs
    # del os.environ["GRAPH_STORAGE_PATH"]

# --- Test Cases (Corrected CallToolRequest construction) ---

def test_handle_get_node_info_success():
    # Correct CallToolRequest structure
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "get_node_info", # Tool name here
            "arguments": {"node_id": "node1"}
        }
    ) 
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_get_node_info(request))
    
    assert not result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    data = json.loads(result.content[0].text) 
    assert data["node_id"] == "node1"
    assert data["filepath"] == "src/file1.py"
    assert data["node_type"] == "function"

def test_handle_get_node_info_not_found():
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "get_node_info",
            "arguments": {"node_id": "nonexistent"}
        }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_get_node_info(request))
    
    assert result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "not found" in result.content[0].text.lower()

def test_handle_search_nodes_by_id():
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "search_nodes",
            "arguments": {"query": "node2"}
            }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_search_nodes(request))
    
    assert not result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    data = json.loads(result.content[0].text)
    assert "nodes" in data
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["node_id"] == "node2"

def test_handle_search_nodes_by_filepath():
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "search_nodes",
            "arguments": {"query": "file1.py"}
        }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_search_nodes(request))
    
    assert not result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    data = json.loads(result.content[0].text)
    assert "nodes" in data
    assert len(data["nodes"]) == 2 # node1 and node3
    node_ids = {node["node_id"] for node in data["nodes"]}
    assert node_ids == {"node1", "node3"}

def test_handle_search_nodes_limit():
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "search_nodes",
            "arguments": {"query": "node", "limit": 1}
        }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_search_nodes(request))
    
    assert not result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    data = json.loads(result.content[0].text)
    assert "nodes" in data
    assert len(data["nodes"]) == 1 # Only one node due to limit

def test_handle_search_nodes_no_results():
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "search_nodes",
            "arguments": {"query": "xyz123"}
        }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_search_nodes(request))
    
    assert not result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    data = json.loads(result.content[0].text)
    assert "nodes" in data
    assert len(data["nodes"]) == 0

def test_handle_list_edges_success():
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "list_edges",
            "arguments": {"node_id": "node1"}
        }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_list_edges(request))
    
    assert not result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    data = json.loads(result.content[0].text)
    assert "edges" in data
    assert len(data["edges"]) == 2 # Edges: node3->node1, node1->node2
    edges_set = {(edge["source"], edge["target"]) for edge in data["edges"]}
    assert edges_set == {("node1", "node2"), ("node3", "node1")}
    
    # Check specific edge details
    for edge in data["edges"]:
        if edge["source"] == "node1":
            assert edge["target"] == "node2"
            assert edge["edge_type"] == "calls"
        else:
            assert edge["source"] == "node3"
            assert edge["target"] == "node1"
            assert edge["edge_type"] == "references"

def test_handle_list_edges_node_not_found():
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "list_edges",
            "arguments": {"node_id": "nonexistent"}
        }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_list_edges(request))
    
    assert result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "not found" in result.content[0].text.lower()

def test_handle_list_edges_node_no_edges():
    # Node2 only has incoming edge node3->node1, node1->node2
    request = CallToolRequest(
        method="tools/call", 
        params={
            "name": "list_edges",
            "arguments": {"node_id": "node2"}
        }
    )
    result = asyncio.run(mcp_integration.mcp_endpoint.handle_list_edges(request))
    
    assert not result.isError
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    data = json.loads(result.content[0].text)
    assert "edges" in data
    # get_edges_for_nodes returns edges *connected* to the node (in or out)
    assert len(data["edges"]) == 1 
    assert data["edges"][0]["source"] == "node1"
    assert data["edges"][0]["target"] == "node2" 