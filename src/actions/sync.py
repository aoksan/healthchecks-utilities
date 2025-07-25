# domain_checker/actions/sync.py
from collections import defaultdict
from .. import api_client, file_handler
from ..logger import info, warn


def sync_file_with_api():
    """
    Synchronizes the local domain file with the API.
    1. Removes UUIDs from the file if they no longer exist in the API.
    2. Adds new entries to the file for checks found in the API but not in the file.
    """
    info("Starting: Sync Domain File with API")
    all_checks = api_client.get_all_checks_details()
    if all_checks is None:
        warn("Failed to retrieve checks from API. Aborting sync.")
        return

    api_checks_map = {check['uuid']: check for check in all_checks}
    api_uuid_set = set(api_checks_map.keys())
    info(f"Found {len(api_uuid_set)} checks via API.")

    raw_lines_data = file_handler.load_domains_raw()
    processed_entries = []
    file_needs_update = False
    used_api_uuids = set()

    for line_data in raw_lines_data:
        original_line = line_data['raw_line']
        if not original_line or original_line.startswith('#'):
            processed_entries.append(
                {'type': 'comment_or_blank', 'content': original_line})
            continue

        parts = original_line.split()
        domain = parts[0]
        current_status_uuid, current_expiry_uuid = None, None

        for part in parts[1:]:
            if part.startswith('s:'):
                current_status_uuid = part.split(':', 1)[1]
            elif part.startswith('e:'):
                current_expiry_uuid = part.split(':', 1)[1]

        final_status_uuid, final_expiry_uuid = current_status_uuid, current_expiry_uuid

        if current_status_uuid and current_status_uuid not in api_uuid_set:
            warn(
                f"Sync: Status UUID '{current_status_uuid}' for '{domain}' not in API. Removing.")
            final_status_uuid = None
            file_needs_update = True
        elif final_status_uuid:
            used_api_uuids.add(final_status_uuid)

        if current_expiry_uuid and current_expiry_uuid not in api_uuid_set:
            warn(
                f"Sync: Expiry UUID '{current_expiry_uuid}' for '{domain}' not in API. Removing.")
            final_expiry_uuid = None
            file_needs_update = True
        elif final_expiry_uuid:
            used_api_uuids.add(final_expiry_uuid)

        processed_entries.append({
            'type': 'domain', 'domain': domain,
            'status_uuid': final_status_uuid, 'expiry_uuid': final_expiry_uuid
        })

    missing_api_uuids = api_uuid_set - used_api_uuids
    new_entries = []
    if missing_api_uuids:
        info(
            f"Found {len(missing_api_uuids)} API checks missing from the file. Adding them...")
        file_needs_update = True

        missing_by_name = defaultdict(
            lambda: {'status_uuid': None, 'expiry_uuid': None})
        for uuid in missing_api_uuids:
            check = api_checks_map[uuid]
            name = check.get('name')
            tags = check.get('tags', '')
            if not name: continue

            if 'status' in tags:
                missing_by_name[name]['status_uuid'] = uuid
            elif 'expiry' in tags:
                missing_by_name[name]['expiry_uuid'] = uuid

        for name, uuids in sorted(missing_by_name.items()):
            new_entries.append({'type': 'domain', 'domain': name, **uuids})

    if file_needs_update:
        file_handler.rewrite_domain_file(processed_entries, new_entries)
    else:
        info("No inconsistencies found. File is already in sync.")

    info("Finished: Sync Domain File with API")
