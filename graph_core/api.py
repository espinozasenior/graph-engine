"""
API Module for Graph Engine

This module provides a FastAPI application for exposing the
dependency graph data through HTTP endpoints.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends

from graph_core.manager import DependencyGraphManager

# Set up logging
logger = logging.getLogger(__name__)


class GraphAPI:
    """
    API wrapper for exposing dependency graph data.
    """
    
    def __init__(self, manager: DependencyGraphManager):
        """
        Initialize the API with a dependency graph manager.
        
        Args:
            manager: An instance of DependencyGraphManager
        """
        self.manager = manager
        self.app = FastAPI(title="Graph Engine API")
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up the API routes."""
        
        @self.app.get("/graph/nodes", response_model=List[Dict[str, Any]])
        async def get_nodes():
            """
            Get all nodes in the dependency graph.
            
            Returns:
                List of node dictionaries
            """
            logger.debug("GET request for /graph/nodes")
            return self.manager.storage.get_all_nodes()
        
        @self.app.get("/graph/edges", response_model=List[Dict[str, Any]])
        async def get_edges():
            """
            Get all edges in the dependency graph.
            
            Returns:
                List of edge dictionaries
            """
            logger.debug("GET request for /graph/edges")
            return self.manager.storage.get_all_edges()


def create_app(manager: DependencyGraphManager) -> FastAPI:
    """
    Create a FastAPI application with the given dependency graph manager.
    
    Args:
        manager: An instance of DependencyGraphManager
        
    Returns:
        A FastAPI application
    """
    api = GraphAPI(manager)
    return api.app 