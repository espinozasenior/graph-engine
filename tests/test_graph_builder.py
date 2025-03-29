"""
Tests for the graph builder which integrates TreeSitterParser.
"""
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_core.analyzer import get_parser_for_file
from graph_core.builder.graph_builder import GraphBuilder


@pytest.fixture
def sample_python_file():
    """Create a sample Python file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp:
        temp.write(b"""
def hello_world():
    print("Hello, World!")

class TestClass:
    def method(self):
        return hello_world()
""")
        temp_name = temp.name
    
    yield temp_name
    
    # Clean up
    os.unlink(temp_name)


@pytest.fixture
def sample_js_file():
    """Create a sample JavaScript file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as temp:
        temp.write(b"""
function helloWorld() {
    console.log("Hello, World!");
}

class TestClass {
    method() {
        return helloWorld();
    }
}
""")
        temp_name = temp.name
    
    yield temp_name
    
    # Clean up
    os.unlink(temp_name)


@pytest.fixture
def mock_tree_sitter_parser():
    """Mock the TreeSitterParser to avoid dependency on language files."""
    with patch('graph_core.analyzer.treesitter_parser.TreeSitterParser') as mock_cls:
        # Configure the mock parser
        mock_parser = MagicMock()
        mock_cls.return_value = mock_parser
        
        # Configure parse_file to return a valid result
        mock_parser.parse_file.return_value = {
            'nodes': [
                {
                    'id': 'function:hello_world',
                    'type': 'function',
                    'name': 'hello_world',
                    'filepath': 'test.py',
                    'start_line': 1,
                    'end_line': 2
                },
                {
                    'id': 'class:TestClass',
                    'type': 'class',
                    'name': 'TestClass',
                    'filepath': 'test.py',
                    'start_line': 4,
                    'end_line': 6
                }
            ],
            'edges': [
                {
                    'source': 'class:TestClass',
                    'target': 'function:hello_world',
                    'type': 'calls'
                }
            ]
        }
        
        yield mock_parser


def test_graph_builder_with_python_file(sample_python_file, mock_tree_sitter_parser):
    """Test GraphBuilder with a Python file."""
    # Create a graph builder
    builder = GraphBuilder()
    
    # Process the file
    builder.process_file(sample_python_file)
    
    # Get the graph
    graph = builder.get_graph()
    
    # Verify the nodes were added to the graph
    assert len(graph.nodes) > 0
    
    # Verify the edges were added
    assert len(graph.edges) > 0
    
    # Verify the mock parser was called with the right arguments
    mock_tree_sitter_parser.parse_file.assert_called_with(sample_python_file)


@patch('graph_core.analyzer.get_parser_for_file')
def test_graph_builder_with_unsupported_file(mock_get_parser, tmp_path):
    """Test GraphBuilder behavior with unsupported file types."""
    # Configure mock to return None for unsupported files
    mock_get_parser.return_value = None
    
    # Create a graph builder
    builder = GraphBuilder()
    
    # Create a text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is not a supported file type")
    
    # Process the file
    builder.process_file(str(text_file))
    
    # Get the graph - should be empty since no parser was found
    graph = builder.get_graph()
    
    # Verify no nodes were added
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


@patch('graph_core.analyzer.PythonParser')
@patch('graph_core.analyzer.TreeSitterParser')
def test_parser_fallback(mock_ts_parser, mock_py_parser, sample_python_file):
    """Test the parser fallback mechanism."""
    # Configure TreeSitterParser to raise an exception
    mock_ts_parser.side_effect = RuntimeError("Failed to load language")
    
    # Configure PythonParser to return a valid result
    mock_parser = mock_py_parser.return_value
    mock_parser.parse_file.return_value = {
        'nodes': [
            {
                'id': 'function:hello_world',
                'type': 'function',
                'name': 'hello_world',
                'filepath': sample_python_file,
                'start_line': 1,
                'end_line': 2
            }
        ],
        'edges': []
    }
    
    # Get a parser for a Python file
    parser = get_parser_for_file(sample_python_file)
    
    # Verify we got a PythonParser
    assert parser is mock_parser
    
    # Create a graph builder
    builder = GraphBuilder()
    
    # Process the file
    builder.process_file(sample_python_file)
    
    # Get the graph
    graph = builder.get_graph()
    
    # Verify nodes were added by the fallback parser
    assert len(graph.nodes) > 0


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 