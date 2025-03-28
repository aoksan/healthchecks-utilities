#!/usr/bin/env bash
# delete_marker.sh - Debug tool to delete expiry check marker file(s).
# If no domain is provided, delete all marker files in /tmp matching "expiry_check_*".
# Running in debug mode; do not use in production.
set -uo pipefail
source ./helper_load_env.bash
source ./helper_log.bash

log_header

if [ "$#" -gt 1 ]; then
  info "Usage: $0 [domain]"
  exit 1
fi

if [ "$#" -eq 0 ]; then
  debug "No domain specified. Deleting all expiry marker files in /tmp."
  for marker_file in /tmp/expiry_check_*; do
    if [ -e "$marker_file" ]; then
      debug "Deleting marker file: $marker_file"
      rm "$marker_file"
    fi
  done
  debug "All marker files deleted."
else
  domain="$1"
  # The marker file is created as /tmp/expiry_check_<domain>,
  # where non-alphanumeric characters in the domain are replaced by underscores.
  marker_file="/tmp/expiry_check_${domain//[^a-zA-Z0-9]/_}"
  if [ -f "$marker_file" ]; then
    debug "Deleting marker file for domain '$domain': $marker_file"
    rm "$marker_file"
    debug "Marker file deleted."
  else
    debug "No marker file found for domain '$domain'."
  fi
fi