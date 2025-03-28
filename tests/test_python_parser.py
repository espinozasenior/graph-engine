"""
Tests for the python_parser module.
"""

import os
import tempfile
import unittest

from graph_core.analyzer.python_parser import PythonParser


class TestPythonParser(unittest.TestCase):
    """Test cases for the PythonParser class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.parser = PythonParser()
        self.maxDiff = None  # Show full diff on assertion failures
    
    def test_parse_function_definitions(self):
        """Test parsing function definitions."""
        code = """
def hello_world():
    print("Hello, World!")
    
def add(a, b):
    return a + b
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file
            result = self.parser.parse_file(filepath)
            
            # Expected nodes (functions)
            expected_nodes = [
                {
                    'id': 'hello_world',
                    'type': 'function',
                    'name': 'hello_world',
                    'full_name': 'hello_world',
                    'filepath': filepath,
                    'line': 2,
                    'end_line': 3
                },
                {
                    'id': 'add',
                    'type': 'function',
                    'name': 'add',
                    'full_name': 'add',
                    'filepath': filepath,
                    'line': 5,
                    'end_line': 6
                }
            ]
            
            # Expected edges (function calls)
            expected_edges = [
                {
                    'source': 'hello_world',
                    'target': 'print',
                    'relation': 'CALLS',
                    'line': 3
                }
            ]
            
            # Check that the nodes are as expected
            for expected_node in expected_nodes:
                self.assertIn(expected_node, result['nodes'])
            
            # Check that the edges are as expected
            for expected_edge in expected_edges:
                self.assertIn(expected_edge, result['edges'])
        finally:
            os.remove(filepath)
    
    def test_parse_class_definitions(self):
        """Test parsing class definitions."""
        code = """
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def greet(self):
        print(f"Hello, my name is {self.name}")
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file
            result = self.parser.parse_file(filepath)
            
            # Expected nodes (class and methods)
            expected_nodes = [
                {
                    'id': 'Person',
                    'type': 'class',
                    'name': 'Person',
                    'filepath': filepath,
                    'line': 2,
                    'end_line': 8
                },
                {
                    'id': 'Person.__init__',
                    'type': 'function',
                    'name': '__init__',
                    'full_name': 'Person.__init__',
                    'filepath': filepath,
                    'line': 3,
                    'end_line': 5
                },
                {
                    'id': 'Person.greet',
                    'type': 'function',
                    'name': 'greet',
                    'full_name': 'Person.greet',
                    'filepath': filepath,
                    'line': 7,
                    'end_line': 8
                }
            ]
            
            # Expected edges (class-method relationships and function calls)
            expected_edges = [
                {
                    'source': 'Person',
                    'target': 'Person.__init__',
                    'relation': 'HAS_METHOD'
                },
                {
                    'source': 'Person',
                    'target': 'Person.greet',
                    'relation': 'HAS_METHOD'
                },
                {
                    'source': 'Person',
                    'target': 'print',
                    'relation': 'CALLS',
                    'line': 8
                }
            ]
            
            # Check nodes and edges
            for expected_node in expected_nodes:
                self.assertIn(expected_node, result['nodes'])
            
            for expected_edge in expected_edges:
                self.assertIn(expected_edge, result['edges'])
        finally:
            os.remove(filepath)
    
    def test_parse_class_inheritance(self):
        """Test parsing class inheritance."""
        code = """
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file
            result = self.parser.parse_file(filepath)
            
            # Expected inheritance edge
            expected_edge = {
                'source': 'Dog',
                'target': 'Animal',
                'relation': 'INHERITS'
            }
            
            # Check that the inheritance edge is present
            self.assertIn(expected_edge, result['edges'])
        finally:
            os.remove(filepath)
    
    def test_parse_imports(self):
        """Test parsing import statements."""
        code = """
import os
import sys as system
from datetime import datetime, timedelta
from collections import defaultdict as dd
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file
            result = self.parser.parse_file(filepath)
            
            # Check that all imports are in the nodes list
            import_nodes = [node for node in result['nodes'] if node['type'] == 'import']
            
            # Check specific imports are present
            self.assertTrue(any(node['name'] == 'os' for node in import_nodes))
            self.assertTrue(any(node['name'] == 'sys' and node['asname'] == 'system' for node in import_nodes))
            self.assertTrue(any(node['name'] == 'datetime.datetime' for node in import_nodes))
            self.assertTrue(any(node['name'] == 'datetime.timedelta' for node in import_nodes))
            self.assertTrue(any(node['name'] == 'collections.defaultdict' and node['asname'] == 'dd' for node in import_nodes))
            
            # Check import edges
            import_edges = [edge for edge in result['edges'] if edge['relation'] == 'IMPORTS']
            self.assertEqual(len(import_edges), len(import_nodes))
        finally:
            os.remove(filepath)
    
    def test_parse_function_calls(self):
        """Test parsing function calls."""
        code = """
