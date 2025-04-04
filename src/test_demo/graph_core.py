"""
Graph Node Demo Module

This module contains classes and functions for testing the graph engine.
"""

class GraphNode:
    """A representation of a node in the graph."""
    
    def __init__(self, node_id, node_type, metadata=None):
        self.id = node_id
        self.node_type = node_type
        self.metadata = metadata or {}
        self.connections = []
    
    def add_connection(self, target_node, edge_type="references"):
        """Add a connection to another node."""
        self.connections.append({
            "target": target_node.id,
            "edge_type": edge_type
        })
        return self
    
    def to_dict(self):
        """Convert node to dictionary representation."""
        return {
            "id": self.id,
            "node_type": self.node_type,
            "metadata": self.metadata,
            "connections": self.connections
        }


def create_example_graph():
    """Create an example graph with several nodes."""
    # Create nodes
    class_node = GraphNode("ClassNode1", "class", {"name": "ExampleClass"})
    method_node1 = GraphNode("MethodNode1", "method", {"name": "method1"})
    method_node2 = GraphNode("MethodNode2", "method", {"name": "method2"})
    variable_node = GraphNode("VarNode1", "variable", {"name": "example_var"})
    
    # Create connections
    class_node.add_connection(method_node1, "contains")
    class_node.add_connection(method_node2, "contains")
    method_node1.add_connection(variable_node, "uses")
    method_node2.add_connection(method_node1, "calls")
    
    return [class_node, method_node1, method_node2, variable_node]


if __name__ == "__main__":
    # Create and display an example graph
    graph = create_example_graph()
    for node in graph:
        print(f"Node: {node.id} ({node.node_type})")
        for conn in node.connections:
            print(f"  -> {conn['target']} ({conn['edge_type']})") 