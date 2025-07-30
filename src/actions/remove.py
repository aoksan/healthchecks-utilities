# domain_checker/actions/remove.py
import os
from .. import api_client, file_handler, config
from ..logger import info, debug, error, warn

def delete_marker(args):
    """
    Handles the 'delete-markers' command by dispatching to the correct
    file_handler function based on the provided filters.
    """
    info("Starting: Delete Marker(s)")
    deleted_count = 0

    try:
        # The --all flag overrides everything else
        if args.all:
            deleted_count = file_handler.delete_all_markers()

        # Handle combinations of domain and type
        elif args.domain and args.type:
            # Most specific: delete one type for one domain
            marker_filename = f"{args.type}_check_{args.domain}"
            if file_handler.delete_one_marker(marker_filename):
                deleted_count = 1

        elif args.domain:
            # Delete all types for a specific domain
            deleted_count = file_handler.delete_markers_for_domain(args.domain)

        elif args.type:
            # Delete all markers of a specific type
            deleted_count = file_handler.delete_markers_by_type(args.type)

        # The check in cli.py ensures we never get here with no args.

        if deleted_count > 0: # type: ignore
            info(f"Successfully deleted {deleted_count} marker file(s).")
        else:
            info("No matching marker files were found to delete.")

    except Exception as e:
        error(f"An unexpected error occurred during marker deletion: {e}")

def remove_single_domain(domain_to_remove, force=False):
    """
    Removes checks for a specific domain from the API and the local file.
    """
    info(f"Starting: Remove Single Domain '{domain_to_remove}'")
    all_checks = api_client.get_all_checks_details()
    if all_checks is None:
        error("Failed to retrieve checks from API. Cannot proceed.")
        return

    uuids_to_delete = [c['uuid'] for c in all_checks if
                       c.get('name') == domain_to_remove]

    if uuids_to_delete:
        info(f"Found {len(uuids_to_delete)} checks in API for '{domain_to_remove}'.")
        if not force:
            confirm = input(
                f"Proceed with deleting these checks from the API? Type 'YES' to confirm: ")
            if confirm != 'YES':
                info("API deletion cancelled.")
                return

        for uuid in uuids_to_delete:
            api_client.delete_check(uuid)
    else:
        info(f"No active checks found in API with name '{domain_to_remove}'.")

    raw_lines = file_handler.load_domains_raw()
    lines_to_keep = [ld for ld in raw_lines if
                     ld['raw_line'].split() and ld['raw_line'].split()[
                         0] != domain_to_remove]

    if len(lines_to_keep) < len(raw_lines):
        info(
            f"Removing '{domain_to_remove}' from {config.DOMAIN_FILE} and rewriting...")
        # Note: A more advanced rewrite could use the file_handler.rewrite_domain_file
        # but for simple removal, this is also fine.
        try:
            with open(config.DOMAIN_FILE, 'w') as f:
                for line_data in lines_to_keep:
                    f.write(line_data['raw_line'] + '\n')
            info(f"Successfully updated {config.DOMAIN_FILE}.")
        except IOError as e:
            error(f"Failed to rewrite {config.DOMAIN_FILE}: {e}")
    else:
        info(f"Domain '{domain_to_remove}' was not found in the file. No changes made.")

    info(f"Finished: Remove Single Domain '{domain_to_remove}'")


def remove_all(force=False):
    """Removes ALL healthchecks from the account and clears the domain file."""
    info("Starting: Remove ALL Checks")
    if not force:
        confirm = input(
            "DANGER: This will delete ALL healthchecks from the API and clear the domain file. Type 'YES' to confirm: ")
        if confirm != 'YES':
            info("Operation cancelled.")
            return

    all_checks = api_client.get_all_checks_details()
    if not all_checks:
        info("No healthchecks found to delete.")
    else:
        info(f"Deleting {len(all_checks)} healthchecks...")
        for check in all_checks:
            api_client.delete_check(check['uuid'])

    try:
        with open(config.DOMAIN_FILE, "w") as f:
            f.write("# Domain file cleared by remove-all command\n")
        info(f"Cleared domain entries in {config.DOMAIN_FILE}")
    except IOError as e:
        error(f"Could not clear domains file: {e}")
    info("Finished: Remove ALL Checks")


def remove_unused():
    """Removes healthchecks from the API that are not listed in the domain file."""
    info("Starting: Remove Unused Checks")
    all_checks = api_client.get_all_checks_details()
    if not all_checks:
        info("No healthchecks on account. Nothing to remove.")
        return

    all_api_uuids = {check['uuid'] for check in all_checks}
    domains_from_file = file_handler.load_domains()
    used_uuids = {d['status_uuid'] for d in domains_from_file if d.get('status_uuid')}
    used_uuids.update(
        {d['expiry_uuid'] for d in domains_from_file if d.get('expiry_uuid')})

    unused_uuids = all_api_uuids - used_uuids
    if not unused_uuids:
        info("No unused checks found.")
        return

    info(f"Found {len(unused_uuids)} unused checks to delete.")
    for uuid in unused_uuids:
        check_info = next((c['name'] for c in all_checks if c['uuid'] == uuid), 'N/A')
        info(f"  - Deleting unused check: {uuid} (Name: {check_info})")
        api_client.delete_check(uuid)

    info(f"Deleted {len(unused_uuids)} unused checks.")
    info("Finished: Remove Unused Checks")
