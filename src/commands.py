# domain_checker/commands.py
from . import file_handler
from .logger import info, debug, error, warn
from .utils import time_it  # <-- 1. Import the decorator
from .actions import check as check_actions, list as list_actions, remove as remove_actions, create as create_actions, sync as sync_actions

# --- High-Level Command Functions ---

@time_it
def action_check_domains():
    """High-level command to check all configured domains."""
    info("Starting: Check Domains")
    domains = file_handler.load_domains()
    if not domains:
        warn("No valid domains loaded to check.")
        return
    for domain_data in domains:
        info(f"--- Processing {domain_data['domain']} ---")
        if domain_data.get('status_uuid'):
            check_actions.check_domain_status(domain_data['domain'], domain_data['status_uuid'])
        if domain_data.get('expiry_uuid'):
            check_actions.check_domain_expiry(domain_data['domain'], domain_data['expiry_uuid'])
    info("Finished: Check Domains")

def action_create(args):
    """Dispatcher for the 'create' command."""
    if args.domain:
        create_actions.create_for_single_domain(
            args.domain,
            status_only=args.status_only,
            expiry_only=args.expiry_only
        )
    else:
        create_actions.create_from_file(
            status_only=args.status_only,
            expiry_only=args.expiry_only
        )

def action_remove(args):
    """Dispatcher for the 'remove' command."""
    if args.domain:
        remove_actions.remove_single_domain(args.domain, force=args.force)
    elif args.all:
        remove_actions.remove_all(force=args.force)
    elif args.unused:
        remove_actions.remove_unused()
    else:
        error("Internal error: No valid arguments for 'remove' command.")

def action_sync_file():
    """High-level command to sync the file with the API."""
    sync_actions.sync_file_with_api()

# Pass-through functions for simple commands
action_list_checks = list_actions.list_api_checks
action_list_domains = list_actions.list_file_domains
action_delete_marker = remove_actions.delete_marker
