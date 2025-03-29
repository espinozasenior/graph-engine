"""
Tests for the graph integration with TreeSitterParser.
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
from graph_core.storage.in_memory_graph import InMemoryGraphStorage
from graph_core.manager import DependencyGraphManager


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


def test_process_file_with_mock_parser(sample_python_file):
    """Test processing a file with the dependency manager."""
    # Create mock parser
    mock_parser = MagicMock()
    mock_parser.parse_file.return_value = {
        'nodes': [
            {
                'id': 'function:hello_world',
                'type': 'function',
                'name': 'hello_world',
                'filepath': sample_python_file,
                'start_line': 1,
                'end_line': 2
            },
            {
                'id': 'class:TestClass',
                'type': 'class',
                'name': 'TestClass',
                'filepath': sample_python_file,
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
    
    # Patch get_parser_for_file to return our mock
    with patch('graph_core.manager.get_parser_for_file', return_value=mock_parser):
        # Create storage and manager
        storage = InMemoryGraphStorage()
        manager = DependencyGraphManager(storage)
        
        # Process the file
        manager.on_file_event('created', sample_python_file)
        
        # Get all nodes
        nodes = storage.get_all_nodes()
        
        # Verify nodes were added
        assert len(nodes) > 0
        
        # Verify the mock parser was called with the right arguments
        mock_parser.parse_file.assert_called_with(sample_python_file)


@patch('graph_core.analyzer.get_parser_for_file')
def test_process_unsupported_file(mock_get_parser, tmp_path):
    """Test processing an unsupported file type."""
    # Configure mock to return None for unsupported files
    mock_get_parser.return_value = None
    
    # Create storage and manager
    storage = InMemoryGraphStorage()
    manager = DependencyGraphManager(storage)
    
    # Create a text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is not a supported file type")
    
    # Process the file
    manager.on_file_event('created', str(text_file))
    
    # Get all nodes - should be empty
    nodes = storage.get_all_nodes()
    
    # Verify no nodes were added
    assert len(nodes) == 0


@patch('graph_core.analyzer.TreeSitterParser')
def test_tree_sitter_integration(mock_ts_parser, sample_python_file):
    """Test the TreeSitterParser integration."""
    # Configure TreeSitterParser to return a valid result
    mock_parser = mock_ts_parser.return_value
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
    
    # Verify we got a TreeSitterParser
    assert parser is mock_parser
    
    # Create storage and manager
    storage = InMemoryGraphStorage()
    manager = DependencyGraphManager(storage)
    
    # Process the file
    manager.on_file_event('created', sample_python_file)
    
    # Get all nodes
    nodes = storage.get_all_nodes()
    
    # Verify nodes were added
    assert len(nodes) > 0


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 