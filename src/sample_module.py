"""
Sample module for testing the dynamic import hook.
"""

# Remove the circular import
# Instead, we'll use our own implementations
from datetime import datetime, timedelta

def hello():
    """Say hello."""
    print("Hello, World!")
    return greeting()

def greeting():
    """Return a greeting message."""
    return "Hello from greeting function!"

def calculate_future_date(days_from_now):
    """Our own implementation of calculate_future_date."""
    today = datetime.now()
    future_date = today + timedelta(days=days_from_now)
    return future_date

class Calculator:
    """Our own implementation of Calculator."""
    
    def __init__(self):
        """Initialize the calculator."""
        self.result = 0
    
    def add(self, a, b):
        """Add two numbers."""
        self.result = a + b
        return self.result
    
    def subtract(self, a, b):
        """Subtract b from a."""
        self.result = a - b
        return self.result

class Person:
    """A simple person class."""
    
    def __init__(self, name):
        """Initialize the person with a name."""
        self.name = name
        # Use our own implementation
        self.creation_date = calculate_future_date(0)
    
    def greet(self):
        """Return a personalized greeting."""
        return f"Hello, {self.name}!"
    
    def calculate_birthday(self, days_until_birthday):
        """Calculate when the birthday will be."""
        birthday_date = calculate_future_date(days_until_birthday)
        return f"{self.name}'s birthday will be on {birthday_date.strftime('%Y-%m-%d')}"

async def async_function():
    """An async function."""
    return "Async Hello!"

def math_operations(a, b):
    """Perform math operations using our Calculator."""
    calc = Calculator()
    sum_result = calc.add(a, b)
    diff_result = calc.subtract(a, b)
    return {
        'sum': sum_result,
        'difference': diff_result
    }

# Only run this if the module is executed directly
if __name__ == "__main__":
    person = Person("Alice")
    print(person.greet())
    print(hello())
    
    # Use our own functionality
    print(person.calculate_birthday(30))
    math_results = math_operations(10, 5)
    print(f"10 + 5 = {math_results['sum']}")
    print(f"10 - 5 = {math_results['difference']}") 