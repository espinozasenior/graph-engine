"""
Python Parser Module

This module provides functionality to parse Python files and extract
information about functions, classes, methods, imports, and function calls.
"""

import ast
import os
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

# Set up logging
logger = logging.getLogger(__name__)


class PythonParser:
    """
    A parser for Python files that extracts information about code structures
    and relationships.
    """

    def __init__(self):
        """Initialize the Python parser."""
        self.nodes = []
        self.edges = []
        self.current_filepath = ""
        self.current_class = None
        self.current_function = None
        self.seen_function_calls = set()
        self.id_counter = 0

    def _generate_id(self, name: str) -> str:
        """
        Generate a unique ID for a node.
        
        Args:
            name: The name to use as a base for the ID
            
        Returns:
            str: A unique ID string
        """
        self.id_counter += 1
        return f"{name}_{self.id_counter}"

    def _get_full_name(self, name: str) -> str:
        """
        Get the full name of a function or method, including class name for methods.
        
        Args:
            name: The function or method name
            
        Returns:
            str: The full name, including class name for methods
        """
        if self.current_class:
            return f"{self.current_class}.{name}"
        return name

    def parse_file(self, filepath: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse a Python file and extract information about code structures and relationships.
        
        Args:
            filepath: Path to the Python file to parse
            
        Returns:
            dict: A dictionary containing nodes and edges representing the code structure
            
        Raises:
            FileNotFoundError: If the filepath does not exist
            SyntaxError: If the Python file has syntax errors
            PermissionError: If there are permission issues accessing the file
        """
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Reset state
        self.nodes = []
        self.edges = []
        self.current_filepath = filepath
        self.current_class = None
        self.current_function = None
        self.seen_function_calls = set()
        self.id_counter = 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                code = file.read()
            
            # Parse the code to an AST
            tree = ast.parse(code, filename=filepath)
            
            # Visit all nodes in the AST
            self._visit_module(tree)
            
            return {
                'nodes': self.nodes,
                'edges': self.edges
            }
            
        except SyntaxError as e:
            logger.error(f"Syntax error in file {filepath}: {str(e)}")
            raise
        except PermissionError as e:
            logger.error(f"Permission error accessing file {filepath}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error parsing file {filepath}: {str(e)}")
            raise

    def _visit_module(self, node: ast.Module) -> None:
        """
        Visit a module node in the AST and process its contents.
        
        Args:
            node: The AST node representing the module
        """
        # Process all top-level nodes
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self._visit_function(child)
            elif isinstance(child, ast.ClassDef):
                self._visit_class(child)
            elif isinstance(child, ast.Import) or isinstance(child, ast.ImportFrom):
                self._visit_import(child)
            elif isinstance(child, ast.Expr) and isinstance(child.value, ast.Call):
                self._visit_call(child.value)
            # Process other node types as needed
            
            # Also find function calls in assignments, etc.
            self._find_calls_in_node(child)

    def _visit_function(self, node: ast.FunctionDef) -> str:
        """
        Visit a function definition node in the AST and create a corresponding node.
        
        Args:
            node: The AST node representing the function
            
        Returns:
            str: The ID of the created function node
        """
        full_name = self._get_full_name(node.name)
        
        # Create a node for the function
        function_id = full_name
        function_node = {
            'id': function_id,
            'type': 'function',
            'name': node.name,
            'full_name': full_name,
            'filepath': self.current_filepath,
            'line': node.lineno,
            'end_line': node.end_lineno
        }
        
        self.nodes.append(function_node)
        
        # Save previous function context
        prev_function = self.current_function
        
        # Set current function for call processing
        self.current_function = full_name
        
        # Process the function body to find calls
        for child in node.body:
            self._find_calls_in_node(child)
        
        # Restore previous function context
        self.current_function = prev_function
        
        return function_id

    def _visit_class(self, node: ast.ClassDef) -> str:
        """
        Visit a class definition node in the AST and create a corresponding node.
        
        Args:
            node: The AST node representing the class
            
        Returns:
            str: The ID of the created class node
        """
        # Create a node for the class
        class_id = node.name
        class_node = {
            'id': class_id,
            'type': 'class',
            'name': node.name,
            'filepath': self.current_filepath,
            'line': node.lineno,
            'end_line': node.end_lineno
        }
        
        self.nodes.append(class_node)
        
        # Process base classes as edges
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.edges.append({
                    'source': class_id,
                    'target': base.id,
                    'relation': 'INHERITS'
                })
        
        # Set the current class for method processing
        prev_class = self.current_class
        self.current_class = node.name
        
        # Process class body
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                method_id = self._visit_function(child)
                
                # Add an edge from the class to the method
                self.edges.append({
                    'source': class_id,
                    'target': method_id,
                    'relation': 'HAS_METHOD'
                })
            elif isinstance(child, ast.Assign):
                self._find_calls_in_node(child)
            # Process other node types as needed
        
        # Restore the previous class context
        self.current_class = prev_class
        
        return class_id

    def _visit_import(self, node: ast.Import or ast.ImportFrom) -> None:
        """
        Visit an import node in the AST and create corresponding nodes and edges.
        
        Args:
            node: The AST node representing the import
        """
        if isinstance(node, ast.Import):
            # Regular import statement (import x, import x as y)
            for name in node.names:
                import_id = self._generate_id("import")
                self.nodes.append({
                    'id': import_id,
                    'type': 'import',
                    'name': name.name,
                    'asname': name.asname,
                    'filepath': self.current_filepath,
                    'line': node.lineno
                })
                
                # Add edge to the module level
                self.edges.append({
                    'source': self.current_filepath,
                    'target': import_id,
                    'relation': 'IMPORTS'
                })
        
        elif isinstance(node, ast.ImportFrom):
            # From import statement (from x import y)
            module = node.module or ''
            for name in node.names:
                import_id = self._generate_id("import")
                self.nodes.append({
                    'id': import_id,
                    'type': 'import',
                    'name': f"{module}.{name.name}" if module else name.name,
                    'module': module,
                    'symbol': name.name,
                    'asname': name.asname,
                    'filepath': self.current_filepath,
                    'line': node.lineno
                })
                
                # Add edge to the module level
                self.edges.append({
                    'source': self.current_filepath,
                    'target': import_id,
                    'relation': 'IMPORTS'
                })

    def _visit_call(self, node: ast.Call) -> None:
        """
        Visit a function call node in the AST and create corresponding edges.
        
        Args:
            node: The AST node representing the function call
        """
        func_name = self._get_call_name(node.func)
        if not func_name:
            return
        
        # Create a unique key for this call
        call_key = (func_name, node.lineno)
        
        # Only process each call once
        if call_key in self.seen_function_calls:
            return
        
        self.seen_function_calls.add(call_key)
        
        # Determine the source (caller)
        if self.current_class:
            # When inside a class, use the class as the source regardless of method
            source = self.current_class
        elif self.current_function:
            # Outside of classes, use the function
            source = self.current_function
        else:
            # At module level
            source = self.current_filepath
        
        # Add an edge for the function call
        self.edges.append({
            'source': source,
            'target': func_name,
            'relation': 'CALLS',
            'line': node.lineno
        })

    def _get_call_name(self, node: ast.expr) -> Optional[str]:
        """
        Get the name of a called function from its AST node.
        
        Args:
            node: The AST node representing the function being called
            
        Returns:
            Optional[str]: The name of the function, or None if it can't be determined
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_call_name(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr
        return None

    def _find_calls_in_node(self, node: ast.AST) -> None:
        """
        Recursively find function calls in an AST node.
        
        Args:
            node: The AST node to search for function calls
        """
        if isinstance(node, ast.Call):
            self._visit_call(node)
        
        # Recursively process child nodes
        for child in ast.iter_child_nodes(node):
            self._find_calls_in_node(child) 