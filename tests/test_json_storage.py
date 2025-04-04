"""
Tests for the JSON graph storage module.
"""

import os
import sys
import json
import tempfile
import unittest
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_core.storage.json_storage import JSONGraphStorage


class TestJSONGraphStorage(unittest.TestCase):
    """Tests for the JSONGraphStorage class."""
    
    def setUp(self):
        """Set up a temporary directory and file for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.json_path = os.path.join(self.temp_dir, "test_graph.json")
        self.storage = JSONGraphStorage(self.json_path)
    
    def tearDown(self):
        """Clean up the temporary directory after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_init_no_file(self):
        """Test initialization when the JSON file doesn't exist."""
        # The file should not exist yet
        self.assertFalse(os.path.exists(self.json_path))
        
        # But the graph should be initialized
        self.assertEqual(self.storage.get_node_count(), 0)
        self.assertEqual(self.storage.get_edge_count(), 0)
        self.assertEqual(len(self.storage.file_nodes), 0)
    
    def test_add_file(self):
        """Test adding a new file to the storage."""
        # Sample parse result
        parse_result = {
            'nodes': [
                {'id': 'function:test_func', 'type': 'function', 'name': 'test_func'}
            ],
            'edges': [
                {'source': 'function:test_func', 'target': 'module:test.py', 'type': 'belongs_to'}
            ]
        }
        
        # Add the file
        self.storage.add_or_update_file("test.py", parse_result)
        
        # Check in-memory state
        self.assertEqual(self.storage.get_node_count(), 2)  # function + module
        self.assertEqual(self.storage.get_edge_count(), 1)
        self.assertIn("test.py", self.storage.file_nodes)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(self.json_path))
        
        # Check file contents
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verify nodes in the file
        self.assertEqual(len(data['nodes']), 2)
        function_node = next((n for n in data['nodes'] if n['id'] == 'function:test_func'), None)
        self.assertIsNotNone(function_node)
        self.assertEqual(function_node['type'], 'function')
        self.assertEqual(function_node['name'], 'test_func')
        
        # Verify edges in the file
        self.assertEqual(len(data['edges']), 1)
        self.assertEqual(data['edges'][0]['source'], 'function:test_func')
        self.assertEqual(data['edges'][0]['type'], 'belongs_to')
        
        # Verify file_nodes in the file
        self.assertIn('test.py', data['file_nodes'])
        self.assertEqual(len(data['file_nodes']['test.py']), 2)  # function + module
    
    def test_update_file(self):
        """Test updating an existing file in the storage."""
        # Add initial file
        initial_parse_result = {
            'nodes': [
                {'id': 'function:original_func', 'type': 'function', 'name': 'original_func'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("test.py", initial_parse_result)
        
        # Update the file with new content
        updated_parse_result = {
            'nodes': [
                {'id': 'function:updated_func', 'type': 'function', 'name': 'updated_func'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("test.py", updated_parse_result)
        
        # Check in-memory state
        nodes = self.storage.get_all_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['id'], 'function:updated_func')
        
        # Check file contents
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verify nodes in the file
        self.assertEqual(len(data['nodes']), 1)
        self.assertEqual(data['nodes'][0]['id'], 'function:updated_func')
        
        # Verify the original node is no longer in the file
        original_node = next((n for n in data['nodes'] if n['id'] == 'function:original_func'), None)
        self.assertIsNone(original_node)
    
    def test_remove_file(self):
        """Test removing a file from the storage."""
        # Add a file
        parse_result = {
            'nodes': [
                {'id': 'function:test_func', 'type': 'function', 'name': 'test_func'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("test.py", parse_result)
        
        # Verify it was added
        self.assertEqual(self.storage.get_node_count(), 1)
        
        # Remove the file
        self.storage.remove_file("test.py")
        
        # Check in-memory state
        self.assertEqual(self.storage.get_node_count(), 0)
        self.assertNotIn("test.py", self.storage.file_nodes)
        
        # Check file contents
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verify nodes in the file
        self.assertEqual(len(data['nodes']), 0)
        
        # Verify file_nodes in the file
        self.assertNotIn('test.py', data['file_nodes'])
    
    def test_shared_nodes(self):
        """Test handling of nodes that are shared between multiple files."""
        # Add first file with a node
        parse_result1 = {
            'nodes': [
                {'id': 'function:shared_func', 'type': 'function', 'name': 'shared_func'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("file1.py", parse_result1)
        
        # Add second file with the same node
        parse_result2 = {
            'nodes': [
                {'id': 'function:shared_func', 'type': 'function', 'name': 'shared_func'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("file2.py", parse_result2)
        
        # Check in-memory state
        self.assertEqual(self.storage.get_node_count(), 1)  # Only one node
        
        # Verify the node is in both file's tracking
        self.assertIn('function:shared_func', self.storage.file_nodes['file1.py'])
        self.assertIn('function:shared_func', self.storage.file_nodes['file2.py'])
        
        # Get the node and check its files attribute
        node = self.storage.get_node('function:shared_func')
        self.assertIsNotNone(node)
        self.assertIn('files', node)
        self.assertEqual(len(node['files']), 2)
        self.assertIn('file1.py', node['files'])
        self.assertIn('file2.py', node['files'])
        
        # Remove one file
        self.storage.remove_file("file1.py")
        
        # Check that the node still exists
        self.assertEqual(self.storage.get_node_count(), 1)
        
        # But it should only be associated with file2.py
        node = self.storage.get_node('function:shared_func')
        self.assertEqual(len(node['files']), 1)
        self.assertIn('file2.py', node['files'])
        
        # Check file contents
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verify node still exists in the file with the correct files list
        node_in_file = next((n for n in data['nodes'] if n['id'] == 'function:shared_func'), None)
        self.assertIsNotNone(node_in_file)
        self.assertEqual(node_in_file['files'], ['file2.py'])
    
    def test_load_graph(self):
        """Test loading a graph from an existing JSON file."""
        # Create a sample graph file
        sample_data = {
            'nodes': [
                {'id': 'function:test_func', 'type': 'function', 'name': 'test_func', 'files': ['test.py']},
                {'id': 'module:test.py', 'type': 'module', 'name': 'test.py', 'files': ['test.py']}
            ],
            'edges': [
                {'source': 'function:test_func', 'target': 'module:test.py', 'type': 'belongs_to', 'file': 'test.py'}
            ],
            'file_nodes': {
                'test.py': ['function:test_func', 'module:test.py']
            }
        }
        
        # Write the sample data to file
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f)
        
        # Create a new storage instance that should load from the file
        storage = JSONGraphStorage(self.json_path)
        
        # Check that the graph was loaded
        self.assertEqual(storage.get_node_count(), 2)  # Both function and module nodes
        
        # Check the loaded nodes
        function_node = storage.get_node('function:test_func')
        self.assertIsNotNone(function_node)
        self.assertEqual(function_node['type'], 'function')
        self.assertEqual(function_node['name'], 'test_func')
        
        module_node = storage.get_node('module:test.py')
        self.assertIsNotNone(module_node)
        self.assertEqual(module_node['type'], 'module')
        
        # Check the loaded file nodes
        self.assertIn('test.py', storage.file_nodes)
        self.assertEqual(len(storage.file_nodes['test.py']), 2)
    
    def test_consistency_after_operations(self):
        """Test that the in-memory graph and on-disk JSON remain consistent after operations."""
        # Add a file
        parse_result = {
            'nodes': [
                {'id': 'function:test_func', 'type': 'function', 'name': 'test_func'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("test.py", parse_result)
        
        # Create a new storage instance that loads from the same file
        storage2 = JSONGraphStorage(self.json_path)
        
        # Check that both instances have the same data
        self.assertEqual(self.storage.get_node_count(), storage2.get_node_count())
        self.assertEqual(len(self.storage.file_nodes), len(storage2.file_nodes))
        
        # Modify the first instance
        self.storage.remove_file("test.py")
        
        # Reload the second instance to get the latest data
        storage2.load_graph()
        
        # Check that both instances still have the same data
        self.assertEqual(self.storage.get_node_count(), storage2.get_node_count())
        self.assertEqual(len(self.storage.file_nodes), len(storage2.file_nodes))
        self.assertEqual(self.storage.get_node_count(), 0)
    
    def test_complex_parse_result(self):
        """Test handling a more complex parse result with multiple nodes and edges."""
        # Complex parse result with multiple nodes and edges
        parse_result = {
            'nodes': [
                {'id': 'module:test_module', 'type': 'module', 'name': 'test_module'},
                {'id': 'class:TestClass', 'type': 'class', 'name': 'TestClass'},
                {'id': 'function:test_method', 'type': 'function', 'name': 'test_method'},
                {'id': 'function:standalone_func', 'type': 'function', 'name': 'standalone_func'}
            ],
            'edges': [
                {'source': 'class:TestClass', 'target': 'module:test_module', 'type': 'belongs_to'},
                {'source': 'function:test_method', 'target': 'class:TestClass', 'type': 'belongs_to'},
                {'source': 'function:standalone_func', 'target': 'module:test_module', 'type': 'belongs_to'},
                {'source': 'function:test_method', 'target': 'function:standalone_func', 'type': 'calls'}
            ]
        }
        
        # Add the file
        self.storage.add_or_update_file("test_module.py", parse_result)
        
        # Check in-memory state
        self.assertEqual(self.storage.get_node_count(), 4)
        self.assertEqual(self.storage.get_edge_count(), 4)
        
        # Check file contents
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verify nodes in the file
        self.assertEqual(len(data['nodes']), 4)
        
        # Verify edges in the file
        self.assertEqual(len(data['edges']), 4)
        
        # Verify file_nodes in the file
        self.assertIn('test_module.py', data['file_nodes'])
        self.assertEqual(len(data['file_nodes']['test_module.py']), 4)
        
        # Check retrieving edges for specific nodes
        method_edges = self.storage.get_edges_for_nodes({'function:test_method'})
        self.assertEqual(len(method_edges), 2)  # belongs_to and calls
        
        # Remove the file
        self.storage.remove_file("test_module.py")
        
        # Check everything was removed
        self.assertEqual(self.storage.get_node_count(), 0)
        self.assertEqual(self.storage.get_edge_count(), 0)

    def test_repeated_save_load(self):
        """Test that repeated save and load operations don't corrupt the data."""
        # Add complex data to storage
        parse_result = {
            'nodes': [
                {'id': 'class:TestClass', 'type': 'class', 'name': 'TestClass'},
                {'id': 'function:test_method', 'type': 'function', 'name': 'test_method'},
                {'id': 'function:another_method', 'type': 'function', 'name': 'another_method'},
                {'id': 'variable:test_var', 'type': 'variable', 'name': 'test_var'}
            ],
            'edges': [
                {'source': 'function:test_method', 'target': 'class:TestClass', 'type': 'belongs_to'},
                {'source': 'function:another_method', 'target': 'class:TestClass', 'type': 'belongs_to'},
                {'source': 'function:test_method', 'target': 'variable:test_var', 'type': 'references'}
            ]
        }
        self.storage.add_or_update_file("test_file.py", parse_result)
        
        # Capture the original state
        original_nodes = sorted(self.storage.get_all_nodes(), key=lambda n: n['id'])
        original_edges = sorted(self.storage.get_all_edges(), key=lambda e: f"{e['source']}-{e['target']}-{e['type']}")
        original_file_nodes = self.storage.file_nodes.copy()
        
        # Perform multiple save and load cycles
        for i in range(5):
            # Force save
            self.storage.save_graph()
            
            # Create a new storage instance that loads from the same file
            reloaded_storage = JSONGraphStorage(self.json_path)
            
            # Verify the data matches the original state
            reloaded_nodes = sorted(reloaded_storage.get_all_nodes(), key=lambda n: n['id'])
            reloaded_edges = sorted(reloaded_storage.get_all_edges(), key=lambda e: f"{e['source']}-{e['target']}-{e['type']}")
            
            # Compare node counts and content
            self.assertEqual(len(original_nodes), len(reloaded_nodes))
            for orig_node, reloaded_node in zip(original_nodes, reloaded_nodes):
                self.assertEqual(orig_node['id'], reloaded_node['id'])
                self.assertEqual(orig_node['type'], reloaded_node['type'])
                self.assertEqual(orig_node['name'], reloaded_node['name'])
            
            # Compare edge counts and content
            self.assertEqual(len(original_edges), len(reloaded_edges))
            for orig_edge, reloaded_edge in zip(original_edges, reloaded_edges):
                self.assertEqual(orig_edge['source'], reloaded_edge['source'])
                self.assertEqual(orig_edge['target'], reloaded_edge['target'])
                self.assertEqual(orig_edge['type'], reloaded_edge['type'])
            
            # Compare file_nodes
            self.assertEqual(len(original_file_nodes), len(reloaded_storage.file_nodes))
            for file_path, node_ids in original_file_nodes.items():
                self.assertIn(file_path, reloaded_storage.file_nodes)
                self.assertEqual(len(node_ids), len(reloaded_storage.file_nodes[file_path]))
                
            # Make the reloaded storage the current one for the next iteration
            self.storage = reloaded_storage

    def test_concurrent_modification_simulation(self):
        """
        Test realistic concurrent modification scenario.
        
        This test shows how multiple processes would typically interact with 
        the same JSON file without losing data.
        """
        # Set up initial data
        parse_result1 = {
            'nodes': [
                {'id': 'function:func1', 'type': 'function', 'name': 'func1'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("file1.py", parse_result1)
        self.storage.save_graph()
        
        # Create a second storage instance pointing to the same file
        storage2 = JSONGraphStorage(self.json_path)
        
        # Both storage instances have their own changes to make
        # First storage adds file2.py
        parse_result2 = {
            'nodes': [
                {'id': 'function:func2', 'type': 'function', 'name': 'func2'}
            ],
            'edges': []
        }
        self.storage.add_or_update_file("file2.py", parse_result2)
        
        # Second storage prepares to add file3.py
        parse_result3 = {
            'nodes': [
                {'id': 'function:func3', 'type': 'function', 'name': 'func3'}
            ],
            'edges': []
        }
        
        # First storage instance saves its changes
        self.storage.save_graph()
        
        # In a real system, before saving its changes, the second storage
        # instance might need to reconcile with changes from other processes
        # We'll simulate this by tracking what we want to add, reloading,
        # then applying our changes
        files_to_update = {"file3.py": parse_result3}
        
        # Reload to get the latest data
        storage2.load_graph()
        
        # Now the second storage has file1.py and file2.py
        # We need to add our changes for file3.py
        for filepath, parse_result in files_to_update.items():
            storage2.add_or_update_file(filepath, parse_result)
        
        # Save the merged changes
        storage2.save_graph()
        
        # Load a fresh instance and verify all data is present
        storage3 = JSONGraphStorage(self.json_path)
        
        # Verify all three files are tracked
        self.assertIn("file1.py", storage3.file_nodes)
        self.assertIn("file2.py", storage3.file_nodes) 
        self.assertIn("file3.py", storage3.file_nodes)
        
        # Verify all nodes are present
        node_ids = [node['id'] for node in storage3.get_all_nodes()]
        self.assertIn("function:func1", node_ids)
        self.assertIn("function:func2", node_ids)
        self.assertIn("function:func3", node_ids)


if __name__ == "__main__":
    unittest.main() 