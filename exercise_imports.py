#!/usr/bin/env python3
"""
Exercise Imports

This script imports and exercises the sample modules to ensure
that the dependency graph captures the relationships between them.
"""

import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Ensure our configuration takes precedence
)
logger = logging.getLogger(__name__)

def main():
    """
    Main function that exercises the imports and relationships.
    """
    print("=" * 50)
    print("STARTING IMPORT EXERCISE")
    print("=" * 50)
    logger.info("Starting import exercise...")
    
    # First, make sure we have the modules in sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(current_dir, 'src')
    sys.path.append(src_dir)
    
    # Import and use sample.py
    logger.info("Importing sample.py...")
    import sample
    result = sample.use_imported_functions()
    print(f"Result from sample: {result}")
    
    # Import and use sample_module.py
    logger.info("Importing sample_module.py...")
    import sample_module
    person = sample_module.Person("David")
    greeting = person.greet()
    print(f"Greeting: {greeting}")
    birthday = person.calculate_birthday(14)
    print(f"Birthday: {birthday}")
    
    # Import and use nested_example.py
    logger.info("Importing nested_example.py...")
    import nested_example
    result = nested_example.outer_function("Testing imports")
    print(f"Result from nested_example: {result}")
    
    person2 = nested_example.Person("Eve", 30)
    greeting = person2.greet()
    print(f"Greeting from nested_example: {greeting}")
    
    # Create and use a counter
    counter = nested_example.create_counter()
    for _ in range(3):
        count = counter()
        print(f"Counter value: {count}")
    
    # Exercise the math operations
    math_results = sample_module.math_operations(20, 10)
    print(f"Math results: {math_results}")
    
    logger.info("Import exercise completed successfully")
    print("=" * 50)
    print("IMPORT EXERCISE COMPLETED")
    print("=" * 50)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 