"""
Tests for the dependency_graph_manager module.
"""

import os
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

from graph_core.manager import DependencyGraphManager, DEFAULT_JSON_PATH
from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.storage.json_storage import JSONGraphStorage
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
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_on_file_event_with_rename_detection(self, mock_get_parser):
        """Test handling file events with rename detection."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser.parse_file.return_value = {
            'nodes': [{'id': 'function:test_func', 'type': 'function', 'name': 'test_func'}],
            'edges': []
        }
        mock_get_parser.return_value = mock_parser
        
        # Create a function to simulate renames being detected
        original_detect_renames = self.manager.detect_renames
        
        def mock_detect_renames():
            if hasattr(self.manager, 'simulate_rename') and self.manager.simulate_rename:
                return [MagicMock(old_path='old_file.py', new_path='new_file.py')]
            return []
        
        self.manager.detect_renames = mock_detect_renames
        
        # Also mock update_node_filepath
        self.manager.update_node_filepath = Mock(return_value=True)
        
        # Test file deletion with rename detection
        self.manager.simulate_rename = True
        self.manager.on_file_event('deleted', 'old_file.py')
        
        # Verify the file was not removed from storage
        self.storage.remove_file.assert_not_called()
        
        # Test file creation with rename detection
        self.manager.on_file_event('created', 'new_file.py')
        
        # Verify update_node_filepath was called but not add_or_update_file
        self.manager.update_node_filepath.assert_called_with('old_file.py', 'new_file.py')
        self.storage.add_or_update_file.assert_not_called()
        
        # Test file creation without a rename being detected
        self.manager.simulate_rename = False
        self.manager.on_file_event('created', 'another_file.py')
        
        # Verify the file was parsed and added to storage
        mock_parser.parse_file.assert_called_with('another_file.py')
        self.storage.add_or_update_file.assert_called_with(
            'another_file.py', mock_parser.parse_file.return_value
        )
        
        # Restore original method
        self.manager.detect_renames = original_detect_renames
    
    def test_integration_rename_detection(self):
        """Test the rename detection integration with the storage."""
        # Create a real InMemoryGraphStorage instance for this test
        storage = InMemoryGraphStorage()
        manager = DependencyGraphManager(storage)
        
        # Add a file with some nodes to the storage
        old_file = 'src/old_file.py'
        new_file = 'src/new_file.py'
        
        # Create test nodes and edges
        nodes = [
            {'id': 'function:test_func', 'type': 'function', 'name': 'test_func', 'filepath': old_file},
            {'id': 'class:TestClass', 'type': 'class', 'name': 'TestClass', 'filepath': old_file}
        ]
        edges = [
            {'source': 'function:test_func', 'target': 'class:TestClass', 'type': 'uses'}
        ]
        
        # Add the file to storage
        storage.add_or_update_file(old_file, {'nodes': nodes, 'edges': edges})
        
        # Verify nodes and edges were added
        self.assertEqual(len(storage.get_all_nodes()), 2)
        self.assertEqual(len(storage.get_all_edges()), 1)
        
        # Directly call update_node_filepath to simulate a rename
        updated = manager.update_node_filepath(old_file, new_file)
        
        # Verify the update was successful
        self.assertTrue(updated)
        
        # Get updated nodes
        updated_nodes = storage.get_all_nodes()
        self.assertEqual(len(updated_nodes), 2)
        
        # Verify node filepaths were updated
        for node in updated_nodes:
            self.assertEqual(node['filepath'], new_file)
            self.assertIn('rename_history', node)
            self.assertIn(old_file, node['rename_history'])
        
        # Verify the file tracking was updated
        self.assertIn(new_file, storage.file_nodes)
        self.assertNotIn(old_file, storage.file_nodes)
        
        # Verify edges were preserved
        edges = storage.get_all_edges()
        self.assertEqual(len(edges), 1)
        
        # Verify the rename was recorded in the manager's history
        self.assertIn(new_file, manager.rename_history)
        self.assertEqual(manager.rename_history[new_file], old_file)

    def test_json_storage_initialization(self):
        """Test initialization with JSONGraphStorage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "test_graph.json")
            
            # Test with storage type parameter
            manager = DependencyGraphManager(storage_type="json", json_path=json_path)
            self.assertIsInstance(manager.storage, JSONGraphStorage)
            self.assertEqual(manager.storage.json_path, json_path)
            self.assertTrue(manager.is_json_storage)
            
            # Test with factory method
            manager2 = DependencyGraphManager.create_with_json_storage(json_path)
            self.assertIsInstance(manager2.storage, JSONGraphStorage)
            self.assertEqual(manager2.storage.json_path, json_path)
            self.assertTrue(manager2.is_json_storage)
            
            # Test with explicit storage instance
            storage = JSONGraphStorage(json_path)
            manager3 = DependencyGraphManager(storage=storage)
            self.assertIsInstance(manager3.storage, JSONGraphStorage)
            self.assertEqual(manager3.storage.json_path, json_path)
            self.assertTrue(manager3.is_json_storage)
    
    def test_memory_storage_initialization(self):
        """Test initialization with InMemoryGraphStorage."""
        # Test with default parameters
        manager = DependencyGraphManager()
        self.assertIsInstance(manager.storage, InMemoryGraphStorage)
        self.assertFalse(manager.is_json_storage)
        
        # Test with storage type parameter
        manager2 = DependencyGraphManager(storage_type="memory")
        self.assertIsInstance(manager2.storage, InMemoryGraphStorage)
        self.assertFalse(manager2.is_json_storage)
        
        # Test with factory method
        manager3 = DependencyGraphManager.create_with_memory_storage()
        self.assertIsInstance(manager3.storage, InMemoryGraphStorage)
        self.assertFalse(manager3.is_json_storage)
        
        # Test with explicit storage instance
        storage = InMemoryGraphStorage()
        manager4 = DependencyGraphManager(storage=storage)
        self.assertIsInstance(manager4.storage, InMemoryGraphStorage)
        self.assertFalse(manager4.is_json_storage)

    @patch('graph_core.manager.get_parser_for_file')
    def test_json_storage_persistence(self, mock_get_parser):
        """Test that operations are persisted to JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "test_graph.json")
            
            # Set up mock parser
            mock_parser = Mock()
            mock_parser.parse_file.return_value = {
                'nodes': [
                    {'id': 'function:test_func', 'type': 'function', 'name': 'test_func'}
                ],
                'edges': [
                    {'source': 'function:test_func', 'target': 'module:test.py', 'type': 'belongs_to'}
                ]
            }
            mock_get_parser.return_value = mock_parser
            
            # Create manager with JSON storage
            manager = DependencyGraphManager.create_with_json_storage(json_path)
            
            # Add a file
            manager.on_file_event('created', 'test.py')
            
            # Verify the file exists and contains expected data
            self.assertTrue(os.path.exists(json_path))
            
            with open(json_path, 'r') as f:
                data = json.load(f)
                self.assertIn('nodes', data)
                self.assertIn('edges', data)
                self.assertIn('file_nodes', data)
                
                # Check nodes
                self.assertGreaterEqual(len(data['nodes']), 1)
                function_node = next((n for n in data['nodes'] if n['id'] == 'function:test_func'), None)
                self.assertIsNotNone(function_node)
                self.assertEqual(function_node['name'], 'test_func')
                
                # Check edges
                self.assertGreaterEqual(len(data['edges']), 1)
                
                # Check file_nodes
                self.assertIn('test.py', data['file_nodes'])
            
            # Create a new manager instance to simulate restarting the application
            manager2 = DependencyGraphManager.create_with_json_storage(json_path)
            
            # Verify the graph was loaded
            nodes = manager2.storage.get_all_nodes()
            self.assertGreaterEqual(len(nodes), 1)
            function_node = next((n for n in nodes if n['id'] == 'function:test_func'), None)
            self.assertIsNotNone(function_node)
            
            # Make a change
            manager2.on_file_event('deleted', 'test.py')
            
            # Verify the change was saved
            with open(json_path, 'r') as f:
                data = json.load(f)
                self.assertEqual(len(data['nodes']), 0)
                self.assertEqual(len(data['edges']), 0)
                self.assertEqual(len(data['file_nodes']), 0)

    @patch('graph_core.manager.get_parser_for_file')
    def test_json_storage_with_dynamic_events(self, mock_get_parser):
        """Test that dynamic events update the JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "test_graph.json")
            
            # Set up mock parser
            mock_parser = Mock()
            mock_parser.parse_file.return_value = {
                'nodes': [
                    {'id': 'function:test_func', 'type': 'function', 'name': 'test_func'},
                    {'id': 'function:another_func', 'type': 'function', 'name': 'another_func'}
                ],
                'edges': []
            }
            mock_get_parser.return_value = mock_parser
            
            # Create manager with JSON storage
            manager = DependencyGraphManager.create_with_json_storage(json_path)
            
            # Add a file
            manager.on_file_event('created', 'test.py')
            
            # Process a dynamic event
            manager.process_dynamic_event('call', 'function:test_func', 'function:another_func')
            
            # Verify the event was saved
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                # Find the dynamic edge
                dynamic_edge = None
                for edge in data['edges']:
                    if (edge['source'] == 'function:test_func' and 
                        edge['target'] == 'function:another_func' and 
                        edge.get('dynamic') == True):
                        dynamic_edge = edge
                        break
                
                self.assertIsNotNone(dynamic_edge)
                self.assertEqual(dynamic_edge['type'], 'calls')
                self.assertEqual(dynamic_edge['dynamic_call_count'], 1)
            
            # Create a new manager and update the call count
            manager2 = DependencyGraphManager.create_with_json_storage(json_path)
            manager2.update_function_call_count('function:test_func')
            
            # Verify the count was updated and saved
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                # Find the function node
                func_node = next((n for n in data['nodes'] if n['id'] == 'function:test_func'), None)
                self.assertIsNotNone(func_node)
                self.assertEqual(func_node.get('dynamic_call_count'), 1)

    @patch('graph_core.manager.get_parser_for_file')
    @patch('graph_core.manager.scan_parse_result_for_secrets')
    def test_json_storage_with_secret_detection(self, mock_scan_result, mock_get_parser):
        """Test that secret detection works with JSON storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "test_graph.json")
            
            # Set up mock parser
            mock_parser = Mock()
            
            # Initial parse result with no secrets
            parse_result = {
                'nodes': [
                    {
                        'id': 'function:get_credentials', 
                        'type': 'function', 
                        'name': 'get_credentials',
                        'start_point': {'row': 1},
                        'end_point': {'row': 5}
                    }
                ],
                'edges': []
            }
            
            # Mock parser to return the parse result
            mock_parser.parse_file.return_value = parse_result
            mock_get_parser.return_value = mock_parser
            
            # Setup the mock scan_parse_result_for_secrets to add secret info
            mock_scan_result.return_value = {
                'nodes': [
                    {
                        'id': 'function:get_credentials', 
                        'type': 'function', 
                        'name': 'get_credentials',
                        'start_point': {'row': 1},
                        'end_point': {'row': 5},
                        'hasSecret': True,
                        'secretWarnings': [
                            {
                                'secretType': 'api_key',
                                'lineNumber': 3,
                                'snippet': "api_key = 'REDACTED'",
                                'confidence': 'high'
                            }
                        ]
                    }
                ],
                'edges': []
            }
            
            # Create manager with JSON storage
            manager = DependencyGraphManager.create_with_json_storage(json_path)
            
            # Process a file
            manager.on_file_event('created', 'test_file.py')
            
            # Verify scan_parse_result_for_secrets was called
            mock_scan_result.assert_called_once()
            
            # Verify the graph was updated with secret information
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                # Find the function node
                func_node = next((n for n in data['nodes'] if n['id'] == 'function:get_credentials'), None)
                self.assertIsNotNone(func_node)
                
                # Check that hasSecret is set to True
                self.assertTrue(func_node.get('hasSecret', False))
                
                # Check that secretWarnings is present and contains the redacted snippet
                self.assertIn('secretWarnings', func_node)
                self.assertEqual(len(func_node['secretWarnings']), 1)
                
                warning = func_node['secretWarnings'][0]
                self.assertEqual(warning['secretType'], 'api_key')
                self.assertEqual(warning['lineNumber'], 3)
                self.assertIn('REDACTED', warning['snippet'])
                self.assertEqual(warning['confidence'], 'high')

    @patch('graph_core.manager.get_parser_for_file')
    def test_migration_to_json_storage(self, mock_get_parser):
        """Test migration from in-memory to JSON storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "migrated_graph.json")
            
            # Set up mock parser
            mock_parser = Mock()
            mock_parser.parse_file.return_value = {
                'nodes': [
                    {'id': 'function:test_func', 'type': 'function', 'name': 'test_func'},
                    {'id': 'class:TestClass', 'type': 'class', 'name': 'TestClass'}
                ],
                'edges': [
                    {'source': 'function:test_func', 'target': 'class:TestClass', 'type': 'uses'}
                ]
            }
            mock_get_parser.return_value = mock_parser
            
            # Create manager with in-memory storage
            manager = DependencyGraphManager.create_with_memory_storage()
            
            # Add a file
            manager.on_file_event('created', 'test.py')
            
            # Verify content is in in-memory storage
            nodes = manager.storage.get_all_nodes()
            self.assertEqual(len(nodes), 2)
            self.assertIn('function:test_func', [n['id'] for n in nodes])
            self.assertIn('class:TestClass', [n['id'] for n in nodes])
            
            edges = manager.storage.get_all_edges()
            self.assertEqual(len(edges), 1)
            
            # Migrate to JSON storage
            result = manager.migrate_to_json_storage(json_path)
            self.assertTrue(result)
            self.assertTrue(manager.is_json_storage)
            self.assertIsInstance(manager.storage, JSONGraphStorage)
            
            # Verify the file exists
            self.assertTrue(os.path.exists(json_path))
            
            # Verify content was migrated correctly
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                # Check nodes
                self.assertEqual(len(data['nodes']), 2)
                func_node = next((n for n in data['nodes'] if n['id'] == 'function:test_func'), None)
                self.assertIsNotNone(func_node)
                self.assertEqual(func_node['name'], 'test_func')
                
                class_node = next((n for n in data['nodes'] if n['id'] == 'class:TestClass'), None)
                self.assertIsNotNone(class_node)
                self.assertEqual(class_node['name'], 'TestClass')
                
                # Check edges
                self.assertEqual(len(data['edges']), 1)
                edge = data['edges'][0]
                self.assertEqual(edge['source'], 'function:test_func')
                self.assertEqual(edge['target'], 'class:TestClass')
                self.assertEqual(edge['type'], 'uses')
                
                # Check file_nodes mapping
                self.assertIn('test.py', data['file_nodes'])
                file_node_ids = data['file_nodes']['test.py']
                self.assertIn('function:test_func', file_node_ids)
                self.assertIn('class:TestClass', file_node_ids)
    
    @patch('graph_core.manager.get_parser_for_file')
    def test_migration_with_existing_data(self, mock_get_parser):
        """Test migration with existing data in JSON storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "migrated_graph.json")
            
            # Set up mock parser
            mock_parser = Mock()
            mock_parser.parse_file.return_value = {
                'nodes': [
                    {'id': 'function:new_func', 'type': 'function', 'name': 'new_func'}
                ],
                'edges': []
            }
            mock_get_parser.return_value = mock_parser
            
            # Create manager with in-memory storage
            manager = DependencyGraphManager.create_with_memory_storage()
            
            # Add a file
            manager.on_file_event('created', 'new.py')
            
            # Migrate to JSON storage
            result = manager.migrate_to_json_storage(json_path)
            self.assertTrue(result)
            
            # Verify the file exists and contains the migrated data
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                # Check that our in-memory data was migrated
                self.assertGreaterEqual(len(data['nodes']), 1)
                found_new_func = False
                for node in data['nodes']:
                    if node['id'] == 'function:new_func':
                        found_new_func = True
                        break
                self.assertTrue(found_new_func, "Could not find migrated function node")
                
                # Check file_nodes mapping contains our file
                self.assertIn('new.py', data['file_nodes'])
    
    def test_migration_error_handling(self):
        """Test error handling during migration."""
        # Test migrating from JSON storage
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "test_graph.json")
            
            # Create manager with JSON storage
            manager = DependencyGraphManager.create_with_json_storage(json_path)
            
            # Try to migrate - should raise ValueError
            with self.assertRaises(ValueError):
                manager.migrate_to_json_storage(json_path)
        
        # Using Windows path that should be invalid because of invalid characters
        if os.name == 'nt':  # Windows
            invalid_path = 'C:\\Invalid\\Path\\With\\*\\Asterisk\\graph.json'
        else:  # Unix-like
            # File in a directory that doesn't exist and requires root permissions
            invalid_path = '/root/nonexistent/directory/graph.json'
            
        # Test migration with invalid path
        manager = DependencyGraphManager.create_with_memory_storage()
        
        # Attempt migration - should return False
        result = manager.migrate_to_json_storage(invalid_path)
        self.assertFalse(result)

    @patch('graph_core.manager.get_parser_for_file')
    def test_json_storage_rename_detection(self, mock_get_parser):
        """Test that rename detection works with JSON storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path = os.path.join(temp_dir, "test_graph.json")
            
            # Set up mock parser
            mock_parser = Mock()
            mock_parser.parse_file.return_value = {
                'nodes': [
                    {'id': 'function:test_func', 'type': 'function', 'name': 'test_func', 'filepath': 'old_file.py'}
                ],
                'edges': []
            }
            mock_get_parser.return_value = mock_parser
            
            # Create manager with JSON storage
            manager = DependencyGraphManager.create_with_json_storage(json_path)
            
            # Add a file
            manager.on_file_event('created', 'old_file.py')
            
            # Update node filepath
            manager.update_node_filepath('old_file.py', 'new_file.py')
            
            # Verify the update was saved
            with open(json_path, 'r') as f:
                data = json.load(f)
                
                # Find the function node
                func_node = next((n for n in data['nodes'] if n['id'] == 'function:test_func'), None)
                self.assertIsNotNone(func_node)
                self.assertEqual(func_node.get('filepath'), 'new_file.py')
                self.assertIn('rename_history', func_node)
                self.assertIn('old_file.py', func_node['rename_history'])
                
                # Check file_nodes mapping
                self.assertIn('new_file.py', data['file_nodes'])
                self.assertNotIn('old_file.py', data['file_nodes'])


if __name__ == '__main__':
    unittest.main() 