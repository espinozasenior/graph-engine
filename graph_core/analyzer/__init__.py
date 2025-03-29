"""
Analyzer package for parsing and analyzing code files.
"""

import os
from typing import Optional

from graph_core.analyzer.python_parser import PythonParser

__all__ = ['PythonParser', 'get_parser_for_file']


def get_parser_for_file(file_path: str) -> Optional[PythonParser]:
    """
    Get the appropriate parser for a given file based on its extension.
    
    Args:
        file_path: Path to the file to be parsed
        
    Returns:
        A parser instance appropriate for the file type, or None if no suitable parser is available
        
    Examples:
        >>> parser = get_parser_for_file('example.py')
        >>> isinstance(parser, PythonParser)
        True
        >>> get_parser_for_file('example.txt') is None
        True
    """
    _, ext = os.path.splitext(file_path)
    
    if ext.lower() == '.py':
        return PythonParser()
    
    # For now, return None for other file types
    return None 