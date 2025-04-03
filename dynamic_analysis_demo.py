"""
Demonstration of the dynamic import hook.

This script shows how to use the import hook to track function calls
and update the graph in real-time.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import the dynamic import hook
from graph_core.dynamic.import_hook import (
    initialize_hook, get_function_calls, clear_call_queue, FunctionCallEvent
)
from graph_core.storage.in_memory import InMemoryGraphStorage
from graph_core.manager import DependencyGraphManager

# Initialize the import hook for the src directory
src_dir = os.path.abspath('src')
print(f"Initializing import hook for {src_dir}")
initialize_hook(src_dir)

# Create the graph manager with in-memory storage
storage = InMemoryGraphStorage()
manager = DependencyGraphManager(storage)

# Process existing files in the src directory
print("Processing existing files...")
file_count = manager.process_existing_files(src_dir)
print(f"Processed {file_count} files")

# Register a dynamic handler to update call counts
def update_call_counts(event_type, source_id, target_id):
    if event_type == 'function_called':
        # Convert event.module_name.function_name to function:module.function format
        func_id = f"function:{source_id.split('.')[-2]}.{source_id.split('.')[-1]}"
        manager.update_function_call_count(func_id)
        print(f"Updated call count for {func_id}")

# Modify the function to process FunctionCallEvent objects
def process_function_call_events():
    """Process function call events and update the graph."""
    events = get_function_calls()
    for event in events:
        # Create a proper function ID from the event
        module_parts = event.module_name.split('.')
        func_id = f"function:{module_parts[-1]}.{event.function_name}"
        
        # Update call count in the graph
        node = storage.get_node(func_id)
        if node:
            # Update existing node
            if 'dynamic_call_count' in node:
                node['dynamic_call_count'] += 1
            else:
                node['dynamic_call_count'] = 1
            
            # Update the node in the graph
            storage.graph.add_node(func_id, **node)
            print(f"Updated call count for {func_id}")
        else:
            # Add a new node if it doesn't exist yet
            node = {
                'id': func_id,
                'type': 'function',
                'name': event.function_name,
                'module': event.module_name,
                'filepath': event.filename,
                'dynamic_call_count': 1,
                'files': {event.filename}
            }
            # Add the node directly to the graph
            storage.graph.add_node(func_id, **{k: v for k, v in node.items() if k != 'id'})
            print(f"Added new node for {func_id}")

# Register the handler
manager.register_dynamic_handler(update_call_counts)

# Clear any previous call events
clear_call_queue()

# Import the sample module (this will trigger the import hook)
print("\nImporting sample_module...")
sys.path.insert(0, os.path.dirname(src_dir))
import src.sample_module as sample

# Use functions from the sample module
print("\nCalling functions from sample_module...")
sample.hello()
result = sample.greeting()
person = sample.Person("Bob")
greeting = person.greet()

# Sleep to allow events to be processed
time.sleep(0.5)

# Process function call events
print("\nProcessing function call events...")
process_function_call_events()

# Get function call events
print("\nFunction Call Events:")
events = get_function_calls()
for event in events:
    print(f"  {event}")

# Print all nodes in the graph
print("\nGraph Nodes:")
nodes = storage.get_all_nodes()
for node in nodes:
    node_type = node.get('type', 'unknown')
    name = node.get('name', 'unnamed')
    dynamic_calls = node.get('dynamic_call_count', 0)
    
    print(f"  {node['id']} ({node_type}): {name} - {dynamic_calls} calls")

print("\nDemonstration complete!") 