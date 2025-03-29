#!/usr/bin/env python3
"""
API Endpoint Checker

Checks the API endpoints to see what data they're returning.
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def print_json(data):
    """Print JSON data in a readable format."""
    print(json.dumps(data, indent=2))

def check_endpoints():
    """Check the API endpoints and print the results."""
    print("Checking API endpoints...")
    
    try:
        # Check nodes endpoint
        print("\n=== NODES ===")
        nodes_response = requests.get(f"{BASE_URL}/graph/nodes")
        nodes = nodes_response.json()
        print(f"Found {len(nodes)} nodes")
        print_json(nodes)
        
        # Check edges endpoint
        print("\n=== EDGES ===")
        edges_response = requests.get(f"{BASE_URL}/graph/edges")
        edges = edges_response.json()
        print(f"Found {len(edges)} edges")
        print_json(edges)
        
        return 0
    except Exception as e:
        print(f"Error checking API: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_endpoints()) 