#!/usr/bin/env python3
import sys
import os
import tempfile
import unittest

# Create a simplified version of the functions we want to test
def load_domains_raw_test(filename):
    """Loads raw lines and comments/blanks from the domain file."""
    lines_data = []
    try:
        with open(filename, 'r') as f:
            for idx, line in enumerate(f):
                lines_data.append({'line_num': idx + 1, 'raw_line': line.strip()})
    except FileNotFoundError:
        print(f"Domains file '{filename}' not found.")
    except IOError as e:
        print(f"Could not read domains file '{filename}': {e}")
    return lines_data

def load_domains_test(filename):
    """Loads domain configurations from the file, skipping invalid."""
    domains = []
    try:
        with open(filename, 'r') as f:
            for idx, line in enumerate(f):
                line_num = idx + 1
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    # Require at least domain and s:uuid
                    if len(parts) >= 2 and any(p.startswith('s:') for p in parts):
                        domain = parts[0]
                        status_uuid = None
                        expiry_uuid = None
                        for part in parts[1:]:
                            if part.startswith('s:'):
                                status_uuid = part.split(':', 1)[1]
                            elif part.startswith('e:'):
                                expiry_uuid = part.split(':', 1)[1]

                        # If status_uuid is somehow still None after check above, something is wrong
                        if not status_uuid:
                             print(f"Internal inconsistency on line {line_num} parsing: '{line}'. Skipping.")
                             continue

                        domains.append({'domain': domain, 'status_uuid': status_uuid, 'expiry_uuid': expiry_uuid or ""})
                    else:
                         # Warn if the line has content but not the required s:uuid
                         print(f"Skipping invalid line {line_num}: '{line}' in {filename}. Expected format: domain s:<uuid> [e:<uuid>]")

    except FileNotFoundError:
        print(f"Domains file '{filename}' not found. No domains loaded.")
    except IOError as e:
        print(f"Could not read domains file '{filename}': {e}")
    return domains

class TestDomainParsing(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_filename = self.temp_file.name

        # Write test data to the file
        test_data = """# Test domains file
# Format: domain s:status_uuid e:expiry_uuid
example.com s:12345678-1234-1234-1234-123456789012 e:87654321-4321-4321-4321-210987654321
test.example.com s:abcdef12-3456-7890-abcd-ef1234567890
invalid.com
# Comment line
"""
        self.temp_file.write(test_data.encode('utf-8'))
        self.temp_file.close()

    def tearDown(self):
        # Remove the temporary file
        os.unlink(self.temp_filename)

    def test_load_domains_raw(self):
        """Test that load_domains_raw correctly loads all lines from the file."""
        lines = load_domains_raw_test(self.temp_filename)
        self.assertEqual(len(lines), 6)  # 6 lines in the test file

        # Check that the first line is a comment
        self.assertEqual(lines[0]['raw_line'], "# Test domains file")

        # Check that the third line is a domain with status and expiry UUIDs
        self.assertEqual(lines[2]['raw_line'], "example.com s:12345678-1234-1234-1234-123456789012 e:87654321-4321-4321-4321-210987654321")

    def test_load_domains(self):
        """Test that load_domains correctly parses valid domain entries."""
        domains = load_domains_test(self.temp_filename)
        self.assertEqual(len(domains), 2)  # Only 2 valid domain entries

        # Check the first domain
        self.assertEqual(domains[0]['domain'], "example.com")
        self.assertEqual(domains[0]['status_uuid'], "12345678-1234-1234-1234-123456789012")
        self.assertEqual(domains[0]['expiry_uuid'], "87654321-4321-4321-4321-210987654321")

        # Check the second domain
        self.assertEqual(domains[1]['domain'], "test.example.com")
        self.assertEqual(domains[1]['status_uuid'], "abcdef12-3456-7890-abcd-ef1234567890")
        self.assertEqual(domains[1]['expiry_uuid'], "")  # No expiry UUID for subdomain

if __name__ == '__main__':
    unittest.main()
