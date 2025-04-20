#!/usr/bin/env bash
set -uo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source helper scripts using absolute paths
source "$SCRIPT_DIR/helper_load_env.bash"
source "$SCRIPT_DIR/helper_log.bash"

log_header

today=$(date +%Y-%m-%d)
seven_days=$((7 * 24 * 60 * 60))

while read -r domain status_field expiry_field; do
  [[ -z "$domain" || "${domain:0:1}" == "#" ]] && continue

  status_uuid=${status_field#s:}
  expiry_uuid=${expiry_field#e:}
  if [[ -z "$status_uuid" ]]; then
    info "→ Skipping $domain: no status UUID provided."
    continue
  fi

  info "→ Checking $domain …"

  ### Website Status Check
  # Retrieve HTTP status code using HTTPS with a 10-second timeout.
  status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -L "https://$domain" || echo "000")
  if [[ "$status" =~ ^2 ]]; then
    curl -s "${BASE_URL}/${status_uuid}" >/dev/null
    info "  ✓ Status: up (HTTP $status)"
  else
    curl -s -X POST -d "status=$status" "${BASE_URL}/${status_uuid}/fail" >/dev/null
    error "  ✗ Status: failure (HTTP $status)"
  fi

  # Weekly expiry check
  if [[ -n "${expiry_uuid// /}" ]]; then
    marker="/tmp/expiry_check_${domain//[^a-zA-Z0-9]/_}"
    # Get marker’s mtime in seconds since epoch (portable)
    if [[ -f "$marker" ]]; then
      file_ts=$(date -r "$marker" +%s 2>/dev/null || stat -f "%m" "$marker")
    else
      file_ts=0
    fi

    if (($(date +%s) - file_ts < seven_days)); then
      info "  ↻ Expiry check already performed within last 7 days for $domain."
    else
      expiry_raw=$(whois "$domain" 2>/dev/null |
        grep -Ei 'Registry Expiry Date|Expiry Date|Expiration Date|paid-till' |
        head -n1 | cut -d: -f2- | sed 's/^[[:space:]]*//;s/\r//') || expiry_raw=""
      registrar=$(whois "$domain" 2>/dev/null |
        grep -Ei '^Registrar:' | head -n1 | cut -d: -f2- | sed 's/^[[:space:]]*//;s/\r//') || registrar=""

      info "  WHOIS info for $domain:"
      info "    Registry Expiry Date: ${expiry_raw:-N/A}"
      info "    Registrar: ${registrar:-N/A}"

      if [[ -n "$expiry_raw" ]]; then
        expiry_date=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expiry_raw" +%Y-%m-%d 2>/dev/null || date -d "$expiry_raw" +%Y-%m-%d 2>/dev/null || echo "")
        if [[ -n "$expiry_date" ]]; then
          now_ts=$(date +%s)
          exp_ts=$(date -j -f "%Y-%m-%d" "$expiry_date" +%s 2>/dev/null || date -d "$expiry_date" +%s)
          days_remaining=$(((exp_ts - now_ts) / 86400))
          curl -s -X POST -d "days_remaining=${days_remaining} expiry_date=${expiry_date}" "${BASE_URL}/${expiry_uuid}" >/dev/null
          info "  ✓ Expiry ping sent: expires in ${days_remaining} days."
        else
          curl -s -X POST -d "expiry_date=not found" "${BASE_URL}/${expiry_uuid}/log" >/dev/null
          error "  ✗ Could not parse expiry date."
        fi
      else
        curl -s -X POST -d "expiry_date=not found" "${BASE_URL}/${expiry_uuid}/log" >/dev/null
        error "  ✗ Expiry date not found."
      fi

      touch "$marker"
    fi
  fi
  info ""
done <"$DOMAIN_FILE"
info "→ All domain checks completed."
