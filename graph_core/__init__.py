"""
Graph Engine Core Package

This package provides the core functionality for analyzing code files
and building dependency graphs.
"""

from graph_core.manager import DependencyGraphManager
from graph_core.api import create_app
from graph_core.analyzer.treesitter_parser import TreeSitterParser

__all__ = ['DependencyGraphManager', 'create_app', 'TreeSitterParser']
