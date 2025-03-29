#!/usr/bin/env python
"""
Sample Python file for testing the graph builder.
"""
import os
import sys
from datetime import datetime, timedelta

class BaseClass:
    """A base class to demonstrate inheritance."""
    
    def __init__(self, name):
        """Initialize with a name."""
        self.name = name
    
    def get_name(self):
        """Return the name."""
        return self.name


class Person(BaseClass):
    """A class representing a person."""
    
    def __init__(self, name, age):
        """Initialize with name and age."""
        super().__init__(name)
        self.age = age
    
    def greet(self):
        """Return a greeting message."""
        return f"Hello, my name is {self.name} and I am {self.age} years old."
    
    def celebrate_birthday(self):
        """Increment age by 1."""
        self.age += 1
        print(f"Happy Birthday! {self.name} is now {self.age} years old.")


def calculate_future_date(days_from_now):
    """Calculate a date in the future."""
    today = datetime.now()
    future_date = today + timedelta(days=days_from_now)
    return future_date


class Calculator:
    """A simple calculator class."""
    
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


def main():
    """Main function."""
    # Create a person
    person = Person("Alice", 30)
    
    # Greet the person
    greeting = person.greet()
    print(greeting)
    
    # Calculate a future date
    future = calculate_future_date(30)
    print(f"30 days from now will be: {future.strftime('%Y-%m-%d')}")
    
    # Celebrate birthday
    person.celebrate_birthday()
    
    # Use os module
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    
    calc = Calculator()
    print(f"2 + 3 = {calc.add(2, 3)}")
    print(f"5 - 2 = {calc.subtract(5, 2)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 