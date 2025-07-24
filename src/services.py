# domain_checker/services.py
import subprocess
import datetime
import requests
import json
import re
from .config import GODADDY_API_KEY, GODADDY_API_URL, GODADDY_API_SECRET
from .logger import info, debug, error, warn

# Move these functions here:
# _get_expiry_from_godaddy(domain)
# _parse_expiry_from_whois(whois_output)

def _get_expiry_from_godaddy(domain):
    """Retrieves domain-healthcheck-cli expiry date from GoDaddy API."""
    if not GODADDY_API_KEY or not GODADDY_API_SECRET:
        debug(f"GoDaddy API Key/Secret not configured. Skipping GoDaddy lookup for {domain}.")
        return None

    url = f"{GODADDY_API_URL.rstrip('/')}/v1/domains/{domain}"
    headers = {
        'Authorization': f'sso-key {GODADDY_API_KEY}:{GODADDY_API_SECRET}',
        'Accept': 'application/json'
    }
    debug(f"Attempting GoDaddy API lookup for {domain} at {url}")

    try:
        response = requests.get(url, headers=headers, timeout=20) # Increased timeout slightly for API

        # Handle common errors
        if response.status_code == 404:
            info(f"  ℹ️ Domain {domain} not found in this GoDaddy account (API returned 404).")
            return None
        elif response.status_code == 401 or response.status_code == 403:
            error(f"  ❌ GoDaddy API Authentication/Authorization failed ({response.status_code}). Check API Key/Secret.")
            return None
        elif response.status_code == 429:
            warn(f"  ⚠️ GoDaddy API rate limit hit while checking {domain}. Try again later.")
            return None

        response.raise_for_status() # Raise HTTPError for other bad responses (5xx, other 4xx)

        response_data = response.json()
        expiry_str = response_data.get('expires')

        if not expiry_str:
            warn(f"  ⚠️ 'expires' field not found in GoDaddy API response for {domain}.")
            debug(f"GoDaddy Response Body: {response_data}")
            return None

        # Parse the ISO 8601 date string
        try:
            # Remove 'Z' and add timezone info for fromisoformat compatibility if needed
            if expiry_str.endswith('Z'):
                expiry_str = expiry_str[:-1] + '+00:00'
            dt_aware = datetime.datetime.fromisoformat(expiry_str)
            # Ensure it's UTC
            dt_aware_utc = dt_aware.astimezone(datetime.timezone.utc)
            return dt_aware_utc
        except ValueError:
            error(f"  ❌ Could not parse expiry date string '{expiry_str}' from GoDaddy API response for {domain}.")
            return None

    except requests.exceptions.Timeout:
        error(f"  ❌ GoDaddy API request timed out for {domain}")
    except requests.exceptions.RequestException as e:
        error(f"  ❌ GoDaddy API request error for {domain}: {e}")
        if e.response is not None:
            error(f"  GoDaddy API Response ({e.response.status_code}): {e.response.text}")
    except json.JSONDecodeError:
        error(f"  ❌ Failed to decode JSON response from GoDaddy API for {domain}.")
        debug(f"GoDaddy Raw Response: {response.text}")
    except Exception as e:
        error(f"  ❌ Unexpected error during GoDaddy API call for {domain}: {e}")

    return None # Indicate failure

def _parse_expiry_from_whois(whois_output):
    """Attempts to parse the expiry date from WHOIS output."""
    # Common patterns for expiry dates - add more as needed
    patterns = [
        # Handle the T...Z format specifically first
        r'(?:Registry Expiry Date|Expiration Date|Expiry Date|paid-till):\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)',
        # General patterns (capture value after the label)
        r'(?:Registry Expiry Date|Expiration Date|Expiry Date|paid-till):\s*(\S+)',
        r'expires:\s*(\S+)',
        r'Expiration Time:\s*(\S+)',
        # --- Add patterns for specific TLDs if known ---
        # Example for a hypothetical .de format if it was 'Changed: YYYYMMDD'
        # r'Changed:\s*(\d{8})',
        # Example for a hypothetical .nl format if it was 'expire date: YYYY-MM-DD'
        # r'expire date:\s*(\d{4}-\d{2}-\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, whois_output, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            # Try parsing common date formats (ISO, variations)
            # Prioritize formats often indicating UTC or specific structures
            formats_to_try = [
                ('%Y-%m-%dT%H:%M:%SZ', True), # Explicit UTC via Z
                ('%Y-%m-%d', False),
                ('%d-%b-%Y', False), # e.g., 01-Jan-2025
                ('%Y.%m.%d', False),
                ('%d/%m/%Y', False),
                ('%Y%m%d', False), # Example for YYYYMMDD from hypothetical 'Changed:'
                # Add other common formats if needed
            ]
            for fmt, is_explicit_utc in formats_to_try:
                try:
                    dt_naive = datetime.datetime.strptime(date_str, fmt)
                    # Make the datetime object timezone-aware (assuming UTC)
                    # WHOIS data is typically UTC, even if not explicitly marked.
                    # If the format explicitly indicated UTC ('Z'), we know it is.
                    # Otherwise, we assume it is.
                    dt_aware = dt_naive.replace(tzinfo=datetime.timezone.utc)
                    return dt_aware
                except ValueError:
                    continue
            warn(f"Could not parse matched WHOIS date string: '{date_str}' with known formats.")
            return None # Matched but couldn't parse

    debug("No expiry date pattern matched in WHOIS output.")
    return None # No pattern matched


# You can also create a new function here to encapsulate the whois subprocess call
def run_whois(domain):
    """Runs the whois command and returns the output."""
    info(f"  → Running WHOIS for {domain}...")
    try:
        process = subprocess.run(['whois', domain], capture_output=True, text=True, check=False, timeout=30)
        if process.returncode != 0:
            error(f"  ❌ WHOIS command failed for {domain} with exit code {process.returncode}. Stderr: {process.stderr.strip()}")
            return None
        return process.stdout
    except FileNotFoundError:
        error(f"  ❌ WHOIS command not found. Please ensure 'whois' is installed and in PATH.")
    except subprocess.TimeoutExpired:
        error(f"  ❌ WHOIS command timed out for {domain}.")
    except Exception as e:
        error(f"  ❌ An unexpected error occurred during WHOIS execution for {domain}: {e}")
    return None
