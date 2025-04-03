"""
Demonstration of Python code instrumentation using the DependencyGraphManager.

This script shows how to initialize the dependency graph manager with Python 
instrumentation to track function calls dynamically.
"""

import os
import sys
import time
import logging

from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.manager import DependencyGraphManager
from graph_core.dynamic.import_hook import initialize_hook, get_function_calls, clear_call_queue, get_monitored_files

# Configure more detailed logging for debugging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """
    Main function that sets up and demonstrates Python instrumentation.
    """
    # Clear any existing call events
    clear_call_queue()
    
    # Create a storage for the dependency graph
    storage = InMemoryGraphStorage()
    
    # Create a manager instance
    manager = DependencyGraphManager(storage)
    
    # Process existing files in the src directory (if it exists)
    try:
        if os.path.exists('src'):
            logger.info("Processing existing files in src directory...")
            count = manager.process_existing_files('src')
            logger.info(f"Finished processing {count} existing files")
    except Exception as e:
        logger.error(f"Error processing existing files: {e}")
    
    # Start Python instrumentation directly using initialize_hook for debugging
    logger.info("Starting Python instrumentation for debugging...")
    src_path = os.path.abspath('src')
    initialize_hook(src_path)
    
    # Now start the manager's instrumentation
    logger.info("Starting manager's Python instrumentation...")
    manager.start_python_instrumentation(watch_dir='src', poll_interval=0.5)
    
    # Import a module that should be instrumented
    try:
        logger.info("Importing test module...")
        # Add src to path if not already there
        src_path = os.path.abspath('src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
            logger.debug(f"Added {src_path} to sys.path")
        
        # Wait a moment for the import hook to be applied
        time.sleep(0.5)
        
        # Print current monitored files
        monitored_files = get_monitored_files()
        logger.debug(f"Currently monitored files before import: {monitored_files}")
        
        # Try to import the module
        try:
            # This will trigger the import hook if successful
            import nested_example
            logger.info(f"Successfully imported test module: {nested_example.__file__}")
            
            # Call some functions to generate events
            logger.info("Calling functions...")
            nested_example.outer_function("test")
            
            # If the module has a Person class, create an instance and call methods
            if hasattr(nested_example, 'Person'):
                person = nested_example.Person("Test Person", 30)
                person.greet()
                person.celebrate_birthday()
            
            # If the module has a counter function, use it
            if hasattr(nested_example, 'create_counter'):
                counter = nested_example.create_counter()
                counter()  # Increment
                counter()  # Increment
                result = counter()  # Increment and return
                logger.info(f"Counter result: {result}")
                
        except ImportError as e:
            logger.warning(f"Could not import test module: {e}")
    except Exception as e:
        logger.error(f"Error during instrumentation test: {e}")
    
    # Wait for events to be processed
    logger.info("Waiting for events to be processed...")
    time.sleep(2)
    
    # Print current monitored files after import
    monitored_files = get_monitored_files()
    logger.debug(f"Currently monitored files after import: {monitored_files}")
    
    # Check if our file is being monitored
    if src_path in str(monitored_files):
        logger.info("The src directory is being monitored")
    else:
        logger.warning(f"The src directory ({src_path}) is NOT being monitored")
        
    # Check for nested_example.py specifically
    nested_example_path = os.path.join(src_path, 'nested_example.py')
    if nested_example_path in monitored_files:
        logger.info(f"The nested_example.py file is being monitored")
    else:
        logger.warning(f"The nested_example.py file ({nested_example_path}) is NOT being monitored")
    
    # Display graph information
    logger.info("Graph information:")
    logger.info(f"Number of nodes: {len(storage.graph.nodes())}")
    logger.info(f"Number of edges: {len(storage.graph.edges())}")
    
    # Display function call events that were captured
    events = get_function_calls()
    logger.info(f"Function call events ({len(events)}):")
    for i, event in enumerate(events):
        logger.info(f"{i+1}. {event.module_name}.{event.function_name}")
    
    # Stop instrumentation
    logger.info("Stopping Python instrumentation...")
    manager.stop_python_instrumentation()
    
    logger.info("Demonstration complete")

if __name__ == "__main__":
    main() 