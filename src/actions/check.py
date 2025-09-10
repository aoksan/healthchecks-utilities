# domain_checker/actions/check.py
import datetime
import requests
from .. import api_client, services, file_handler
from ..logger import info, debug, error, warn

def check_domain_status(domain, status_uuid):
    """Checks website status and pings the status healthcheck."""
    info(f"Checking status for {domain}...")
    try:
        response = requests.get(f"https://{domain}", timeout=10, allow_redirects=True, verify=True, headers={'User-Agent': 'domain-hc-script/1.0'})
        if 200 <= response.status_code < 400:
            api_client.ping_check(status_uuid)
            info(f"  ✓ Status: up (HTTP {response.status_code}) for {domain}")
        else:
            api_client.ping_check(status_uuid, "/fail", payload=f"status={response.status_code}")
            error(f"  ✗ Status: down/error (HTTP {response.status_code}) for {domain}")
    except requests.exceptions.RequestException as e:
        api_client.ping_check(status_uuid, "/fail", payload=f"status=error_{type(e).__name__}")
        error(f"  ✗ Status check failed for {domain}: {e}")

# The list is ordered from most urgent (lowest day count) to least.
# Each tuple contains: (day_threshold, tag_string)
EXPIRY_LEVELS = [
    (0, 'expired'),
    (7, 'expires_in_<7d'),
    (30, 'expires_in_<30d'),
    (60, 'expires_in_<60d'),
    (90, 'expires_in_<90d'),
]
# Define standard tags for non-threshold states.
OK_TAG = 'expiry_ok'
LOOKUP_FAILED_TAG = 'lookup_failed'

# --- 2. Derive the list of all managed tags directly from the definitions above. ---
# This ensures the list is always in sync with the logic.
MANAGED_EXPIRY_TAGS = [tag for _, tag in EXPIRY_LEVELS] + [OK_TAG, LOOKUP_FAILED_TAG]

def check_domain_expiry(domain, expiry_uuid):
    """Checks domain expiry, pings the healthcheck, and updates status tags."""
    info(f"Checking expiry for {domain}...")

    if file_handler.is_marker_valid(domain):
        info(f"  ✓ Valid marker found for {domain}. Skipping full expiry check.")
        return

    # --- 1. Determine Expiry Date ---
    expiry_date, source = None, "unknown"
    if domain.count('.') > 1:
        info(f"  ↪ Skipping WHOIS/API lookup for apparent subdomain: {domain}")
        api_client.ping_check(expiry_uuid, payload="status=skipped_subdomain")
        # Optional: You could also add a 'subdomain' tag here
        return

    whois_output = services.run_whois(domain)
    if whois_output:
        expiry_date = services._parse_expiry_from_whois(whois_output)
        if expiry_date: source = "WHOIS"

    if not expiry_date:
        expiry_date_godaddy = services._get_expiry_from_godaddy(domain)
        if expiry_date_godaddy:
            expiry_date = expiry_date_godaddy
            source = "GoDaddy API"

    file_handler.create_expiry_marker(domain)

    # --- 2. Calculate Status and Desired Tag ---
    desired_tag = None
    days_left = None

    if expiry_date:
        info(f"  ✓ Found Expiry Date via {source}: {expiry_date.strftime('%Y-%m-%d')}")
        days_left = (expiry_date - datetime.datetime.now(datetime.timezone.utc)).days

        # --- 3. Determine the correct tag by iterating through the defined levels. ---
        for threshold, tag in EXPIRY_LEVELS:
            if days_left <= threshold:
                desired_tag = tag
                break

        if desired_tag is None:
            desired_tag = OK_TAG

        # --- 4. Handle logging and pinging based on the determined tag. ---
        if desired_tag == 'expired':
            warn(f"  ✗ Domain {domain} has expired! ({abs(days_left)} days ago)")
            api_client.ping_check(expiry_uuid + "/fail", payload=f"status=expired&days_left={days_left}")
        elif desired_tag == 'expires_in_<7d':
            warn(f"  ⚠ Domain {domain} expires very soon! ({days_left} days)")
            api_client.ping_check(expiry_uuid + "/fail", payload=f"status=expiring_soon&days_left={days_left}")
        elif desired_tag in ['expires_in_<30d', 'expires_in_<60d', 'expires_in_<90d']:
            warn(f"  ⚠ Domain {domain} expires soon! ({days_left} days)")
            api_client.ping_check(expiry_uuid, payload=f"status=expiring_soon&days_left={days_left}")
        else: # This covers OK_TAG
            info(f"  ✓ Domain {domain} expiry is OK ({days_left} days remaining).")
            api_client.ping_check(expiry_uuid, payload=f"status=ok&days_left={days_left}")
    else:
        desired_tag = LOOKUP_FAILED_TAG
        error(f"  ✗ Failed to determine expiry date for {domain}.")
        api_client.ping_check(expiry_uuid + "/fail", payload="status=lookup_failed")

    # --- Update Tags if Necessary ---
    if not desired_tag:
        return # Should not happen, but a safeguard.

    check_details = api_client.get_check_details(expiry_uuid)
    if not check_details:
        error(f"Could not fetch details for check {expiry_uuid} to update tags.")
        return

    current_tags = check_details.get('tags', '').split()

    if desired_tag in current_tags:
        debug(f"Tag '{desired_tag}' is already present for {domain}. No update needed.")
        return

    # Preserve any tags that are not part of our managed set
    new_tags = [tag for tag in current_tags if tag not in MANAGED_EXPIRY_TAGS]
    new_tags.append(desired_tag)
    debug(f"Updating tags for {domain}: {new_tags}")
    api_client.update_check_tags(expiry_uuid, new_tags)
