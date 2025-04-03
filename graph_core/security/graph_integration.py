"""
Graph Integration Module for Secret Scanner

This module provides functionality to integrate the secret scanner with the dependency graph.
"""

import logging
from typing import Dict, Any, List, Union

from graph_core.security.secret_scanner import SecretFinding, scan_file_for_secrets

# Set up logging
logger = logging.getLogger(__name__)


def add_secret_findings_to_node(node: Dict[str, Any], findings: List[SecretFinding]) -> Dict[str, Any]:
    """
    Add secret findings to a node in the dependency graph.
    
    Args:
        node: The node to update
        findings: List of SecretFinding objects
        
    Returns:
        Updated node with secret warning information
    """
    if not findings:
        return node
        
    # Don't modify the original node
    updated_node = node.copy()
    
    # Add hasSecret flag
    updated_node['hasSecret'] = True
    
    # Add secretWarnings list with redacted snippets
    updated_node['secretWarnings'] = []
    
    for finding in findings:
        warning = {
            'secretType': finding.secret_type,
            'lineNumber': finding.line_number,
            'snippet': finding.snippet,  # This is already redacted
            'confidence': finding.confidence
        }
        updated_node['secretWarnings'].append(warning)
    
    logger.warning(f"Added {len(findings)} secret warnings to node: {node.get('id', 'unknown')}")
    return updated_node


def scan_nodes_for_secrets(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Scan nodes in the dependency graph for potential secrets.
    
    Args:
        nodes: List of nodes to scan
        
    Returns:
        Updated list of nodes with secret warnings added where applicable
    """
    updated_nodes = []
    
    for node in nodes:
        # Skip nodes without a filepath
        if 'filepath' not in node:
            updated_nodes.append(node)
            continue
            
        # Skip non-file nodes
        if node.get('type') not in ['file', 'module', 'class', 'function']:
            updated_nodes.append(node)
            continue
            
        # Scan the file for secrets
        try:
            findings = scan_file_for_secrets(node['filepath'])
            
            # Filter findings to only include those relevant to this node
            # For function/class nodes, only include findings in their line range
            if node.get('type') in ['function', 'class'] and 'start_point' in node and 'end_point' in node:
                start_line = node.get('start_point', {}).get('row', 0)
                end_line = node.get('end_point', {}).get('row', float('inf'))
                
                node_findings = [
                    finding for finding in findings
                    if start_line <= finding.line_number <= end_line
                ]
            else:
                # For file/module nodes, include all findings
                node_findings = findings
                
            # Add findings to the node
            if node_findings:
                updated_node = add_secret_findings_to_node(node, node_findings)
                updated_nodes.append(updated_node)
            else:
                updated_nodes.append(node)
                
        except Exception as e:
            logger.error(f"Error scanning node {node.get('id', 'unknown')}: {str(e)}")
            updated_nodes.append(node)
    
    return updated_nodes


def scan_parse_result_for_secrets(parse_result: Dict[str, List], filepath: str) -> Dict[str, List]:
    """
    Scan a parse result for potential secrets and update nodes accordingly.
    
    Args:
        parse_result: Parse result containing nodes and edges
        filepath: Path to the file that was parsed
        
    Returns:
        Updated parse result with secret warnings added to nodes
    """
    if 'nodes' not in parse_result:
        return parse_result
        
    # Scan the file for secrets
    try:
        findings = scan_file_for_secrets(filepath)
        
        if not findings:
            return parse_result
            
        # Create a mapping of line numbers to findings
        line_to_findings: Dict[int, List[SecretFinding]] = {}
        for finding in findings:
            if finding.line_number not in line_to_findings:
                line_to_findings[finding.line_number] = []
            line_to_findings[finding.line_number].append(finding)
        
        # Create a deep copy of the parse result to avoid modifying the original
        updated_result = {
            'nodes': [],
            'edges': parse_result.get('edges', []).copy()
        }
        
        # Update nodes with secret warnings
        for node in parse_result['nodes']:
            node_copy = node.copy()  # Make a copy of the node to avoid modifying the original
            
            # Skip nodes without position information
            if 'start_point' not in node_copy or 'end_point' not in node_copy:
                updated_result['nodes'].append(node_copy)
                continue
                
            start_line = node_copy.get('start_point', {}).get('row', 0)
            end_line = node_copy.get('end_point', {}).get('row', float('inf'))
            
            # Collect findings for this node
            node_findings = []
            for line_num, line_findings in line_to_findings.items():
                if start_line <= line_num <= end_line:
                    node_findings.extend(line_findings)
            
            # Add findings to the node
            if node_findings:
                updated_node = add_secret_findings_to_node(node_copy, node_findings)
                updated_result['nodes'].append(updated_node)
            else:
                updated_result['nodes'].append(node_copy)
        
        return updated_result
        
    except Exception as e:
        logger.error(f"Error scanning parse result for {filepath}: {str(e)}")
        return parse_result 