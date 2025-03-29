"""
Tests for the TreeSitterParser class which parses code files into nodes and edges.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from graph_core.analyzer.treesitter_parser import TreeSitterParser


class TestTreeSitterParser(unittest.TestCase):
    """Test suite for TreeSitterParser."""

    def setUp(self):
        """Set up test environment."""
        # For testing purposes, we'll mock the Language loading
        self.patcher = patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language')
        self.mock_language = self.patcher.start()
        
        # Mock the Parser instance
        self.mock_parser = MagicMock()
        self.mock_language.return_value.parser.return_value = self.mock_parser
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Set up mock for Path.exists to avoid file not found errors
        self.path_exists_patcher = patch('pathlib.Path.exists')
        self.mock_path_exists = self.path_exists_patcher.start()
        self.mock_path_exists.return_value = True
    
    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()
        self.path_exists_patcher.stop()
        self.temp_dir.cleanup()
    
    def test_init_with_supported_language(self):
        """Test initialization with a supported language."""
        parser = TreeSitterParser('python')
        self.assertEqual(parser.language, 'python')
        self.mock_language.assert_called_once()
    
    def test_init_with_unsupported_language(self):
        """Test initialization with an unsupported language."""
        with self.assertRaises(ValueError):
            TreeSitterParser('unsupported_language')
    
    def test_parse_python_function(self):
        """Test parsing a Python file with a function definition."""
        # Create a temporary Python file
        python_code = """
def hello_world():
    print("Hello, World!")
    return "Hello"
        """
        filepath = os.path.join(self.temp_dir.name, 'test_function.py')
        with open(filepath, 'w') as f:
            f.write(python_code)
        
        # Create a mock AST structure
        mock_tree = MagicMock()
        self.mock_parser.parse.return_value = mock_tree
        
        # Setup mock nodes for the function definition
        mock_root = MagicMock()
        mock_function_def = MagicMock()
        mock_function_def.type = 'function_definition'
        mock_function_def.start_point = (1, 0)
        mock_function_def.end_point = (3, 14)
        
        mock_identifier = MagicMock()
        mock_identifier.type = 'identifier'
        mock_identifier.text = b'hello_world'
        mock_identifier.start_point = (1, 4)
        mock_identifier.end_point = (1, 15)
        
        # Setup the tree traversal
        mock_root.children = [mock_function_def]
        mock_function_def.children = [mock_identifier]
        mock_tree.root_node = mock_root
        
        # Parse the file
        parser = TreeSitterParser('python')
        result = parser.parse_file(filepath)
        
        # Assertions
        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        
        # Verify nodes
        self.assertEqual(len(result['nodes']), 1)
        node = result['nodes'][0]
        self.assertEqual(node['id'], 'function:hello_world')
        self.assertEqual(node['type'], 'function')
        self.assertEqual(node['name'], 'hello_world')
        
        # No edges in this simple case
        self.assertEqual(len(result['edges']), 0)
    
    def test_parse_python_class(self):
        """Test parsing a Python file with a class definition."""
        # Create a temporary Python file with a class
        python_code = """
