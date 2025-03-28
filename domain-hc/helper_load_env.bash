#!/usr/bin/env bash
set -euo pipefail

source ./helper_log.bash

# Load API_URL and API_KEY from .env
if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
else
  warn ".env file not found. Please create one with API_URL and API_KEY." >&2
  exit 1
fi

# Validate that API_URL and API_KEY are set
if [[ -z "${API_URL:-}" || -z "${API_KEY:-}" ]]; then
  warn "API_URL and/or API_KEY are not defined in .env." >&2
  exit 1
fi

# Build full API endpoint (ensure no trailing slash)
export PING_API_URL="${BASE_URL%/}" # probably not needed
export CHECKS_API_URL="${API_URL%/}/checks/"
export CHANNELS_API_URL="${API_URL%/}/channels/"
export BADGES_API_URL="${API_URL%/}/badges/"
export DB_STATUS_API_URL="${API_URL%/}/status/"
