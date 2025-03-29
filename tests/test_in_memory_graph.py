"""
Tests for the in_memory_graph module.
"""

import unittest
from graph_core.storage.in_memory_graph import InMemoryGraphStorage


class TestInMemoryGraphStorage(unittest.TestCase):
    """Test cases for the InMemoryGraphStorage class."""
    
    def setUp(self):
        """Set up the test environment."""
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
        
        # Check that nodes have the file attribute
        for node in nodes:
            self.assertIn('files', node)
            self.assertEqual(node['files'], {filepath})
        
        # Check that the edge is correct
        self.assertEqual(len(edges), 1)
        edge = edges[0]
        self.assertEqual(edge['source'], 'func1')
        self.assertEqual(edge['target'], 'func2')
        self.assertEqual(edge['relation'], 'CALLS')
        self.assertEqual(edge['file'], filepath)
    
    def test_add_file_with_module_references(self):
        """Test adding a file with module-level references."""
        # Create a parse result with module-level references
        filepath = 'test_module.py'
        parse_result = {
            'nodes': [
                {'id': 'class1', 'type': 'class', 'name': 'Class1'}
            ],
            'edges': [
                {'source': filepath, 'target': 'os.path', 'relation': 'IMPORTS'},
                {'source': 'class1', 'target': filepath, 'relation': 'DEFINED_IN'}
            ]
        }
        
        self.graph_storage.add_or_update_file(filepath, parse_result)
        
        # Check node and edge counts
        # Should have 3 nodes: class1, module:filepath, and os.path
        # Should have 2 edges
        self.assertEqual(self.graph_storage.get_node_count(), 3)
        self.assertEqual(self.graph_storage.get_edge_count(), 2)
        
        # Check that the module node was created
        module_id = f"module:{filepath}"
        module_node = self.graph_storage.get_node(module_id)
        self.assertIsNotNone(module_node)
        self.assertEqual(module_node['type'], 'module')
        
        # Check that edges use the module node ID
        edges = self.graph_storage.get_all_edges()
        module_edges = [edge for edge in edges if edge['source'] == module_id or edge['target'] == module_id]
        self.assertEqual(len(module_edges), 2)
    
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
                {'source': 'file1_only', 'target': 'shared_func', 'relation': 'CALLS'}
            ]
        }
        
        parse_result2 = {
            'nodes': [
                {'id': 'shared_func', 'type': 'function', 'name': 'shared_func'},
                {'id': 'file2_only', 'type': 'function', 'name': 'file2_only'}
            ],
            'edges': [
                {'source': 'file2_only', 'target': 'shared_func', 'relation': 'CALLS'}
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
        self.assertEqual(shared_node['files'], {file2})
        
        # Now remove file2
        self.graph_storage.remove_file(file2)
        
        # Should have 0 nodes and 0 edges
        self.assertEqual(self.graph_storage.get_node_count(), 0)
        self.assertEqual(self.graph_storage.get_edge_count(), 0)
    
    def test_update_file(self):
        """Test updating a file replaces old nodes/edges."""
        filepath = 'update_test.py'
        
        # Initial version of the file
        initial_result = {
            'nodes': [
                {'id': 'old_func', 'type': 'function', 'name': 'old_func'},
                {'id': 'common_func', 'type': 'function', 'name': 'common_func'}
            ],
            'edges': [
                {'source': 'old_func', 'target': 'common_func', 'relation': 'CALLS'}
            ]
        }
        
        self.graph_storage.add_or_update_file(filepath, initial_result)
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        self.assertEqual(self.graph_storage.get_edge_count(), 1)
        
        # Updated version of the file
        updated_result = {
            'nodes': [
                {'id': 'new_func', 'type': 'function', 'name': 'new_func'},
                {'id': 'common_func', 'type': 'function', 'name': 'common_func'}
            ],
            'edges': [
                {'source': 'new_func', 'target': 'common_func', 'relation': 'CALLS'}
            ]
        }
        
        self.graph_storage.add_or_update_file(filepath, updated_result)
        
        # Check final state
        # Should have 2 nodes (new_func and common_func) and 1 edge
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        self.assertEqual(self.graph_storage.get_edge_count(), 1)
        
        nodes = self.graph_storage.get_all_nodes()
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'new_func', 'common_func'})
        
        # Check that the edge now goes from new_func to common_func
        edges = self.graph_storage.get_all_edges()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['source'], 'new_func')
        self.assertEqual(edges[0]['target'], 'common_func')
    
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
        self.assertEqual(common_node['files'], {file1, file2, file3})
        
        # Remove file1 - node should remain with 2 files
        self.graph_storage.remove_file(file1)
        self.assertEqual(self.graph_storage.get_node_count(), 1)
        
        common_node = self.graph_storage.get_node('common')
        self.assertEqual(common_node['files'], {file2, file3})
        
        # Remove file2 - node should remain with 1 file
        self.graph_storage.remove_file(file2)
        self.assertEqual(self.graph_storage.get_node_count(), 1)
        
        common_node = self.graph_storage.get_node('common')
        self.assertEqual(common_node['files'], {file3})
        
        # Remove file3 - node should be removed
        self.graph_storage.remove_file(file3)
        self.assertEqual(self.graph_storage.get_node_count(), 0)
    
    def test_repeated_file_changes(self):
        """Test handling repeated updates to the same file."""
        filepath = 'changing_file.py'
        
        # Version 1 of the file
        version1 = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1'},
                {'id': 'func2', 'type': 'function', 'name': 'func2'}
            ],
            'edges': [
                {'source': 'func1', 'target': 'func2', 'relation': 'CALLS'}
            ]
        }
        
        # Version 2 - modify func1, remove func2, add func3
        version2 = {
            'nodes': [
                {'id': 'func1', 'type': 'function', 'name': 'func1_renamed'},
                {'id': 'func3', 'type': 'function', 'name': 'func3'}
            ],
            'edges': [
                {'source': 'func1', 'target': 'func3', 'relation': 'CALLS'}
            ]
        }
        
        # Version 3 - remove func1, modify func3, add func4
        version3 = {
            'nodes': [
                {'id': 'func3', 'type': 'function', 'name': 'func3_modified'},
                {'id': 'func4', 'type': 'function', 'name': 'func4'}
            ],
            'edges': [
                {'source': 'func3', 'target': 'func4', 'relation': 'CALLS'}
            ]
        }
        
        # Apply version 1
        self.graph_storage.add_or_update_file(filepath, version1)
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        self.assertEqual(self.graph_storage.get_edge_count(), 1)
        
        # Nodes should be func1 and func2
        nodes = self.graph_storage.get_all_nodes()
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'func1', 'func2'})
        
        # Apply version 2
        self.graph_storage.add_or_update_file(filepath, version2)
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        self.assertEqual(self.graph_storage.get_edge_count(), 1)
        
        # Nodes should be func1 and func3
        nodes = self.graph_storage.get_all_nodes()
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'func1', 'func3'})
        
        # Edge should go from func1 to func3
        edges = self.graph_storage.get_all_edges()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['source'], 'func1')
        self.assertEqual(edges[0]['target'], 'func3')
        
        # Apply version 3
        self.graph_storage.add_or_update_file(filepath, version3)
        self.assertEqual(self.graph_storage.get_node_count(), 2)
        self.assertEqual(self.graph_storage.get_edge_count(), 1)
        
        # Nodes should be func3 and func4
        nodes = self.graph_storage.get_all_nodes()
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'func3', 'func4'})
        
        # Node func3 should have the updated name
        func3_node = self.graph_storage.get_node('func3')
        self.assertEqual(func3_node['name'], 'func3_modified')
        
        # Edge should go from func3 to func4
        edges = self.graph_storage.get_all_edges()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['source'], 'func3')
        self.assertEqual(edges[0]['target'], 'func4')
    
    def test_invalid_parse_result(self):
        """Test handling of invalid parse results."""
        # Test with missing 'nodes' key
        with self.assertRaises(KeyError):
            self.graph_storage.add_or_update_file('test.py', {'edges': []})
        
        # Test with missing 'edges' key
        with self.assertRaises(KeyError):
            self.graph_storage.add_or_update_file('test.py', {'nodes': []})
    
    def test_remove_nonexistent_file(self):
        """Test removing a file that doesn't exist."""
        # Should not raise an exception
        self.graph_storage.remove_file('nonexistent.py')
        
        # Graph should still be empty
        self.assertEqual(self.graph_storage.get_node_count(), 0)
        self.assertEqual(self.graph_storage.get_edge_count(), 0)


if __name__ == '__main__':
    unittest.main() 