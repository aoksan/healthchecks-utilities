# domain_checker/actions/list.py
from .. import api_client, file_handler, config
from ..logger import info

def list_api_checks():
    """Lists all healthchecks found via the API."""
    info("Starting: List Checks from API")
    all_checks = api_client.get_all_healthchecks_details()
    if not all_checks:
        info("No healthchecks found on the account.")
        return
    info(f"Found {len(all_checks)} Healthchecks:")
    for check in sorted(all_checks, key=lambda x: x.get('name', '').lower()):
        info(f"  - Name: {check.get('name', 'N/A'):<30} UUID: {check['uuid']} Status: {check.get('status','N/A')}")
    info("Finished: List Checks from API")

def list_file_domains():
    """Lists domains configured in the local file."""
    info("Starting: List Domains from File")
    domains = file_handler.load_domains()
    if not domains:
        info(f"No valid domains found in {config.DOMAIN_FILE}.")
        return
    info(f"Valid domains configured in {config.DOMAIN_FILE}:")
    for domain in domains:
        status = f"Status UUID: {domain['status_uuid'] or '(Not set)'}"
        expiry = f"Expiry UUID: {domain['expiry_uuid'] or '(Not set)'}"
        info(f"  - Domain: {domain['domain']:<30} {status} {expiry}")
    info("Finished: List Domains from File")