def main():
    x = calculate(10)
    print(x)
    helper_function()

def calculate(n):
    return n * 2

def helper_function():
    result = calculate(5)
    return result
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file
            result = self.parser.parse_file(filepath)
            
            # Expected call edges
            expected_calls = [
                {
                    'source': 'main',
                    'target': 'calculate',
                    'relation': 'CALLS'
                },
                {
                    'source': 'main',
                    'target': 'print',
                    'relation': 'CALLS'
                },
                {
                    'source': 'main',
                    'target': 'helper_function',
                    'relation': 'CALLS'
                },
                {
                    'source': 'helper_function',
                    'target': 'calculate',
                    'relation': 'CALLS'
                }
            ]
            
            # Check that all expected calls are present
            # (we don't check line numbers here as they can vary)
            call_edges = [{'source': e['source'], 'target': e['target'], 'relation': e['relation']} 
                          for e in result['edges'] if e['relation'] == 'CALLS']
            
            for expected_call in expected_calls:
                self.assertIn(expected_call, call_edges)
        finally:
            os.remove(filepath)
    
    def test_parse_method_calls(self):
        """Test parsing method calls within classes."""
        code = """
class Calculator:
    def __init__(self):
        self.value = 0
    
    def add(self, n):
        self.value += n
        self.display()
    
    def display(self):
        print(f"Current value: {self.value}")
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file
            result = self.parser.parse_file(filepath)
            
            # Expected call edge (from add method to display method)
            self.assertTrue(any(
                edge['source'] == 'Calculator' and 
                edge['target'] == 'print' and 
                edge['relation'] == 'CALLS'
                for edge in result['edges']
            ))
        finally:
            os.remove(filepath)
    
    def test_file_not_found(self):
        """Test handling of a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            self.parser.parse_file("non_existent_file.py")
    
    def test_syntax_error(self):
        """Test handling of Python syntax errors."""
        code = """
def broken_function()
    print("This has a syntax error")
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file - should raise SyntaxError
            with self.assertRaises(SyntaxError):
                self.parser.parse_file(filepath)
        finally:
            os.remove(filepath)
    
    def test_complex_example(self):
        """Test parsing a more complex example with multiple features."""
        code = """
import os
from datetime import datetime

def format_date(date):
    return date.strftime("%Y-%m-%d")

class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
    
    def log(self, message):
        timestamp = datetime.now()
        formatted_date = format_date(timestamp)
        with open(self.log_file, 'a') as f:
            f.write(f"{formatted_date}: {message}\\n")
    
    def clear_log(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

# Create a logger and use it
logger = Logger("app.log")
logger.log("Application started")
"""
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            filepath = tmp.name
        
        try:
            # Parse the file
            result = self.parser.parse_file(filepath)
            
            # Check for the expected nodes
            node_types = [node['type'] for node in result['nodes']]
            self.assertIn('import', node_types)
            self.assertIn('function', node_types)
            self.assertIn('class', node_types)
            
            # Check that the Logger class is defined
            self.assertTrue(any(node['id'] == 'Logger' for node in result['nodes']))
            
            # Check that Logger.log and Logger.clear_log methods are defined
            self.assertTrue(any(node['id'] == 'Logger.log' for node in result['nodes']))
            self.assertTrue(any(node['id'] == 'Logger.clear_log' for node in result['nodes']))
            
            # Check for function call edges
            # Logger.log calls format_date
            self.assertTrue(any(
                edge['source'] == 'Logger' and 
                edge['target'] == 'format_date' and 
                edge['relation'] == 'CALLS'
                for edge in result['edges']
            ))
            
            # Logger.log calls open
            self.assertTrue(any(
                edge['source'] == 'Logger' and 
                edge['target'] == 'open' and 
                edge['relation'] == 'CALLS'
                for edge in result['edges']
            ))
            
            # Logger.clear_log calls os.path.exists and os.remove
            self.assertTrue(any(
                edge['source'] == 'Logger' and 
                edge['target'].endswith('exists') and 
                edge['relation'] == 'CALLS'
                for edge in result['edges']
            ))
            
            self.assertTrue(any(
                edge['source'] == 'Logger' and 
                edge['target'].endswith('remove') and 
                edge['relation'] == 'CALLS'
                for edge in result['edges']
            ))
        finally:
            os.remove(filepath)


if __name__ == '__main__':
    unittest.main() 