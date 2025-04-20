#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source helper scripts using absolute paths
source "$SCRIPT_DIR/helper_load_env.bash"
source "$SCRIPT_DIR/helper_log.bash"

log_header

info "→ Starting full cleanup: deleting ALL Healthchecks and removing all non-comment entries from $DOMAIN_FILE"

# Fetch all existing check UUIDs from Healthchecks.io
all_uuids=$(curl -s -H "X-Api-Key: $API_KEY" "$CHECKS_API_URL" | jq -r '.checks[].uuid')
deleted_count=0

default_internal_field=""
# Delete every check unconditionally
for uuid in $all_uuids; do
  curl -s -o /dev/null -X DELETE "${CHECKS_API_URL}${uuid}" -H "X-Api-Key: $API_KEY"
  info "✓ Deleted check: $uuid"
  ((deleted_count++))
done

# Remove all non-comment lines from DOMAIN_FILE, preserving comments and blank lines
tmpfile=$(mktemp)
grep -E '^\s*#|^\s*$' "$DOMAIN_FILE" > "$tmpfile"
mv "$tmpfile" "$DOMAIN_FILE"
info "✓ Removed all non-comment entries from $DOMAIN_FILE"

# Summary
if (( deleted_count == 0 )); then
  info "→ No checks found to delete."
else
  info "→ Cleanup successful: deleted $deleted_count checks."
fi

info "→ Full cleanup complete"
