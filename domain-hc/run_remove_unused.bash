#!/usr/bin/env bash
set -euo pipefail

source ./helper_load_env.bash
source ./helper_log.bash

log_header

info "→ Starting cleanup of unused Healthchecks"

all_uuids=$(curl -s -H "X-Api-Key: $API_KEY" "$CHECKS_API_URL" | jq -r '.checks[].uuid')
used_uuids=()
while IFS=' ' read -r domain status_field expiry_field; do
  [[ -z "$domain" || "${domain:0:1}" == "#" ]] && continue
  used_uuids+=( "${status_field#s:}" )
  [[ -n "$expiry_field" ]] && used_uuids+=( "${expiry_field#e:}" )
done <"$DOMAIN_FILE"

deleted_count=0
for uuid in $all_uuids; do
  if [[ ! " ${used_uuids[*]:-} " =~ $uuid ]]; then
    curl -s -o /dev/null -X DELETE "$CHECKS_API_URL$uuid" -H "X-Api-Key: $API_KEY"
    info "✓ Deleted unused check: $uuid"
    ((deleted_count++))
  fi
done

if (( deleted_count == 0 )); then
  info "→ No unused checks to delete — all clear!"
else
  info "→ Cleanup successful: deleted $deleted_count unused check(s)."
fi

info "→ Cleanup complete"
