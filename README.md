# Graph Engine

A tool for analyzing code dependencies and visualizing them as a graph.

## Components

### Core Components

1. **Parser**: Parses source code files to extract nodes (functions, classes) and edges (dependencies).
   - `DependencyExtractor`: Extracts nodes and edges from Python files.
   - `TreeSitterParser`: Uses Tree-sitter to extract structural information from code files in various languages.

2. **Graph Storage**: Stores the dependency graph.
   - `InMemoryGraphStorage`: Stores the graph in memory.

3. **Graph Manager**: Manages the dependency graph, handling updates and queries.
   - `DependencyGraphManager`: Coordinates parsing and storage.

4. **API**: Provides HTTP access to the dependency graph.
   - `GraphAPI`: FastAPI application that exposes graph data via HTTP endpoints.

5. **File Watcher**: Watches for file changes and updates the graph automatically.

## Setup

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/graph-engine.git
   cd graph-engine
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Build the Tree-sitter language libraries:
   ```bash
   python graph_core/analyzer/treesitter_parser/build_languages.py
   ```

## Usage

### Running the API Server

Start the API server with file watching:

```bash
python run_graph_manager.py --watch-dir src/ --host 127.0.0.1 --port 8000
```

### Accessing the API

Once the server is running, you can access the following endpoints:

- `GET /graph/nodes` - Retrieve all nodes in the dependency graph
- `GET /graph/edges` - Retrieve all edges in the dependency graph

### Using the TreeSitterParser

The `TreeSitterParser` can be used to parse code files and extract structural information:

```python
from graph_core.analyzer.treesitter_parser import TreeSitterParser

# Initialize parser for Python
parser = TreeSitterParser('python')

# Parse a file
result = parser.parse_file('path/to/your/file.py')

# Access nodes and edges
nodes = result['nodes']
edges = result['edges']

# Print information about nodes
for node in nodes:
    print(f"Node: {node['name']} (Type: {node['type']})")

# Print information about edges
for edge in edges:
    print(f"Edge: {edge['source']} -> {edge['target']} (Type: {edge['type']})")
```

### Supported Languages

The `TreeSitterParser` supports the following languages:

- Python (`.py`)
- JavaScript (`.js`)
- TypeScript (`.ts`, `.tsx`)

## Testing

Run the tests:

```bash
pytest
```

## License

[MIT License](LICENSE)