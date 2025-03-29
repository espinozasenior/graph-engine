"""
Tests for the dependency_graph_manager module.
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock, call

from graph_core.manager import DependencyGraphManager
from graph_core.storage.in_memory_graph import InMemoryGraphStorage
from graph_core.dynamic.import_hook import FunctionCallEvent


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
        
        # Use os.path.join to make paths OS-independent
        root_dir = os.path.normpath('/test')
        subdir = os.path.join(root_dir, 'subdir')
        
        mock_walk.return_value = [
            (root_dir, ['subdir'], ['test1.py', 'test2.js', 'test3.txt']),
            (subdir, [], ['test4.ts', 'test5.tsx', 'test6.md'])
        ]
        
        mock_parser = Mock()
        mock_parser.parse_file.return_value = {
            'nodes': [{'id': 'test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_get_parser.return_value = mock_parser
        
        # Call the method
        result = self.manager.process_existing_files(root_dir)
        
        # Verify the result
        self.assertEqual(result, 4)  # 4 supported files
        
        # Verify parser calls
        self.assertEqual(mock_get_parser.call_count, 4)
        
        # Use os.path.join to create the expected paths
        file1 = os.path.join(root_dir, 'test1.py')
        file2 = os.path.join(root_dir, 'test2.js')
        file3 = os.path.join(subdir, 'test4.ts')
        file4 = os.path.join(subdir, 'test5.tsx')
        
        mock_get_parser.assert_any_call(file1)
        mock_get_parser.assert_any_call(file2)
        mock_get_parser.assert_any_call(file3)
        mock_get_parser.assert_any_call(file4)
        
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
    
    @patch('graph_core.manager.initialize_hook')
    @patch('threading.Thread')
    def test_start_python_instrumentation(self, mock_thread_class, mock_initialize_hook):
        """Test starting Python instrumentation."""
        # Set up mock thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Call the method with all parameters
        watch_dir = 'src/test_dir'
        poll_interval = 0.75
        exclude_patterns = ['test_', 'excluded']
        include_patterns = ['main', 'core']
        cache_dir = '/tmp/test_cache'
        
        self.manager.start_python_instrumentation(
            watch_dir=watch_dir,
            poll_interval=poll_interval,
            exclude_patterns=exclude_patterns,
            include_patterns=include_patterns,
            cache_dir=cache_dir
        )
        
        # Verify initialize_hook was called with the correct parameters
        expected_dir = os.path.abspath(watch_dir)
        mock_initialize_hook.assert_called_once_with(
            expected_dir,
            exclude_patterns=exclude_patterns,
            include_patterns=include_patterns,
            cache_dir=cache_dir
        )
        
        # Verify the thread was created and started
        mock_thread_class.assert_called_once()
        self.assertEqual(mock_thread_class.call_args[1]['target'], self.manager._process_function_call_events)
        self.assertTrue(mock_thread_class.call_args[1]['daemon'])
        mock_thread.start.assert_called_once()
        
        # Verify instance variables were set correctly
        self.assertTrue(self.manager.instrumentation_active)
        self.assertEqual(self.manager.instrumentation_thread, mock_thread)
        self.assertEqual(self.manager.instrumentation_watch_dir, expected_dir)
        self.assertEqual(self.manager.instrumentation_poll_interval, poll_interval)
        self.assertEqual(self.manager.exclude_patterns, exclude_patterns)
        self.assertEqual(self.manager.include_patterns, include_patterns)
        self.assertEqual(self.manager.cache_dir, cache_dir)
    
    @patch('graph_core.manager.initialize_hook')
    @patch('threading.Thread')
    def test_start_python_instrumentation_already_active(self, mock_thread_class, mock_initialize_hook):
        """Test starting Python instrumentation when it's already active."""
        # Simulate already active instrumentation
        self.manager.instrumentation_active = True
        
        # Call the method
        self.manager.start_python_instrumentation()
        
        # Verify initialize_hook was not called
        mock_initialize_hook.assert_not_called()
        
        # Verify the thread was not created
        mock_thread_class.assert_not_called()
    
    @patch('threading.Thread')
    def test_stop_python_instrumentation(self, mock_thread_class):
        """Test stopping Python instrumentation."""
        # Set up for active instrumentation
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.manager.instrumentation_active = True
        self.manager.instrumentation_thread = mock_thread
        
        # Call the method
        self.manager.stop_python_instrumentation()
        
        # Verify thread was joined
        mock_thread.join.assert_called_once_with(timeout=2.0)
        
        # Verify instance variable was updated
        self.assertFalse(self.manager.instrumentation_active)
    
    def test_stop_python_instrumentation_not_active(self):
        """Test stopping Python instrumentation when it's not active."""
        # Ensure instrumentation is not active
        self.manager.instrumentation_active = False
        
        # Call the method
        self.manager.stop_python_instrumentation()
        
        # No assertions needed - just verify no exceptions
    
    @patch('graph_core.manager.get_function_calls')
    @patch('time.sleep')
    def test_process_function_call_events(self, mock_sleep, mock_get_function_calls):
        """Test processing function call events from the queue."""
        # Set up mocks
        event1 = FunctionCallEvent(module_name='test_module', function_name='test_func', filename='test_file.py')
        event2 = FunctionCallEvent(module_name='test_module', function_name='nested.func', filename='test_file.py')
        
        # Configure mock to return events once, then empty list to break the loop
        mock_get_function_calls.side_effect = [[event1, event2], []]
        
        # Create a spy for _process_function_call_event
        self.manager._process_function_call_event = Mock()
        
        # Set up to run only for one loop
        self.manager.instrumentation_active = True
        
        def stop_after_first_call(*args, **kwargs):
            self.manager.instrumentation_active = False
        
        mock_sleep.side_effect = stop_after_first_call
        
        # Call the method
        self.manager._process_function_call_events()
        
        # Verify events were processed
        self.manager._process_function_call_event.assert_has_calls([
            call(event1),
            call(event2)
        ])
        
        # Verify sleep was called with the correct interval
        mock_sleep.assert_called_once_with(self.manager.instrumentation_poll_interval)
    
    def test_process_function_call_event(self):
        """Test processing a single function call event."""
        # Set up a real instance with a mocked storage
        real_storage = Mock(spec=InMemoryGraphStorage)
        manager = DependencyGraphManager(real_storage)
        
        # Mock the necessary methods
        manager.update_function_call_count = Mock()
        manager.process_dynamic_event = Mock()
        
        # Create test events
        event1 = FunctionCallEvent(module_name='test_module', function_name='simple_func', filename='test_file.py')
        event2 = FunctionCallEvent(module_name='test_module', function_name='outer_func.inner_func', filename='test_file.py')
        
        # Process the simple function event
        manager._process_function_call_event(event1)
        
        # Verify the function call count was updated
        manager.update_function_call_count.assert_called_once_with('function:test_module.simple_func')
        manager.process_dynamic_event.assert_not_called()
        
        # Reset mocks
        manager.update_function_call_count.reset_mock()
        manager.process_dynamic_event.reset_mock()
        
        # Process the nested function event
        manager._process_function_call_event(event2)
        
        # Verify both the function call count and dynamic event were processed
        manager.update_function_call_count.assert_called_once_with('function:test_module.inner_func')
        manager.process_dynamic_event.assert_called_once_with(
            'call', 'function:test_module.outer_func', 'function:test_module.inner_func'
        )
    
    @patch('graph_core.dynamic.import_hook.clear_transformation_cache')
    def test_clear_instrumentation_cache(self, mock_clear_cache):
        """Test clearing the instrumentation cache."""
        # Set a cache directory
        cache_dir = '/tmp/test_cache'
        self.manager.cache_dir = cache_dir
        
        # Call the method
        self.manager.clear_instrumentation_cache()
        
        # Verify the cache was cleared with the correct path
        mock_clear_cache.assert_called_once_with(cache_dir)


if __name__ == '__main__':
    unittest.main() 