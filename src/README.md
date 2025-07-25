# Healthchecks Utilities - Python

This directory contains Python utilities for monitoring domain health and expiry using Healthchecks.io.

## Installation and Setup

This project is managed using [Rye](https://rye-up.com/).

### Prerequisites

- The `whois` command-line tool installed on your system.
- [Rye](https://rye-up.com/guide/installation/) installed on your system.

### Setup

1.  **Clone the repository.**

2.  **Navigate to the project root and sync dependencies:**
    From the root directory of this repository, run:
    ```bash
    rye sync
    ```
    Rye will handle installing the correct Python version and all project dependencies.

## Configuration

Create a `.env` file in the project's root directory (next to `pyproject.toml`) with the following variables:

```
API_URL=https://healthchecks.io/api/v3/
API_KEY=your_healthchecks_api_key
BASE_URL=https://hc-ping.com
DOMAIN_FILE=domains.txt
```

Note that `DOMAIN_FILE` should point to the `domains.txt` file in the root of the project.

## Usage

Run the script using `rye run` from the project root:

```bash
rye run healthchecks-utilities <command>
```

Available commands:

- `create`: Ensure checks exist for all domains in file, creating if missing.
- `check`: Check status/expiry for configured domains and ping healthchecks.
- `remove`: Remove checks from API and/or file (e.g., `--unused`, `--all`, `<domain>`).
- `list-checks`: List all healthchecks registered in the Healthchecks.io account.
- `list-domains`: List valid domains and their UUIDs configured in the local file.
- `delete-markers`: Delete temporary expiry check marker files from /tmp.
- `sync-file`: Syncs local file with API (adds/removes checks).

For more information, run the script with `--help`:

```bash
rye run healthchecks-utilities --help
```
