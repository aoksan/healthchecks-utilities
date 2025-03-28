#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="logs.log"
SCRIPT_NAME=$(basename "$0")

log_header() {
  local width=60
  local name=" $SCRIPT_NAME "
  local pad fill line

  pad=$(( (width - ${#name}) / 2 ))
  fill=$(printf '=%.0s' $(seq 1 $pad))
  line="${fill}${name}${fill}"
  (( (width - ${#name}) % 2 )) && line="${line}="

  echo "$line" >&2
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line" >>"$LOG_FILE"
}

log() {
  local level=$1; shift
  echo "[$level] $*" >&2
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" >>"$LOG_FILE"
}

info()  { log "INFO"  "$@"; }
verbose() { log "VERBOSE" "$@"; }
debug() { log "DEBUG" "$@"; }
warn() { log "WARN" "$@"; }
alert() { log "ALERT" "$@"; }
error() { log "ERROR" "$@"; }
