# domain_checker/actions/create.py

from .. import api_client, file_handler, config
from ..logger import info, debug, error, warn


def create_for_single_domain(domain_to_process, status_only=False, expiry_only=False):
    """
    Ensures healthchecks exist for a SINGLE specified domain and adds/updates
    its entry in the domain file, respecting creation flags.
    """
    info(
        f"Starting: Create Single Domain Checks for '{domain_to_process}' (StatusOnly: {status_only}, ExpiryOnly: {expiry_only})")
    raw_lines_data = file_handler.load_domains_raw()
    processed_domains = []
    domain_found = False
    updated = False

    target_status_uuid = None
    target_expiry_uuid = None
    is_subdomain = domain_to_process.count('.') > 1

    for line_data in raw_lines_data:
        original_line = line_data['raw_line']
        entry = {'type': 'comment_or_blank', 'content': original_line}

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

            entry = {'type': 'domain', 'domain': domain,
                     'status_uuid': current_status_uuid,
                     'expiry_uuid': current_expiry_uuid}

            if domain == domain_to_process:
                domain_found = True
                info(
                    f"Found existing entry for '{domain_to_process}'. Checking UUIDs...")
                target_status_uuid = current_status_uuid
                target_expiry_uuid = current_expiry_uuid

                if not expiry_only and not target_status_uuid:
                    new_uuid = api_client.create_check(domain_to_process,
                                                             'status')
                    if new_uuid:
                        target_status_uuid = new_uuid
                        entry['status_uuid'] = new_uuid
                        updated = True

                if not status_only and not target_expiry_uuid and not is_subdomain:
                    new_uuid = api_client.create_check(domain_to_process,
                                                             'expiry')
                    if new_uuid:
                        target_expiry_uuid = new_uuid
                        entry['expiry_uuid'] = new_uuid
                        updated = True

        processed_domains.append(entry)

    if not domain_found:
        info(f"Domain '{domain_to_process}' not found. Creating new entry...")
        if not expiry_only:
            target_status_uuid = api_client.create_check(domain_to_process,
                                                               'status')
        if not status_only and not is_subdomain:
            target_expiry_uuid = api_client.create_check(domain_to_process,
                                                               'expiry')

        if target_status_uuid or target_expiry_uuid:
            processed_domains.append({
                'type': 'domain', 'domain': domain_to_process,
                'status_uuid': target_status_uuid, 'expiry_uuid': target_expiry_uuid
            })
            updated = True
        else:
            error(f"Failed to create any checks for new domain '{domain_to_process}'.")

    if updated:
        file_handler.rewrite_domain_file(processed_domains)
    else:
        info(
            f"No updates needed or creation failed for '{domain_to_process}'. File not changed.")

    info(f"Finished: Create Single Domain Checks for '{domain_to_process}'")


def create_from_file(status_only=False, expiry_only=False):
    """
    Reads the domain file, creates missing healthchecks respecting flags,
    and rewrites the file with updated info.
    """
    info(
        f"Starting: Create Domain Checks from file (StatusOnly: {status_only}, ExpiryOnly: {expiry_only})")
    raw_lines_data = file_handler.load_domains_raw()
    if not raw_lines_data:
        info("Domain file is empty or not found. Nothing to create.")
        return

    processed_domains = []
    updated = False

    for line_data in raw_lines_data:
        original_line = line_data['raw_line']
        if not original_line or original_line.startswith('#'):
            processed_domains.append(
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

        if not expiry_only and not current_status_uuid:
            new_uuid = api_client.create_check(domain, 'status')
            if new_uuid:
                current_status_uuid = new_uuid
                updated = True

        is_subdomain = domain.count('.') > 1
        if not status_only and not current_expiry_uuid and not is_subdomain:
            new_uuid = api_client.create_check(domain, 'expiry')
            if new_uuid:
                current_expiry_uuid = new_uuid
                updated = True

        processed_domains.append({
            'type': 'domain', 'domain': domain,
            'status_uuid': current_status_uuid, 'expiry_uuid': current_expiry_uuid
        })

    if updated:
        file_handler.rewrite_domain_file(processed_domains)
    else:
        info("No new UUIDs needed. Domain file remains unchanged.")

    info("Finished: Create Domain Checks from file")
