# Healthchecks Utilities

This repository provides a modular set of Bash scripts for managing domain uptime and expiry monitoring via [Healthchecks.io](https://healthchecks.io/), a free and open-source cron job monitoring service.

The project is organized into:

- `domain-hc/`: Tools for checking domains, creating or cleaning up Healthchecks, and tracking expiry.
- `doc/`: Manual files for command-line documentation. (WORKING)

Each domain is tracked via a central `domains.txt` file, where each line includes a status UUID and optionally an expiry UUID. These UUIDs correspond to individual checks on Healthchecks.io and are actively pinged or logged depending on domain availability and WHOIS expiry data.

The scripts are built to work together, using shared helper files for things like logging and environment setup. WHOIS checks, expiry markers, and Healthchecks API interactions are reused across scripts.

Since this project was written with the help of ChatGPT, it’s a bit experimental—you might run into small bugs or quirks, especially with unusual domain setups. Feel free to tweak things as needed.

Refer to `doc/domain-hc.1` for detailed usage. (WORKING)


## Reference

- Healthchecks.io: [https://healthchecks.io](https://healthchecks.io)

