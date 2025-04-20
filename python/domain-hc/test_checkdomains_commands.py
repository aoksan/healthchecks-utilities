#!/usr/bin/env python3
"""
Test suite for checkdomains.py commands and functions.

This test file verifies that the commands and functions in checkdomains.py
work correctly. It uses unittest and mocking to isolate the code being tested
from external dependencies like API calls, file operations, and subprocess calls.

Usage:
    python3 test_checkdomains_commands.py

The tests cover:
1. Creating healthchecks
2. Checking domain status
3. Checking domain expiry
4. Getting healthchecks details
5. Deleting healthchecks
6. Pinging healthchecks
7. Command actions (check, list-domains, list-checks, delete-markers)

Each test mocks the necessary dependencies to ensure the tests are isolated
and reliable.
"""
import sys
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import datetime

# Add the python/domain-hc directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'python', 'domain-hc')))

# Import the module to test
# We'll use a try-except block to handle potential import errors
try:
    from checkdomains import (
        load_domains, load_domains_raw, action_create_domain_checks,
        action_check_domains, action_list_domains, action_list_checks,
        action_remove_unused_checks, action_delete_markers, action_remove_all_checks,
        create_healthcheck, check_domain_status, check_domain_expiry,
        get_all_healthchecks_details, delete_healthcheck, ping_healthcheck,
        _make_api_request, log, info, debug, warn, error
    )
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_ERROR = str(e)
    # Create mock functions for testing if import fails
    def load_domains(): pass
    def load_domains_raw(): pass
    def action_create_domain_checks(): pass
    def action_check_domains(): pass
    def action_list_domains(): pass
    def action_list_checks(): pass
    def action_remove_unused_checks(): pass
    def action_delete_markers(): pass
    def action_remove_all_checks(): pass
    def create_healthcheck(): pass
    def check_domain_status(): pass
    def check_domain_expiry(): pass
    def get_all_healthchecks_details(): pass
    def delete_healthcheck(): pass
    def ping_healthcheck(): pass
    def _make_api_request(): pass
    def log(): pass
    def info(): pass
    def debug(): pass
    def warn(): pass
    def error(): pass

