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
    -d "{\"name\":\"${domain}\",\"slug\":\"${slug}-domain\",\"unique\":[\"slug\"],\"tags\":\"domain\",\"schedule\":\"0 0 * * 7\",\"tz\":\"Europe/Istanbul\"}" \
    | jq -r '.uuid // empty')
  else
    e_uuid=""
  fi
  #  {"checks": [{"name": "awd", "slug": "awd", "tags": "awd", "desc": "", "grace": 3600, "n_pings": 0, "status": "new", "started": false, "last_ping": null, "next_ping": null, "manual_resume": false, "methods": "", "subject": "", "subject_fail": "", "start_kw": "", "success_kw": "", "failure_kw": "", "filter_subject": false, "filter_body": false, "badge_url": "http://localhost:8000/b/2/273da815-d61a-47fd-869e-378225a9ef8c.svg", "uuid": "5f7d1995-83e6-431b-9df9-a6d4394c2c20", "ping_url": "http://localhost:8000/ping/5f7d1995-83e6-431b-9df9-a6d4394c2c20", "update_url": "http://localhost:8000/api/v3/checks/5f7d1995-83e6-431b-9df9-a6d4394c2c20", "pause_url": "http://localhost:8000/api/v3/checks/5f7d1995-83e6-431b-9df9-a6d4394c2c20/pause", "resume_url": "http://localhost:8000/api/v3/checks/5f7d1995-83e6-431b-9df9-a6d4394c2c20/resume", "channels": "65615aa6-9803-4ccf-a181-7e023ff0cdaf", "timeout": 604800}]}%
  #  {"checks": [{"name": "awd", "slug": "awd", "tags": "awd", "desc": "", "grace": 3600, "n_pings": 0, "status": "new", "started": false, "last_ping": null, "next_ping": null, "manual_resume": false, "methods": "", "subject": "", "subject_fail": "", "start_kw": "", "success_kw": "", "failure_kw": "", "filter_subject": false, "filter_body": false, "badge_url": "http://localhost:8000/b/2/273da815-d61a-47fd-869e-378225a9ef8c.svg", "uuid": "5f7d1995-83e6-431b-9df9-a6d4394c2c20", "ping_url": "http://localhost:8000/ping/5f7d1995-83e6-431b-9df9-a6d4394c2c20", "update_url": "http://localhost:8000/api/v3/checks/5f7d1995-83e6-431b-9df9-a6d4394c2c20", "pause_url": "http://localhost:8000/api/v3/checks/5f7d1995-83e6-431b-9df9-a6d4394c2c20/pause", "resume_url": "http://localhost:8000/api/v3/checks/5f7d1995-83e6-431b-9df9-a6d4394c2c20/resume", "channels": "65615aa6-9803-4ccf-a181-7e023ff0cdaf", "schedule": "0 0 * * 7", "tz": "Europe/Istanbul"}]}%

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


