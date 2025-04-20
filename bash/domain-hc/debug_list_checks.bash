#!/usr/bin/env bash
# list_checks.sh - Debug tool to list each domain with its associated UUIDs
# and, in verbose mode, display check details from the API including tags.
# Running in debug mode; do not use in production.
#
# Usage:
#   ./list_checks.sh [-v]
#   -v    Verbose mode: show full check info from API.

set -uo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source helper scripts using absolute paths
source "$SCRIPT_DIR/helper_load_env.bash"
source "$SCRIPT_DIR/helper_log.bash"

log_header

VERBOSE=false

# Process options.
while getopts ":v" opt; do
  case ${opt} in
  v)
    VERBOSE=true
    ;;
  \?)
    info "Usage: $0 [-v]" >&2
    exit 1
    ;;
  esac
done
shift $((OPTIND - 1))

if [ ! -f "$DOMAIN_FILE" ]; then
  debug "Domains file '$DOMAIN_FILE' not found."
  exit 1
fi

# Ensure jq is installed.
if ! command -v jq >/dev/null 2>&1; then
  debug "'jq' is required for parsing the API response. Please install jq."
  exit 1
fi

debug "Fetching checks from API at ${CHECKS_API_URL}"
api_response=$(curl -s --header "X-Api-Key: ${API_KEY}" "$CHECKS_API_URL")
if [ -z "$api_response" ]; then
  debug "No response from API. Check your connectivity or API key."
  exit 1
fi

debug "Listing domain checks from ${DOMAIN_FILE}:"
while read -r line; do
  # Skip empty lines or lines starting with "#"
  [[ -z "$line" || "${line:0:1}" == "#" ]] && continue

  # Expecting format: domain status_uuid [expiry_uuid]
  IFS=' ' read -r domain status expiry <<<"$line"
  status_uuid=${status#*:}
  expiry_uuid=${expiry#*:}

  debug "---------------------------------------------------"
  debug "Domain:        $domain"
  debug "Status UUID:   ${status_uuid:-N/A}"
  debug "Expiry UUID:   ${expiry_uuid:-N/A}"

  if [ "$VERBOSE" = true ]; then
    # For status_uuid: check API response for a matching check.
    if [[ -n "$status_uuid" ]]; then
      check=$(echo "$api_response" | jq -r --arg key "$status_uuid" '.checks[] | select((.uuid==$key) or (.unique_key==$key))')
      if [[ -n "$check" ]]; then
        tags=$(echo "$check" | jq -r '.tags')
        echo "Status Check Info (Tags: $tags)"
        echo "$check" | jq .
      else
        echo "No API check found for status_uuid $status_uuid"
      fi
    fi

    # For expiry_uuid: check API response for a matching check.
    if [[ -n "$expiry_uuid" ]]; then
      check=$(echo "$api_response" | jq -r --arg key "$expiry_uuid" '.checks[] | select((.uuid==$key) or (.unique_key==$key))')
      if [[ -n "$check" ]]; then
        tags=$(echo "$check" | jq -r '.tags')
        echo "Expiry Check Info (Tags: $tags):"
        echo "$check" | jq .
      else
        echo "No API check found for expiry_uuid $expiry_uuid"
      fi
    fi
  fi
done <"$DOMAIN_FILE"
debug "---------------------------------------------------"
