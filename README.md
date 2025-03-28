# Healthchecks Utilities

This repository provides a modular set of Bash scripts for managing domain uptime and expiry monitoring via [Healthchecks.io](https://healthchecks.io/), a free and open-source cron job monitoring service.

The project is organized into:

- `domain-hc/`: Tools for checking domains, creating or cleaning up Healthchecks, and tracking expiry.
- `doc/`: Manual files for command-line documentation.
- `another-hc/`: Placeholder for future healthcheck-related modules.

Each domain is tracked via a central `domains.txt` file with assigned Healthcheck UUIDs for status and optional expiry.

Environment variables, logging, and WHOIS integration are supported out of the box.

Refer to `domain-hc/README.md` and `doc/domain-hc.1` for detailed usage.

## Reference

- Healthchecks.io: [https://healthchecks.io](https://healthchecks.io)

