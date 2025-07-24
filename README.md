# Healthchecks Utilities

This repository provides utilities for managing domain uptime and expiry monitoring via [Healthchecks.io](https://healthchecks.io/), a free and open-source cron job monitoring service. It includes both Bash scripts and a Python implementation with package management support.

The project is organized into:

- `bash/domain-hc/`: Bash tools for checking domains, creating or cleaning up Healthchecks, and tracking expiry.
- `python/`: Python implementation of domain health checks with package management support.
- `doc-test/`: Manual files for command-line documentation. (WORKING)

Each domain is tracked via a central `domains.txt` file, where each line includes a status UUID and optionally an expiry UUID. These UUIDs correspond to individual checks on Healthchecks.io and are actively pinged or logged depending on domain availability and WHOIS expiry data.

The scripts are built to work together, using shared helper files for things like logging and environment setup. WHOIS checks, expiry markers, and Healthchecks API interactions are reused across scripts.

Since this project was written with the help of ChatGPT, it’s a bit experimental—you might run into small bugs or quirks, especially with unusual domain setups. Feel free to tweak things as needed.

Refer to `doc-test/domain-hc.1` for detailed usage of the Bash scripts.

## Python Implementation

The `python/` directory contains a Python implementation of the domain health checks. This implementation provides the same functionality as the Bash scripts but with a more structured approach and better error handling.

### Package Management

The Python implementation now supports package management using:

1. **requirements.txt** - For traditional pip-based dependency management
2. **pyproject.toml** - For modern Python packaging (PEP 621 compliant)

For detailed installation and usage instructions, see the [Python README](domain_checker/README.md).

## Reference

- Healthchecks.io: [https://healthchecks.io](https://healthchecks.io)
