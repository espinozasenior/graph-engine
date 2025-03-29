"""
Sample module for testing the dynamic import hook.
"""

def hello():
    """Say hello."""
    print("Hello, World!")
    return greeting()

def greeting():
    """Return a greeting message."""
    return "Hello from greeting function!"

class Person:
    """A simple person class."""
    
    def __init__(self, name):
        """Initialize the person with a name."""
        self.name = name
    
    def greet(self):
        """Return a personalized greeting."""
        return f"Hello, {self.name}!"

async def async_function():
    """An async function."""
    return "Async Hello!"

# Only run this if the module is executed directly
if __name__ == "__main__":
    person = Person("Alice")
    print(person.greet())
    print(hello()) 