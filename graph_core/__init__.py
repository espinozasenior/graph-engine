"""
Graph Engine Core Package

This package provides the core functionality for analyzing code files
and building dependency graphs.
"""

from graph_core.manager import DependencyGraphManager
from graph_core.api import create_app
from graph_core.analyzer.treesitter_parser import TreeSitterParser
from graph_core.storage.json_storage import JSONGraphStorage
from graph_core.storage.in_memory import InMemoryGraphStorage

__all__ = [
    'DependencyGraphManager', 
    'create_app', 
    'TreeSitterParser',
    'JSONGraphStorage',
    'InMemoryGraphStorage'
]
