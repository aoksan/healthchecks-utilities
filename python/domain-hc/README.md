# Healthchecks Utilities - Python

This directory contains Python utilities for monitoring domain health and expiry using Healthchecks.io.

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package installer)
- `whois` command-line tool installed on your system

### Using pip with requirements.txt

The simplest way to install the required dependencies is using pip with the provided requirements.txt file:

```bash
# Navigate to the python directory
cd python

# Install dependencies
pip install -r requirements.txt
```

### Using pip with pyproject.toml (modern approach)

For a more modern approach, you can use pip with the pyproject.toml file (requires pip >= 21.3):

```bash
# Navigate to the project root
cd /path/to/healthchecks-utilities

# Install the project in development mode
pip install -e .
```

### Verifying Installation

You can verify that all dependencies are installed correctly by running the test script:

```bash
python python/test_dependencies.py
```

## Configuration

Create a `.env` file in the python directory with the following variables:

```
API_URL=https://healthchecks.io/api/v3/
API_KEY=your_healthchecks_api_key
BASE_URL=https://hc-ping.com
DOMAIN_FILE=domains.txt
```

## Usage

Run the script with one of the available commands:

```bash
python checkdomains.py <command>
```

Available commands:
- `create`: Ensure checks exist for all domains in file, creating if missing.
- `check`: Check status/expiry for configured domains and ping healthchecks.
- `remove-unused`: Remove healthchecks from API not found in the local file.
- `remove-all`: DANGER: Remove ALL healthchecks from API and clear local file.
- `list-checks`: List all healthchecks registered in the Healthchecks.io account.
- `list-domains`: List valid domains and their UUIDs configured in the local file.
- `delete-markers`: Delete temporary expiry check marker files from /tmp.

For more information, run the script without any command:

```bash
python checkdomains.py
```