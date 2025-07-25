# Healthchecks Utilities

This repository provides a Python utility for managing domain uptime and expiry monitoring via [Healthchecks.io](https://healthchecks.io/), a free and open-source cron job monitoring service.

The Python source code is located in the `src/` directory. Each domain is tracked via a central `domains.txt` file, where each line includes a status UUID and optionally an expiry UUID. These UUIDs correspond to individual checks on Healthchecks.io and are actively pinged or logged depending on domain availability and WHOIS expiry data.

## Python Implementation

The project is managed using [Rye](https://rye-up.com/), with common tasks wrapped in a `Makefile` for convenience.

### Installation & Setup

1.  **Install Rye:** Before you begin, ensure you have Rye installed on your system. Follow the instructions on the [official Rye website](https://rye-up.com/guide/installation/).

2.  **Install Project Dependencies:** Navigate to the project's root directory and run the `install` command:
    ```bash
    make install
    ```
    This will use Rye to sync the project, download the correct Python version, create a virtual environment, and install all required dependencies.

### Usage

This project provides a `Makefile` to simplify common operations. You can see a list of all available commands by running `make help`.

#### Running the Application

To run the main utility, you should use `rye run`, which executes commands within the project's managed environment.

```bash
rye run healthchecks-utilities <command>
```

For example, to list all configured domains:

```bash
rye run healthchecks-utilities list-domains
```

#### Activating a Development Shell

If you need an interactive shell with the virtual environment activated, simply run:

```bash
make source
```

This will spawn a new shell session. To return to your original shell, just type `exit`.

#### Development Tasks

The Makefile includes shortcuts for common development tasks:

- **`make lint`**: Run the linter to check code quality.
- **`make test`**: Run the unit tests.

## Reference

- Healthchecks.io: [https://healthchecks.io](https://healthchecks.io)
