# Graph Engine

A comprehensive tool for analyzing code dependencies, visualizing them as a graph, and enabling AI agents to explore codebases efficiently through MCP integration.

## Features

- **Multi-language parsing**: Analyze Python, JavaScript, and TypeScript code using Tree-sitter
- **Real-time file watching**: Automatically update the dependency graph as files change
- **Dynamic instrumentation**: Capture function calls at runtime using a custom Python import hook
- **Rename detection**: Maintain continuity when files or functions are renamed
- **Security scanning**: Identify and mask potential secrets in code
- **JSON persistence**: Store and reload the graph between sessions
- **MCP integration**: Allow AI agents to explore code in manageable chunks
- **REST API**: Access graph data via HTTP endpoints for visualization and integration

## Installation

### Prerequisites

- Python 3.10+ 
- pip

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/Celebr4tion/graph-engine.git
   cd graph-engine
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Build the Tree-sitter language libraries:
   ```bash
   python -m graph_core.analyzer.treesitter_parser.build_languages
   ```

## Usage

### Running the API Server

Start the API server with file watching:

```bash
python run_graph_manager.py --watch-dir path/to/your/code --host 127.0.0.1 --port 8000
```

This will:
1. Process all existing files in the watch directory
2. Start a file watcher to monitor changes
3. Start a FastAPI server with endpoints for accessing the graph data

### Generating a Graph Snapshot

To generate a snapshot of your code's dependency graph:

```bash
python generate_graph_snapshot.py --src-dir path/to/your/code --output graph_snapshot.json
```

This will analyze all supported files in the directory and save the graph data as a JSON file.

### Using Dynamic Instrumentation

For Python projects, you can enable dynamic instrumentation to capture actual function calls at runtime:

```python
from graph_core.manager import DependencyGraphManager

# Create a manager
manager = DependencyGraphManager()

# Start instrumentation
manager.start_python_instrumentation(
    watch_dir='path/to/your/code',
    exclude_patterns=[r'test_.*\.py'],  # Skip test files
    include_patterns=[r'.*\.py']        # Only instrument Python files
)

# Your code will now be monitored for function calls
# The graph will be updated with dynamic call information
```

### Accessing the API

Once the server is running, you can access the following endpoints:

- `GET /graph/nodes` - Retrieve all nodes in the dependency graph
- `GET /graph/nodes/{node_id}` - Get details for a specific node
- `GET /graph/edges` - Retrieve all edges in the dependency graph
- `GET /graph/search?keyword={keyword}` - Search for nodes matching a keyword

### MCP Integration for AI Agents

The Graph Engine provides an MCP interface that allows AI agents to query the code graph in smaller, manageable chunks. This makes it ideal for exploring a codebase incrementally without having to process large amounts of data at once.

For details on using the MCP integration, see [Using MCP with Graph Engine](docs/using_mcp.md).

## Architecture

### Core Components

1. **Parser**: Parses source code files to extract nodes (functions, classes) and edges (dependencies).
   - `TreeSitterParser`: Uses Tree-sitter to extract structural information from code files.

2. **Graph Storage**: Stores the dependency graph.
   - `InMemoryGraphStorage`: Stores the graph in memory.
   - `JSONGraphStorage`: Persists the graph to a JSON file.

3. **Graph Manager**: Manages the dependency graph, handling updates and queries.
   - `DependencyGraphManager`: Coordinates parsing, storage, and event handling.

4. **File Watcher**: Watches for file changes and updates the graph automatically.

5. **Dynamic Instrumentation**: Monitors Python code execution to track function calls at runtime.

6. **Security Scanner**: Identifies potential secrets in code and masks them.

7. **MCP Integration**: Provides a Machine-Callable Program interface for AI agents.
   - `GraphEngineMCP`: Exposes graph data in smaller, manageable chunks via MCP.

8. **API**: Provides HTTP access to the dependency graph.
   - `GraphAPI`: FastAPI application that exposes graph data via HTTP endpoints.

## Supported Languages

The `TreeSitterParser` supports the following languages:

- Python (`.py`)
- JavaScript (`.js`)
- TypeScript (`.ts`, `.tsx`)

## Development

### Running Tests

```bash
pytest
```

For coverage report:

```bash
pytest --cov=graph_core --cov-report=html
```

### Performance Profiling

To profile the performance of the graph engine:

```bash
python performance/profiler.py path/to/your/code
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Hippocratic License](LICENSE.md)

## Acknowledgements

- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) for language parsing
- [NetworkX](https://networkx.org/) for graph operations
- [FastAPI](https://fastapi.tiangolo.com/) for API development
- [Watchdog](https://pythonhosted.org/watchdog/) for file system monitoring