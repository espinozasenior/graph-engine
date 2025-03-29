"""
Sample module with nested functions for testing the enhanced import hook.
"""

def outer_function(x):
    """A function with a nested function."""
    
    def inner_function(y):
        """A nested function."""
        return x + y
    
    # Call the inner function
    return inner_function(10)

class Person:
    """A class with methods for testing."""
    
    def __init__(self, name, age):
        """Initialize the person."""
        self.name = name
        self.age = age
        
    def greet(self):
        """Return a greeting."""
        
        def get_greeting_prefix():
            """A nested function in a method."""
            if self.age < 18:
                return "Hi"
            return "Hello"
        
        return f"{get_greeting_prefix()}, {self.name}!"
    
    def celebrate_birthday(self):
        """Increment age and return a message."""
        self.age += 1
        return f"Happy {self.age}th birthday, {self.name}!"

def create_counter():
    """Return a closure that maintains a count."""
    count = 0
    
    def increment():
        """Increment and return the count."""
        nonlocal count
        count += 1
        return count
    
    return increment 