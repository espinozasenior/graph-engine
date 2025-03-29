"""
Tests for the dynamic import hook.
"""

import os
import sys
import tempfile
from pathlib import Path
import importlib
import types
import unittest.mock
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_core.dynamic import import_hook


@pytest.fixture
def sample_module_path():
    """Create a temporary directory with a sample Python module."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a sample Python module
        module_path = Path(tempdir) / "sample_module.py"
        
        with open(module_path, "w") as f:
            f.write("""
def hello_world():
    return "Hello, World!"

def calculate_sum(a, b):
    return a + b

class Person:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"

async def async_function():
    return "Async Hello!"
""")
        
        yield str(module_path)


def test_instrumentation_transformer():
    """Test that the AST transformer correctly adds instrumentation code."""
    # Sample Python code
    sample_code = """
def test_function():
    return "test"

async def async_test():
    return "async test"
"""
    
    # Parse the code
    tree = import_hook.ast.parse(sample_code)
    
    # Apply the transformer
    transformer = import_hook.InstrumentationTransformer("test_module", "test.py")
    transformed_tree = transformer.visit(tree)
    
    # Fix locations
    import_hook.ast.fix_missing_locations(transformed_tree)
    
    # Convert to string
    transformed_code = import_hook.ast.unparse(transformed_tree)
    
    # Check that the function call instrumentation was added
    assert "function_call_queue.put" in transformed_code
    assert "FunctionCallEvent" in transformed_code
    assert "test_function" in transformed_code
    assert "async_test" in transformed_code


def test_should_instrument():
    """Test the logic for determining if a file should be instrumented."""
    # Create instrumenter with watch_dir set to /tmp
    with tempfile.TemporaryDirectory() as tempdir:
        instrumenter = import_hook.PythonInstrumenter(tempdir)
        
        # Files in the watch directory should be instrumented
        py_file_in_dir = os.path.join(tempdir, "test.py")
        assert instrumenter.should_instrument(py_file_in_dir) is True
        
        # Files outside the watch directory should not be instrumented
        py_file_outside = os.path.join(os.path.dirname(tempdir), "outside.py")
        assert instrumenter.should_instrument(py_file_outside) is False
        
        # Non-Python files should not be instrumented
        non_py_file = os.path.join(tempdir, "test.txt")
        assert instrumenter.should_instrument(non_py_file) is False


def test_instrument_code():
    """Test code instrumentation."""
    # Sample Python code
    sample_code = """
def test_function():
    return "test"
"""
    
    with tempfile.TemporaryDirectory() as tempdir:
        instrumenter = import_hook.PythonInstrumenter(tempdir)
        filename = os.path.join(tempdir, "test.py")
        
        # Instrument the code
        result = instrumenter.instrument_code(sample_code, "test_module", filename)
        
        # Check if the code was instrumented
        assert "function_call_queue.put" in result
        assert "FunctionCallEvent" in result
        assert "test_function" in result
        assert "from graph_core.dynamic.import_hook import" in result


def test_function_call_event():
    """Test the FunctionCallEvent class."""
    event = import_hook.FunctionCallEvent("test_func", "test_module", "test.py")
    
    assert event.function_name == "test_func"
    assert event.module_name == "test_module"
    assert event.filename == "test.py"
    assert event.timestamp is not None
    
    # Check string representation
    assert "test_module.test_func called at" in str(event)
    assert "test.py" in str(event)


@pytest.fixture
def watch_dir():
    """Create a temporary directory to watch."""
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir


def test_initialize_hook(watch_dir):
    """Test initializing the import hook."""
    # Mock sys.meta_path to avoid affecting the real import system
    with unittest.mock.patch("sys.meta_path", []):
        finder = import_hook.initialize_hook(watch_dir)
        
        # Check that the finder was installed
        assert finder in sys.meta_path
        assert isinstance(finder, import_hook.InstrumentationFinder)


def test_dynamic_instrumentation(sample_module_path, watch_dir):
    """Test dynamic instrumentation by loading a module through the hook."""
    # Create a symbolic link to the sample module in the watch directory
    watch_path = os.path.join(watch_dir, "linked_module.py")
    with open(sample_module_path, "r") as src, open(watch_path, "w") as dst:
        dst.write(src.read())
    
    # Add the watch directory to sys.path
    sys.path.insert(0, watch_dir)
    
    # Clear any previous imports
    if "linked_module" in sys.modules:
        del sys.modules["linked_module"]
    
    try:
        # Clear the call queue
        import_hook.clear_call_queue()
        
        # Initialize the hook
        import_hook.initialize_hook(watch_dir)
        
        # Import the module (this should trigger instrumentation)
        linked_module = importlib.import_module("linked_module")
        
        # Call functions to trigger events
        linked_module.hello_world()
        linked_module.calculate_sum(1, 2)
        person = linked_module.Person("Test")
        person.greet()
        
        # Check that the functions were called
        events = import_hook.get_function_calls()
        
        # We expect at least 3 events (hello_world, calculate_sum, greet)
        # Note: __init__ may also be included depending on how it's instrumented
        function_names = [event.function_name for event in events]
        
        assert "hello_world" in function_names
        assert "calculate_sum" in function_names
        assert "greet" in function_names
        
        # Check that the file is being monitored
        monitored_files = import_hook.get_monitored_files()
        assert os.path.abspath(watch_path) in [os.path.abspath(path) for path in monitored_files]
        
    finally:
        # Clean up sys.path
        if watch_dir in sys.path:
            sys.path.remove(watch_dir)
        
        # Remove the finder from sys.meta_path
        sys.meta_path = [
            finder for finder in sys.meta_path 
            if not isinstance(finder, import_hook.InstrumentationFinder)
        ]
        
        # Remove the module from sys.modules
        if "linked_module" in sys.modules:
            del sys.modules["linked_module"]


def test_get_function_calls():
    """Test getting function call events from the queue."""
    # Clear the queue
    import_hook.clear_call_queue()
    
    # Add some events
    event1 = import_hook.FunctionCallEvent("func1", "module1", "file1.py")
    event2 = import_hook.FunctionCallEvent("func2", "module2", "file2.py")
    
    import_hook.function_call_queue.put(event1)
    import_hook.function_call_queue.put(event2)
    
    # Get the events
    events = import_hook.get_function_calls()
    
    # Check that we got both events
    assert len(events) == 2
    assert any(event.function_name == "func1" for event in events)
    assert any(event.function_name == "func2" for event in events)


def test_clear_call_queue():
    """Test clearing the function call queue."""
    # Add some events
    event = import_hook.FunctionCallEvent("func", "module", "file.py")
    import_hook.function_call_queue.put(event)
    
    # Clear the queue
    import_hook.clear_call_queue()
    
    # Check that the queue is empty
    assert import_hook.get_function_calls() == []


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 