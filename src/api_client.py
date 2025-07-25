# domain_checker/api_client.py
import requests
import re
import json
from .config import API_KEY, API_URL, BASE_URL, USER_AGENT
from .logger import info, debug, error, warn

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

def create_check(domain, check_type):
    """Creates a status or expiry check for a given domain-healthcheck-cli."""
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
        # TODO: Consider making this interval configurable, or change the default to 1 minute.
        #  Currently we adjust to 1 hour
        #  Note: The command may appear slow due to intentional sleep or waiting,
        #       which could misleadingly trigger timeout logic or false error detection.
        #       Current runtime stats for check command:
        #         - User CPU time: 0.53s
        #         - System CPU time: 0.08s
        #         - CPU usage: 5%
        #         - Total elapsed time: 11.491s
        data['grace'] = 3600  # 1-hour grace
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
        # error(f"Failed to create {check_type} check for {domain-healthcheck-cli}. API response: {response_data}") # Redundant logging
        return None # API call failed or didn't return expected data

# TODO: Implement update_check
# def update_check(uuid):
#     return False

def delete_check(uuid):
    """Deletes a check by its UUID."""
    if not uuid:
        warn("Skipping deletion: No UUID provided.")
        return False # Indicate failure

    response_data = _make_api_request('DELETE', f'checks/{uuid}')

    # Success is indicated if _make_api_request didn't return None AND didn't log an error.
    # The returned data itself (the deleted object) is confirmation of success here.
    # We rely on _make_api_request logging errors if the status code was bad.
    if response_data is not None: # Hypothetically check if needed
        # Log success based on receiving a response (or None for 204) without prior error logs
        info(f"Deletion API call for check {uuid} appears successful.")
        # Optionally, log the details if needed for confirmation:
        # if response_data:
        #     debug(f"API returned deleted object details: {response_data}")
        return True
    else:
        # An error should have already been logged by _make_api_request
        error(f"Deletion failed for check {uuid}.")
        return False # Indicate failure

def get_all_checks_details():
    """Retrieves details for all checks."""
    response_data = _make_api_request('GET', 'checks/')
    return response_data.get('checks', []) if response_data else []

def ping_check(uuid, endpoint_suffix="", payload=None):
    """Pings a check endpoint (success, fail, log, start). Uses POST if payload is present."""
    if not uuid:
        warn(f"Skipping ping: No UUID provided (suffix: {endpoint_suffix})")
        return
    # Ensure BASE_URL is properly configured
    if not BASE_URL or not BASE_URL.startswith(('http://', 'https://')):
        error(f"Invalid BASE_URL configured: '{BASE_URL}'. Cannot ping.")
        return

    ping_url = f"{BASE_URL.rstrip('/')}/{uuid}{endpoint_suffix}"
    # Start with base headers, modify within the block if needed
    headers = {'User-Agent': USER_AGENT}
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

def get_check_details(uuid):
    """Retrieves the full details for a single check by its UUID."""
    if not uuid:
        warn("Cannot get check details: No UUID provided.")
        return None

    # This reuses your existing robust request helper
    return _make_api_request('GET', f'checks/{uuid}')

def update_check_tags(uuid, tags_list):
    """Updates the tags for a specific check. Expects a list of strings."""
    if not uuid:
        warn("Cannot update tags: No UUID provided.")
        return False

    # The Healthchecks API expects a space-separated string for tags
    tags_string = " ".join(sorted(tags_list))
    payload = {'tags': tags_string}

    info(f"Updating tags for check {uuid} to: \"{tags_string}\"")
    response_data = _make_api_request('POST', f'checks/{uuid}', data=payload)

    # A successful update returns the updated check object
    if response_data and response_data.get('tags') == tags_string:
        debug(f"Successfully updated tags for {uuid}.")
        return True
    else:
        error(f"Failed to update tags for {uuid}.")
        return False
