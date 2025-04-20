#!/usr/bin/env python3
import os
import subprocess
import datetime
import json
import requests
import re
import argparse
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv() # Loads environment variables from .env file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Get script directory

# --- Configuration (can be loaded from .env or command-line arguments) ---
API_URL = os.getenv("API_URL", "https://healthchecks.io/api/v3/")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://hc-ping.com")
DOMAIN_FILE = os.getenv("DOMAIN_FILE", os.path.join(SCRIPT_DIR, "domains.txt"))
MARKER_DIR = "/tmp/domain-hc-markers" # Default marker directory path
# Use script directory as a base path for domains.txt if not specified in environment

# Simple validation for API_KEY
if not API_KEY:
    print("ERROR: API_KEY environment variable not set. Please set it or create a .env file.")
    exit(1)

# --- Helper Functions ---
def log(level, message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    try:
        log_file = os.path.join(SCRIPT_DIR, "logs.log")
        with open(log_file, "a") as f:
            f.write(log_line + "\n")
    except IOError as e:
        print(f"Warning: Could not write to log file: {e}")

def info(message):  log("INFO", message)
def debug(message): log("DEBUG", message) # Consider adding a verbose flag to enable/disable debug logs
def warn(message):  log("WARN", message)
def error(message): log("ERROR", message)

def _make_api_request(method, endpoint, data=None, params=None):
    """Helper function for making API requests."""
    headers = {'X-Api-Key': API_KEY, 'Content-Type': 'application/json'}
    url = f"{API_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = requests.request(method, url, headers=headers, json=data, params=params, timeout=15)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        if method.upper() == 'DELETE':
            # Success for DELETE could be 204 No Content OR 200 OK with body
            if response.status_code == 204 or response.status_code == 200:
                # Check if there *is* content before trying to parse JSON
                if response.content:
                    try:
                        # Return the body if present (might be the deleted object)
                        # Or return a simple success indicator if parsing fails, but the status is ok
                        return response.json()
                    except json.JSONDecodeError:
                        debug(f"DELETE successful ({response.status_code}) but response body was not valid JSON for {url}")
                        return {"status": "success", "code": response.status_code} # Indicate success
                else:
                    # No content, typical 204 success
                    return None # Indicate success with no content
            else:
                # This case should be caught by raise_for_status, but safety check
                error(f"DELETE request failed with status code {response.status_code} for {url}")
                return None # Indicate failure explicitly

        # --- Handle GET/POST/PUT etc. ---
        # Check for empty content even for non-DELETE success codes if needed
        if not response.content:
            debug(f"Request successful ({response.status_code}) but no content returned for {method} {url}")
            # Decide what to return - None or an empty dict? None might be cleaner.
            return None
        # Try to parse JSON for other successful requests
        return response.json()

    except requests.exceptions.Timeout:
        error(f"API request timed out: {method} {url}")
    except requests.exceptions.RequestException as e:
        error(f"API request error: {method} {url} - {e}")
        if e.response is not None:
            error(f"API Response ({e.response.status_code}): {e.response.text}")
    return None # Indicate failure on exceptions

def create_healthcheck(domain, check_type):
    """Creates a status or expiry healthcheck for a given domain."""
    slug = re.sub(r'[^a-z0-9]+', '-', domain.lower()) # Generate a safe slug
    data = {
        'name': domain,
        'slug': f'{slug}-{check_type}',
        'unique': ['slug'], # Ensure slug uniqueness
        'tags': check_type, # Use single string (e.g., "status" or "expiry")
    }
    if check_type == 'status':
        data['tz'] = 'Europe/Istanbul'
        data['schedule'] = '*/5 * * * *' # 5-minute interval
        data['grace'] = 60  # 1-minute grace
    elif check_type == 'expiry':
        data['timeout'] = 3600 * 24 * 7 # 7-day timeout
        data['grace'] = 3600 * 24 # 1-day grace

    response_data = _make_api_request('POST', 'checks/', data=data)

    # --- Enhanced UUID Extraction ---
    if response_data:
        # Preferentially use the 'update_url' or 'ping_url' to extract UUID if present
        uuid = None
        for url_key in ['update_url', 'ping_url']:
            url_val = response_data.get(url_key)
            if url_val:
                match = re.search(r'/([a-f0-9-]+)(?:/|$)', url_val) # Look for UUID in the path
                if match:
                    uuid = match.group(1)
                    break # Found UUID

        if uuid:
            info(f"Successfully created {check_type} check for {domain} with UUID: {uuid}")
            return uuid
        else:
            # Fallback or error if UUID couldn't be extracted
            error(f"Could not extract UUID from successful API response for {check_type} check for {domain}. Response: {response_data}")
            return None
    else:
        # Error already logged by _make_api_request
        # error(f"Failed to create {check_type} check for {domain}. API response: {response_data}") # Redundant logging
        return None # API call failed or didn't return expected data

def load_domains_raw():
    """Loads raw lines and comments/blanks from the domain file."""
    lines_data = []
    try:
        with open(DOMAIN_FILE, 'r') as f:
            for idx, line in enumerate(f):
                lines_data.append({'line_num': idx + 1, 'raw_line': line.strip()})
    except FileNotFoundError:
        warn(f"Domains file '{DOMAIN_FILE}' not found.")
    except IOError:
        error(f"Could not read domains file '{DOMAIN_FILE}'.")
    return lines_data

def action_create_single_domain(domain_to_process):
    """
    Ensures healthchecks exist for a SINGLE specified domain and adds/updates
    its entry in the domain file.
    """
    info(f"Starting: Create Single Domain Checks for '{domain_to_process}'")
    raw_lines_data = load_domains_raw()
    processed_domains = []
    domain_found = False
    updated = False # Track if changes are needed for this specific domain

    target_status_uuid = None
    target_expiry_uuid = None
    target_is_subdomain = domain_to_process.count('.') > 1

    # Iterate through existing lines to find the domain and preserve others
    for line_data in raw_lines_data:
        original_line = line_data['raw_line']
        entry = {'type': 'comment_or_blank', 'content': original_line} # Default

        if original_line and not original_line.startswith('#'):
            parts = original_line.split()
            domain = parts[0]
            current_status_uuid = None
            current_expiry_uuid = None
            for part in parts[1:]:
                if part.startswith('s:'):
                    current_status_uuid = part.split(':', 1)[1]
                elif part.startswith('e:'):
                    current_expiry_uuid = part.split(':', 1)[1]

            entry = { # Store existing domain info
                'type': 'domain',
                'domain': domain,
                'status_uuid': current_status_uuid,
                'expiry_uuid': current_expiry_uuid
            }

            # Check if this is the domain we are looking for
            if domain == domain_to_process:
                domain_found = True
                info(f"Found existing entry for '{domain_to_process}'. Checking UUIDs...")
                target_status_uuid = current_status_uuid
                target_expiry_uuid = current_expiry_uuid

                # Create missing STATUS check
                if not target_status_uuid:
                    warn(f"Existing entry for '{domain_to_process}' is missing status UUID. Creating...")
                    new_status_uuid = create_healthcheck(domain_to_process, 'status')
                    if new_status_uuid:
                        target_status_uuid = new_status_uuid
                        entry['status_uuid'] = target_status_uuid # Update entry for rewrite
                        updated = True
                    else:
                        warn(f"Failed to create status check for '{domain_to_process}'.")

                # Create missing EXPIRY check (if applicable)
                if not target_expiry_uuid:
                    if target_is_subdomain:
                        info(f"Skipping EXPIRY check creation for apparent subdomain: {domain_to_process}")
                    elif target_status_uuid: # Only create if status is present
                        warn(f"Existing entry for '{domain_to_process}' is missing expiry UUID. Creating...")
                        new_expiry_uuid = create_healthcheck(domain_to_process, 'expiry')
                        if new_expiry_uuid:
                            target_expiry_uuid = new_expiry_uuid
                            entry['expiry_uuid'] = target_expiry_uuid # Update entry for rewrite
                            updated = True
                        else:
                            warn(f"Failed to create expiry check for '{domain_to_process}'.")
                    else:
                        warn(f"Skipping expiry check creation for '{domain_to_process}' because status check is missing or failed.")

        processed_domains.append(entry) # Add the processed/preserved line

    # If the domain was not found in the file, create checks and add it
    if not domain_found:
        info(f"Domain '{domain_to_process}' not found in {DOMAIN_FILE}. Creating new entry...")
        target_status_uuid = create_healthcheck(domain_to_process, 'status')
        if target_status_uuid:
            updated = True # Need to write the new entry
            if not target_is_subdomain:
                target_expiry_uuid = create_healthcheck(domain_to_process, 'expiry')
                if target_expiry_uuid:
                    updated = True
                else:
                    warn(f"Failed to create expiry check for new domain '{domain_to_process}'.")
            else:
                info(f"Skipping EXPIRY check creation for new apparent subdomain: {domain_to_process}")

            # Add the new domain entry to the list for writing
            processed_domains.append({
                'type': 'domain',
                'domain': domain_to_process,
                'status_uuid': target_status_uuid,
                'expiry_uuid': target_expiry_uuid
            })
        else:
            error(f"Failed to create initial status check for new domain '{domain_to_process}'. Cannot add to file.")


    # Rewrite the file only if changes were made or a new domain was added
    if updated:
        info(f"Rewriting {DOMAIN_FILE} for domain '{domain_to_process}'...")
        try:
            with open(DOMAIN_FILE, 'w') as outfile:
                for entry in processed_domains:
                    if entry['type'] == 'comment_or_blank':
                        outfile.write(entry['content'] + "\n")
                    elif entry['type'] == 'domain':
                        line_parts = [entry['domain']]
                        if entry['status_uuid']: line_parts.append(f"s:{entry['status_uuid']}")
                        if entry['expiry_uuid']: line_parts.append(f"e:{entry['expiry_uuid']}")
                        outfile.write(" ".join(line_parts) + "\n")
            info(f"Successfully updated {DOMAIN_FILE} for '{domain_to_process}'.")
        except IOError as e:
            error(f"Failed to rewrite {DOMAIN_FILE}: {e}")
    else:
        info(f"No updates needed or creation failed for '{domain_to_process}'. File not changed.")

    info(f"Finished: Create Single Domain Checks for '{domain_to_process}'")

def action_create_domain_checks_from_file():
    """
    Reads the domain file, creates missing healthchecks (status for all, expiry only for non-subdomains),
    and rewrites the file with updated info.
    (Processes ENTIRE file)
    """
    info("Starting: Create Domain Checks (Processing File)")
    raw_lines_data = load_domains_raw()
    if not raw_lines_data:
        info("Domain file is empty or not found. Nothing to create.")
        return

    processed_domains = [] # Store results for rewriting the file
    updated = False # Flag to track if any changes were made

    for line_data in raw_lines_data:
        line_num = line_data['line_num']
        original_line = line_data['raw_line']

        # Preserve comments and blank lines
        if not original_line or original_line.startswith('#'):
            processed_domains.append({'type': 'comment_or_blank', 'content': original_line})
            continue

        # Try parsing the line
        parts = original_line.split()
        domain = parts[0]
        current_status_uuid = None
        current_expiry_uuid = None

        if len(parts) < 1: # Should not happen if not blank/comment, but safety checks
            warn(f"Skipping malformed line {line_num}: '{original_line}'")
            processed_domains.append({'type': 'comment_or_blank', 'content': f"# Skipped malformed line: {original_line}"})
            continue

        # Extract existing UUIDs if present
        for part in parts[1:]:
            if part.startswith('s:'):
                current_status_uuid = part.split(':', 1)[1]
            elif part.startswith('e:'):
                current_expiry_uuid = part.split(':', 1)[1]

        # --- Create missing STATUS check (always attempt if missing) ---
        new_status_uuid = None
        if not current_status_uuid:
            warn(f"Domain '{domain}' (line {line_num}) is missing status UUID. Creating...")
            new_status_uuid = create_healthcheck(domain, 'status')
            if new_status_uuid:
                current_status_uuid = new_status_uuid # Update with the new UUID
                updated = True
            else:
                warn(f"Failed to create status check for '{domain}'. It will remain without a status UUID in the file.")

        # --- Create missing EXPIRY check (only if needed AND not a subdomain) ---
        new_expiry_uuid = None
        if not current_expiry_uuid:
            # Determine if it's a subdomain (adjust the dot count threshold if needed)
            is_subdomain = domain.count('.') > 1 # More than 2 dots

            if is_subdomain:
                info(f"Skipping EXPIRY check creation for apparent subdomain: {domain} (line {line_num})")
                # Ensure current_expiry_uuid remains None or empty
                current_expiry_uuid = None
            elif current_status_uuid: # Only create expiry if status is present (newly created or existing)
                warn(f"Domain '{domain}' (line {line_num}) is missing expiry UUID and is not a subdomain. Creating...")
                new_expiry_uuid = create_healthcheck(domain, 'expiry')
                if new_expiry_uuid:
                    current_expiry_uuid = new_expiry_uuid # Update with the new UUID
                    updated = True
                else:
                    warn(f"Failed to create expiry check for '{domain}'. It will remain without an expiry UUID.")
            else:
                # Status check creation failed or was missing, so don't create expiry either
                warn(f"Skipping expiry check creation for '{domain}' because status check creation failed or was missing.")
                current_expiry_uuid = None


        # Store the final state for this domain for rewriting
        processed_domains.append({
            'type': 'domain',
            'domain': domain,
            'status_uuid': current_status_uuid,
            'expiry_uuid': current_expiry_uuid # This will be None if skipped/failed
        })

    # --- Rewrite the entire domain file ---
    if updated:
        info(f"Rewriting {DOMAIN_FILE} with updated UUIDs...")
        try:
            with open(DOMAIN_FILE, 'w') as outfile:
                for entry in processed_domains:
                    if entry['type'] == 'comment_or_blank':
                        outfile.write(entry['content'] + "\n")
                    elif entry['type'] == 'domain':
                        line_parts = [entry['domain']]
                        # Only add s: if status_uuid exists
                        if entry['status_uuid']:
                            line_parts.append(f"s:{entry['status_uuid']}")
                        else:
                            warn(f"Note: Domain '{entry['domain']}' ended up without a status UUID in the final output.")
                        # Only add e: if expiry_uuid exists
                        if entry['expiry_uuid']:
                            line_parts.append(f"e:{entry['expiry_uuid']}")
                        outfile.write(" ".join(line_parts) + "\n")
            info(f"Successfully rewrote {DOMAIN_FILE}.")
        except IOError as e:
            error(f"Failed to rewrite {DOMAIN_FILE}: {e}")
            error("Please check file permissions and disk space.")
            error("Original file might be unchanged, or partially written.")
    else:
        info("No new UUIDs were successfully created or file structure changes needed. Domain file remains unchanged.")

    info("Finished: Create Domain Checks (Processing File)")


# --- Other action_ functions (check_domains, remove_unused, etc.) ---
# Need to be reviewed to ensure they use the corrected load_domains or handle
# potential missing UUIDs gracefully if create failed previously.
# For now, assuming they work with the output of the corrected load_domains.

# --- load_domains (keep the original one for other commands) ---
def load_domains():
    """Loads domain configurations from the DOMAIN_FILE, skipping invalid."""
    domains = []
    try:
        with open(DOMAIN_FILE, 'r') as f:
            for idx, line in enumerate(f):
                line_num = idx + 1
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    # --- Change: Require at least domain and s:uuid ---
                    if len(parts) >= 2 and any(p.startswith('s:') for p in parts):
                        domain = parts[0]
                        status_uuid = None
                        expiry_uuid = None
                        for part in parts[1:]:
                            if part.startswith('s:'):
                                status_uuid = part.split(':', 1)[1]
                            elif part.startswith('e:'):
                                expiry_uuid = part.split(':', 1)[1]

                        # If status_uuid is somehow still None after check above, something is wrong
                        if not status_uuid:
                             warn(f"Internal inconsistency on line {line_num} parsing: '{line}'. Skipping.")
                             continue

                        domains.append({'domain': domain, 'status_uuid': status_uuid, 'expiry_uuid': expiry_uuid or ""})
                    else:
                         # Warn if the line has content but not the required s:uuid
                         warn(f"Skipping invalid line {line_num}: '{line}' in {DOMAIN_FILE}. Expected format: domain s:<uuid> [e:<uuid>]")

    except FileNotFoundError:
        warn(f"Domains file '{DOMAIN_FILE}' not found. No domains loaded.")
    except IOError as e:
        error(f"Could not read domains file '{DOMAIN_FILE}': {e}")
    return domains

def action_sync_file():
    """
    Synchronizes the local domain file with the API.
    1. Removes UUIDs from file entries if they no longer exist in the API.
    2. Adds new entries to the file for checks found in the API but not in the file.
    """
    info("Starting: Sync Domain File with API (Add Missing)")

    # 1. Get all existing check details from the API
    all_checks_details = get_all_healthchecks_details()
    if all_checks_details is None: # Check if API call failed critically
        error("Failed to retrieve checks from API. Aborting sync.")
        return

    # Create a set of UUIDs and a dict mapping UUID to details for easy lookup
    api_uuid_set = set()
    api_checks_dict = {}
    if isinstance(all_checks_details, list):
        try:
            for check in all_checks_details:
                if isinstance(check, dict) and 'uuid' in check:
                    uuid = check['uuid']
                    api_uuid_set.add(uuid)
                    api_checks_dict[uuid] = check # Store full details
                else:
                    warn(f"Unexpected item format in API check details: {check}")
        except TypeError as e:
            error(f"Error processing API check details list: {e}")
            return
    else:
        error("API check details are not in the expected list format. Aborting sync.")
        return

    info(f"Found {len(api_uuid_set)} check UUIDs via API.")

    # 2. Read the raw local file content and process existing entries
    raw_lines_data = load_domains_raw()
    processed_file_entries = [] # Stores final lines (comments, validated domains)
    file_needs_update = False # Track if file content changes
    used_api_uuids_from_file = set() # Track UUIDs mentioned in the file

    if not raw_lines_data:
        info("Local domain file is empty or not found.")
        # Proceed to potentially add all API checks if the file was missing/empty

    for line_data in raw_lines_data:
        line_num = line_data['line_num']
        original_line = line_data['raw_line']
        entry_type = 'comment_or_blank'
        entry_content = original_line
        final_domain = None
        final_status_uuid = None
        final_expiry_uuid = None

        if original_line and not original_line.startswith('#'):
            entry_type = 'domain'
            parts = original_line.split()
            domain = parts[0]
            current_status_uuid = None
            current_expiry_uuid = None

            for part in parts[1:]:
                if part.startswith('s:'):
                    current_status_uuid = part.split(':', 1)[1]
                elif part.startswith('e:'):
                    current_expiry_uuid = part.split(':', 1)[1]

            final_domain = domain # Keep the domain name

            # Validate Status UUID
            if current_status_uuid:
                if current_status_uuid in api_uuid_set:
                    final_status_uuid = current_status_uuid # Keep it
                    used_api_uuids_from_file.add(current_status_uuid) # Mark as used
                else:
                    warn(f"Sync: Status UUID '{current_status_uuid}' for domain '{domain}' (line {line_num}) not found in API. Removing.")
                    file_needs_update = True # Mark file for rewrite

            # Validate Expiry UUID
            if current_expiry_uuid:
                if current_expiry_uuid in api_uuid_set:
                    final_expiry_uuid = current_expiry_uuid # Keep it
                    used_api_uuids_from_file.add(current_expiry_uuid) # Mark as used
                else:
                    warn(f"Sync: Expiry UUID '{current_expiry_uuid}' for domain '{domain}' (line {line_num}) not found in API. Removing.")
                    file_needs_update = True # Mark file for rewrite

            # Check if the original line changed due to UUID removal
            original_parts_set = set(parts[1:])
            final_parts_list = []
            if final_status_uuid: final_parts_list.append(f"s:{final_status_uuid}")
            if final_expiry_uuid: final_parts_list.append(f"e:{final_expiry_uuid}")
            if set(final_parts_list) != original_parts_set:
                file_needs_update = True # Content changed

        # Store the processed/validated data for this line
        processed_file_entries.append({
            'type': entry_type,
            'content': entry_content, # Store original line for comments/blanks for now
            'domain': final_domain,
            'status_uuid': final_status_uuid,
            'expiry_uuid': final_expiry_uuid
        })

    # 3. Identify API checks missing from the file
    missing_api_uuids = api_uuid_set - used_api_uuids_from_file
    info(f"Found {len(missing_api_uuids)} check UUIDs in API but not in the local file.")

    newly_added_entries = []
    if missing_api_uuids:
        file_needs_update = True # Mark file for rewrite if adding new entries
        info("Attempting to add missing checks to the file...")

        # Group missing checks by their 'name' field to combine status/expiry
        missing_checks_by_name = defaultdict(lambda: {'status_uuid': None, 'expiry_uuid': None, 'details': []})

        for uuid in missing_api_uuids:
            check_details = api_checks_dict.get(uuid)
            if not check_details:
                warn(f"Could not find details for missing API UUID '{uuid}'. Skipping add.")
                continue

            domain_name = check_details.get('name')
            tags = check_details.get('tags', '') # API returns space-separated string

            if not domain_name:
                warn(f"API Check UUID '{uuid}' has no name. Skipping add.")
                continue

            missing_checks_by_name[domain_name]['details'].append(check_details) # Store details if needed later
            if 'status' in tags.split():
                if missing_checks_by_name[domain_name]['status_uuid']:
                    warn(f"Multiple 'status' checks found for name '{domain_name}' in missing API checks (UUIDs: {missing_checks_by_name[domain_name]['status_uuid']}, {uuid}). Using first found.")
                else:
                    missing_checks_by_name[domain_name]['status_uuid'] = uuid
            elif 'expiry' in tags.split():
                if missing_checks_by_name[domain_name]['expiry_uuid']:
                    warn(f"Multiple 'expiry' checks found for name '{domain_name}' in missing API checks (UUIDs: {missing_checks_by_name[domain_name]['expiry_uuid']}, {uuid}). Using first found.")
                else:
                    missing_checks_by_name[domain_name]['expiry_uuid'] = uuid
            else:
                warn(f"Missing API Check UUID '{uuid}' (Name: '{domain_name}') has unexpected tags: '{tags}'. Treating as status for now.")
                # Default to status if tags are non-standard, or handle differently
                if not missing_checks_by_name[domain_name]['status_uuid']:
                    missing_checks_by_name[domain_name]['status_uuid'] = uuid


        # Create the new entries to be added to the file
        added_count = 0
        for domain_name, uuids in sorted(missing_checks_by_name.items()): # Sort by name
            if not uuids['status_uuid'] and not uuids['expiry_uuid']:
                warn(f"Could not assign type (status/expiry) for checks associated with name '{domain_name}'. Skipping add.")
                continue

            info(f"  + Adding entry for '{domain_name}' (Status: {uuids['status_uuid'] or 'N/A'}, Expiry: {uuids['expiry_uuid'] or 'N/A'})")
            newly_added_entries.append({
                'type': 'domain',
                'domain': domain_name,
                'status_uuid': uuids['status_uuid'],
                'expiry_uuid': uuids['expiry_uuid']
            })
            added_count += 1
        info(f"Prepared {added_count} new entries to add.")


    # 4. Rewrite the file ONLY if changes were detected (validation or adds)
    if file_needs_update:
        info(f"Rewriting {DOMAIN_FILE} with synchronised data...")
        try:
            with open(DOMAIN_FILE, 'w') as outfile:
                # Write validated original entries first
                for entry in processed_file_entries:
                    if entry['type'] == 'comment_or_blank':
                        outfile.write(entry['content'] + "\n")
                    elif entry['type'] == 'domain':
                        line_parts = [entry['domain']]
                        if entry['status_uuid']: line_parts.append(f"s:{entry['status_uuid']}")
                        if entry['expiry_uuid']: line_parts.append(f"e:{entry['expiry_uuid']}")
                        # Avoid writing lines with only domain if both UUIDs were removed and not re-added
                        if len(line_parts) > 1:
                            outfile.write(" ".join(line_parts) + "\n")
                        else:
                            warn(f"Skipping write for '{entry['domain']}' as both UUIDs were invalid and removed.")

                # Append the newly identified entries
                if newly_added_entries:
                    outfile.write("\n# --- Checks Added by Sync Command ---\n")
                    for entry in newly_added_entries:
                        line_parts = [entry['domain']]
                        if entry['status_uuid']: line_parts.append(f"s:{entry['status_uuid']}")
                        if entry['expiry_uuid']: line_parts.append(f"e:{entry['expiry_uuid']}")
                        outfile.write(" ".join(line_parts) + "\n")

            info(f"Successfully synchronized {DOMAIN_FILE}.")
        except IOError as e:
            error(f"Failed to rewrite {DOMAIN_FILE} during sync: {e}")
            error("Please check file permissions and disk space.")
    else:
        info("No inconsistencies found or missing checks to add. File remains unchanged.")

    info("Finished: Sync Domain File with API (Add Missing)")
def check_domain_status(domain, status_uuid):
    """Checks website status and pings the status healthcheck."""
    info(f"Checking status for {domain}...")
    # TODO 1: Change verify=False to True
    try:
        response = requests.get(f"https://{domain}", timeout=10, allow_redirects=True, verify=False, headers={'User-Agent': 'domain-hc-script/1.0'})
        status_code = response.status_code
        if 200 <= status_code < 400:
            ping_healthcheck(status_uuid)
            info(f"  ✓ Status: up (HTTP {status_code})")
        else:
            ping_healthcheck(status_uuid, "/fail", payload=f"status={status_code}")
            error(f"  ✗ Status: down/error (HTTP {status_code})")
    except requests.exceptions.Timeout:
        ping_healthcheck(status_uuid, "/fail", payload="status=timeout")
        error("  ✗ Status check timed out")
    except requests.exceptions.SSLError:
        ping_healthcheck(status_uuid, "/fail", payload="status=ssl_error")
        error("  ✗ SSL Error")
    except requests.exceptions.ConnectionError:
        ping_healthcheck(status_uuid, "/fail", payload="status=connection_error")
        error("  ✗ Connection Error")
    except requests.exceptions.RequestException:
        ping_healthcheck(status_uuid, "/fail", payload="status=request_error")
        error("  ✗ Request Error")

def action_check_domains():
    """Runs status and expiry checks for all configured domains."""
    info("Starting: Check Domains")
    domains = load_domains() # Uses the version that skips invalid lines
    if not domains:
        warn("No valid domains loaded to check.")
        return
    for domain_data in domains:
        info(f"--- Processing {domain_data['domain']} ---")
        # This call will now work because the function is defined
        check_domain_status(domain_data['domain'], domain_data['status_uuid'])
        if domain_data.get('expiry_uuid'): # Check if expiry UUID exists and is not empty
            check_domain_expiry(domain_data['domain'], domain_data['expiry_uuid'])
        else:
            debug(f"Skipping expiry check for {domain_data['domain']} (no expiry UUID configured).")
    info("Finished: Check Domains")

def action_remove_single_domain(domain_to_remove, force=False):
    """
    Removes checks associated with a specific domain name from the API
    and removes the corresponding line from the local domain file.
    """
    info(f"Starting: Remove Single Domain '{domain_to_remove}'")

    # 1. Find associated UUIDs from the API (based on name)
    all_checks_details = get_all_healthchecks_details()
    if all_checks_details is None:
        error("Failed to retrieve checks from API. Cannot determine which checks to remove.")
        return

    uuids_to_delete = []
    checks_to_delete_info = [] # For logging
    for check in all_checks_details:
        # Ensure check is a dict and has 'name' and 'uuid'
        if isinstance(check, dict) and check.get('name') == domain_to_remove and 'uuid' in check:
            uuids_to_delete.append(check['uuid'])
            checks_to_delete_info.append(f"UUID: {check['uuid']}, Tags: [{check.get('tags', '')}]")

    proceed_with_api_delete = False # Default
    if not uuids_to_delete:
        info(f"No active checks found in API with name '{domain_to_remove}'. Checking file...")
        # Proceed to check and potentially remove from the file anyway
    else:
        info(f"Found {len(uuids_to_delete)} checks in API matching name '{domain_to_remove}':")
        for info_line in checks_to_delete_info:
            print(f"  - {info_line}") # Use print directly, not log, for multi-line info

        if not force:
            confirm = input(f"Proceed with deleting these {len(uuids_to_delete)} checks from the API? Type 'YES' to confirm: ")
            if confirm == 'YES':
                proceed_with_api_delete = True
            else:
                info("API deletion cancelled.")
        else:
            warn(f"Executing 'remove {domain_to_remove}' with --force flag. Bypassing API deletion confirmation!")
            proceed_with_api_delete = True # Force flag bypasses prompt

        if proceed_with_api_delete:
            deleted_count = 0
            failed_count = 0
            info("Deleting checks from API...")
            for uuid in uuids_to_delete:
                if delete_healthcheck(uuid):
                    deleted_count += 1
                else:
                    failed_count += 1
            info(f"API Deletion Result: {deleted_count} successful, {failed_count} failed.")
            if failed_count > 0:
                warn("Some API deletions failed. The domain might remain partially in the file.")

    # 2. Remove the domain line(s) from the local file
    raw_lines_data = load_domains_raw()
    if not raw_lines_data:
        info("Local domain file is empty or not found. No file update needed.")
        info(f"Finished: Remove Single Domain '{domain_to_remove}'")
        return

    processed_file_entries = []
    found_in_file = False
    removed_from_file = False

    for line_data in raw_lines_data:
        original_line = line_data['raw_line']
        keep_line = True

        if original_line and not original_line.startswith('#'):
            parts = original_line.split()
            domain_in_line = parts[0]
            if domain_in_line == domain_to_remove:
                info(f"Removing line for '{domain_to_remove}' from {DOMAIN_FILE}: '{original_line}'")
                keep_line = False
                found_in_file = True
                removed_from_file = True

        if keep_line:
            processed_file_entries.append(original_line) # Keep original line string

    if not found_in_file:
        info(f"Domain '{domain_to_remove}' was not found in {DOMAIN_FILE}.")

    if removed_from_file:
        info(f"Rewriting {DOMAIN_FILE} without '{domain_to_remove}'...")
        try:
            with open(DOMAIN_FILE, 'w') as outfile:
                for line in processed_file_entries:
                    outfile.write(line + "\n")
            info(f"Successfully updated {DOMAIN_FILE}.")
        except IOError as e:
            error(f"Failed to rewrite {DOMAIN_FILE}: {e}")
    elif found_in_file:
        # This case shouldn't happen with current logic but is a safety net
        warn("Domain was found in file but removal logic failed. File not changed.")
    else:
        info("No changes needed for the domain file.")

    info(f"Finished: Remove Single Domain '{domain_to_remove}'")

def action_remove_all_checks(force=False):
    """Removes ALL healthchecks from the account and clears the domain file."""
    info("Starting: Remove ALL Checks")
    if not force:
        confirm = input("WARNING: This will delete ALL healthchecks on the account associated with the API key and clear the domains file. Type 'YES' to confirm: ")
        if confirm != 'YES':
            info("Operation cancelled.")
            return
    else:
        warn("Executing 'remove --all' with --force flag. Bypassing confirmation!")

    all_checks_details = get_all_healthchecks_details()
    deleted_count = 0
    failed_count = 0
    if not all_checks_details:
        info("No healthchecks found to delete.")
    else:
        info(f"Deleting {len(all_checks_details)} healthchecks...")
        for check in all_checks_details:
            uuid = check['uuid']
            info(f"  - Attempting delete: {uuid} (Name: {check.get('name', 'N/A')})")
            if delete_healthcheck(uuid):
                deleted_count += 1
            else:
                failed_count += 1
        info(f"Finished deletions: {deleted_count} successful, {failed_count} failed.")

    # Clear the domain file (keeping comments if desired, or completely empty)
    try:
        with open(DOMAIN_FILE, "w") as f:
            f.write("# Domain file cleared by remove-all command\n")
            f.write("# Add new domains in the format: example.com s:<status_uuid> e:<expiry_uuid>\n")
        info(f"Cleared domain entries in {DOMAIN_FILE}")
    except IOError:
        error(f"Could not clear domains file '{DOMAIN_FILE}'.")
        error("Please check file permissions and disk space.")
        error("Original file might be unchanged, or partially written.")
    info("Finished: Remove ALL Checks")


def action_remove_unused_checks():
    """Removes healthchecks that are not listed in the domain file."""
    info("Starting: Remove Unused Checks")
    all_checks_details = get_all_healthchecks_details()
    if not all_checks_details:
        info("No healthchecks found on the account. Nothing to remove.")
        return

    all_api_uuids = {check['uuid'] for check in all_checks_details}
    debug(f"Found {len(all_api_uuids)} checks via API.")

    # Use the load_domains that skips invalid lines, as only valid entries count
    domains = load_domains()
    used_uuids = set()
    for d in domains:
        if d.get('status_uuid'):
            used_uuids.add(d['status_uuid'])
        if d.get('expiry_uuid'):
            used_uuids.add(d['expiry_uuid'])
    debug(f"Found {len(used_uuids)} used UUIDs from valid entries in {DOMAIN_FILE}.")

    unused_uuids = all_api_uuids - used_uuids
    deleted_count = 0
    if not unused_uuids:
        info("No unused checks found.")
    else:
        info(f"Found {len(unused_uuids)} unused checks to delete:")
        for uuid in unused_uuids:
             check_info = next((c for c in all_checks_details if c['uuid'] == uuid), None)
             if check_info:
                 info(f"  - Deleting unused check: {uuid} (Name: {check_info.get('name', 'N/A')}, Tags: {check_info.get('tags', 'N/A')})")
             else:
                 info(f"  - Deleting unused check: {uuid}")
             delete_healthcheck(uuid)
             deleted_count += 1
        info(f"Deleted {deleted_count} unused checks.")
    info("Finished: Remove Unused Checks")

# --- Helper Functions needed by other actions ---
def delete_healthcheck(uuid):
    """Deletes a healthcheck by its UUID."""
    if not uuid:
        warn("Skipping deletion: No UUID provided.")
        return False # Indicate failure

    response_data = _make_api_request('DELETE', f'checks/{uuid}')

    # Success is indicated if _make_api_request didn't return None AND didn't log an error.
    # The returned data itself (the deleted object) is confirmation of success here.
    # We rely on _make_api_request logging errors if the status code was bad.
    if response_data is not None: # Hypothetically check if needed
        # Log success based on receiving a response (or None for 204) without prior error logs
        info(f"Deletion API call for healthcheck {uuid} appears successful.")
        # Optionally, log the details if needed for confirmation:
        # if response_data:
        #     debug(f"API returned deleted object details: {response_data}")
        return True
    else:
        # An error should have already been logged by _make_api_request
        error(f"Deletion failed for healthcheck {uuid}.")
        return False # Indicate failure

# In this refined version, we simplify: if _make_api_request returns anything
# (including the deleted object) or None (for 204) WITHOUT having logged an error
# (due to raise_for_status), we consider it a success for this function.
# A more complex state tracking could be added if needed.

def get_all_healthchecks_details():
    """Retrieves details for all healthchecks."""
    response_data = _make_api_request('GET', 'checks/')
    return response_data.get('checks', []) if response_data else []

def ping_healthcheck(uuid, endpoint_suffix="", payload=None):
    """Pings a healthcheck endpoint (success, fail, log, start). Uses POST if payload is present."""
    if not uuid:
        warn(f"Skipping ping: No UUID provided (suffix: {endpoint_suffix})")
        return
    # Ensure BASE_URL is properly configured
    if not BASE_URL or not BASE_URL.startswith(('http://', 'https://')):
        error(f"Invalid BASE_URL configured: '{BASE_URL}'. Cannot ping.")
        return

    ping_url = f"{BASE_URL.rstrip('/')}/{uuid}{endpoint_suffix}"
    # Start with base headers, modify within the block if needed
    headers = {'User-Agent': 'domain-hc-script/1.0'}
    try:
        # --- Determine method based on payload presence first ---
        if payload:
            method = 'POST'
        else:
            # No payload, use POST only if suffix exists (fail, log, etc.)
            method = 'POST' if endpoint_suffix else 'GET'

        # Use separate args for requests.request
        request_args = {'headers': headers, 'timeout': 10}

        if method == 'POST' and payload:
            # Set Content-Type and data for POST with payload
            request_args['headers']['Content-Type'] = 'application/x-www-form-urlencoded'
            request_args['data'] = payload # Send the raw string payload

        # Make the request using the constructed arguments
        response = requests.request(method, url=ping_url, **request_args)
        response.raise_for_status()
        # Debug log shows method used
        debug(f"Ping successful ({method}): {ping_url} (Payload: {payload})")
    except requests.exceptions.RequestException as e:
        error(f"Ping failed ({method}): {ping_url} - {e}")

def _parse_whois_expiry(whois_output):
    """Attempts to parse the expiry date from WHOIS output."""
    # Common patterns for expiry dates - add more as needed
    patterns = [
        # Handle the T...Z format specifically first
        r'(?:Registry Expiry Date|Expiration Date|Expiry Date|paid-till):\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)',
        # General patterns (capture value after the label)
        r'(?:Registry Expiry Date|Expiration Date|Expiry Date|paid-till):\s*(\S+)',
        r'expires:\s*(\S+)',
        r'Expiration Time:\s*(\S+)'
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
                ('%d-%b-%Y', False),
                ('%Y.%m.%d', False),
                ('%d/%m/%Y', False),
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
            warn(f"Could not parse matched date string: '{date_str}' with known formats.")
            return None # Matched but couldn't parse

    debug("No expiry date pattern matched in WHOIS output.")
    return None # No pattern matched

def check_domain_expiry(domain, expiry_uuid):
    """Checks domain expiry using WHOIS and pings the expiry healthcheck. Skips WHOIS for subdomains."""
    info(f"Checking expiry for {domain}...")

    # --- Subdomain Check ---
    # Skip WHOIS if there are more than 1 dot (e.g., test.domain.com)
    # Adjust this threshold if needed (e.g., > 2 for domain.co.uk handling)
    is_subdomain = domain.count('.') > 1
    if is_subdomain:
        info(f"  ↪ Skipping WHOIS lookup for apparent subdomain: {domain}")
        # Ping success to keep the check alive on Healthchecks.io, but note it was skipped
        ping_healthcheck(expiry_uuid, payload="status=skipped_subdomain")
        # We don't need marker logic for skipped subdomains as no check is performed
        return # Exit the function early
    # --- End Subdomain Check ---

    # Marker file logic to avoid checking *root* domains too frequently
    marker_file = os.path.join(MARKER_DIR, f"expiry_check_{re.sub(r'[^a-zA-Z0-9.-]+', '_', domain)}") # Allow `.` and `-`
    seven_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7) # Use UTC now

    try:
        os.makedirs(MARKER_DIR, exist_ok=True) # Ensure marker directory exists
        if os.path.exists(marker_file):
            try:
                marker_timestamp = os.path.getmtime(marker_file)
                # Convert marker timestamp to UTC datetime object
                marker_time = datetime.datetime.fromtimestamp(marker_timestamp, datetime.timezone.utc)
                if marker_time >= seven_days_ago:
                    info(f"  ↻ Expiry check skipped (within last 7 days based on marker {marker_time.strftime('%Y-%m-%d %H:%M:%S %Z')}) for {domain}.")
                    # ping_healthcheck(expiry_uuid)
                    return
            except Exception as e:
                warn(f"Could not read or interpret marker file timestamp for {marker_file}: {e}")
                # Proceed with check if marker reading fails
    except OSError as e:
        error(f"Could not create/access marker directory {MARKER_DIR}: {e}")
        # Decide whether to continue without marker logic or fail
        # If we can't use markers, mayaction_delete_markersbe we should still proceed, but log it?
        # For now, let's proceed, but it won't update the marker later.
        pass # Continue the check

    # --- WHOIS Execution ---
    try:
        info(f"  → Running WHOIS for {domain}...")
        # Explicitly capture output as text, handle potential errors
        process = subprocess.run(['whois', domain], capture_output=True, text=True, check=False, timeout=30) # Added timeout

        if process.returncode != 0:
            # WHOIS command failed
            error(f"  ❌ WHOIS command failed for {domain} with exit code {process.returncode}. Stderr: {process.stderr.strip()}")
            ping_healthcheck(expiry_uuid + "/fail", payload=f"stderr={process.stderr.strip()}") # Ping fail
            return # Don't proceed further if WHOIS fails

        whois_output = process.stdout
        debug(f"WHOIS output for {domain}:\n{whois_output[:500]}...") # Log truncated output

        # --- Expiry Parsing ---
        expiry_date = _parse_whois_expiry(whois_output)

        if expiry_date:
            info(f"  ✓ Parsed Expiry Date for {domain}: {expiry_date.strftime('%Y-%m-%d')}")
            now = datetime.datetime.now(datetime.timezone.utc)
            time_until_expiry = expiry_date - now

            # Check if expiry is within 30 days (configurable threshold)
            if time_until_expiry <= datetime.timedelta(days=30):
                warn(f"  ⚠️ Domain {domain} expires soon! ({time_until_expiry.days} days)")
                # Consider pinging fail or a specific endpoint if expiring soon
                ping_healthcheck(expiry_uuid + "/fail", payload=f"status=expiring_soon&days_left={time_until_expiry.days}")
            else:
                info(f"  ✓ Domain {domain} expiry is OK ({time_until_expiry.days} days remaining).")
                ping_healthcheck(expiry_uuid, payload=f"status=ok&days_left={time_until_expiry.days}") # Ping success

            # --- Update Marker File ---
            try:
                # Create or update the marker file timestamp
                with open(marker_file, 'w') as f:
                    f.write(datetime.datetime.now(datetime.timezone.utc).isoformat()) # Write timestamp
                info(f"  ✓ Updated marker file: {marker_file}")
            except IOError as e:
                error(f"  ❌ Failed to write marker file {marker_file}: {e}")
                # Ping failure if marker update fails? Or just log? Let's log for now.

        else:
            # Expiry date could not be parsed
            error(f"  ❌ Could not parse expiry date for {domain} from WHOIS output.")
            ping_healthcheck(expiry_uuid + "/fail", payload="status=parsing_failed") # Ping fail

    except FileNotFoundError:
        error(f"  ❌ WHOIS command not found. Please ensure 'whois' is installed and in PATH.")
        ping_healthcheck(expiry_uuid + "/fail", payload="status=whois_not_found")
    except subprocess.TimeoutExpired:
        error(f"  ❌ WHOIS command timed out for {domain}.")
        ping_healthcheck(expiry_uuid + "/fail", payload="status=timeout")
    except Exception as e:
        # Catch other potential errors during subprocess execution or parsing
        error(f"  ❌ An unexpected error occurred during WHOIS check for {domain}: {e}")
        # Use traceback for more detail if needed: import traceback; traceback.print_exc()
        ping_healthcheck(expiry_uuid + "/fail", payload=f"status=unexpected_error&error={str(e)}")

def action_list_checks():
    """Lists all healthchecks found via the API."""
    info("Starting: List Checks from API")
    all_checks_details = get_all_healthchecks_details()
    if not all_checks_details:
        info("No healthchecks found on the account.")
    else:
        info(f"Found {len(all_checks_details)} Healthchecks:")
        # Sort checks by name for consistent output
        for check in sorted(all_checks_details, key=lambda x: x.get('name', '').lower()):
             # API returns tags as a space-separated string, not list
             tags_str = check.get('tags', '')
             # Formats last ping nicely if present
             last_ping_str = check.get('last_ping')
             if last_ping_str:
                 try:
                      # Attempt to parse and format the timestamp
                      last_ping_dt = datetime.datetime.fromisoformat(last_ping_str.replace('Z', '+00:00'))
                      last_ping_formatted = last_ping_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
                 except ValueError:
                      last_ping_formatted = last_ping_str # Keep original if parsing fails
             else:
                 last_ping_formatted = "Never"

             info(f"  - Name: {check.get('name', 'N/A'):<30} UUID: {check['uuid']} Tags: [{tags_str}] Last Ping: {last_ping_formatted} Status: {check.get('status','N/A')}")
    info("Finished: List Checks from API")


def action_list_domains():
    """Lists domains configured in the local file."""
    info("Starting: List Domains from File")
    # Use the version of load_domains that skips invalid lines for listing
    domains = load_domains()
    if not domains:
        info(f"No valid domains found in {DOMAIN_FILE}.")
    else:
        info(f"Valid domains configured in {DOMAIN_FILE}:")
        for domain in domains:
             expiry_info = f"Expiry UUID: {domain['expiry_uuid']}" if domain['expiry_uuid'] else "Expiry UUID: (Not set)"
             info(f"  - Domain: {domain['domain']:<30} Status UUID: {domain['status_uuid']} {expiry_info}")
    info("Finished: List Domains from File")

def action_delete_markers():
    """Deletes the temporary expiry check marker files."""
    info("Starting: Delete Expiry Markers")
    deleted_count = 0
    if not os.path.isdir(MARKER_DIR):
        info(f"Marker directory '{MARKER_DIR}' does not exist. Nothing to delete.")
        return

    try:
        for filename in os.listdir(MARKER_DIR):
            if filename.startswith("expiry_check_"):
                file_path = os.path.join(MARKER_DIR, filename)
                try:
                    os.remove(file_path)
                    info(f"  - Deleted marker: {file_path}")
                    deleted_count += 1
                except OSError as e:
                    error(f"Could not delete marker file '{file_path}': {e}")
        if deleted_count == 0:
            info(f"No marker files found matching 'expiry_check_*' in {MARKER_DIR}.")
        else:
            info(f"Deleted {deleted_count} marker files from {MARKER_DIR}.")
    except OSError as e:
        error(f"Could not list files in marker directory '{MARKER_DIR}': {e}")
    info("Finished: Delete Expiry Markers")

def action_remove(args):
    """Dispatcher function for the 'remove' command."""
    info(f"Executing 'remove' command...")
    force_flag = args.force # Get the force flag value

    # Priority 1: Specific domain is provided
    if args.domain:
        if args.all:
            warn("Ignoring --all flag because a specific domain was provided.")
        if args.unused:
            warn("Ignoring --unused flag because a specific domain was provided.")
        # Call the function to remove a single domain's checks, passing force flag
        action_remove_single_domain(args.domain, force=force_flag)

    # Priority 2: "--all" flag is used
    elif args.all:
        # Call the function to remove everything, passing force flag
        action_remove_all_checks(force=force_flag)

    # Priority 3: "--unused" flag is used (No confirmation needed for this one)
    elif args.unused:
        if force_flag:
            # Force doesn't apply to --unused as it has no prompt
            debug("--force flag has no effect with --unused.")
        action_remove_unused_checks()

    # Priority 4: 'remove' command used with no domain and no flags
    else:
        error("No arguments provided for 'remove'. Specify a domain, --all, or --unused.")
        print("\nUsage options for 'remove':")
        print(f"  {os.path.basename(__file__)} remove <domain_name> [-f] # Remove specific domain (force)")
        print(f"  {os.path.basename(__file__)} remove --unused           # Remove API checks not in file")
        print(f"  {os.path.basename(__file__)} remove --all [-f]        # DANGER: Remove all checks (force)")
        exit(1) # Exit with error status

# --- Command Mapping ---
COMMAND_MAP = {
    'create': {'func': action_create_domain_checks_from_file, 'help': 'Ensure checks exist for domains (processes file if no domain specified).'},
    'check': {'func': action_check_domains, 'help': 'Check status/expiry for configured domains and ping healthchecks.'},
    'remove': {'func': action_remove, 'help': 'Remove checks from API/file (use --all, --unused, or specify domain).'},
    'list-checks': {'func': action_list_checks, 'help': 'List all healthchecks registered in the Healthchecks.io account.'},
    'list-domains': {'func': action_list_domains, 'help': 'List valid domains and their UUIDs configured in the local file.'},
    'delete-markers': {'func': action_delete_markers, 'help': 'Delete temporary expiry check marker files from /tmp.'},
    'sync-file': {'func': action_sync_file, 'help': 'Removes non-existent UUIDs from the local domains file.'}
    # Note: action_create_single_domain is called via argparse logic, not directly via COMMAND_MAP lookup
}

# --- Main Execution ---
if __name__ == "__main__":
    # Set up the main parser
    parser = argparse.ArgumentParser(
        description="Manage Healthchecks.io domain status and expiry checks.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest='command', # Store the command name in 'command'
        help='Available commands',
        metavar='COMMAND'
    )
    # Make command mandatory by default unless no args are given later
    # subparsers.required = True # Optional: force a command if args are present

    # --- Define the 'create' subcommand ---
    create_parser = subparsers.add_parser(
        'create',
        help='Ensure checks exist for domains. Processes file if no domain specified.',
        description='Creates missing healthchecks. If DOMAIN is provided, only processes that domain. Otherwise, processes all entries in the domain file.'
    )
    create_parser.add_argument(
        'domain',
        nargs='?', # Makes the domain argument optional
        type=str,
        help='Optional: A specific domain name to create/update checks for.'
    )

    # --- Define other commands using subparsers ---
    check_parser = subparsers.add_parser('check', help=COMMAND_MAP['check']['help'])
    list_checks_parser = subparsers.add_parser('list-checks', help=COMMAND_MAP['list-checks']['help'])
    list_domains_parser = subparsers.add_parser('list-domains', help=COMMAND_MAP['list-domains']['help'])
    delete_markers_parser = subparsers.add_parser('delete-markers', help=COMMAND_MAP['delete-markers']['help'])
    sync_file_parser = subparsers.add_parser('sync-file', help=COMMAND_MAP['sync-file']['help'])

    # --- Define the merged 'remove' subcommand ---
    remove_parser = subparsers.add_parser(
        'remove',
        help='Remove checks from API and/or file. See remove --help.',
        description='Removes healthchecks based on arguments provided.'
    )
    # --- Add mutually exclusive flags for --all and --unused ---
    remove_group = remove_parser.add_mutually_exclusive_group()
    remove_group.add_argument(
        '--all',
        action='store_true',
        help='DANGER: Remove ALL checks from API and clear local file.'
    )
    remove_group.add_argument(
        '--unused',
        action='store_true',
        help='Remove API checks that are NOT listed in the local file.'
    )
    remove_parser.add_argument(
        'domain',
        nargs='?', # Optional positional argument
        type=str,
        help='Optional: A specific domain name whose checks should be removed from API and file. Overrides --all and --unused.'
    )
    remove_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Bypass confirmation prompts for deletion (--all or specific domain).'
    )

    # Parse arguments
    args = parser.parse_args()

    # --- Updated Execution Logic ---
    if args.command == 'create':
        if args.domain:
            # Call a new function for single domain creation
            action_create_single_domain(args.domain)
        else:
            # Call the existing function for processing the whole file
            action_create_domain_checks_from_file() # Rename original function
    elif args.command == 'remove':
        action_remove(args) # Pass the parsed args to the dispatcher
    elif args.command == 'check':
        action_check_domains()
    elif args.command == 'list-checks':
        action_list_checks()
    elif args.command == 'list-domains':
        action_list_domains()
    elif args.command == 'delete-markers':
        action_delete_markers()
    elif args.command == 'sync-file':
        action_sync_file()
    else:
        # No command was provided (e.g., script run with no arguments)
        print("Available commands:")
        max_len = max(len(cmd) for cmd in COMMAND_MAP.keys())
        for cmd, details in COMMAND_MAP.items():
            print(f"  {cmd:<{max_len}}   {details['help']}")
        print(f"\nRun '{os.path.basename(__file__)} <COMMAND> --help' for more info on a command.")

    # --- Removed the previous try...except block that called function_to_run directly ---
    # --- Error handling is now within the specific action_ functions or the main block if needed ---