class Person:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"
        """
        filepath = os.path.join(self.temp_dir.name, 'test_class.py')
        with open(filepath, 'w') as f:
            f.write(python_code)
        
        # Create a mock AST structure
        mock_tree = MagicMock()
        self.mock_parser.parse.return_value = mock_tree
        
        # Setup mock nodes for the class definition
        mock_root = MagicMock()
        mock_class_def = MagicMock()
        mock_class_def.type = 'class_definition'
        mock_class_def.start_point = (1, 0)
        mock_class_def.end_point = (6, 40)
        
        mock_class_name = MagicMock()
        mock_class_name.type = 'identifier'
        mock_class_name.text = b'Person'
        
        mock_init_method = MagicMock()
        mock_init_method.type = 'function_definition'
        mock_init_method.start_point = (2, 4)
        mock_init_method.end_point = (3, 24)
        
        mock_init_name = MagicMock()
        mock_init_name.type = 'identifier'
        mock_init_name.text = b'__init__'
        
        mock_greet_method = MagicMock()
        mock_greet_method.type = 'function_definition'
        mock_greet_method.start_point = (5, 4)
        mock_greet_method.end_point = (6, 40)
        
        mock_greet_name = MagicMock()
        mock_greet_name.type = 'identifier'
        mock_greet_name.text = b'greet'
        
        # Setup the tree traversal
        mock_root.children = [mock_class_def]
        mock_class_def.children = [mock_class_name, mock_init_method, mock_greet_method]
        mock_init_method.children = [mock_init_name]
        mock_greet_method.children = [mock_greet_name]
        mock_tree.root_node = mock_root
        
        # Parse the file
        parser = TreeSitterParser('python')
        result = parser.parse_file(filepath)
        
        # Assertions
        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        
        # Verify nodes (should have class and two methods)
        self.assertEqual(len(result['nodes']), 3)
        
        # Find nodes by type/name
        class_node = next((n for n in result['nodes'] if n['type'] == 'class' and n['name'] == 'Person'), None)
        init_node = next((n for n in result['nodes'] if n['type'] == 'function' and n['name'] == '__init__'), None)
        greet_node = next((n for n in result['nodes'] if n['type'] == 'function' and n['name'] == 'greet'), None)
        
        self.assertIsNotNone(class_node)
        self.assertIsNotNone(init_node)
        self.assertIsNotNone(greet_node)
        
        # Verify edges (methods should be connected to class)
        self.assertEqual(len(result['edges']), 2)
        
        # Find edges
        init_edge = next((e for e in result['edges'] if e['source'] == init_node['id'] and e['target'] == class_node['id']), None)
        greet_edge = next((e for e in result['edges'] if e['source'] == greet_node['id'] and e['target'] == class_node['id']), None)
        
        self.assertIsNotNone(init_edge)
        self.assertIsNotNone(greet_edge)
        self.assertEqual(init_edge['type'], 'member_of')
        self.assertEqual(greet_edge['type'], 'member_of')
    
    def test_parse_python_imports(self):
        """Test parsing a Python file with import statements."""
        # Create a temporary Python file with imports
        python_code = """
import os
from datetime import datetime, timedelta
import sys as system
from collections import defaultdict as dd
        """
        filepath = os.path.join(self.temp_dir.name, 'test_imports.py')
        with open(filepath, 'w') as f:
            f.write(python_code)
        
        # Create a mock AST structure
        mock_tree = MagicMock()
        self.mock_parser.parse.return_value = mock_tree
        
        # Setup mock nodes for the imports
        mock_root = MagicMock()
        
        # import os
        mock_import1 = MagicMock()
        mock_import1.type = 'import_statement'
        mock_import1.start_point = (1, 0)
        mock_import1.end_point = (1, 9)
        mock_import1_name = MagicMock()
        mock_import1_name.type = 'dotted_name'
        mock_import1_name.text = b'os'
        
        # from datetime import datetime, timedelta
        mock_import2 = MagicMock()
        mock_import2.type = 'import_from_statement'
        mock_import2.start_point = (2, 0)
        mock_import2.end_point = (2, 38)
        mock_import2_module = MagicMock()
        mock_import2_module.type = 'dotted_name'
        mock_import2_module.text = b'datetime'
        mock_import2_names = MagicMock()
        mock_import2_names.type = 'import_name'
        mock_import2_names.text = b'datetime, timedelta'
        
        # import sys as system
        mock_import3 = MagicMock()
        mock_import3.type = 'import_statement'
        mock_import3.start_point = (3, 0)
        mock_import3.end_point = (3, 19)
        mock_import3_name = MagicMock()
        mock_import3_name.type = 'dotted_name'
        mock_import3_name.text = b'sys'
        mock_import3_alias = MagicMock()
        mock_import3_alias.type = 'alias'
        mock_import3_alias.text = b'system'
        
        # from collections import defaultdict as dd
        mock_import4 = MagicMock()
        mock_import4.type = 'import_from_statement'
        mock_import4.start_point = (4, 0)
        mock_import4.end_point = (4, 40)
        mock_import4_module = MagicMock()
        mock_import4_module.type = 'dotted_name'
        mock_import4_module.text = b'collections'
        mock_import4_names = MagicMock()
        mock_import4_names.type = 'import_name'
        mock_import4_names.text = b'defaultdict as dd'
        
        # Setup the tree traversal
        mock_root.children = [mock_import1, mock_import2, mock_import3, mock_import4]
        mock_import1.children = [mock_import1_name]
        mock_import2.children = [mock_import2_module, mock_import2_names]
        mock_import3.children = [mock_import3_name, mock_import3_alias]
        mock_import4.children = [mock_import4_module, mock_import4_names]
        mock_tree.root_node = mock_root
        
        # Parse the file
        parser = TreeSitterParser('python')
        result = parser.parse_file(filepath)
        
        # Assertions
        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        
        # Verify nodes
        import_nodes = [n for n in result['nodes'] if n['type'] == 'import']
        self.assertEqual(len(import_nodes), 4)
        
        # Verify specific imports
        os_import = next((n for n in result['nodes'] if n['type'] == 'import' and n['name'] == 'os'), None)
        datetime_import = next((n for n in result['nodes'] if n['type'] == 'import' and n['name'] == 'datetime'), None)
        sys_import = next((n for n in result['nodes'] if n['type'] == 'import' and n['name'] == 'sys'), None)
        collections_import = next((n for n in result['nodes'] if n['type'] == 'import' and n['name'] == 'collections'), None)
        
        self.assertIsNotNone(os_import)
        self.assertIsNotNone(datetime_import)
        self.assertIsNotNone(sys_import)
        self.assertIsNotNone(collections_import)
        
        # Verify edges
        # Should have edges for the imported modules
        self.assertTrue(any(e['type'] == 'imports' for e in result['edges']))
    
    def test_parse_javascript_function(self):
        """Test parsing a JavaScript file with function declarations."""
        # Create a temporary JavaScript file
        js_code = """
