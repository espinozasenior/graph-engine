"""
Demonstration of the enhanced import hook with nested functions.

This script shows how the import hook tracks nested function calls.
"""

import os
import sys
import time
import logging
from pathlib import Path
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import the dynamic import hook
from graph_core.dynamic.import_hook import (
    initialize_hook, get_function_calls, clear_call_queue, FunctionCallEvent
)

# Initialize the import hook for the src directory
src_dir = os.path.abspath('src')
print(f"Initializing import hook for {src_dir}")
initialize_hook(src_dir)

# Clear any previous call events
clear_call_queue()

# Import the nested example module (this will trigger instrumentation)
print("\nImporting nested_example module...")
sys.path.insert(0, os.path.dirname(src_dir))
import src.nested_example as nested

# Use functions from the nested example module
print("\nCalling functions with nested functions...")

# 1. Call outer function which contains an inner function
result = nested.outer_function(5)
print(f"outer_function result: {result}")

# 2. Create a person and use methods
person = nested.Person("Alice", 16)
greeting = person.greet()  # This calls a nested get_greeting_prefix
print(f"person.greet result: {greeting}")

birthday_msg = person.celebrate_birthday()
print(f"person.celebrate_birthday result: {birthday_msg}")

# 3. Create and use a counter (closure)
counter = nested.create_counter()
for _ in range(3):
    count = counter()
    print(f"counter result: {count}")

# Sleep to allow events to be processed
time.sleep(0.5)

# Get function call events
print("\nFunction Call Events:")
events = get_function_calls()
for i, event in enumerate(events, 1):
    print(f"{i}. {event.module_name}.{event.function_name}")

print("\nDemonstration complete!") 