"""
Tests for the secret scanner module.
"""

import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from graph_core.security.secret_scanner import (
    SecretFinding,
    scan_file_for_secrets,
    scan_line_for_secrets,
    redact_secret
)
from graph_core.security.graph_integration import (
    add_secret_findings_to_node,
    scan_nodes_for_secrets,
    scan_parse_result_for_secrets
)


class TestSecretScanner(unittest.TestCase):
    """Test cases for the secret scanner."""
    
    def setUp(self):
        """Set up the test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, "test_file.py")
    
    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()
    
    def create_test_file(self, content):
        """Create a temporary test file with the given content."""
        with open(self.test_file_path, 'w') as f:
            f.write(content)
        return self.test_file_path
    
    def test_redact_secret(self):
        """Test the redact_secret function."""
        # Test with a short secret
        text = "password='short'"
        redacted = redact_secret(text, 10, 5)
        self.assertEqual(redacted, "password='s***t'")
        
        # Test with a longer secret
        text = "api_key='longersecretkey'"
        redacted = redact_secret(text, 9, 17)
        self.assertEqual(redacted, "api_key='lo*************ey'")
    
    def test_scan_line_for_secrets_aws_key(self):
        """Test scanning a line with an AWS key."""
        line = "aws_access_key_id = 'AKIAIOSFODNN7EXAMPLE'"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].secret_type, "aws_access_key")
        self.assertEqual(findings[0].line_number, 1)
        # Ensure the secret is redacted in the snippet
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", findings[0].snippet)
        self.assertIn("**", findings[0].snippet)
    
    def test_scan_line_for_secrets_generic_api_key(self):
        """Test scanning a line with a generic API key."""
        line = "api_key = 'abcd1234efgh5678ijkl'"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        self.assertEqual(len(findings), 1)
        self.assertIn("api_key", findings[0].secret_type)
        self.assertEqual(findings[0].line_number, 1)
        # Ensure the secret is redacted in the snippet
        self.assertNotIn("abcd1234efgh5678ijkl", findings[0].snippet)
    
    def test_scan_line_for_secrets_password(self):
        """Test scanning a line with a password."""
        line = "password = 'super_secure_password'"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        self.assertEqual(len(findings), 1)
        self.assertIn("password", findings[0].secret_type)
        self.assertEqual(findings[0].line_number, 1)
        # Ensure the secret is redacted in the snippet
        self.assertNotIn("super_secure_password", findings[0].snippet)
    
    def test_scan_line_for_secrets_private_key(self):
        """Test scanning a line with a private key."""
        line = "key = '''-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...'''"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].secret_type, "private_key")
        self.assertEqual(findings[0].line_number, 1)
    
    def test_scan_line_for_secrets_connection_string(self):
        """Test scanning a line with a connection string."""
        line = "conn_str = 'postgresql://user:password@localhost:5432/mydatabase'"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].secret_type, "connection_string")
        self.assertEqual(findings[0].line_number, 1)
        # Ensure the secret is redacted in the snippet
        self.assertNotIn("user:password", findings[0].snippet)
    
    def test_scan_line_for_secrets_jwt(self):
        """Test scanning a line with a JWT token."""
        line = "token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].secret_type, "jwt_token")
        self.assertEqual(findings[0].line_number, 1)
        # Ensure the secret is redacted in the snippet
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", findings[0].snippet)
    
    def test_scan_line_for_secrets_test_placeholder(self):
        """Test scanning a line with a test/placeholder password."""
        line = "password = 'test_password'"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        # Should not detect test passwords
        self.assertEqual(len(findings), 0)
        
        line = "password = 'placeholder'"
        findings = scan_line_for_secrets(line, 1, "test.py")
        
        # Should not detect placeholder passwords
        self.assertEqual(len(findings), 0)
    
    def test_scan_file_for_secrets(self):
        """Test scanning a file for secrets."""
        content = """
# This is a test file with secrets
api_key = 'abcd1234efgh5678ijkl'
password = 'test_password'  # This should not be detected
conn_str = 'postgresql://user:password@localhost:5432/mydatabase'

def authenticate():
    secret_token = 'a_very_secret_token_here'
    return secret_token
