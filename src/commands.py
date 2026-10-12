from . import file_handler
from .logger import info, debug, error, warn
from .utils import time_it  # <-- 1. Import the decorator
from .actions import (
    check as check_actions,
    list as list_actions,
    remove as remove_actions,
    create as create_actions,
    sync as sync_actions,
)

# --- High-Level Command Functions ---


@time_it
def action_check_domains(force_update_tags: bool = False):
    """High-level command to check all configured domains."""
    info("Starting: Check Domains")
    if force_update_tags:
        info(
            "Note: --force-update-tags flag is active. Tags will be updated regardless of current state."
        )

    domains = file_handler.load_domains()
    if not domains:
        warn("No valid domains loaded to check.")
        return
    for domain_data in domains:
        info(f"--- Processing {domain_data['domain']} ---")
        if domain_data.get("status_uuid"):
            check_actions.check_domain_status(
                domain_data["domain"], domain_data["status_uuid"]
            )
        if domain_data.get("expiry_uuid"):
            check_actions.check_domain_expiry(
                domain_data["domain"], domain_data["expiry_uuid"], force_update_tags
            )
    info("Finished: Check Domains")


def action_create(
    domain: str | None = None, status_only: bool = False, expiry_only: bool = False
):
    """Dispatcher for the 'create' command."""
    if domain:
        create_actions.create_for_single_domain(
            domain, status_only=status_only, expiry_only=expiry_only
        )
    else:
        create_actions.create_from_file(
            status_only=status_only, expiry_only=expiry_only
        )


def action_remove(
    domain: str | None = None,
    remove_all: bool = False,
    unused: bool = False,
    force: bool = False,
):
    """Dispatcher for the 'remove' command."""
    if domain:
        remove_actions.remove_single_domain(domain, force=force)
    elif remove_all:
        remove_actions.remove_all(force=force)
    elif unused:
        remove_actions.remove_unused()
    else:
        error("Internal error: No valid arguments for 'remove' command.")


def action_sync_file():
    """High-level command to sync the file with the API."""
    sync_actions.sync_file_with_api()


# Pass-through functions for simple commands
action_list_checks = list_actions.list_api_checks
action_list_domains = list_actions.list_file_domains


def action_delete_marker(
    domain: str | None = None, marker_type: str | None = None, all_markers: bool = False
):
    """Dispatcher for the 'delete-markers' command."""
    remove_actions.delete_marker(
        domain=domain,
        marker_type=marker_type,
        all_markers=all_markers,
    )
