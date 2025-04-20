# Healthchecks Domain Utilities

This directory contains scripts for managing domain health checks using the Healthchecks.io API.

## Recent Changes

### Absolute Path Handling

The scripts in this directory have been updated to use absolute paths instead of relative paths. This ensures that the scripts can be run from any directory, including from crontab or other contexts, and they will be able to find all their dependencies.

Key changes:

1. Added a `SCRIPT_DIR` variable to each script that determines the absolute path of the directory where the script is located:
   ```bash
   SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
   ```

2. Modified all source commands to use this absolute path:
   ```bash
   source "$SCRIPT_DIR/helper_load_env.bash"
   source "$SCRIPT_DIR/helper_log.bash"
   ```

3. Updated the `.env` file to use an absolute path for the `DOMAIN_FILE` variable:
   ```bash
   DOMAIN_FILE="${SCRIPT_DIR}/domains.txt"
   ```

4. Updated the `.env.example` file to provide guidance on using absolute paths.

These changes ensure that the scripts will find their dependencies regardless of the current working directory when they are executed.

## Usage

### Configuration

1. Copy `.env.example` to `.env` and update the values:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to set your API key and other configuration options.

### Running the Scripts

The scripts can be run from any directory:

```bash
/path/to/bash/domain-hc/run_check_domains.bash
```

Or you can add them to crontab:

```
0 * * * * /path/to/bash/domain-hc/run_check_domains.bash
```

## Testing

A test script is provided to verify that the absolute path changes work correctly:

```bash
./test_paths.bash
```

This script changes to a different directory and then tries to source the helper scripts to confirm that they can be found regardless of the current working directory.