"""
        file_path = self.create_test_file(content)
        findings = scan_file_for_secrets(file_path)
        
        # Should detect 2 secrets (api_key and connection string)
        # The test_password should not be detected
        self.assertEqual(len(findings), 2)
        
        # Create another file with no secrets
        content = """
# This file has no secrets
password = 'test'
placeholder_key = 'YOUR_API_KEY_HERE'
"""
        file_path = self.create_test_file(content)
        findings = scan_file_for_secrets(file_path)
        
        # Should not detect any secrets
        self.assertEqual(len(findings), 0)
    
    def test_scan_file_for_nonexistent_file(self):
        """Test scanning a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            scan_file_for_secrets("nonexistent_file.py")
    
    def test_add_secret_findings_to_node(self):
        """Test adding secret findings to a node."""
        node = {
            'id': 'function:test_func',
            'type': 'function',
            'name': 'test_func'
        }
        
        findings = [
            SecretFinding(
                secret_type="api_key",
                line_number=10,
                snippet="api_key = 'ab***12'",
                file_path="test.py",
                confidence="high"
            )
        ]
        
        updated_node = add_secret_findings_to_node(node, findings)
        
        # Check that the node was updated correctly
        self.assertTrue(updated_node['hasSecret'])
        self.assertEqual(len(updated_node['secretWarnings']), 1)
        self.assertEqual(updated_node['secretWarnings'][0]['secretType'], "api_key")
        self.assertEqual(updated_node['secretWarnings'][0]['lineNumber'], 10)
        self.assertEqual(updated_node['secretWarnings'][0]['snippet'], "api_key = 'ab***12'")
        
        # Test with no findings
        updated_node = add_secret_findings_to_node(node, [])
        
        # Node should not be modified
        self.assertNotIn('hasSecret', updated_node)
        self.assertNotIn('secretWarnings', updated_node)
    
    def test_scan_nodes_for_secrets(self):
        """Test scanning nodes for secrets."""
        with patch('graph_core.security.graph_integration.scan_file_for_secrets') as mock_scan:
            # Mock the scan_file_for_secrets function to return a secret finding
            mock_scan.return_value = [
                SecretFinding(
                    secret_type="api_key",
                    line_number=10,
                    snippet="api_key = 'ab***12'",
                    file_path="test.py",
                    confidence="high"
                )
            ]
            
            nodes = [
                {
                    'id': 'function:test_func',
                    'type': 'function',
                    'name': 'test_func',
                    'filepath': 'test.py',
                    'start_point': {'row': 5},
                    'end_point': {'row': 15}
                },
                {
                    'id': 'class:TestClass',
                    'type': 'class',
                    'name': 'TestClass',
                    'filepath': 'test.py',
                    'start_point': {'row': 20},
                    'end_point': {'row': 30}
                }
            ]
            
            updated_nodes = scan_nodes_for_secrets(nodes)
            
            # The first node should have a secret finding (line 10 is within its range)
            self.assertTrue(updated_nodes[0]['hasSecret'])
            self.assertEqual(len(updated_nodes[0]['secretWarnings']), 1)
            
            # The second node should not have a secret finding (line 10 is outside its range)
            self.assertNotIn('hasSecret', updated_nodes[1])
    
    def test_scan_parse_result_for_secrets(self):
        """Test scanning a parse result for secrets."""
        content = """
# This is a test file with secrets
api_key = 'abcd1234efgh5678ijkl'

def authenticate():
    secret_token = 'a_very_secret_token_here'
    return secret_token
"""
        file_path = self.create_test_file(content)

        # Create a mock parse result with correct line numbers matching the content
        parse_result = {
            'nodes': [
                {
                    'id': 'function:authenticate',
                    'type': 'function',
                    'name': 'authenticate',
                    'start_point': {'row': 5},  # Line numbers in content start at 1
                    'end_point': {'row': 7}
                },
                {
                    'id': 'variable:api_key',
                    'type': 'variable',
                    'name': 'api_key',
                    'start_point': {'row': 3},  # Changed from 2 to 3 to match content
                    'end_point': {'row': 3}
                }
            ],
            'edges': []
        }

        # Test with a patch to ensure predictable findings
        with patch('graph_core.security.secret_scanner.scan_file_for_secrets') as mock_scan:
            # Create mock findings for each line with correct line numbers
            mock_scan.return_value = [
                SecretFinding(
                    secret_type="api_key", 
                    line_number=3,  # Line numbers should match parse_result
                    snippet="api_key = 'ab***kl'",
                    file_path=file_path
                ),
                SecretFinding(
                    secret_type="token", 
                    line_number=6,  # Line numbers should match parse_result
                    snippet="secret_token = 'a_***re'",
                    file_path=file_path
                )
            ]
            
            updated_result = scan_parse_result_for_secrets(parse_result, file_path)
            
            # Both nodes should have secret findings
            self.assertTrue('hasSecret' in updated_result['nodes'][0])
            self.assertTrue(updated_result['nodes'][0]['hasSecret'])
            self.assertEqual(len(updated_result['nodes'][0]['secretWarnings']), 1)
            
            self.assertTrue('hasSecret' in updated_result['nodes'][1])
            self.assertTrue(updated_result['nodes'][1]['hasSecret'])
            self.assertEqual(len(updated_result['nodes'][1]['secretWarnings']), 1)


