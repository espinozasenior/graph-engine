"""
Tests for the file_watcher module.
"""

import os
import time
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from graph_core.watchers.file_watcher import start_file_watcher, _map_event_type, EventType
from watchfiles import Change


class TestFileWatcher(unittest.TestCase):
    """Test cases for the file_watcher module."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.callback = Mock()
    
    def tearDown(self):
        """Clean up the test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_map_event_type(self):
        """Test the _map_event_type function."""
        self.assertEqual(_map_event_type(Change.added), EventType.CREATED)
        self.assertEqual(_map_event_type(Change.modified), EventType.MODIFIED)
        self.assertEqual(_map_event_type(Change.deleted), EventType.DELETED)
        
        # Test with an unknown change type
        class UnknownChange:
            pass
        
        self.assertEqual(_map_event_type(UnknownChange()), EventType.MODIFIED)
    
    def test_start_file_watcher_directory_not_found(self):
        """Test start_file_watcher with a non-existent directory."""
        with self.assertRaises(FileNotFoundError):
            start_file_watcher(self.callback, "non_existent_directory")
    
    def test_start_file_watcher_not_a_directory(self):
        """Test start_file_watcher with a file instead of a directory."""
        # Create a temporary file
        temp_file = os.path.join(self.temp_dir, "test_file")
        with open(temp_file, "w") as f:
            f.write("test")
        
        with self.assertRaises(NotADirectoryError):
            start_file_watcher(self.callback, temp_file)
    
    @patch('graph_core.watchers.file_watcher.watch')
    def test_start_file_watcher_file_created(self, mock_watch):
        """Test start_file_watcher detects file creation."""
        # Mock the watch function to return a single change event
        mock_watch.return_value = [
            {(Change.added, os.path.join(self.temp_dir, "test_file"))}
        ]
        
        # Call the function with the mocked watch
        start_file_watcher(self.callback, self.temp_dir)
        
        # Assert the callback was called with the correct parameters
        self.callback.assert_called_once_with(
            EventType.CREATED.value, 
            os.path.join(self.temp_dir, "test_file")
        )
    
    @patch('graph_core.watchers.file_watcher.watch')
    def test_start_file_watcher_file_modified(self, mock_watch):
        """Test start_file_watcher detects file modification."""
        # Mock the watch function to return a single change event
        mock_watch.return_value = [
            {(Change.modified, os.path.join(self.temp_dir, "test_file"))}
        ]
        
        # Call the function with the mocked watch
        start_file_watcher(self.callback, self.temp_dir)
        
        # Assert the callback was called with the correct parameters
        self.callback.assert_called_once_with(
            EventType.MODIFIED.value, 
            os.path.join(self.temp_dir, "test_file")
        )
    
    @patch('graph_core.watchers.file_watcher.watch')
    def test_start_file_watcher_file_deleted(self, mock_watch):
        """Test start_file_watcher detects file deletion."""
        # Mock the watch function to return a single change event
        mock_watch.return_value = [
            {(Change.deleted, os.path.join(self.temp_dir, "test_file"))}
        ]
        
        # Call the function with the mocked watch
        start_file_watcher(self.callback, self.temp_dir)
        
        # Assert the callback was called with the correct parameters
        self.callback.assert_called_once_with(
            EventType.DELETED.value, 
            os.path.join(self.temp_dir, "test_file")
        )
    
    @patch('graph_core.watchers.file_watcher.watch')
    def test_start_file_watcher_multiple_changes(self, mock_watch):
        """Test start_file_watcher handles multiple changes."""
        # Mock the watch function to return multiple change events
        file1 = os.path.join(self.temp_dir, "file1")
        file2 = os.path.join(self.temp_dir, "file2")
        file3 = os.path.join(self.temp_dir, "file3")
        
        mock_watch.return_value = [
            {
                (Change.added, file1),
                (Change.modified, file2),
                (Change.deleted, file3)
            }
        ]
        
        # Call the function with the mocked watch
        start_file_watcher(self.callback, self.temp_dir)
        
        # Assert the callback was called with the correct parameters for each change
        expected_calls = [
            unittest.mock.call(EventType.CREATED.value, file1),
            unittest.mock.call(EventType.MODIFIED.value, file2),
            unittest.mock.call(EventType.DELETED.value, file3)
        ]
        
        # The order of calls might be different, so we check that all expected calls were made
        self.assertEqual(len(self.callback.mock_calls), 3)
        for call in expected_calls:
            self.assertIn(call, self.callback.mock_calls)
    
    @patch('graph_core.watchers.file_watcher.watch')
    def test_callback_exception_handled(self, mock_watch):
        """Test that exceptions in the callback are handled properly."""
        # Create a callback that raises an exception
        def failing_callback(event_type, file_path):
            raise ValueError("Test exception")
        
        # Mock the watch function to return a single change event
        mock_watch.return_value = [
            {(Change.added, os.path.join(self.temp_dir, "test_file"))}
        ]
        
        # Call the function with the mocked watch and failing callback
        # This should not raise an exception
        start_file_watcher(failing_callback, self.temp_dir)
    
    @patch('graph_core.watchers.file_watcher.watch')
    def test_permission_error_propagated(self, mock_watch):
        """Test that permission errors are propagated."""
        # Mock the watch function to raise a PermissionError
        mock_watch.side_effect = PermissionError("Test permission error")
        
        # Call the function with the mocked watch
        with self.assertRaises(PermissionError):
            start_file_watcher(self.callback, self.temp_dir)


if __name__ == '__main__':
    unittest.main() 