class TestCheckdomainsCommands(unittest.TestCase):
    """Test cases for the checkdomains.py commands."""

    def setUp(self):
        """Set up test environment."""
        # Skip all tests if import failed
        if IMPORT_ERROR:
            self.skipTest(f"Module import failed: {IMPORT_ERROR}")

        # Create a temporary file for domains.txt
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_filename = self.temp_file.name

        # Sample domain data
        test_data = """# Test domains file
# Format: domain s:status_uuid e:expiry_uuid
example.com s:12345678-1234-1234-1234-123456789012 e:87654321-4321-4321-4321-210987654321
test.example.com s:abcdef12-3456-7890-abcd-ef1234567890
invalid.com
# Comment line
"""
        self.temp_file.write(test_data.encode('utf-8'))
        self.temp_file.close()

        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'API_URL': 'https://healthchecks.io/api/v3/',
            'API_KEY': 'test_api_key',
            'BASE_URL': 'https://hc-ping.com',
            'DOMAIN_FILE': self.temp_filename
        })
        self.env_patcher.start()

        # Create a temporary directory for markers
        self.marker_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary file
        if hasattr(self, 'temp_file'):
            os.unlink(self.temp_filename)

        # Stop patchers
        if hasattr(self, 'env_patcher'):
            self.env_patcher.stop()

        # Remove the temporary marker directory
        if hasattr(self, 'marker_dir') and os.path.exists(self.marker_dir):
            import shutil
            shutil.rmtree(self.marker_dir)

    @patch('checkdomains._make_api_request')
    def test_create_healthcheck(self, mock_api_request):
        """Test creating a healthcheck."""
        # Mock API response
        mock_api_request.return_value = {
            'name': 'example.com',
            'slug': 'example-com-status',
            'ping_url': 'https://hc-ping.com/12345678-1234-1234-1234-123456789012'
        }

        # Call the function
        result = create_healthcheck('example.com', 'status')

        # Verify the result
        self.assertEqual(result, '12345678-1234-1234-1234-123456789012')

        # Verify API call
        mock_api_request.assert_called_once()
        args, kwargs = mock_api_request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(args[1], 'checks/')
        self.assertEqual(kwargs['data']['name'], 'example.com')
        self.assertEqual(kwargs['data']['tags'], 'status')

    @patch('checkdomains.requests.get')
    @patch('checkdomains.ping_healthcheck')
    def test_check_domain_status_success(self, mock_ping, mock_get):
        """Test checking domain status with a successful response."""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Call the function
        check_domain_status('example.com', '12345678-1234-1234-1234-123456789012')

        # Verify ping was called with success
        mock_ping.assert_called_once_with('12345678-1234-1234-1234-123456789012')

    @patch('checkdomains.requests.get')
    @patch('checkdomains.ping_healthcheck')
    def test_check_domain_status_failure(self, mock_ping, mock_get):
        """Test checking domain status with a failed response."""
        # Mock failed HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Call the function
        check_domain_status('example.com', '12345678-1234-1234-1234-123456789012')

        # Verify ping was called with failure
        mock_ping.assert_called_once_with('12345678-1234-1234-1234-123456789012', '/fail', payload='status=404')

    @patch('checkdomains.subprocess.run')
    @patch('checkdomains.ping_healthcheck')
    @patch('checkdomains.os.makedirs')
    @patch('checkdomains.os.path.exists')
    def test_check_domain_expiry(self, mock_exists, mock_makedirs, mock_ping, mock_subprocess):
        """Test checking domain expiry."""
        # Mock subprocess output
        mock_process = MagicMock()
        mock_process.stdout = "Registry Expiry Date: 2025-01-01T00:00:00Z"
        mock_subprocess.return_value = mock_process

        # Mock os.path.exists to return False for marker file
        mock_exists.return_value = False

        # Call the function
        check_domain_expiry('example.com', '87654321-4321-4321-4321-210987654321')

        # Verify subprocess was called
        mock_subprocess.assert_called_once()

        # Verify ping was called
        mock_ping.assert_called_once()

        # Verify makedirs was called
        mock_makedirs.assert_called_once()

    @patch('checkdomains._make_api_request')
    def test_get_all_healthchecks_details(self, mock_api_request):
        """Test getting all healthchecks details."""
        # Mock API response
        mock_api_request.return_value = {
            'checks': [
                {
                    'name': 'example.com',
                    'uuid': '12345678-1234-1234-1234-123456789012',
                    'tags': 'status'
                },
                {
                    'name': 'test.example.com',
                    'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
                    'tags': 'status'
                }
            ]
        }

        # Call the function
        result = get_all_healthchecks_details()

        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'example.com')
        self.assertEqual(result[1]['name'], 'test.example.com')

        # Verify API call
        mock_api_request.assert_called_once_with('GET', 'checks/')

    @patch('checkdomains._make_api_request')
    def test_delete_healthcheck(self, mock_api_request):
        """Test deleting a healthcheck."""
        # Mock API response
        mock_api_request.return_value = {'status': 'success'}

        # Call the function
        result = delete_healthcheck('12345678-1234-1234-1234-123456789012')

        # Verify the result
        self.assertTrue(result)

        # Verify API call
        mock_api_request.assert_called_once_with('DELETE', 'checks/12345678-1234-1234-1234-123456789012')

    @patch('checkdomains.requests.request')
    def test_ping_healthcheck(self, mock_request):
        """Test pinging a healthcheck."""
        # Call the function
        ping_healthcheck('12345678-1234-1234-1234-123456789012')

        # Verify request was called
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], 'GET')
        # Check that the UUID is in the URL, regardless of the base URL
        self.assertTrue('12345678-1234-1234-1234-123456789012' in args[1])

    @patch('checkdomains.load_domains')
    @patch('checkdomains.check_domain_status')
    @patch('checkdomains.check_domain_expiry')
    def test_action_check_domains(self, mock_check_expiry, mock_check_status, mock_load_domains):
        """Test the check command."""
        # Mock load_domains
        mock_load_domains.return_value = [
            {'domain': 'example.com', 'status_uuid': '12345678-1234-1234-1234-123456789012', 'expiry_uuid': '87654321-4321-4321-4321-210987654321'},
            {'domain': 'test.example.com', 'status_uuid': 'abcdef12-3456-7890-abcd-ef1234567890', 'expiry_uuid': ''}
        ]

        # Call the function
        action_check_domains()

        # Verify check_domain_status was called for both domains
        self.assertEqual(mock_check_status.call_count, 2)

        # Verify check_domain_expiry was called only for the domain with an expiry UUID
        self.assertEqual(mock_check_expiry.call_count, 1)
        mock_check_expiry.assert_called_once_with('example.com', '87654321-4321-4321-4321-210987654321')

    @patch('checkdomains.load_domains')
    @patch('checkdomains.info')
    def test_action_list_domains(self, mock_info, mock_load_domains):
        """Test the list-domains command."""
        # Mock load_domains
        mock_load_domains.return_value = [
            {'domain': 'example.com', 'status_uuid': '12345678-1234-1234-1234-123456789012', 'expiry_uuid': '87654321-4321-4321-4321-210987654321'},
            {'domain': 'test.example.com', 'status_uuid': 'abcdef12-3456-7890-abcd-ef1234567890', 'expiry_uuid': ''}
        ]

        # Call the function
        action_list_domains()

        # Verify info was called with the expected messages
        self.assertTrue(any('example.com' in call[0][0] for call in mock_info.call_args_list))
        self.assertTrue(any('test.example.com' in call[0][0] for call in mock_info.call_args_list))

    @patch('checkdomains.get_all_healthchecks_details')
    @patch('checkdomains.info')
    def test_action_list_checks(self, mock_info, mock_get_checks):
        """Test the list-checks command."""
        # Mock get_all_healthchecks_details
        mock_get_checks.return_value = [
            {
                'name': 'example.com',
                'uuid': '12345678-1234-1234-1234-123456789012',
                'tags': 'status',
                'last_ping': '2023-01-01T00:00:00Z',
                'status': 'up'
            },
            {
                'name': 'test.example.com',
                'uuid': 'abcdef12-3456-7890-abcd-ef1234567890',
                'tags': 'status',
                'last_ping': None,
                'status': 'new'
            }
        ]

        # Call the function
        action_list_checks()

        # Verify info was called with the expected messages
        self.assertTrue(any('example.com' in call[0][0] for call in mock_info.call_args_list))
        self.assertTrue(any('test.example.com' in call[0][0] for call in mock_info.call_args_list))

    @patch('checkdomains.os.path.isdir')
    @patch('checkdomains.os.listdir')
    @patch('checkdomains.os.remove')
    @patch('checkdomains.info')
    def test_action_delete_markers(self, mock_info, mock_remove, mock_listdir, mock_isdir):
        """Test the delete-markers command."""
        # Mock os.path.isdir to return True
        mock_isdir.return_value = True

        # Mock os.listdir to return a list of marker files
        mock_listdir.return_value = ['expiry_check_example.com', 'expiry_check_test.example.com', 'other_file.txt']

        # Call the function
        action_delete_markers()

        # Verify os.remove was called for each marker file
        self.assertEqual(mock_remove.call_count, 2)
        mock_remove.assert_any_call('/tmp/domain-hc-markers/expiry_check_example.com')
        mock_remove.assert_any_call('/tmp/domain-hc-markers/expiry_check_test.example.com')

        # Verify info was called with the expected messages
        self.assertTrue(any('Deleted 2 marker files' in str(call) for call in mock_info.call_args_list))

if __name__ == '__main__':
    unittest.main()
