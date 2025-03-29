"""
Tests for the dependency_graph_manager module.
"""

import os
import tempfile
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
        self.assertEqual(self.manager.SUPPORTED_EXTENSIONS, ['.py', '.js', '.ts', '.tsx'])
    
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
    def test_on_file_event_created_javascript(self, mock_get_parser):
        """Test handling a 'created' file event for a JavaScript file."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser.parse_file.return_value = {
            'nodes': [{'id': 'function:test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_get_parser.return_value = mock_parser
        
        # Call the method
        filepath = 'test.js'
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
    
    def test_on_file_event_unsupported_file(self):
        """Test handling a file event for an unsupported file type."""
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
    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('os.walk')
    def test_process_existing_files(self, mock_walk, mock_isdir, mock_exists, mock_get_parser):
        """Test processing existing files in a directory."""
        # Set up mocks
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_walk.return_value = [
            ('/test', ['subdir'], ['test1.py', 'test2.js', 'test3.txt']),
            ('/test/subdir', [], ['test4.ts', 'test5.tsx', 'test6.md'])
        ]
        
        mock_parser = Mock()
        mock_parser.parse_file.return_value = {
            'nodes': [{'id': 'test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_get_parser.return_value = mock_parser
        
        # Call the method
        result = self.manager.process_existing_files('/test')
        
        # Verify the result
        self.assertEqual(result, 4)  # 4 supported files
        
        # Verify parser calls
        self.assertEqual(mock_get_parser.call_count, 4)
        mock_get_parser.assert_any_call('/test/test1.py')
        mock_get_parser.assert_any_call('/test/test2.js')
        mock_get_parser.assert_any_call('/test/subdir/test4.ts')
        mock_get_parser.assert_any_call('/test/subdir/test5.tsx')
        
        # Verify storage updates
        self.assertEqual(self.storage.add_or_update_file.call_count, 4)
    
    @patch('os.path.exists')
    def test_process_existing_files_directory_not_found(self, mock_exists):
        """Test processing files when the directory doesn't exist."""
        mock_exists.return_value = False
        
        with self.assertRaises(FileNotFoundError):
            self.manager.process_existing_files('/nonexistent')
    
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_process_existing_files_not_a_directory(self, mock_isdir, mock_exists):
        """Test processing files when the path is not a directory."""
        mock_exists.return_value = True
        mock_isdir.return_value = False
        
        with self.assertRaises(ValueError):
            self.manager.process_existing_files('/file.txt')
    
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
        mock_watcher_callback('modified', 'test2.js')
        mock_watcher_callback('deleted', 'test3.ts')
        mock_watcher_callback('created', 'test4.txt')  # Unsupported
        
        # Verify the storage was updated correctly
        self.assertEqual(self.storage.add_or_update_file.call_count, 2)
        self.assertEqual(self.storage.remove_file.call_count, 1)
        
        # Check the call arguments
        self.storage.add_or_update_file.assert_any_call('test1.py', mock_parser.parse_file.return_value)
        self.storage.add_or_update_file.assert_any_call('test2.js', mock_parser.parse_file.return_value)
        self.storage.remove_file.assert_called_once_with('test3.ts')


if __name__ == '__main__':
    unittest.main() 