"""
Direct test of the import hook functionality.

This script directly tests the import hook without using the DependencyGraphManager.
"""

import os
import sys
import time
import logging
import importlib

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test the import hook directly."""
    # First import the import hook module
    from graph_core.dynamic.import_hook import (
        initialize_hook, 
        get_function_calls, 
        clear_call_queue,
        get_monitored_files,
        function_call_queue,
        FunctionCallEvent
    )
    
    # Clear any existing events
    logger.info("Clearing function call queue")
    clear_call_queue()
    
    # Initialize the hook
    src_path = os.path.abspath('src')
    logger.info(f"Initializing import hook for {src_path}")
    initialize_hook(src_path)
    
    # Add src to path if not already there
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        logger.debug(f"Added {src_path} to sys.path")
    
    # Print monitored files before import
    monitored_files = get_monitored_files()
    logger.debug(f"Monitored files before import: {monitored_files}")
    
    # Force reload if the module was already imported
    if 'nested_example' in sys.modules:
        logger.info("Module already imported, forcing reload")
        del sys.modules['nested_example']
    
    # Import the module
    logger.info("Importing nested_example")
    try:
        import nested_example
        logger.info(f"Successfully imported nested_example")
        
        # Test the module by calling functions
        logger.info("Calling functions in nested_example")
        
        # Test direct function call
        result = nested_example.outer_function("direct test")
        logger.info(f"outer_function result: {result}")
        
        # Test class instantiation and method calls
        if hasattr(nested_example, 'Person'):
            logger.info("Creating Person instance")
            person = nested_example.Person("Test User", 25)
            
            logger.info("Calling greet method")
            greeting = person.greet()
            logger.info(f"Greeting: {greeting}")
            
            logger.info("Calling celebrate_birthday method")
            birthday_msg = person.celebrate_birthday()
            logger.info(f"Birthday message: {birthday_msg}")
        
        # Test closure
        if hasattr(nested_example, 'create_counter'):
            logger.info("Testing counter closure")
            counter = nested_example.create_counter()
            for i in range(3):
                count = counter()
                logger.info(f"Counter value: {count}")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    
    # Wait for events to be processed
    logger.info("Waiting for events to be processed")
    time.sleep(1)
    
    # Print monitored files after import
    monitored_files = get_monitored_files()
    logger.debug(f"Monitored files after import: {monitored_files}")
    
    # Manually inject an event to check if queue is working
    logger.info("Injecting test event into queue")
    test_event = FunctionCallEvent(
        function_name="test_function",
        module_name="test_module",
        filename="test_file.py"
    )
    function_call_queue.put(test_event)
    
    # Check for events
    logger.info("Getting function call events")
    events = get_function_calls()
    logger.info(f"Found {len(events)} events:")
    for i, event in enumerate(events):
        logger.info(f"{i+1}. {event.module_name}.{event.function_name} in {event.filename}")
    
    logger.info("Test complete")

if __name__ == "__main__":
    main() 