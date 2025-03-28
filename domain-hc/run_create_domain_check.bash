#!/usr/bin/env bash
set -euo pipefail

source ./helper_load_env.bash
source ./helper_log.bash

log_header

create_check() {
  local domain=$1 slug=${domain//./-}
  info "→ Creating checks for $domain"
  local s_uuid e_uuid

  s_uuid=$(curl -sS -X POST "$CHECKS_API_URL" \
    -H "X-Api-Key: $API_KEY" -H "Content-Type: application/json" \
    -d "{\"name\":\"${domain}\",\"slug\":\"${slug}-status\",\"unique\":[\"slug\"],\"tags\":\"status\",\"timeout\":300}" \
    | jq -r '.uuid // empty')

  if [[ "$domain" != *.*.* ]]; then
    e_uuid=$(curl -sS -X POST "$CHECKS_API_URL" \
    -H "X-Api-Key: $API_KEY" -H "Content-Type: application/json" \
    -d "{\"name\":\"${domain}\",\"slug\":\"${slug}-domain\",\"unique\":[\"slug\"],\"tags\":\"domain\",\"schedule\":\"0 0 * * 7\",\"tz\":\"UTC\"}" \
    | jq -r '.uuid // empty')
  else
    e_uuid=""
  fi

  info "✓ Created: ${domain} s:${s_uuid} e:${e_uuid}"
  echo "${domain} s:${s_uuid} e:${e_uuid}"
}

if [[ $# -eq 1 ]]; then
  domain=$1
  if grep -q "^${domain} " "$DOMAIN_FILE"; then
    info "→ Skipping $domain: checks already exist"
    exit 0
  fi
  create_check "$domain" >>"$DOMAIN_FILE"
else
  tmpfile=$(mktemp)
  while IFS= read -r line; do
    [[ "$line" =~ ^#|^$ ]] && echo "$line" >>"$tmpfile" && continue
    domain=${line%% *}
    if grep -q "^${domain} " "$DOMAIN_FILE"; then
      info "→ Skipping $domain: checks already exist"
      echo "$line" >>"$tmpfile"
    else
      create_check "$domain" >>"$tmpfile"
    fi
  done <"$DOMAIN_FILE"
  mv "$tmpfile" "$DOMAIN_FILE"
fi


