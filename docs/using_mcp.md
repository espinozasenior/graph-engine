# Using MCP with Graph Engine

The Graph Engine provides a Machine-Callable Program (MCP) interface that enables AI agents and users to query the code graph in smaller, manageable chunks. This makes it ideal for LLMs to explore a codebase incrementally without having to process large amounts of data at once.

## What is MCP?

MCP (Machine-Callable Program) is a protocol that enables AI agents to call functions and access structured data from applications. The Graph Engine implements MCP endpoints to provide a standardized way for AI agents to explore and analyze code dependencies.

## Connecting to the MCP Interface

The Graph Engine exposes MCP endpoints that can be accessed programmatically. You can connect to these endpoints using standard HTTP requests or the MCP client library.

```python
from mcp.client import MCPClient

# Connect to the Graph Engine MCP endpoint
client = MCPClient("http://localhost:8000/mcp")

# Now you can invoke MCP tools
```

## Querying the Code Graph

The MCP interface provides several tools to query the code graph in small, manageable chunks:

### Listing Nodes with Filters

```python
# List up to 10 function nodes
response = await client.call_tool("list_nodes", {"filters": {"node_type": "function"}, "limit": 10})
nodes = response.get_json()["nodes"]

# Process results
for node in nodes:
    print(f"Function: {node['name']} in {node['filepath']}")
```

### Getting Details for a Specific Node

```python
# Get details for a specific node
node_id = "function:math_utils.calculate_area"
response = await client.call_tool("get_node_details", {"node_id": node_id})
node_details = response.get_json()

# Process the result
print(f"Function name: {node_details['name']}")
print(f"Parameters: {node_details['parameters']}")
print(f"Defined in: {node_details['filepath']} (lines {node_details['start_line']}-{node_details['end_line']})")
```

### Searching for Nodes

```python
# Search for nodes matching a keyword
keyword = "calculate"
response = await client.call_tool("search_nodes", {"keyword": keyword, "limit": 5})
matching_nodes = response.get_json()["nodes"]

# Process results
print(f"Found {len(matching_nodes)} nodes matching '{keyword}':")
for node in matching_nodes:
    print(f"- {node['node_type']} {node['name']} in {node['filepath']}")
```

### Finding Function Relationships

```python
# Find functions that call a specific function
function_id = "function:auth.validate_user"
response = await client.call_tool("find_functions_calling", {"function_id": function_id})
callers = response.get_json()["functions"]

# Show who calls this function
print(f"Functions that call {function_id}:")
for caller in callers:
    print(f"- {caller['name']} in {caller['filepath']}")

# Find functions called by a specific function
response = await client.call_tool("find_functions_called_by", {"function_id": function_id})
callees = response.get_json()["functions"]

# Show what this function calls
print(f"Functions called by {function_id}:")
for callee in callees:
    print(f"- {callee['name']} in {callee['filepath']}")
```

### Listing Edges for a Node

```python
# Get all edges (relationships) for a node
response = await client.call_tool("list_edges_for_node", {"node_id": function_id, "direction": "both"})
edges = response.get_json()["edges"]

# Process the edges
print(f"Relationships for {function_id}:")
for edge in edges:
    print(f"- {edge['source']} {edge['edge_type']} {edge['target']}")
```

## Accessing Dynamic Instrumentation Data

The Graph Engine can capture dynamic function call information when instrumentation is enabled. This data can be accessed through the MCP interface.

```python
# Find functions with dynamic call information
response = await client.call_tool("list_nodes", {"filters": {"dynamic_call_count": {"$exists": True}}})
dynamic_nodes = response.get_json()["nodes"]

# Process results
print("Functions with dynamic call data:")
for node in dynamic_nodes:
    print(f"- {node['name']} called {node['metadata'].get('dynamic_call_count', 0)} times")
```

## Example Scenario: Exploring a Function and Its Dependencies

Here's an example of how an AI agent might explore a function and its dependencies using the MCP interface:

```python
async def explore_function(client, function_name):
    # Step 1: Search for the function
    response = await client.call_tool("search_nodes", {"keyword": function_name})
    nodes = response.get_json()["nodes"]
    
    if not nodes:
        return f"No functions found matching '{function_name}'"
    
    # Step 2: Get details for the first matching function
    function_id = nodes[0]["node_id"]
    response = await client.call_tool("get_node_details", {"node_id": function_id})
    function_details = response.get_json()
    
    # Step 3: Find what this function calls
    response = await client.call_tool("find_functions_called_by", {"function_id": function_id})
    dependencies = response.get_json()["functions"]
    
    # Step 4: Find what calls this function
    response = await client.call_tool("find_functions_calling", {"function_id": function_id})
    callers = response.get_json()["functions"]
    
    # Now we can generate an analysis report
    report = [f"## Analysis of function '{function_details['name']}'"]
    report.append(f"\nDefined in: {function_details['filepath']} (lines {function_details['start_line']}-{function_details['end_line']})")
    report.append(f"\nParameters: {', '.join(function_details['parameters'])}")
    
    if dependencies:
        report.append("\n### Dependencies:")
        for dep in dependencies:
            report.append(f"- {dep['name']} ({dep['filepath']})")
    else:
        report.append("\nThis function does not call any other functions.")
    
    if callers:
        report.append("\n### Called by:")
        for caller in callers:
            report.append(f"- {caller['name']} ({caller['filepath']})")
    else:
        report.append("\nThis function is not called by any other functions in the codebase.")
    
    return "\n".join(report)
```

This approach allows AI agents to efficiently explore and understand a codebase by retrieving only the relevant information when needed, rather than trying to process the entire code graph at once.

## REST API Alternative

If you prefer using the REST API instead of MCP, you can access similar functionality through the HTTP endpoints:

```bash
# List all nodes (with pagination)
curl -X GET "http://localhost:8000/api/graph/nodes?limit=10&offset=0"

# Get a specific node
curl -X GET "http://localhost:8000/api/graph/nodes/function:math_utils.calculate_area" 

# Search for nodes
curl -X GET "http://localhost:8000/api/graph/search?keyword=calculate&limit=5"

# Get edges for a node
curl -X GET "http://localhost:8000/api/graph/edges?node_id=function:auth.validate_user&direction=both"
```

The REST API returns the same data structures as the MCP interface but follows traditional REST conventions. 