function greeting(name) {
    return `Hello, ${name}!`;
}

const sayGoodbye = (name) => {
    console.log(`Goodbye, ${name}!`);
};
        """
        filepath = os.path.join(self.temp_dir.name, 'test_function.js')
        with open(filepath, 'w') as f:
            f.write(js_code)
        
        # Create a mock AST structure
        mock_tree = MagicMock()
        self.mock_parser.parse.return_value = mock_tree
        
        # Setup mock nodes for the functions
        mock_root = MagicMock()
        
        # function greeting(name) { ... }
        mock_func_decl = MagicMock()
        mock_func_decl.type = 'function_declaration'
        mock_func_decl.start_point = (1, 0)
        mock_func_decl.end_point = (3, 1)
        mock_func_name = MagicMock()
        mock_func_name.type = 'identifier'
        mock_func_name.text = b'greeting'
        
        # const sayGoodbye = (name) => { ... };
        mock_var_decl = MagicMock()
        mock_var_decl.type = 'lexical_declaration'
        mock_var_decl.start_point = (5, 0)
        mock_var_decl.end_point = (7, 2)
        mock_var_name = MagicMock()
        mock_var_name.type = 'identifier'
        mock_var_name.text = b'sayGoodbye'
        mock_arrow_func = MagicMock()
        mock_arrow_func.type = 'arrow_function'
        
        # Setup the tree traversal
        mock_root.children = [mock_func_decl, mock_var_decl]
        mock_func_decl.children = [mock_func_name]
        mock_var_decl.children = [mock_var_name, mock_arrow_func]
        mock_tree.root_node = mock_root
        
        # Parse the file
        parser = TreeSitterParser('javascript')
        result = parser.parse_file(filepath)
        
        # Assertions
        self.assertIn('nodes', result)
        self.assertIn('edges', result)
        
        # Verify nodes
        self.assertEqual(len(result['nodes']), 2)
        
        greeting_node = next((n for n in result['nodes'] if n['name'] == 'greeting'), None)
        say_goodbye_node = next((n for n in result['nodes'] if n['name'] == 'sayGoodbye'), None)
        
        self.assertIsNotNone(greeting_node)
        self.assertIsNotNone(say_goodbye_node)
        self.assertEqual(greeting_node['type'], 'function')
        self.assertEqual(say_goodbye_node['type'], 'function')
    
    @patch('os.path.exists')
    def test_invalid_file_path(self, mock_exists):
        """Test parsing with an invalid file path."""
        mock_exists.return_value = False
        parser = TreeSitterParser('python')
        with self.assertRaises(FileNotFoundError):
            parser.parse_file('nonexistent_file.py')
    
    def test_empty_file(self):
        """Test parsing an empty file."""
        # Create an empty file
        filepath = os.path.join(self.temp_dir.name, 'empty.py')
        with open(filepath, 'w') as f:
            f.write('')
        
        # Setup empty AST
        mock_tree = MagicMock()
        self.mock_parser.parse.return_value = mock_tree
        mock_root = MagicMock()
        mock_root.children = []
        mock_tree.root_node = mock_root
        
        # Parse the file
        parser = TreeSitterParser('python')
        result = parser.parse_file(filepath)
        
        # Assertions - should have empty nodes and edges lists
        self.assertEqual(len(result['nodes']), 0)
        self.assertEqual(len(result['edges']), 0)
    
    @patch('graph_core.analyzer.treesitter_parser.tree_sitter_parser.Language')
    def test_language_loading_error(self, mock_language_class):
        """Test handling of language loading errors."""
        # Make the Language constructor raise an exception
        mock_language_class.side_effect = Exception("Language loading error")
        
        with self.assertRaises(RuntimeError):
            TreeSitterParser('python')


if __name__ == '__main__':
    unittest.main() 