class TestRealLifeExamples(unittest.TestCase):
    """Test cases with real-life examples of secrets."""
    
    def setUp(self):
        """Set up the test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.temp_dir.name, "test_file.py")
    
    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()
    
    def create_test_file(self, content):
        """Create a temporary test file with the given content."""
        with open(self.test_file_path, 'w') as f:
            f.write(content)
        return self.test_file_path
    
    def test_aws_credentials(self):
        """Test detection of AWS credentials."""
        content = """
# AWS configuration
aws_access_key_id = 'AKIAIOSFODNN7EXAMPLE'
aws_secret_access_key = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
"""
        file_path = self.create_test_file(content)
        findings = scan_file_for_secrets(file_path)
        
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].secret_type, "aws_access_key")
        self.assertEqual(findings[1].secret_type, "aws_access_key")
    
    def test_database_configuration(self):
        """Test detection of database connection strings."""
        content = """
# Database configuration
POSTGRES_URL = 'postgresql://user:password123@localhost:5432/mydatabase'
MONGODB_URI = 'mongodb://dbuser:dbpass@mongodb0.example.com:27017/admin'
REDIS_URL = 'redis://default:complex-password-here@redis-12345.c1.us-east-1-3.ec2.cloud.redislabs.com:12345'
"""
        file_path = self.create_test_file(content)
        findings = scan_file_for_secrets(file_path)
        
        self.assertEqual(len(findings), 3)
        for finding in findings:
            self.assertEqual(finding.secret_type, "connection_string")
    
    def test_api_keys_and_tokens(self):
        """Test detection of API keys and tokens."""
        content = """
# API key examples
API_KEY = 'abcdef1234567890abcdef'
GITHUB_TOKEN = 'ghp_1234567890abcdefghijklmnopqrstuvwxyz'
AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
"""
        file_path = self.create_test_file(content)
        findings = scan_file_for_secrets(file_path)
        
        # Should detect at least one of the API keys
        self.assertGreater(len(findings), 0)
        
        # Check that at least one finding is correctly categorized
        api_key_found = False
        token_found = False
        
        for finding in findings:
            if 'api_key' in finding.secret_type:
                api_key_found = True
            if 'token' in finding.secret_type or 'jwt' in finding.secret_type:
                token_found = True
        
        # Verify that at least one type of finding was detected
        self.assertTrue(api_key_found or token_found, 
                        "Neither API key nor token was detected")
    
    def test_no_false_positives(self):
        """Test that common patterns don't trigger false positives."""
        content = r"""
# These should not be detected as secrets
password = 'test_password'
password = 'example'
password = 'dummy-password'
password = 'placeholder'
api_key = 'YOUR_API_KEY_HERE'
api_key = 'XXXX_PLACE_YOUR_KEY_HERE_XXXX'

# Regular expressions
regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
pattern = r'[a-zA-Z0-9]+'
"""
        file_path = self.create_test_file(content)
        findings = scan_file_for_secrets(file_path)
        
        # Should not detect any secrets (all are test/placeholder values)
        self.assertEqual(len(findings), 0, f"Found false positives: {findings}")


if __name__ == '__main__':
    unittest.main() 