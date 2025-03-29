"""
Demonstration of import hook integration with DependencyGraphManager.

This script shows how the DependencyGraphManager can be used to track function calls
through Python instrumentation, with module filtering and caching.
"""

import os
import time
import logging
import tempfile

from graph_core.storage.in_memory_graph import InMemoryGraphStorage
from graph_core.manager import DependencyGraphManager
from graph_core.dynamic.import_hook import (
    FunctionCallEvent, function_call_queue, clear_call_queue
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Main demonstration function.
    """
    # Clear any existing events
    clear_call_queue()
    logger.info("Cleared existing function call events")
    
    # Create a storage for the dependency graph
    storage = InMemoryGraphStorage()
    
    # Create a manager instance
    manager = DependencyGraphManager(storage)
    
    # Process existing files in the src directory
    if os.path.exists('src'):
        logger.info("Processing existing files in src directory...")
        count = manager.process_existing_files('src')
        logger.info(f"Processed {count} files in src directory")
    
    # Create some function nodes in the graph for demonstration
    logger.info("Creating function nodes for demonstration...")
    function_ids = [
        "function:nested_example.outer_function",
        "function:nested_example.inner_function",
        "function:nested_example.greet",
        "function:nested_example.generate_greeting"
    ]
    
    # Add the nodes to the graph
    for func_id in function_ids:
        # Strip the "function:" prefix to get the name
        name = func_id.split(":", 1)[1]
        
        # Add the node
        storage.graph.add_node(
            func_id, 
            id=func_id,
            type="function",
            name=name,
            files={"src/nested_example.py"}
        )
    
    # Create a cache directory
    cache_dir = tempfile.mkdtemp(prefix="instrumentation_cache_")
    logger.info(f"Using cache directory: {cache_dir}")
    
    # Start Python instrumentation with filtering and caching
    watch_dir = os.path.abspath('src')
    logger.info(f"Starting Python instrumentation for {watch_dir}...")
    
    # Exclude any test modules
    exclude_patterns = ["test_"]
    # Include only nested_example module
    include_patterns = ["nested_example"]
    
    manager.start_python_instrumentation(
        watch_dir=watch_dir,
        poll_interval=0.5,
        exclude_patterns=exclude_patterns,
        include_patterns=include_patterns,
        cache_dir=cache_dir
    )
    
    logger.info(f"Module filtering: exclude={exclude_patterns}, include={include_patterns}")
    
    # Manually add some events to the queue to simulate function calls
    logger.info("Adding manual function call events to the queue...")
    events = [
        FunctionCallEvent(
            function_name="outer_function.outer_function", 
            module_name="nested_example", 
            filename=os.path.join(watch_dir, "nested_example.py")
        ),
        FunctionCallEvent(
            function_name="outer_function.inner_function.inner_function",
            module_name="nested_example",
            filename=os.path.join(watch_dir, "nested_example.py")
        ),
        FunctionCallEvent(
            function_name="greet.greet",
            module_name="nested_example",
            filename=os.path.join(watch_dir, "nested_example.py")
        ),
        FunctionCallEvent(
            function_name="greet.generate_greeting.generate_greeting",
            module_name="nested_example",
            filename=os.path.join(watch_dir, "nested_example.py")
        )
    ]
    
    # Add events to the queue
    for event in events:
        function_call_queue.put(event)
    
    # Wait for events to be processed
    logger.info("Waiting for events to be processed...")
    time.sleep(3)
    
    # Display graph information
    logger.info("Graph information:")
    
    # Get all nodes and print relevant ones
    nodes = list(storage.graph.nodes(data=True))
    logger.info(f"Total nodes: {len(nodes)}")
    
    function_nodes = [n for n in nodes if n[0].startswith("function:")]
    logger.info(f"Function nodes with call counts:")
    
    for node_id, data in function_nodes:
        call_count = data.get('dynamic_call_count', 0)
        if call_count > 0:
            logger.info(f"  Node: {node_id}, call count: {call_count}")
    
    # Get all edges and print dynamic ones
    edges = list(storage.graph.edges(data=True))
    logger.info(f"Total edges: {len(edges)}")
    
    dynamic_edges = [e for e in edges if e[2].get('dynamic', False)]
    logger.info(f"Dynamic edges:")
    
    for source, target, data in dynamic_edges:
        call_count = data.get('dynamic_call_count', 0)
        logger.info(f"  Edge: {source} -> {target}, call count: {call_count}")
    
    # Show that we have a cache
    cache_files = os.listdir(cache_dir)
    logger.info(f"Cache contains {len(cache_files)} files")
    
    # Clear the cache
    logger.info("Clearing instrumentation cache...")
    manager.clear_instrumentation_cache()
    
    # Verify cache is cleared
    cache_files = os.listdir(cache_dir)
    logger.info(f"Cache contains {len(cache_files)} files after clearing")
    
    # Stop instrumentation
    logger.info("Stopping Python instrumentation...")
    manager.stop_python_instrumentation()
    
    # Clean up the cache directory
    os.rmdir(cache_dir)
    
    logger.info("Demonstration complete")

if __name__ == "__main__":
    main() 