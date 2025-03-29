"""
Tests for the API module.
"""

import json
import unittest
from unittest.mock import Mock, MagicMock, patch

from fastapi.testclient import TestClient

from graph_core.api import create_app
from graph_core.manager import DependencyGraphManager
from graph_core.storage.in_memory_graph import InMemoryGraphStorage


class TestAPI(unittest.TestCase):
    """Test cases for the API module."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create mock storage
        self.storage = Mock(spec=InMemoryGraphStorage)
        
        # Setup default mock returns
        self.storage.get_all_nodes.return_value = []
        self.storage.get_all_edges.return_value = []
        
        # Create mock manager with our mock storage
        self.manager = Mock(spec=DependencyGraphManager)
        self.manager.storage = self.storage
        
        # Create the FastAPI app with our mock manager
        self.app = create_app(self.manager)
        
        # Create a test client
        self.client = TestClient(self.app)
    
    def test_get_nodes_empty(self):
        """Test GET /graph/nodes with empty graph."""
        # Set up mock storage to return empty list
        self.storage.get_all_nodes.return_value = []
        
        # Make the request
        response = self.client.get("/graph/nodes")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
    
    def test_get_edges_empty(self):
        """Test GET /graph/edges with empty graph."""
        # Set up mock storage to return empty list
        self.storage.get_all_edges.return_value = []
        
        # Make the request
        response = self.client.get("/graph/edges")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
    
    def test_get_nodes_with_data(self):
        """Test GET /graph/nodes with mock data."""
        # Mock data
        mock_nodes = [
            {'id': 'func1', 'type': 'function', 'name': 'func1', 'files': {'test.py'}},
            {'id': 'func2', 'type': 'function', 'name': 'func2', 'files': {'test.py'}}
        ]
        
        # Since set objects aren't JSON serializable, we need to convert them
        serializable_nodes = []
        for node in mock_nodes:
            node_copy = node.copy()
            node_copy['files'] = list(node_copy['files'])
            serializable_nodes.append(node_copy)
        
        # Set up mock storage to return our nodes
        self.storage.get_all_nodes.return_value = serializable_nodes
        
        # Make the request
        response = self.client.get("/graph/nodes")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]['id'], 'func1')
        self.assertEqual(response.json()[1]['id'], 'func2')
    
    def test_get_edges_with_data(self):
        """Test GET /graph/edges with mock data."""
        # Mock data
        mock_edges = [
            {
                'source': 'func1',
                'target': 'func2',
                'relation': 'CALLS',
                'line': 3,
                'file': 'test.py'
            }
        ]
        
        # Set up mock storage to return our edges
        self.storage.get_all_edges.return_value = mock_edges
        
        # Make the request
        response = self.client.get("/graph/edges")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        edge = response.json()[0]
        self.assertEqual(edge['source'], 'func1')
        self.assertEqual(edge['target'], 'func2')
        self.assertEqual(edge['relation'], 'CALLS')
    
    def test_integration_with_storage(self):
        """Test API integration with real storage."""
        # Create a real storage instance
        real_storage = InMemoryGraphStorage()
        
        # Create parse result similar to what would come from PythonParser
        parse_result = {
            'nodes': [
                {'id': 'class1', 'type': 'class', 'name': 'Class1'},
                {'id': 'class1.method1', 'type': 'function', 'name': 'method1', 'full_name': 'class1.method1'}
            ],
            'edges': [
                {'source': 'class1', 'target': 'class1.method1', 'relation': 'HAS_METHOD'}
            ]
        }
        
        # Add parse result to storage
        real_storage.add_or_update_file('test.py', parse_result)
        
        # Replace mock storage with real storage in mock manager
        self.manager.storage = real_storage
        
        # Make requests
        nodes_response = self.client.get("/graph/nodes")
        edges_response = self.client.get("/graph/edges")
        
        # Check nodes response
        self.assertEqual(nodes_response.status_code, 200)
        nodes = nodes_response.json()
        self.assertEqual(len(nodes), 2)
        node_ids = {node['id'] for node in nodes}
        self.assertEqual(node_ids, {'class1', 'class1.method1'})
        
        # Check edges response
        self.assertEqual(edges_response.status_code, 200)
        edges = edges_response.json()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['source'], 'class1')
        self.assertEqual(edges[0]['target'], 'class1.method1')
        self.assertEqual(edges[0]['relation'], 'HAS_METHOD')


if __name__ == '__main__':
    unittest.main() 