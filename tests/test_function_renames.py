"""
Tests for function rename detection.

This module tests the functionality for detecting and updating renamed functions
in the dependency graph.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_core.watchers.rename_detection import match_functions
from graph_core.manager import DependencyGraphManager
from graph_core.storage.in_memory import InMemoryGraphStorage


# Test data: Function with original name
PYTHON_OLD_FUNCTION = """
def original_function(param1, param2):
    # A test function
    result = param1 + param2
    return result
"""

# Test data: Same function with new name
PYTHON_NEW_FUNCTION = """
def renamed_function(param1, param2):
    # A test function
    result = param1 + param2
    return result
"""

# Test data: Function with slight body changes
PYTHON_MODIFIED_FUNCTION = """
def renamed_function(param1, param2):
    # A test function with minor changes
    # Added comment
    result = param1 + param2
    return result  # Another comment
"""

# Test data: More significantly changed function
PYTHON_DIFFERENT_FUNCTION = """
def different_function(p1, p2, p3):
    # A completely different function
    if p1 > 0:
        return p1 * p2 * p3
    else:
        return p1 + p2 + p3
"""


class TestFunctionRenameDetection(unittest.TestCase):
    """Tests for function rename detection."""

    def test_match_functions_exact_body(self):
        """Test matching functions with exactly the same body."""
        # Create old AST with one function
        old_ast = {
            'nodes': [
                {
                    'id': 'function:original_function',
                    'type': 'function',
                    'name': 'original_function',
                    'body': PYTHON_OLD_FUNCTION,
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        # Create new AST with renamed function but same body
        new_ast = {
            'nodes': [
                {
                    'id': 'function:renamed_function',
                    'type': 'function',
                    'name': 'renamed_function',
                    'body': PYTHON_OLD_FUNCTION,  # Same body
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        # Test function matching
        matches = match_functions(old_ast, new_ast)
        
        # Verify the match
        self.assertEqual(len(matches), 1)
        self.assertIn('function:original_function', matches)
        self.assertEqual(matches['function:original_function'], 'function:renamed_function')

    def test_match_functions_similar_body(self):
        """Test matching functions with similar but not identical bodies."""
        # Create old AST with one function
        old_ast = {
            'nodes': [
                {
                    'id': 'function:original_function',
                    'type': 'function',
                    'name': 'original_function',
                    'body': PYTHON_OLD_FUNCTION,
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        # Create new AST with renamed function and slightly modified body
        new_ast = {
            'nodes': [
                {
                    'id': 'function:renamed_function',
                    'type': 'function',
                    'name': 'renamed_function',
                    'body': PYTHON_MODIFIED_FUNCTION,  # Slightly modified
                    'start_point': (1, 0),
                    'end_point': (6, 0)
                }
            ],
            'edges': []
        }
        
        # Test function matching with a lower similarity threshold for testing
        matches = match_functions(old_ast, new_ast, similarity_threshold=0.4)
        
        # Verify the match - should still match despite minor changes
        self.assertEqual(len(matches), 1)
        self.assertIn('function:original_function', matches)
        self.assertEqual(matches['function:original_function'], 'function:renamed_function')

    def test_match_functions_different_body(self):
        """Test that functions with significantly different bodies don't match."""
        # Create old AST with one function
        old_ast = {
            'nodes': [
                {
                    'id': 'function:original_function',
                    'type': 'function',
                    'name': 'original_function',
                    'body': PYTHON_OLD_FUNCTION,
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        # Create new AST with renamed function and completely different body
        new_ast = {
            'nodes': [
                {
                    'id': 'function:different_function',
                    'type': 'function',
                    'name': 'different_function',
                    'body': PYTHON_DIFFERENT_FUNCTION,  # Different body
                    'start_point': (1, 0),
                    'end_point': (8, 0)
                }
            ],
            'edges': []
        }
        
        # Test function matching
        matches = match_functions(old_ast, new_ast)
        
        # Verify no matches were found
        self.assertEqual(len(matches), 0)

    def test_match_functions_multiple_candidates(self):
        """Test matching when there are multiple candidate functions."""
        # Create old AST with two functions
        old_ast = {
            'nodes': [
                {
                    'id': 'function:function1',
                    'type': 'function',
                    'name': 'function1',
                    'body': 'def function1(a, b): return a + b',
                    'start_point': (1, 0),
                    'end_point': (1, 30)
                },
                {
                    'id': 'function:function2',
                    'type': 'function',
                    'name': 'function2',
                    'body': 'def function2(a, b): return a * b',
                    'start_point': (3, 0),
                    'end_point': (3, 30)
                }
            ],
            'edges': []
        }
        
        # Create new AST with renamed functions
        new_ast = {
            'nodes': [
                {
                    'id': 'function:add_func',
                    'type': 'function',
                    'name': 'add_func',
                    'body': 'def add_func(a, b): return a + b',  # Similar to function1
                    'start_point': (1, 0),
                    'end_point': (1, 30)
                },
                {
                    'id': 'function:multiply_func',
                    'type': 'function',
                    'name': 'multiply_func',
                    'body': 'def multiply_func(a, b): return a * b',  # Similar to function2
                    'start_point': (3, 0),
                    'end_point': (3, 35)
                }
            ],
            'edges': []
        }
        
        # Test function matching
        matches = match_functions(old_ast, new_ast)
        
        # Verify the matches
        self.assertEqual(len(matches), 2)
        self.assertIn('function:function1', matches)
        self.assertIn('function:function2', matches)
        self.assertEqual(matches['function:function1'], 'function:add_func')
        self.assertEqual(matches['function:function2'], 'function:multiply_func')


class TestDependencyGraphManagerFunctionRenames(unittest.TestCase):
    """Tests for function rename handling in DependencyGraphManager."""

    def setUp(self):
        """Set up test environment."""
        self.storage = InMemoryGraphStorage()
        self.manager = DependencyGraphManager(self.storage)

    def test_update_function_names(self):
        """Test updating function names when a match is found."""
        # Add a function to the storage first
        old_parse_result = {
            'nodes': [
                {
                    'id': 'function:module.original_function',
                    'type': 'function',
                    'name': 'original_function',
                    'body': PYTHON_OLD_FUNCTION,
                    'filepath': 'test.py',
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        self.storage.add_or_update_file('test.py', old_parse_result)
        
        # Create a new AST with the renamed function
        new_ast = {
            'nodes': [
                {
                    'id': 'function:module.renamed_function',
                    'type': 'function',
                    'name': 'renamed_function',
                    'body': PYTHON_OLD_FUNCTION,  # Same body
                    'filepath': 'test.py',
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        # Call update_function_names
        renamed_functions = self.manager.update_function_names(old_parse_result, new_ast)
        
        # Verify the function was renamed
        self.assertEqual(len(renamed_functions), 1)
        old_id = 'function:module.original_function'
        new_id = 'function:module.renamed_function'
        self.assertIn(old_id, renamed_functions)
        self.assertEqual(renamed_functions[old_id], new_id)
        
        # Verify the node in storage was updated
        node = self.storage.get_node(old_id)
        self.assertIsNotNone(node)
        self.assertEqual(node['name'], 'renamed_function')
        self.assertIn('rename_history', node)
        self.assertIn('original_function', node['rename_history'])

    def test_function_rename_with_mocked_detection(self):
        """Test the function rename with mocked match_functions."""
        # Create original AST with a function
        old_ast = {
            'nodes': [
                {
                    'id': 'function:original_function',
                    'type': 'function',
                    'name': 'original_function',
                    'body': PYTHON_OLD_FUNCTION,
                    'filepath': 'test.py',
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        # Add to storage
        self.storage.add_or_update_file('test.py', old_ast)
        
        # Create new AST with renamed function
        new_ast = {
            'nodes': [
                {
                    'id': 'function:renamed_function',
                    'type': 'function',
                    'name': 'renamed_function',
                    'body': PYTHON_OLD_FUNCTION,  # Same body
                    'filepath': 'test.py',
                    'start_point': (1, 0),
                    'end_point': (5, 0)
                }
            ],
            'edges': []
        }
        
        # Mock match_functions to ensure it returns our expected match
        with patch('graph_core.watchers.rename_detection.match_functions') as mock_match:
            mock_match.return_value = {'function:original_function': 'function:renamed_function'}
            
            # Call update_function_names
            renamed_functions = self.manager.update_function_names(old_ast, new_ast)
            
            # Verify the function was renamed
            self.assertEqual(len(renamed_functions), 1)
            old_id = 'function:original_function'
            new_id = 'function:renamed_function'
            self.assertIn(old_id, renamed_functions)
            self.assertEqual(renamed_functions[old_id], new_id)
            
            # Verify the node in storage was updated
            node = self.storage.get_node(old_id)
            self.assertIsNotNone(node)
            self.assertEqual(node['name'], 'renamed_function')
            self.assertIn('rename_history', node)
            self.assertIn('original_function', node['rename_history'])
            
            # Verify only one node exists (no duplicates)
            all_nodes = self.storage.get_all_nodes()
            self.assertEqual(len(all_nodes), 1, "Should have exactly one node after rename")

    def test_update_function_names_with_edges(self):
        """Test that edges are preserved when a function is renamed."""
        # Add functions with an edge between them
        old_parse_result = {
            'nodes': [
                {
                    'id': 'function:caller',
                    'type': 'function',
                    'name': 'caller',
                    'body': 'def caller(): return original_function()',
                    'filepath': 'test.py',
                    'start_point': (1, 0),
                    'end_point': (1, 40)
                },
                {
                    'id': 'function:original_function',
                    'type': 'function',
                    'name': 'original_function',
                    'body': PYTHON_OLD_FUNCTION,
                    'filepath': 'test.py',
                    'start_point': (3, 0),
                    'end_point': (7, 0)
                }
            ],
            'edges': [
                {
                    'source': 'function:caller',
                    'target': 'function:original_function',
                    'type': 'calls'
                }
            ]
        }
        
        self.storage.add_or_update_file('test.py', old_parse_result)
        
        # Create new AST with renamed function
        new_ast = {
            'nodes': [
                {
                    'id': 'function:caller',
                    'type': 'function',
                    'name': 'caller',
                    'body': 'def caller(): return renamed_function()',  # Updated call
                    'filepath': 'test.py',
                    'start_point': (1, 0),
                    'end_point': (1, 40)
                },
                {
                    'id': 'function:renamed_function',
                    'type': 'function',
                    'name': 'renamed_function',
                    'body': PYTHON_OLD_FUNCTION,
                    'filepath': 'test.py',
                    'start_point': (3, 0),
                    'end_point': (7, 0)
                }
            ],
            'edges': [
                {
                    'source': 'function:caller',
                    'target': 'function:renamed_function',
                    'type': 'calls'
                }
            ]
        }
        
        # Call update_function_names with mocked detection
        with patch('graph_core.watchers.rename_detection.match_functions') as mock_match:
            mock_match.return_value = {'function:original_function': 'function:renamed_function'}
            
            renamed_functions = self.manager.update_function_names(old_parse_result, new_ast)
            
            # Verify the function was renamed
            self.assertEqual(len(renamed_functions), 1)
            
            # Verify the edges are still present in the graph
            edges = self.storage.get_all_edges()
            self.assertEqual(len(edges), 1)
            
            # The edge should still point to the original node ID since we're updating the node, not recreating it
            edge = edges[0]
            self.assertEqual(edge['source'], 'function:caller')
            self.assertEqual(edge['target'], 'function:original_function')
            self.assertEqual(edge['type'], 'calls')


if __name__ == "__main__":
    unittest.main() 