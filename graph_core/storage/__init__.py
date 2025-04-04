"""
Storage module for the dependency graph.

This package provides different storage implementations for the dependency graph.
"""
from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.storage.json_storage import JSONGraphStorage

__all__ = ['InMemoryGraphStorage', 'JSONGraphStorage'] 