"""
Analyzer package for parsing and analyzing code files.
"""

import os
from typing import Optional

from graph_core.analyzer.treesitter_parser import TreeSitterParser

__all__ = ['TreeSitterParser', 'get_parser_for_file']


def get_parser_for_file(file_path: str) -> Optional[TreeSitterParser]:
    """
    Get the appropriate parser for a given file based on its extension.
    
    Args:
        file_path: Path to the file to be parsed
        
    Returns:
        A parser instance appropriate for the file type, or None if no suitable parser is available
        
    Examples:
        >>> parser = get_parser_for_file('example.py')
        >>> isinstance(parser, TreeSitterParser)
        True
        >>> parser = get_parser_for_file('example.js')
        >>> isinstance(parser, TreeSitterParser)
        True
        >>> get_parser_for_file('example.txt') is None
        True
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # Map file extensions to languages supported by TreeSitterParser
    extensions_to_language = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript', 
        '.tsx': 'typescript'
    }
    
    if ext in extensions_to_language:
        try:
            return TreeSitterParser(extensions_to_language[ext])
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create parser for {file_path}: {str(e)}")
            return None
    
    # Return None for unsupported file types
    return None 