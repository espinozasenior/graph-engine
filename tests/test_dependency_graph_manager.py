"""
Tests for the dependency_graph_manager module.
"""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock

from graph_core.manager import DependencyGraphManager
from graph_core.storage.in_memory_graph import InMemoryGraphStorage


class TestDependencyGraphManager(unittest.TestCase):
    """Test cases for the DependencyGraphManager class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.storage = Mock(spec=InMemoryGraphStorage)
        self.manager = DependencyGraphManager(self.storage)
    
    def test_init(self):
        """Test initialization of DependencyGraphManager."""
        self.assertEqual(self.manager.storage, self.storage)
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_on_file_event_created(self, mock_get_parser):
        """Test handling a 'created' file event for a Python file."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser.parse_file.return_value = {
            'nodes': [{'id': 'test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_get_parser.return_value = mock_parser
        
        # Call the method
        filepath = 'test.py'
        self.manager.on_file_event('created', filepath)
        
        # Verify the parser was called
        mock_get_parser.assert_called_once_with(filepath)
        mock_parser.parse_file.assert_called_once_with(filepath)
        
        # Verify the storage was updated
        self.storage.add_or_update_file.assert_called_once_with(
            filepath, mock_parser.parse_file.return_value
        )
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_on_file_event_modified(self, mock_get_parser):
        """Test handling a 'modified' file event for a Python file."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser.parse_file.return_value = {
            'nodes': [{'id': 'test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_get_parser.return_value = mock_parser
        
        # Call the method
        filepath = 'test.py'
        self.manager.on_file_event('modified', filepath)
        
        # Verify the parser was called
        mock_get_parser.assert_called_once_with(filepath)
        mock_parser.parse_file.assert_called_once_with(filepath)
        
        # Verify the storage was updated
        self.storage.add_or_update_file.assert_called_once_with(
            filepath, mock_parser.parse_file.return_value
        )
    
    def test_on_file_event_deleted(self):
        """Test handling a 'deleted' file event for a Python file."""
        filepath = 'test.py'
        self.manager.on_file_event('deleted', filepath)
        
        # Verify the storage was updated
        self.storage.remove_file.assert_called_once_with(filepath)
    
    def test_on_file_event_non_python(self):
        """Test handling a file event for a non-Python file."""
        filepath = 'test.txt'
        self.manager.on_file_event('created', filepath)
        
        # Verify the storage was not updated
        self.storage.add_or_update_file.assert_not_called()
        self.storage.remove_file.assert_not_called()
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_on_file_event_no_parser(self, mock_get_parser):
        """Test handling a file event when no parser is available."""
        # Set up mocks
        mock_get_parser.return_value = None
        
        # Call the method
        filepath = 'test.py'
        self.manager.on_file_event('created', filepath)
        
        # Verify the storage was not updated
        self.storage.add_or_update_file.assert_not_called()
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_on_file_event_file_not_found(self, mock_get_parser):
        """Test handling a file event when the file is not found."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser.parse_file.side_effect = FileNotFoundError()
        mock_get_parser.return_value = mock_parser
        
        # Call the method - should not raise an exception
        filepath = 'nonexistent.py'
        self.manager.on_file_event('created', filepath)
        
        # Verify the storage was not updated
        self.storage.add_or_update_file.assert_not_called()
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_on_file_event_permission_error(self, mock_get_parser):
        """Test handling a file event when there's a permission error."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser.parse_file.side_effect = PermissionError()
        mock_get_parser.return_value = mock_parser
        
        # Call the method - should not raise an exception
        filepath = 'protected.py'
        self.manager.on_file_event('created', filepath)
        
        # Verify the storage was not updated
        self.storage.add_or_update_file.assert_not_called()
    
    def test_on_file_event_invalid_type(self):
        """Test handling a file event with an invalid event type."""
        with self.assertRaises(ValueError):
            self.manager.on_file_event('invalid', 'test.py')
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_integration_with_watcher(self, mock_get_parser):
        """Test integration with file watcher by simulating watcher events."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser.parse_file.return_value = {
            'nodes': [{'id': 'test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_get_parser.return_value = mock_parser
        
        # Create a mock file watcher
        mock_watcher_callback = None
        
        def start_mock_watcher(callback, watch_dir='src'):
            nonlocal mock_watcher_callback
            mock_watcher_callback = callback
            return None
        
        # Simulate a file watcher starting and sending events
        start_mock_watcher(self.manager.on_file_event)
        
        # Simulate file events
        mock_watcher_callback('created', 'test1.py')
        mock_watcher_callback('modified', 'test2.py')
        mock_watcher_callback('deleted', 'test3.py')
        
        # Verify the storage was updated correctly
        self.assertEqual(self.storage.add_or_update_file.call_count, 2)
        self.assertEqual(self.storage.remove_file.call_count, 1)
        
        # Check the call arguments
        self.storage.add_or_update_file.assert_any_call('test1.py', mock_parser.parse_file.return_value)
        self.storage.add_or_update_file.assert_any_call('test2.py', mock_parser.parse_file.return_value)
        self.storage.remove_file.assert_called_once_with('test3.py')


if __name__ == '__main__':
    unittest.main() 