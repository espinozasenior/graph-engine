"""
Tests for the TreeSitterParser class.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module directly to mock its dependencies
import graph_core.analyzer.treesitter_parser.tree_sitter_parser as parser_module
from graph_core.analyzer.treesitter_parser.tree_sitter_parser import TreeSitterParser

# Test data: Simple Python code sample
PYTHON_CODE_SAMPLE = """
def hello_world():
    print("Hello, World!")

class TestClass:
    def method(self):
        return hello_world()
"""

# Test data: Simple JavaScript code sample
JS_CODE_SAMPLE = """
function helloWorld() {
    console.log("Hello, World!");
}

class TestClass {
    method() {
        return helloWorld();
    }
}
"""

@pytest.fixture
def mock_tree_sitter():
    """Fixture to mock tree_sitter components."""
    with patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language') as mock_language, \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Parser') as mock_parser_class:
        
        # Create and configure mock objects
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        
        # Create mock tree structure
        mock_root_node = MagicMock()
        mock_root_node.type = "module"
        
        # Add function node as child
        mock_function = MagicMock()
        mock_function.type = "function_definition"
        mock_function.text = b"def hello_world():"
        mock_function.start_point = (1, 0)
        mock_function.end_point = (2, 22)
        
        # Add class node as child
        mock_class = MagicMock()
        mock_class.type = "class_definition"
        mock_class.text = b"class TestClass:"
        mock_class.start_point = (4, 0)
        mock_class.end_point = (6, 24)
        
        # Method within class
        mock_method = MagicMock()
        mock_method.type = "function_definition"
        mock_method.text = b"def method(self):"
        mock_method.start_point = (5, 4)
        mock_method.end_point = (6, 24)
        
        # Set up hierarchy
        mock_class.children = [mock_method]
        mock_root_node.children = [mock_function, mock_class]
        
        # Set up mock tree
        mock_tree = MagicMock()
        mock_tree.root_node = mock_root_node
        
        # Configure parser to return the mock tree
        mock_parser.parse.return_value = mock_tree
        
        yield mock_parser

def test_parser_initialization():
    """Test initialization of TreeSitterParser with a mock."""
    with patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language'), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Parser'), \
         patch('pathlib.Path.exists', return_value=True):
        
        parser = TreeSitterParser('python')
        assert parser.language == 'python'
        
        # Test with unsupported language
        with pytest.raises(ValueError):
            TreeSitterParser('invalid_language')

@patch('os.path.exists', return_value=True)
def test_parse_file_basic_structure(mock_exists, mock_tree_sitter, tmp_path):
    """Test parsing a Python file returns correct structure."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language'), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Parser'):
        
        parser = TreeSitterParser('python')
        
        # Explicitly set the parser to our mock
        parser.parser = mock_tree_sitter
    
    # Create a temporary Python file
    test_file = tmp_path / "test.py"
    test_file.write_text(PYTHON_CODE_SAMPLE)
    
    # Parse the file
    result = parser.parse_file(str(test_file))
    
    # Validate the basic structure
    assert 'nodes' in result
    assert 'edges' in result
    assert isinstance(result['nodes'], list)
    assert isinstance(result['edges'], list)
    
    # Check parser was called correctly
    mock_tree_sitter.parse.assert_called_once()

@patch('os.path.exists', return_value=False)
def test_file_not_found(mock_exists):
    """Test handling of non-existent files."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language'), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Parser'):
        
        parser = TreeSitterParser('python')
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file('nonexistent.py')

@patch('os.path.exists', return_value=True)
def test_file_extension_mismatch(mock_exists):
    """Test handling of file extension that doesn't match parser language."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language'), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Parser'):
        
        parser = TreeSitterParser('python')
        
        with pytest.raises(ValueError):
            parser.parse_file('script.js')

@patch('os.path.exists', return_value=True)
def test_parser_caching(mock_exists):
    """Test that parsers are cached and reused."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language') as mock_lang, \
         patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Parser') as mock_parser_class:
        
        # Clear the cache
        TreeSitterParser._parsers = {}
        
        # Create first parser
        parser1 = TreeSitterParser('python')
        
        # Check Language was called once
        assert mock_lang.call_count == 1
        
        # Create second parser for same language
        parser2 = TreeSitterParser('python')
        
        # Check Language wasn't called again
        assert mock_lang.call_count == 1
        
        # Verify both parsers use the same parser instance
        assert parser1.parser is parser2.parser

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 