"""
Security Module

This module provides security-related functionality for the graph engine,
including secret detection and security vulnerability scanning.
"""

from graph_core.security.secret_scanner import (
    SecretFinding,
    scan_file_for_secrets,
    scan_directory_for_secrets
)

from graph_core.security.graph_integration import (
    add_secret_findings_to_node,
    scan_nodes_for_secrets,
    scan_parse_result_for_secrets
)

__all__ = [
    'SecretFinding',
    'scan_file_for_secrets',
    'scan_directory_for_secrets',
    'add_secret_findings_to_node',
    'scan_nodes_for_secrets',
    'scan_parse_result_for_secrets'
] 