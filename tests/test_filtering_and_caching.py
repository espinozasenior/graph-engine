"""
Tests for the import hook module filtering and caching features.
"""

import os
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from graph_core.dynamic.import_hook import (
    PythonInstrumenter, 
    TransformationCache,
    initialize_hook,
    clear_transformation_cache
)

class TestModuleFiltering(unittest.TestCase):
    """Test cases for the module filtering feature."""
    
    def setUp(self):
        """Set up the test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.watch_dir = os.path.join(self.test_dir, "src")
        os.makedirs(self.watch_dir, exist_ok=True)
        
        # Create a few test files
        self.main_file = os.path.join(self.watch_dir, "main.py")
        with open(self.main_file, "w") as f:
            f.write("def main_func(): pass\n")
        
        self.utils_file = os.path.join(self.watch_dir, "utils.py")
        with open(self.utils_file, "w") as f:
            f.write("def util_func(): pass\n")
        
        self.test_file = os.path.join(self.watch_dir, "test_module.py")
        with open(self.test_file, "w") as f:
            f.write("def test_func(): pass\n")
        
        # Create a file outside the watch directory
        self.outside_file = os.path.join(self.test_dir, "outside.py")
        with open(self.outside_file, "w") as f:
            f.write("def outside_func(): pass\n")
    
    def tearDown(self):
        """Clean up the test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_basic_filtering(self):
        """Test basic filtering based on watch directory."""
        instrumenter = PythonInstrumenter(self.watch_dir)
        
        # Files in the watch directory should be instrumented
        self.assertTrue(instrumenter.should_instrument(self.main_file))
        self.assertTrue(instrumenter.should_instrument(self.utils_file))
        self.assertTrue(instrumenter.should_instrument(self.test_file))
        
        # Files outside the watch directory should not be instrumented
        self.assertFalse(instrumenter.should_instrument(self.outside_file))
        
        # Non-Python files should not be instrumented
        self.assertFalse(instrumenter.should_instrument(os.path.join(self.watch_dir, "data.txt")))
    
    def test_exclude_patterns(self):
        """Test excluding modules based on patterns."""
        exclude_patterns = ["test_", "utils"]
        instrumenter = PythonInstrumenter(self.watch_dir, exclude_patterns=exclude_patterns)
        
        # Files matching exclude patterns should not be instrumented
        self.assertTrue(instrumenter.should_instrument(self.main_file))
        self.assertFalse(instrumenter.should_instrument(self.utils_file))
        self.assertFalse(instrumenter.should_instrument(self.test_file))
        
        # Files outside the watch directory should not be instrumented
        self.assertFalse(instrumenter.should_instrument(self.outside_file))
    
    def test_include_patterns(self):
        """Test including only modules that match patterns."""
        include_patterns = ["main"]
        instrumenter = PythonInstrumenter(self.watch_dir, include_patterns=include_patterns)
        
        # Only files matching include patterns should be instrumented
        self.assertTrue(instrumenter.should_instrument(self.main_file))
        self.assertFalse(instrumenter.should_instrument(self.utils_file))
        self.assertFalse(instrumenter.should_instrument(self.test_file))
        
        # Files outside the watch directory should not be instrumented
        self.assertFalse(instrumenter.should_instrument(self.outside_file))
    
    def test_mixed_patterns(self):
        """Test using both include and exclude patterns."""
        include_patterns = ["main", "test_"]
        exclude_patterns = ["test_module"]
        instrumenter = PythonInstrumenter(
            self.watch_dir, 
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        )
        
        # Files matching include patterns but not exclude patterns should be instrumented
        self.assertTrue(instrumenter.should_instrument(self.main_file))
        self.assertFalse(instrumenter.should_instrument(self.utils_file))
        self.assertFalse(instrumenter.should_instrument(self.test_file))


class TestTransformationCache(unittest.TestCase):
    """Test cases for the transformation cache feature."""
    
    def setUp(self):
        """Set up the test environment."""
        self.cache_dir = tempfile.mkdtemp()
        self.cache = TransformationCache(self.cache_dir)
        
        self.test_file = os.path.join(self.cache_dir, "test.py")
        self.original_code = "def test_func(): pass\n"
        self.transformed_code = "from graph_core.dynamic.import_hook import function_call_queue, FunctionCallEvent\n\ndef test_func():\n    function_call_queue.put(FunctionCallEvent('test_func', 'test', 'test.py'))\n    pass\n"
    
    def tearDown(self):
        """Clean up the test environment."""
        shutil.rmtree(self.cache_dir)
    
    def test_cache_put_and_get(self):
        """Test putting and getting code from the cache."""
        # Initially, the cache should be empty
        self.assertIsNone(self.cache.get(self.test_file, self.original_code))
        
        # Put code in the cache
        self.cache.put(self.test_file, self.original_code, self.transformed_code)
        
        # Now we should get the transformed code
        cached_code = self.cache.get(self.test_file, self.original_code)
        self.assertEqual(cached_code, self.transformed_code)
    
    def test_cache_key_based_on_content(self):
        """Test that the cache key is based on the content, not just the filename."""
        # Put code in the cache
        self.cache.put(self.test_file, self.original_code, self.transformed_code)
        
        # Modify the code
        modified_code = self.original_code + "# Added comment\n"
        
        # Should not get a cache hit for modified content
        self.assertIsNone(self.cache.get(self.test_file, modified_code))
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        # Put code in the cache
        self.cache.put(self.test_file, self.original_code, self.transformed_code)
        
        # Clear the cache
        self.cache.clear()
        
        # Cache should be empty now
        self.assertIsNone(self.cache.get(self.test_file, self.original_code))
    
    @patch('builtins.open')
    def test_cache_error_handling(self, mock_open):
        """Test handling errors when reading from the cache."""
        # Mock an error when opening a file
        mock_open.side_effect = IOError("Test error")
        
        # Should return None on error
        self.assertIsNone(self.cache.get(self.test_file, self.original_code))


if __name__ == '__main__':
    unittest.main() 