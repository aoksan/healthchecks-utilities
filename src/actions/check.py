# domain_checker/actions/check.py
import datetime
import requests
from .. import api_client, services
from ..logger import info, debug, error, warn

def check_domain_status(domain, status_uuid):
    """Checks website status and pings the status healthcheck."""
    info(f"Checking status for {domain}...")
    try:
        response = requests.get(f"https://{domain}", timeout=10, allow_redirects=True, verify=True, headers={'User-Agent': 'domain-hc-script/1.0'})
        if 200 <= response.status_code < 400:
            api_client.ping_healthcheck(status_uuid)
            info(f"  ✓ Status: up (HTTP {response.status_code}) for {domain}")
        else:
            api_client.ping_healthcheck(status_uuid, "/fail", payload=f"status={response.status_code}")
            error(f"  ✗ Status: down/error (HTTP {response.status_code}) for {domain}")
    except requests.exceptions.RequestException as e:
        api_client.ping_healthcheck(status_uuid, "/fail", payload=f"status=error_{type(e).__name__}")
        error(f"  ✗ Status check failed for {domain}: {e}")

def check_domain_expiry(domain, expiry_uuid):
    """Checks domain expiry and pings the healthcheck."""
    info(f"Checking expiry for {domain}...")
    if domain.count('.') > 1:
        info(f"  ↪ Skipping WHOIS/API lookup for apparent subdomain: {domain}")
        api_client.ping_healthcheck(expiry_uuid, payload="status=skipped_subdomain")
        return

    # Marker file logic can be moved to file_handler.py if desired

    expiry_date, source = None, "unknown"
    whois_output = services.run_whois(domain)
    if whois_output:
        expiry_date = services._parse_expiry_from_whois(whois_output)
        if expiry_date: source = "WHOIS"

    if not expiry_date:
        expiry_date_godaddy = services._get_expiry_from_godaddy(domain)
        if expiry_date_godaddy:
            expiry_date = expiry_date_godaddy
            source = "GoDaddy API"

    if expiry_date:
        info(f"  ✓ Found Expiry Date via {source} for {domain}: {expiry_date.strftime('%Y-%m-%d')}")
        days_left = (expiry_date - datetime.datetime.now(datetime.timezone.utc)).days
        if days_left <= 0:
            warn(f"  ✗ Domain {domain} has expired! ({abs(days_left)} days ago)")
            api_client.ping_healthcheck(expiry_uuid + "/fail", payload=f"status=expired&days_left={days_left}")
        else:
            info(f"  ✓ Domain {domain} expiry is OK ({days_left} days remaining).")
            api_client.ping_healthcheck(expiry_uuid, payload=f"status=ok&days_left={days_left}")
    else:
        error(f"  ✗ Failed to determine expiry date for {domain}.")
        api_client.ping_healthcheck(expiry_uuid + "/fail", payload="status=lookup_failed")
