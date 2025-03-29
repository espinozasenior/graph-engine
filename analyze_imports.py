#!/usr/bin/env python3
"""
Import Analyzer

This script helps analyze imports between files in the src directory
and makes sure they are detected by the graph engine.
"""

import os
import sys
import time
import logging
import importlib
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def touch_files():
    """Touch all files in the src directory to trigger file events."""
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
    logger.info(f"Touching files in {src_dir} to trigger file events...")
    
    for root, _, files in os.walk(src_dir):
        for file in files:
            filepath = os.path.join(root, file)
            # Skip __pycache__ directory and compiled files
            if '__pycache__' in filepath or file.endswith('.pyc'):
                continue
                
            logger.info(f"Touching file: {filepath}")
            # Read the file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Write the same content back
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Wait a moment to ensure the file event is processed
            time.sleep(0.5)

def execute_imports():
    """Import the modules to trigger dynamic analysis."""
    logger.info("Importing modules to trigger dynamic analysis...")
    
    # Add src to path
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
    sys.path.insert(0, src_dir)
    
    try:
        # Import the modules
        logger.info("Importing sample_module...")
        import sample_module
        logger.info("Importing nested_example...")
        import nested_example
        logger.info("Importing sample...")
        import sample
        
        # Execute some functions to demonstrate relationships
        logger.info("Executing functions...")
        
        # From sample_module
        sample_module.hello()
        person = sample_module.Person("Test")
        person.greet()
        
        # From nested_example
        nested_example.outer_function("test")
        person2 = nested_example.Person("Test", 30)
        person2.greet()
        
        # From sample
        sample.use_imported_functions()
        
        logger.info("Function execution complete.")
    except Exception as e:
        logger.error(f"Error executing imports: {e}")

def main():
    """Main function to run the import analyzer."""
    logger.info("Starting import analyzer...")
    
    # Touch files to trigger file events
    touch_files()
    
    # Wait for file events to be processed
    logger.info("Waiting for file events to be processed...")
    time.sleep(2)
    
    # Execute imports to trigger dynamic analysis
    execute_imports()
    
    # Check API endpoints
    logger.info("Checking API endpoints...")
    subprocess.run([sys.executable, "check_api.py"], check=True)
    
    logger.info("Import analyzer completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 