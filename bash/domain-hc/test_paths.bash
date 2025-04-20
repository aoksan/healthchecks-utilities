#!/usr/bin/env bash
# test_paths.bash - Test script to verify that the absolute path changes work correctly
# This script should be run from a different directory to test that the scripts can find their dependencies

set -euo pipefail

# Get the absolute path to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Script directory: $SCRIPT_DIR"

# Change to a different directory
cd /tmp
echo "Current directory: $(pwd)"

# Try to run one of the scripts using its absolute path
echo "Running helper_load_env.bash from a different directory..."
source "$SCRIPT_DIR/helper_load_env.bash"

echo "Success! The script was able to find its dependencies."
echo "API_URL: $API_URL"
echo "BASE_URL: $BASE_URL"
echo "DOMAIN_FILE: $DOMAIN_FILE"

echo "Test completed successfully!"