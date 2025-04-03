"""
Demonstration of the performance improvements in the import hook instrumentation system.

This script shows how to use:
1. Module filtering to reduce overhead for large codebases
2. Code transformation caching to avoid redundant AST transformations
"""

import os
import time
import logging
import shutil
import timeit
from pathlib import Path

from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.manager import DependencyGraphManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def measure_import_time(module_name: str) -> float:
    """Measure the time it takes to import a module.
    
    Args:
        module_name: Name of the module to import
    
    Returns:
        Import time in seconds
    """
    setup_code = f"""
import sys
if '{module_name}' in sys.modules:
    del sys.modules['{module_name}']
"""
    
    stmt = f"import {module_name}"
    return timeit.timeit(stmt=stmt, setup=setup_code, number=1)

def create_test_modules():
    """Create test modules with varying complexity."""
    # Create test directory if it doesn't exist
    test_dir = Path("test_modules")
    test_dir.mkdir(exist_ok=True)
    
    # Create an __init__.py file
    init_file = test_dir / "__init__.py"
    init_file.write_text("")
    
    # Create a simple module
    simple_module = test_dir / "simple.py"
    simple_module.write_text("""
def simple_function():
    return "Hello, world!"

class SimpleClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
""")
    
    # Create a complex module with many functions
    complex_module = test_dir / "complex.py"
    
    # Generate a large number of functions
    functions = []
    for i in range(50):
        functions.append(f"""
def function_{i}(param1, param2=None):
    '''Function {i} docstring'''
    result = f"Processing {{param1}}"
    if param2:
        result += f" with {{param2}}"
    
    def nested_func():
        return f"Nested in function_{i}"
    
    return nested_func() + " - " + result
""")
    
    # Generate a few classes
    classes = []
    for i in range(5):
        methods = []
        for j in range(10):
            methods.append(f"""
    def method_{j}(self, param1, param2=None):
        '''Method {j} docstring'''
        result = f"{{self.name}} processing {{param1}}"
        if param2:
            result += f" with {{param2}}"
        
        def nested_method():
            return f"Nested in Class_{i}.method_{j}"
        
        return nested_method() + " - " + result
""")
        
        classes.append(f"""
class Class_{i}:
    '''Class {i} docstring'''
    
    def __init__(self, name="Class_{i}"):
        self.name = name
        self.value = {i * 10}
    
{"".join(methods)}
""")
    
    # Write the complex module
    complex_module.write_text(f"""
'''Complex module with many functions and classes'''

import os
import sys
import time
from typing import List, Dict, Any, Optional

{"".join(functions)}

{"".join(classes)}

if __name__ == "__main__":
    print("Complex module imported")
""")
    
    # Create a module that should be excluded from instrumentation
    excluded_module = test_dir / "excluded.py"
    excluded_module.write_text("""
def excluded_function():
    return "This function should not be instrumented"

class ExcludedClass:
    def __init__(self):
        self.value = "excluded"
    
    def get_value(self):
        return self.value
""")
    
    # Return the directory path
    return test_dir

def main():
    """Main demonstration function."""
    # Create test modules
    logger.info("Creating test modules...")
    test_dir = create_test_modules()
    test_dir_path = str(test_dir)
    
    # Make sure the test directory is in the Python path
    if test_dir_path not in os.sys.path:
        os.sys.path.insert(0, test_dir_path)
    
    # Create a storage and manager
    storage = InMemoryGraphStorage()
    manager = DependencyGraphManager(storage)
    
    # Clear any existing cache
    cache_dir = os.path.join(os.path.expanduser("~"), ".instrumentation_cache")
    if os.path.exists(cache_dir):
        logger.info(f"Clearing existing cache: {cache_dir}")
        shutil.rmtree(cache_dir)
    
    # Test 1: Import without instrumentation
    logger.info("\n=== Test 1: Without Instrumentation ===")
    import_time = measure_import_time("test_modules.complex")
    logger.info(f"Import time without instrumentation: {import_time:.4f} seconds")
    
    # Test 2: Import with instrumentation, no cache
    logger.info("\n=== Test 2: With Instrumentation (No Cache) ===")
    manager.start_python_instrumentation(
        watch_dir=test_dir_path,
        cache_dir=cache_dir
    )
    # Need to force reimport
    if "test_modules.complex" in os.sys.modules:
        del os.sys.modules["test_modules.complex"]
    import_time = measure_import_time("test_modules.complex")
    logger.info(f"Import time with instrumentation (no cache): {import_time:.4f} seconds")
    manager.stop_python_instrumentation()
    
    # Test 3: Import with instrumentation, with cache
    logger.info("\n=== Test 3: With Instrumentation (With Cache) ===")
    manager.start_python_instrumentation(
        watch_dir=test_dir_path,
        cache_dir=cache_dir
    )
    # Force reimport
    if "test_modules.complex" in os.sys.modules:
        del os.sys.modules["test_modules.complex"]
    import_time = measure_import_time("test_modules.complex")
    logger.info(f"Import time with instrumentation (with cache): {import_time:.4f} seconds")
    manager.stop_python_instrumentation()
    
    # Test 4: Import with module filtering
    logger.info("\n=== Test 4: With Module Filtering ===")
    manager.start_python_instrumentation(
        watch_dir=test_dir_path,
        cache_dir=cache_dir,
        exclude_patterns=["excluded"]
    )
    # Force reimport of complex module
    if "test_modules.complex" in os.sys.modules:
        del os.sys.modules["test_modules.complex"]
    complex_import_time = measure_import_time("test_modules.complex")
    logger.info(f"Import time for complex module with filtering: {complex_import_time:.4f} seconds")
    
    # Force reimport of excluded module
    if "test_modules.excluded" in os.sys.modules:
        del os.sys.modules["test_modules.excluded"]
    excluded_import_time = measure_import_time("test_modules.excluded")
    logger.info(f"Import time for excluded module: {excluded_import_time:.4f} seconds")
    manager.stop_python_instrumentation()
    
    # Cleanup
    logger.info("\nCleaning up...")
    # Remove test modules
    shutil.rmtree(test_dir_path, ignore_errors=True)
    # Clear cache
    manager.clear_instrumentation_cache()
    
    logger.info("Performance demonstration complete")

if __name__ == "__main__":
    main() 