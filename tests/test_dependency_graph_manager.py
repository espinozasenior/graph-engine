"""
Tests for the dependency_graph_manager module.
"""

import os
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call, mock_open
import networkx as nx

from graph_core.manager import DependencyGraphManager, DEFAULT_JSON_PATH
from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.storage.json_storage import JSONGraphStorage, calculate_content_hash
from graph_core.dynamic.import_hook import FunctionCallEvent


class TestDependencyGraphManager(unittest.TestCase):
    """Test cases for the DependencyGraphManager class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.storage = Mock(spec=InMemoryGraphStorage)
        # Add file_nodes attribute to mock to support the new functionality
        self.storage.file_nodes = {}
        self.manager = DependencyGraphManager(self.storage)
    
    def test_init(self):
        """Test initialization of DependencyGraphManager."""
        self.assertEqual(self.manager.storage, self.storage)
        self.assertEqual(self.manager.SUPPORTED_EXTENSIONS, ['.py', '.js', '.ts', '.tsx'])
    
    @patch('graph_core.manager.get_parser_for_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'content')
    @patch('graph_core.manager.scan_parse_result_for_secrets', side_effect=lambda pr, fp: pr)
    def test_on_file_event_created(self, mock_scan_secrets, mock_file_open, mock_get_parser):
        """Test handling a 'created' file event for a Python file."""
        mock_parser = Mock()
        parse_result = {
            'nodes': [{'id': 'module:test.py', 'type': 'module', 'name': 'test.py', 'filepath': 'test.py'}],
            'edges': []
        }
        mock_parser.parse_file.return_value = parse_result
        mock_get_parser.return_value = mock_parser
        filepath = 'test.py'
        self.manager.on_file_event('created', filepath)
        mock_file_open.assert_called_once_with(filepath, 'rb')
        mock_get_parser.assert_called_once_with(filepath)
        mock_parser.parse_file.assert_called_once_with(filepath)
        mock_scan_secrets.assert_called_once()
        self.storage.add_or_update_file.assert_called_once()
        args, kwargs = self.storage.add_or_update_file.call_args
        self.assertEqual(args[0], filepath)
        self.assertIn('content_hash', kwargs)
        self.assertIsNotNone(kwargs['content_hash'])
    
    @patch('graph_core.manager.get_parser_for_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'content_js')
    @patch('graph_core.manager.scan_parse_result_for_secrets', side_effect=lambda pr, fp: pr)
    def test_on_file_event_created_javascript(self, mock_scan_secrets, mock_file_open, mock_get_parser):
        """Test handling a 'created' file event for a JavaScript file."""
        mock_parser = Mock()
        parse_result = {
            'nodes': [{'id': 'module:test.js', 'type': 'module', 'name': 'test.js', 'filepath': 'test.js'}],
            'edges': []
        }
        mock_parser.parse_file.return_value = parse_result
        mock_get_parser.return_value = mock_parser
        filepath = 'test.js'
        self.manager.on_file_event('created', filepath)
        mock_file_open.assert_called_once_with(filepath, 'rb')
        mock_get_parser.assert_called_once_with(filepath)
        mock_parser.parse_file.assert_called_once_with(filepath)
        mock_scan_secrets.assert_called_once()
        self.storage.add_or_update_file.assert_called_once()
        args, kwargs = self.storage.add_or_update_file.call_args
        self.assertIn('content_hash', kwargs)
        self.assertIsNotNone(kwargs['content_hash'])
    
    @patch('graph_core.manager.get_parser_for_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'content')
    @patch('graph_core.manager.scan_parse_result_for_secrets', side_effect=lambda pr, fp: pr)
    @patch('graph_core.manager.DependencyGraphManager.update_function_names', return_value={})
    def test_on_file_event_modified(self, mock_update_names, mock_scan_secrets, mock_file_open, mock_get_parser):
        """Test handling a 'modified' file event for a Python file."""
        mock_parser = Mock()
        parse_result = {
            'nodes': [{'id': 'module:test.py', 'type': 'module', 'name': 'test.py', 'filepath': 'test.py'}],
            'edges': []
        }
        mock_parser.parse_file.return_value = parse_result
        mock_get_parser.return_value = mock_parser
        filepath = 'test.py'
        self.manager.on_file_event('modified', filepath)
        mock_file_open.assert_called_once_with(filepath, 'rb')
        mock_get_parser.assert_called_once_with(filepath)
        mock_parser.parse_file.assert_called_once_with(filepath)
        mock_scan_secrets.assert_called_once()
        self.storage.add_or_update_file.assert_called_once()
        args, kwargs = self.storage.add_or_update_file.call_args
        self.assertEqual(args[0], filepath)
        self.assertIn('content_hash', kwargs)
        self.assertIsNotNone(kwargs['content_hash'])
    
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
        manager = DependencyGraphManager()
        manager.on_file_event('invalid', 'test.py')
        # Instead of raising an error, the method should log a warning and continue
        # We're just asserting that the method runs without exception
        self.assertTrue(True)  # If we got here, the test passes
    
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
        """Test processing files when the target is not a directory."""
        # Set up mocks
        mock_exists.return_value = True
        mock_isdir.return_value = False
        
        with self.assertRaises(ValueError):
            self.manager.process_existing_files('/test/not_a_dir')
    
    @patch('graph_core.manager.get_parser_for_file')
    @patch('builtins.open', new_callable=mock_open, read_data=b'content')
    def test_integration_with_watcher(self, mock_file_open, mock_get_parser):
        """Test integration with file watcher by simulating watcher events."""
        # Set up mocks
        mock_parser = Mock()
        parse_result = {
            'nodes': [{'id': 'test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_parser.parse_file.return_value = parse_result
        mock_get_parser.return_value = mock_parser

        # Create a mock file watcher
        mock_watcher_callback = None

        def start_mock_watcher(callback, watch_dir='src'):
            nonlocal mock_watcher_callback
            mock_watcher_callback = callback
            return None

        # Simulate a file watcher starting and sending events
        start_mock_watcher(self.manager.on_file_event)

        # Mock storage hash check for modification
        self.storage.get_file_content_hash.return_value = "old_hash"
        # Mock storage file tracking needed for modification
        self.storage.file_nodes = {'test2.js': {'some_node_id'}}
        self.storage.get_node.return_value = {'id': 'some_node_id', 'content_hash': 'old_hash'}

        # Simulate file events within a context that mocks secrets/renames
        with patch('graph_core.manager.scan_parse_result_for_secrets', side_effect=lambda pr, fp: pr):
            with patch('graph_core.manager.DependencyGraphManager.update_function_names', return_value={}):
                mock_watcher_callback('created', 'test1.py')
                mock_watcher_callback('modified', 'test2.js')
                mock_watcher_callback('deleted', 'test3.ts')
                mock_watcher_callback('created', 'test4.txt')  # Unsupported

        # Verify the storage was updated correctly
        # Both created (test1.py) and modified (test2.js) should call add_or_update_file
        self.assertEqual(self.storage.add_or_update_file.call_count, 2)
        self.assertEqual(self.storage.remove_file.call_count, 1)

        # Check the call arguments specifically for the modified file
        found_modified_call = False
        for call_args in self.storage.add_or_update_file.call_args_list:
            args, kwargs = call_args
            if args[0] == 'test2.js':
                found_modified_call = True
                self.assertIn('content_hash', kwargs)
                self.assertNotEqual(kwargs['content_hash'], "old_hash")
                break
        self.assertTrue(found_modified_call, "Call for modified file 'test2.js' not found")

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
    
    @patch('time.time')
    def test_detect_renames(self, mock_time):
        """Test detection of renamed files."""
        # Set up mock time
        mock_time.return_value = 100.0
        
        # Add some deleted and created files to the buffers
        self.manager.deleted_files.append((99.0, 'old_file.py'))
        self.manager.created_files.append((99.5, 'new_file.py'))
        
        # Patch the detect_renames function to return a rename event
        with patch('graph_core.manager.detect_renames') as mock_detect_renames:
            mock_detect_renames.return_value = [
                MagicMock(
                    old_path='old_file.py',
                    new_path='new_file.py'
                )
            ]
            
            # Call detect_renames
            result = self.manager.detect_renames()
            
            # Verify the results
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].old_path, 'old_file.py')
            self.assertEqual(result[0].new_path, 'new_file.py')
            
            # Verify the deleted and created files were removed from the buffers
            self.assertEqual(len(self.manager.deleted_files), 0)
            self.assertEqual(len(self.manager.created_files), 0)
            
            # Verify the rename history was updated
            self.assertEqual(self.manager.rename_history['new_file.py'], 'old_file.py')
    
    def test_update_node_filepath(self):
        """Test updating the filepath property of nodes."""
        # Set up test data
        old_path = 'old_file.py'
        new_path = 'new_file.py'
        
        # Mock the storage and its graph property
        self.storage.file_nodes = {old_path: {'node1', 'node2'}}
        self.storage.graph = Mock()
        
        # Mock get_node to return a node
        self.storage.get_node.side_effect = lambda node_id: {
            'node1': {'id': 'node1', 'filepath': old_path, 'name': 'Test Node 1'},
            'node2': {'id': 'node2', 'filepath': old_path, 'name': 'Test Node 2'}
        }.get(node_id)
        
        # Call update_node_filepath
        result = self.manager.update_node_filepath(old_path, new_path)
        
        # Verify the result
        self.assertTrue(result)
        
        # Verify node updates
        expected_calls = [
            call('node1', **{'filepath': new_path, 'name': 'Test Node 1', 'rename_history': [old_path]}),
            call('node2', **{'filepath': new_path, 'name': 'Test Node 2', 'rename_history': [old_path]})
        ]
        self.storage.graph.add_node.assert_has_calls(expected_calls, any_order=True)
        
        # Verify file_nodes updates
        self.assertIn(new_path, self.storage.file_nodes)
        self.assertNotIn(old_path, self.storage.file_nodes)
        self.assertEqual(self.storage.file_nodes[new_path], {'node1', 'node2'})
        
        # Verify rename history was updated
        self.assertEqual(self.manager.rename_history[new_path], old_path)
    
    def test_update_node_filepath_nonexistent_file(self):
        """Test updating the filepath property of nodes for a nonexistent file."""
        # Set up test data
        old_path = 'nonexistent.py'
        new_path = 'new_file.py'
        
        # Mock the storage without the old file
        self.storage.file_nodes = {}
        self.storage.graph = Mock()
        
        # Call update_node_filepath
        result = self.manager.update_node_filepath(old_path, new_path)
        
        # Verify the result
        self.assertFalse(result)
        
        # Verify no nodes were updated
        self.storage.graph.add_node.assert_not_called()
        
        # Verify rename history was not updated
        self.assertNotIn(new_path, self.manager.rename_history)
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'content')
    @patch('graph_core.manager.get_parser_for_file')
    @patch('graph_core.manager.DependencyGraphManager.detect_renames')
    @patch('graph_core.manager.DependencyGraphManager.update_node_filepath')
    @patch('graph_core.manager.scan_parse_result_for_secrets')
    def test_on_file_event_with_rename_detection(self, mock_scan, mock_update_node, mock_detect_renames, mock_get_parser, mock_file_open):
        """Test handling file events with rename detection."""
        mock_parser = Mock()
        parse_result = {
            'nodes': [
                {'id': 'function:test_func', 'type': 'function', 'name': 'test_func'},
                {'id': 'module:another_file.py', 'type': 'module', 'name': 'another_file.py', 'filepath': 'another_file.py'} # Module for hashing
                ],
            'edges': []
        }
        mock_parser.parse_file.return_value = parse_result
        mock_get_parser.return_value = mock_parser

        # --- Test Deletion with Rename ---
        mock_detect_renames.return_value = [MagicMock(old_path='old_file.py', new_path='new_file.py')]
        self.manager.on_file_event('deleted', 'old_file.py')
        mock_detect_renames.assert_called() # Ensure rename detection was checked
        self.storage.remove_file.assert_not_called() # File removal should be skipped
        # Reset mocks for next part
        mock_file_open.reset_mock()
        mock_get_parser.reset_mock()
        mock_scan.reset_mock()
        mock_update_node.reset_mock()
        self.storage.reset_mock()

        # --- Test Creation with Rename ---
        mock_detect_renames.reset_mock()
        mock_detect_renames.return_value = [MagicMock(old_path='old_file.py', new_path='new_file.py')]
        self.manager.on_file_event('created', 'new_file.py')
        mock_detect_renames.assert_called() # Rename detection checked again
        mock_update_node.assert_called_with('old_file.py', 'new_file.py')
        # Parsing and adding should be skipped
        mock_file_open.assert_not_called() # No open needed if renamed
        mock_get_parser.assert_not_called()
        mock_scan.assert_not_called()
        self.storage.add_or_update_file.assert_not_called()
        mock_update_node.reset_mock()
        mock_detect_renames.reset_mock()

        # --- Test Creation without Rename ---
        mock_detect_renames.return_value = [] # Simulate no rename detected
        self.manager.on_file_event('created', 'another_file.py')
        mock_detect_renames.assert_called()
        mock_update_node.assert_not_called() # update_node_filepath shouldn't be called
        # File should be opened, parsed, scanned, and added
        mock_file_open.assert_called_with('another_file.py', 'rb') # Opened for hashing
        mock_get_parser.assert_called_with('another_file.py')
        mock_parser.parse_file.assert_called_with('another_file.py')
        mock_scan.assert_called() # Secrets scan should run
        self.storage.add_or_update_file.assert_called() # Add should be called

    @patch('builtins.open', new_callable=mock_open, read_data=b'content')
    @patch('graph_core.manager.scan_parse_result_for_secrets', side_effect=lambda pr, fp: pr)
    @patch('graph_core.manager.get_parser_for_file')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('os.walk')
    def test_process_existing_files(self, mock_walk, mock_isdir, mock_exists, mock_get_parser, mock_scan_secrets, mock_file_open):
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
        # Need module nodes in parse result for hash storage
        def side_effect_parse(filepath):
             filename = os.path.basename(filepath)
             module_id = f"module:{filename}"
             return {
                 'nodes': [{'id': module_id, 'type': 'module', 'name': filename, 'filepath': filepath}],
                 'edges': []
             }
        mock_parser.parse_file.side_effect = side_effect_parse
        mock_get_parser.return_value = mock_parser

        result = self.manager.process_existing_files(root_dir)

        self.assertEqual(result, 4)
        self.assertEqual(mock_file_open.call_count, 4)
        # Check that open was called for each expected file
        opened_files = {args[0] for args, kwargs in mock_file_open.call_args_list}
        self.assertEqual(opened_files, {os.path.join(root_dir, 'test1.py'), os.path.join(root_dir, 'test2.js'), os.path.join(subdir, 'test4.ts'), os.path.join(subdir, 'test5.tsx')})
        self.assertEqual(mock_get_parser.call_count, 4)
        self.assertEqual(mock_parser.parse_file.call_count, 4)
        self.assertEqual(mock_scan_secrets.call_count, 4)
        self.assertEqual(self.storage.add_or_update_file.call_count, 4)
    
    @patch('graph_core.manager.scan_parse_result_for_secrets', side_effect=lambda pr, fp: pr)
    @patch('graph_core.manager.DependencyGraphManager.update_function_names') # Mock rename check
    @patch('graph_core.manager.get_parser_for_file')
    def test_skip_modified_event_if_content_unchanged(self, mock_get_parser, mock_update_names, mock_scan_secrets):
        """Test that 'modified' event processing is skipped if file content hash is the same."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test.py")
            content = b"def func():\n  pass\n"
            # Write initial file (real write)
            with open(filepath, "wb") as f:
                f.write(content)
            initial_hash = calculate_content_hash(content)

            # Use real InMemoryStorage for easier hash checking
            storage = InMemoryGraphStorage()
            manager = DependencyGraphManager(storage=storage)
            mock_parser = Mock()
            mock_parser.parse_file.return_value = {
                'nodes': [{'id': 'module:test.py', 'type': 'module', 'name': 'test.py', 'filepath': filepath}], 'edges': []
            }
            mock_get_parser.return_value = mock_parser

            # Simulate creation - uses REAL open to read file and calculate hash
            manager.on_file_event('created', filepath)

            # Verify initial processing happened and hash is correct
            self.assertIsNotNone(storage.get_file_content_hash(filepath))
            self.assertEqual(storage.get_file_content_hash(filepath), initial_hash)
            mock_parser.parse_file.assert_called_once_with(filepath)
            mock_scan_secrets.assert_called_once()

            # Reset mocks for the 'modified' event check
            mock_parser.reset_mock()
            mock_scan_secrets.reset_mock()
            mock_update_names.reset_mock()

            # Simulate modification event WITHOUT changing content
            # Use mock_open HERE to control the content read for hash comparison
            with patch('builtins.open', mock_open(read_data=content)) as mock_modified_open:
                manager.on_file_event('modified', filepath)
                mock_modified_open.assert_called_with(filepath, 'rb') # Verify open was called for hash check

            # Verify that parser and storage update were SKIPPED
            mock_parser.parse_file.assert_not_called()
            mock_scan_secrets.assert_not_called()
            mock_update_names.assert_not_called()

            # Simulate modification WITH changing content
            new_content = b"def new_func():\n  pass\n"
            # Real write to change file content
            with open(filepath, "wb") as f:
                 f.write(new_content)
            new_hash = calculate_content_hash(new_content)

            # Reset mocks
            mock_parser.reset_mock()
            mock_scan_secrets.reset_mock()
            mock_update_names.reset_mock()

            # Use mock_open again HERE to control content read for hash check
            with patch('builtins.open', mock_open(read_data=new_content)) as mock_modified_open_new:
                 manager.on_file_event('modified', filepath)
                 mock_modified_open_new.assert_called_with(filepath, 'rb') # Verify open called

            # Verify processing DID happen this time
            mock_parser.parse_file.assert_called_once() # Verify parsing happened
            mock_scan_secrets.assert_called_once()
            mock_update_names.assert_called_once()
            self.assertEqual(storage.get_file_content_hash(filepath), new_hash) # Verify hash updated


if __name__ == '__main__':
    unittest.main() 