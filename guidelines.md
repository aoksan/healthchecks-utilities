# Healthchecks Utilities Development Guidelines

This document provides essential information for developers working on the Healthchecks Utilities project.

## Build/Configuration Instructions

### Environment Setup

1. **Python Environment**:
   - The project requires Python 3.6+ with pip
   - Use the included virtual environment:
     ```bash
     source venv/bin/activate
     ```
   - If creating a new environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt  # If requirements.txt exists, otherwise install manually
     ```

2. **Dependencies**:
   - Required Python packages:
     - `requests`
     - `python-dotenv`
   - System dependencies:
     - `whois` command-line tool must be installed on the system

3. **Configuration**:
   - Create a `.env` file in the project root or in the `domain-hc` directory with:
     ```
     API_URL=https://healthchecks.io/api/v3/
     API_KEY=your_healthchecks_api_key
     BASE_URL=https://hc-ping.com
     DOMAIN_FILE=domains.txt
     ```
   - Alternatively, set these as environment variables

## Testing Information

### Running Tests

1. **Unit Tests**:
   - Tests are located in the `.junie` directory
   - Run tests with:
     ```bash
     python3 .junie/test_domain_parsing.py
     ```

2. **Manual Testing**:
   - Test domain checking:
     ```bash
     python3 checkdomains.py check
     ```
   - Test creating domain checks:
     ```bash
     python3 checkdomains.py create
     ```
   - List configured domains:
     ```bash
     python3 checkdomains.py list-domains
     ```

### Adding New Tests

1. **Creating Unit Tests**:
   - Use Python's `unittest` framework
   - Place test files in the `.junie` directory
   - Follow the pattern in `test_domain_parsing.py`:
     - Create a test class that inherits from `unittest.TestCase`
     - Use `setUp` and `tearDown` methods for test preparation and cleanup
     - Name test methods with a `test_` prefix

2. **Test Example**:
   Here's a simple test for the domain parsing functionality:

   ```python
   import unittest
   import tempfile

   # Create a simplified version of the function to test
   def load_domains_test(filename):
       # Implementation here...
       return domains

   class TestExample(unittest.TestCase):
       def setUp(self):
           # Create a temporary test file
           self.temp_file = tempfile.NamedTemporaryFile(delete=False)
           self.temp_filename = self.temp_file.name
           test_data = "example.com s:12345678-1234-1234-1234-123456789012\n"
           self.temp_file.write(test_data.encode('utf-8'))
           self.temp_file.close()

       def tearDown(self):
           # Clean up
           import os
           os.unlink(self.temp_filename)

       def test_function(self):
           # Test the function
           result = load_domains_test(self.temp_filename)
           self.assertEqual(len(result), 1)
           self.assertEqual(result[0]['domain'], "example.com")
   ```

## Additional Development Information

### Code Structure

1. **Main Components**:
   - `checkdomains.py`: Python script for domain checking and management
   - `domain-hc/`: Directory containing Bash scripts for domain health checks
   - `domains.txt`: Configuration file listing domains to monitor

2. **Domain File Format**:
   - Each line follows the format: `domain s:<status_uuid> [e:<expiry_uuid>]`
   - Status UUID is required for all domains
   - Expiry UUID is optional and typically omitted for subdomains
   - Lines starting with `#` are treated as comments

3. **Logging**:
   - The application logs to `logs.log` in the project root
   - Each script also outputs to stdout/stderr
   - Log format: `[YYYY-MM-DD HH:MM:SS] [LEVEL] Message`

### Debugging Tips

1. **Common Issues**:
   - If domain checks fail, ensure the `whois` command is installed
   - For API errors, verify your API key and URL in the `.env` file
   - Check permissions on marker files in `/tmp/domain-hc-markers/`

2. **Useful Commands**:
   - Delete expiry markers to force re-checking: `python3 checkdomains.py delete-markers`
   - List all checks from the API: `python3 checkdomains.py list-checks`
   - Remove unused checks: `python3 checkdomains.py remove-unused`

3. **Development Workflow**:
   - Make changes to the Python script or Bash scripts
   - Test changes with a small subset of domains
   - Run the appropriate command to verify functionality
   - Check logs for errors or unexpected behavior