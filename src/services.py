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
            error(f"  ✗ GoDaddy API Authentication/Authorization failed ({response.status_code}). Check API Key/Secret.")
            return None
        elif response.status_code == 429:
            warn(f"  ⚠ GoDaddy API rate limit hit while checking {domain}. Try again later.")
            return None

        response.raise_for_status() # Raise HTTPError for other bad responses (5xx, other 4xx)

        response_data = response.json()
        expiry_str = response_data.get('expires')

        if not expiry_str:
            warn(f"  ⚠ 'expires' field not found in GoDaddy API response for {domain}.")
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
            error(f"  ✗ Could not parse expiry date string '{expiry_str}' from GoDaddy API response for {domain}.")
            return None

    except requests.exceptions.Timeout:
        error(f"  ✗ GoDaddy API request timed out for {domain}")
    except requests.exceptions.RequestException as e:
        error(f"  ✗ GoDaddy API request error for {domain}: {e}")
        if e.response is not None:
            error(f"  GoDaddy API Response ({e.response.status_code}): {e.response.text}")
    except json.JSONDecodeError:
        error(f"  ✗ Failed to decode JSON response from GoDaddy API for {domain}.")
        debug(f"GoDaddy Raw Response: {response.text}")
    except Exception as e:
        error(f"  ✗ Unexpected error during GoDaddy API call for {domain}: {e}")

    return None # Indicate failure

def _parse_expiry_from_whois(whois_output):
    """
    Attempts to parse an expiry date from raw WHOIS output text.

    This function is designed to be robust against the highly inconsistent formatting
    of WHOIS records. It operates using a multi-stage process:

    1.  **Pattern Matching**: It iterates through a list of 3 primary regular
        expressions, ordered from most specific (e.g., ISO 8601 format) to most
        general (e.g., 'Key: Value'). This handles different labels like
        'Registry Expiry Date', 'expires', etc., and captures the potential
        date string. A debug log is generated for each successful match.

    2.  **Date Parsing**: For each string captured by a pattern, the function
        attempts to parse it using a list of 5 common date formats (e.g.,
        '%Y-%m-%d', '%d-%b-%Y'). It also includes a special check for UNIX
        timestamps.

    3.  **First Success Wins**: The function returns the *first* successfully
        parsed date. If a pattern matches a string that cannot be parsed, the
        function discards it and moves on to the next pattern, ensuring that
        a single malformed line does not cause the entire process to fail.

    If no pattern yields a parsable date after checking the entire WHOIS text,
    the function returns None.
    """
    if not whois_output:
        return None

    # Common patterns for expiry dates. More specific patterns should come first.
    patterns = [
        # Pattern for ISO 8601 format with 'Z' (e.g., 2025-10-22T04:00:00Z)
        r'(?:Registry Expiry Date|Expiration Date|Expiry Date|paid-till):\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)',
        # Pattern for dates like '31-Dec-2029'
        r'(?:expires|Expiry Date):\s*(\d{1,2}-[A-Za-z]{3}-\d{4})',
        # General pattern for various 'Key: Value' formats (YYYY-MM-DD, etc.)
        r'(?:Registry Expiry Date|Expiration Date|Expiry Date|paid-till|Expiration Time):\s*(\S+)'
    ]

    formats_to_try = [
        ('%Y-%m-%dT%H:%M:%SZ', True), # e.g., 2029-12-31T12:00:00Z
        ('%Y.%m.%d', False), # e.g., 2029.12.31
        ('%Y-%m-%d', False), # e.g., 2029-12-31
        ('%Y-%m-%d', False), # e.g., 2029-12-31
        ('%Y/%m/%d', False), # e.g., 2029/12/31
        ('%d/%m/%Y', False), # e.g., 31/12/2029
        ('%d-%m-%Y', False), # e.g., 31-12-2029
        ('%d-%b-%Y', False), # e.g., 31-Dec-2029
        ('%d %b %Y', False), # e.g., 31 Dec 2029
        ('%d %B %Y', False), # e.g., 31 December 2029
        ('%Y%m%d'  , False), # e.g., 20291231
        ('%Y.%m.%d %H:%M:%S', False), # e.g., 2029.12.31 12:00:00
        ('%Y-%m-%d %H:%M:%S', False), # e.g., 2029-12-31 12:00:00
    ]

    for pattern in patterns:
        match = re.search(pattern, whois_output, re.IGNORECASE)
        if not match:
            continue  # This pattern didn't find anything, move to the next.

        date_str = match.group(1).strip()

        # --- YOUR REQUESTED DEBUG LOG ---
        debug(f"Pattern '{pattern}' matched. Attempting to parse captured string: '{date_str}'")

        if not date_str:
            continue # No date string captured, skip to next pattern

        # Try UNIX timestamp first
        if date_str.isdigit() and len(date_str) in (10, 13):
            try:
                ts = int(date_str[:10])
                dt_aware = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                debug(f"Successfully parsed '{date_str}' as a UNIX timestamp.")
                return dt_aware
            except (ValueError, OSError):
                pass # Not a valid timestamp, proceed to other formats

        # Try string-based formats
        for fmt, _ in formats_to_try:
            try:
                dt_naive = datetime.datetime.strptime(date_str, fmt)
                dt_aware = dt_naive.replace(tzinfo=datetime.timezone.utc)
                # Success! We found a pattern and parsed it.
                debug(f"Successfully parsed '{date_str}' with format '{fmt}'.")
                return dt_aware
            except ValueError:
                # This format didn't work for this string, try the next format.
                continue

    # If we've exhausted all patterns and none yielded a parsable date:
    debug("No parsable expiry date found in WHOIS output after trying all patterns.")
    return None # Indicate failure


# You can also create a new function here to encapsulate the whois subprocess call
def run_whois(domain):
    """Runs the whois command and returns the output."""
    info(f"  → Running WHOIS for {domain}...")
    try:
        process = subprocess.run(['whois', domain], capture_output=True, text=True, check=False, timeout=30)
        if process.returncode != 0:
            error(f"  ✗ WHOIS command failed for {domain} with exit code {process.returncode}. Stderr: {process.stderr.strip()}")
            return None
        return process.stdout
    except FileNotFoundError:
        error(f"  ✗ WHOIS command not found. Please ensure 'whois' is installed and in PATH.")
    except subprocess.TimeoutExpired:
        error(f"  ✗ WHOIS command timed out for {domain}.")
    except Exception as e:
        error(f"  ✗ An unexpected error occurred during WHOIS execution for {domain}: {e}")
    return None
