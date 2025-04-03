"""
Tests for the in_memory_graph module.
"""

import unittest
from graph_core.storage.in_memory import InMemoryGraphStorage


class TestInMemoryGraphStorage(unittest.TestCase):
    """Test cases for the InMemoryGraphStorage class."""
    
    def setUp(self):
        """Set up a fresh InMemoryGraphStorage instance for each test."""
        self.graph_storage = InMemoryGraphStorage()
    
    def test_add_file_basic(self):
        """Test adding a file with basic nodes and edges."""
        # Create a simple parse result with nodes and edges
        parse_result = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1'},
                {'id': 'func2', 'type': 'function', 'name': 'func2'}
            ],
            'edges': [
                {'source': 'func1', 'target': 'func2', 'relation': 'CALLS'}
            ]
        }

        filepath = 'test_file.py'
        self.graph_storage.add_or_update_file(filepath, parse_result)

        # Check that nodes and edges were added correctly
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        self.assertEqual(self.graph_storage.get_edge_count(), 1)
    
        nodes = self.graph_storage.get_all_nodes()
        edges = self.graph_storage.get_all_edges()

        # Check that node IDs and types are correct
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'func1', 'func2'})

        # Check that nodes have the file attribute (stored as a list)
        for node in nodes:
            self.assertIn('files', node)
            self.assertEqual(set(node['files']), {filepath})
    
    def test_add_file_with_module_references(self):
        """Test adding a file with module-level references."""
        # Create a parse result with module-level references
        filepath = 'test_module.py'
        parse_result = {
            'nodes': [
                {'id': 'class1', 'type': 'class', 'name': 'Class1'},
                {'id': 'module:test_module.py', 'type': 'module', 'name': 'test_module'}
            ],
            'edges': [
                {'source': 'module:test_module.py', 'target': 'os.path', 'type': 'imports'},
                {'source': 'class1', 'target': 'module:test_module.py', 'type': 'defined_in'}
            ]
        }

        self.graph_storage.add_or_update_file(filepath, parse_result)

        # Check node and edge counts
        self.assertEqual(self.graph_storage.get_node_count(), 3)  # class1, module:filepath, and os.path
        self.assertEqual(self.graph_storage.get_edge_count(), 2)

        # Check that the module node exists
        module_id = 'module:test_module.py'
        module_node = self.graph_storage.get_node(module_id)
        self.assertIsNotNone(module_node)
        self.assertEqual(module_node['type'], 'module')
    
    def test_remove_file(self):
        """Test removing a file and its nodes/edges."""
        # Add two files with some shared nodes
        file1 = 'file1.py'
        file2 = 'file2.py'

        parse_result1 = {
            'nodes': [
                {'id': 'shared_func', 'type': 'function', 'name': 'shared_func'},
                {'id': 'file1_only', 'type': 'function', 'name': 'file1_only'}
            ],
            'edges': [
                {'source': 'file1_only', 'target': 'shared_func', 'type': 'calls'}
            ]
        }

        parse_result2 = {
            'nodes': [
                {'id': 'shared_func', 'type': 'function', 'name': 'shared_func'},
                {'id': 'file2_only', 'type': 'function', 'name': 'file2_only'}
            ],
            'edges': [
                {'source': 'file2_only', 'target': 'shared_func', 'type': 'calls'}
            ]
        }

        self.graph_storage.add_or_update_file(file1, parse_result1)
        self.graph_storage.add_or_update_file(file2, parse_result2)

        # Check initial state - should have 3 nodes and 2 edges
        self.assertEqual(self.graph_storage.get_node_count(), 3)
        self.assertEqual(self.graph_storage.get_edge_count(), 2)

        # Remove file1
        self.graph_storage.remove_file(file1)

        # Check final state
        # Should have removed file1_only node but kept shared_func
        # Should have 2 nodes (shared_func, file2_only) and 1 edge
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        self.assertEqual(self.graph_storage.get_edge_count(), 1)

        nodes = self.graph_storage.get_all_nodes()
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'shared_func', 'file2_only'})

        # Check that shared_func now only belongs to file2
        shared_node = self.graph_storage.get_node('shared_func')
        self.assertEqual(set(shared_node['files']), {file2})
    
    def test_multi_file_references(self):
        """Test handling nodes referenced by multiple files."""
        file1 = 'file1.py'
        file2 = 'file2.py'
        file3 = 'file3.py'

        # All three files reference the same node
        parse_result1 = {
            'nodes': [{'id': 'common', 'type': 'function', 'name': 'common'}],
            'edges': []
        }

        parse_result2 = {
            'nodes': [{'id': 'common', 'type': 'function', 'name': 'common'}],
            'edges': []
        }

        parse_result3 = {
            'nodes': [{'id': 'common', 'type': 'function', 'name': 'common'}],
            'edges': []
        }

        # Add all three files
        self.graph_storage.add_or_update_file(file1, parse_result1)
        self.graph_storage.add_or_update_file(file2, parse_result2)
        self.graph_storage.add_or_update_file(file3, parse_result3)

        # Should have 1 node referenced by 3 files
        self.assertEqual(self.graph_storage.get_node_count(), 1)

        # Check that the node has all three files
        common_node = self.graph_storage.get_node('common')
        self.assertEqual(set(common_node['files']), {file1, file2, file3})
    
    def test_add_file_with_existing_nodes(self):
        """Test adding a file that references existing nodes."""
        # Add first file with two nodes
        file1 = 'file1.py'
        parse_result1 = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1'},
                {'id': 'func2', 'type': 'function', 'name': 'func2'}
            ],
            'edges': []
        }
        self.graph_storage.add_or_update_file(file1, parse_result1)
        
        # Add second file that also references func1
        file2 = 'file2.py'
        parse_result2 = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1'},
                {'id': 'func3', 'type': 'function', 'name': 'func3'}
            ],
            'edges': []
        }
        self.graph_storage.add_or_update_file(file2, parse_result2)
        
        # Should have 3 nodes: func1, func2, func3
        self.assertEqual(self.graph_storage.get_node_count(), 3)
        
        # Check that func1 is associated with both files
        func1_node = self.graph_storage.get_node('func1')
        self.assertEqual(set(func1_node['files']), {file1, file2})
        
        # Check that func2 is only associated with file1
        func2_node = self.graph_storage.get_node('func2')
        self.assertEqual(set(func2_node['files']), {file1})
        
        # Check that func3 is only associated with file2
        func3_node = self.graph_storage.get_node('func3')
        self.assertEqual(set(func3_node['files']), {file2})
    
    def test_update_file(self):
        """Test updating an existing file."""
        filepath = 'test_file.py'
        
        # Add initial version of the file
        parse_result1 = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1'},
                {'id': 'func2', 'type': 'function', 'name': 'func2'}
            ],
            'edges': [
                {'source': 'func1', 'target': 'func2', 'type': 'calls'}
            ]
        }
        self.graph_storage.add_or_update_file(filepath, parse_result1)
        
        # Update the file with different nodes/edges
        parse_result2 = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1_renamed'},
                {'id': 'func3', 'type': 'function', 'name': 'func3'}
            ],
            'edges': [
                {'source': 'func1', 'target': 'func3', 'type': 'calls'}
            ]
        }
        self.graph_storage.add_or_update_file(filepath, parse_result2)
        
        # Check that func2 was removed and func3 was added
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        
        nodes = self.graph_storage.get_all_nodes()
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'func1', 'func3'})
        
        # Check that the edge was updated
        edges = self.graph_storage.get_all_edges()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['source'], 'func1')
        self.assertEqual(edges[0]['target'], 'func3')
    
    def test_get_node(self):
        """Test getting a specific node by ID."""
        # Add a file with a node
        filepath = 'test_file.py'
        parse_result = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1', 'extra': 'data'}
            ],
            'edges': []
        }
        self.graph_storage.add_or_update_file(filepath, parse_result)
        
        # Get the node
        node = self.graph_storage.get_node('func1')
        
        # Check that the node has the expected properties
        self.assertIsNotNone(node)
        self.assertEqual(node['id'], 'func1')
        self.assertEqual(node['type'], 'function')
        self.assertEqual(node['name'], 'func1')
        self.assertEqual(node['extra'], 'data')
        self.assertEqual(set(node['files']), {filepath})
        
        # Check that a non-existent node returns None
        self.assertIsNone(self.graph_storage.get_node('non_existent'))
    
    def test_get_edges_for_nodes(self):
        """Test getting edges connected to specific nodes."""
        # Add a file with nodes and edges
        filepath = 'test_file.py'
        parse_result = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1'},
                {'id': 'func2', 'type': 'function', 'name': 'func2'},
                {'id': 'func3', 'type': 'function', 'name': 'func3'}
            ],
            'edges': [
                {'source': 'func1', 'target': 'func2', 'type': 'calls'},
                {'source': 'func2', 'target': 'func3', 'type': 'calls'},
                {'source': 'func3', 'target': 'func1', 'type': 'calls'}
            ]
        }
        self.graph_storage.add_or_update_file(filepath, parse_result)
        
        # Get edges for func1 and func3
        # Use list to ensure consistent order for potential future detailed checks
        edges = self.graph_storage.get_edges_for_nodes(['func1', 'func3'])

        # Should have 3 unique edges connected to func1 or func3:
        # (func1 -> func2), (func3 -> func1), (func2 -> func3)
        self.assertEqual(len(edges), 3)

        # Verify the specific edges (optional, but good practice)
        edge_tuples = {(e['source'], e['target'], e['type']) for e in edges}
        expected_tuples = {
            ('func1', 'func2', 'calls'), 
            ('func3', 'func1', 'calls'), 
            ('func2', 'func3', 'calls')
        }
        self.assertEqual(edge_tuples, expected_tuples)
    
    def test_handle_empty_parse_result(self):
        """Test handling an empty parse result."""
        filepath = 'empty_file.py'
        parse_result = {
            'nodes': [],
            'edges': []
        }
        
        # Should not raise any exceptions
        self.graph_storage.add_or_update_file(filepath, parse_result)
        
        # Should have created an empty entry in file_nodes
        self.assertIn(filepath, self.graph_storage.file_nodes)
        self.assertEqual(len(self.graph_storage.file_nodes[filepath]), 0)
    
    def test_non_existent_file_removal(self):
        """Test removing a file that doesn't exist in storage."""
        # Should not raise any exceptions
        self.graph_storage.remove_file('non_existent.py')


if __name__ == '__main__':
    unittest.main() 