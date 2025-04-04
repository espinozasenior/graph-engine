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


@pytest.fixture
def advanced_module_path():
    """Create a temporary directory with a Python module containing advanced patterns."""
    with tempfile.TemporaryDirectory() as tempdir:
        # Create a sample Python module with advanced patterns
        module_path = Path(tempdir) / "advanced_module.py"
        
        with open(module_path, "w") as f:
            f.write('''
# Module with nested functions, closures, and complex class patterns

def outer_function(x):
    """A function containing a nested function."""
    
    def inner_function(y):
        """A nested function."""
        return x + y
    
    # Call the inner function
    return inner_function(10)

# Function returning a closure
def create_multiplier(factor):
    """Returns a closure that multiplies by the given factor."""
    
    def multiplier(x):
        return x * factor
    
    return multiplier

# Class with inheritance and multiple methods
class Vehicle:
    """Base vehicle class."""
    
    def __init__(self, make, model):
        self.make = make
        self.model = model
        
    def description(self):
        return f"{self.make} {self.model}"

class Car(Vehicle):
    """Car class extending Vehicle."""
    
    def __init__(self, make, model, year):
        super().__init__(make, model)
        self.year = year
        
    def full_description(self):
        return f"{self.year} {self.make} {self.model}"
    
    def honk(self):
        return "Beep!"

# Function with lambda expressions
def apply_operation(data, operation=None):
    """Apply an operation to data."""
    if operation is None:
        operation = lambda x: x * 2
    
    return [operation(item) for item in data]

# Async function with nested function
async def fetch_data(url):
    """Simulate fetching data with a nested function."""
    
    def process_data(data):
        return data.upper()
    
    # Simulate fetching data
    data = f"Data from {url}"
    return process_data(data)
''')
        
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
        
        # With our new implementation, function names include their nesting level
        # So we check if the function names end with the expected names
        assert any(name.endswith('.hello_world') or name == 'hello_world' for name in function_names)
        assert any(name.endswith('.calculate_sum') or name == 'calculate_sum' for name in function_names)
        assert any(name.endswith('.__init__') or name == '__init__' for name in function_names)
        assert any(name.endswith('.greet') or name == 'greet' for name in function_names)
        
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


def test_instrumentation_transformer_with_nested_functions():
    """Test that the AST transformer correctly handles nested functions."""
    # Sample Python code with nested functions
    sample_code = """
def outer_function(x):
    def inner_function(y):
        return x + y
    return inner_function(10)

class TestClass:
    def __init__(self, value):
        self.value = value
        
    def get_value(self):
        return self.value
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
    
    # Check that all functions are instrumented
    assert "function_call_queue.put" in transformed_code
    assert "FunctionCallEvent" in transformed_code
    
    # Check for proper function name handling
    assert "outer_function" in transformed_code
    assert "inner_function" in transformed_code
    assert "__init__" in transformed_code
    assert "get_value" in transformed_code
    
    # Verify proper nesting in instrumentation calls
    # The exact format may vary between Python versions, so check both possible formats
    assert ("'outer_function.outer_function'" in transformed_code or 
            '"outer_function.outer_function"' in transformed_code)
    assert any(nested_name in transformed_code for nested_name in [
        "'outer_function.inner_function'", 
        '"outer_function.inner_function"',
        "'outer_function.inner_function.inner_function'",
        '"outer_function.inner_function.inner_function"'
    ])


def test_dynamic_instrumentation_with_advanced_patterns(advanced_module_path, watch_dir):
    """Test dynamic instrumentation with advanced code patterns."""
    # Create a symbolic link to the sample module in the watch directory
    watch_path = os.path.join(watch_dir, "advanced_module.py")
    with open(advanced_module_path, "r") as src, open(watch_path, "w") as dst:
        dst.write(src.read())
    
    # Add the watch directory to sys.path
    sys.path.insert(0, watch_dir)
    
    # Clear any previous imports
    if "advanced_module" in sys.modules:
        del sys.modules["advanced_module"]
    
    try:
        # Clear the call queue
        import_hook.clear_call_queue()
        
        # Initialize the hook
        import_hook.initialize_hook(watch_dir)
        
        # Import the module (this should trigger instrumentation)
        advanced_module = importlib.import_module("advanced_module")
        
        # Call functions to trigger events
        advanced_module.outer_function(5)
        double = advanced_module.create_multiplier(2)
        double(10)
        car = advanced_module.Car("Toyota", "Corolla", 2022)
        car.description()
        car.full_description()
        car.honk()
        advanced_module.apply_operation([1, 2, 3])
        
        # Check that the functions were called
        events = import_hook.get_function_calls()
        
        # Collect function names that were called
        function_names = [event.function_name for event in events]
        
        # Check for various expected functions - with the updated naming pattern
        assert any(name.endswith('.outer_function') or name == 'outer_function' for name in function_names)
        assert any('inner_function' in name for name in function_names)
        assert any(name.endswith('.create_multiplier') or name == 'create_multiplier' for name in function_names)
        assert any('multiplier' in name for name in function_names)
        assert any(name.endswith('.__init__') or name == '__init__' for name in function_names)
        assert any(name.endswith('.description') or name == 'description' for name in function_names)
        assert any(name.endswith('.full_description') or name == 'full_description' for name in function_names)
        assert any(name.endswith('.honk') or name == 'honk' for name in function_names)
        assert any(name.endswith('.apply_operation') or name == 'apply_operation' for name in function_names)
        
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
        if "advanced_module" in sys.modules:
            del sys.modules["advanced_module"]


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 