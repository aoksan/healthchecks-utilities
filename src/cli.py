# domain_checker/cli.py
import argparse
import os
from dotenv import load_dotenv
from . import commands, config

def main():
    """Main entry point for the CLI tool."""
    load_dotenv()
    config.validate_config()

    # --- 1. Set up the main parser ---
    parser = argparse.ArgumentParser(
        description="Manage Healthchecks.io domain status and expiry checks.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True
    )

    # --- 2. Define the parser for each command ---

    # Command: create
    create_parser = subparsers.add_parser(
        'create',
        help='Ensure checks exist for domains. Processes file if no domain is specified.'
    )
    create_parser.add_argument(
        'domain',
        nargs='?',
        help='Optional: A specific domain to create/update checks for.'
    )
    create_flags = create_parser.add_mutually_exclusive_group()
    create_flags.add_argument(
        '--status-only',
        action='store_true',
        help='Only create the status check.'
    )
    create_flags.add_argument(
        '--expiry-only',
        action='store_true',
        help='Only create the expiry check (ignores subdomain rule).'
    )
    create_parser.set_defaults(func=commands.action_create)

    # Command: check
    check_parser = subparsers.add_parser('check', help='Check status/expiry for all configured domains.')
    check_parser.set_defaults(func=commands.action_check_domains)

    # Command: remove
    remove_parser = subparsers.add_parser('remove', help='Remove checks from API and/or file.')
    remove_group = remove_parser.add_mutually_exclusive_group(required=True)
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
    remove_group.add_argument('domain', nargs='?', help='A specific domain to remove.')
    remove_parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Bypass confirmation prompts for deletion.'
    )
    remove_parser.set_defaults(func=commands.action_remove)

    # Command: list-checks
    list_checks_parser = subparsers.add_parser('list-checks', help='List all checks from the Healthchecks.io API.')
    list_checks_parser.set_defaults(func=commands.action_list_checks)

    # Command: list-domains
    list_domains_parser = subparsers.add_parser('list-domains', help='List all domains configured in the local file.')
    list_domains_parser.set_defaults(func=commands.action_list_domains)

    # Command: delete-markers
    delete_markers_parser = subparsers.add_parser(
        'delete-markers',
        help='Delete temporary expiry check marker file(s).'
    )
    # These are now standard, independent arguments, NOT in a group.
    delete_markers_parser.add_argument(
        '-d', '--domain',
        type=str,
        help='The specific domain to delete markers for.'
    )
    delete_markers_parser.add_argument(
        '-t', '--type',
        choices=['status', 'expiry'],
        help='The type of marker to delete (can be combined with --domain).'
    )
    delete_markers_parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Delete ALL marker files, ignoring other filters.'
    )
    delete_markers_parser.set_defaults(func=commands.action_delete_marker)

    # Command: sync-file
    sync_file_parser = subparsers.add_parser('sync-file', help='Syncs local file with API (adds/removes checks).')
    sync_file_parser.set_defaults(func=commands.action_sync_file)

    # --- 3. Parse arguments and execute the associated function ---
    args = parser.parse_args()

    if args.command == 'delete-markers' and not (args.domain or args.type or args.all):
        delete_markers_parser.print_help()
        parser.exit(0,"\nError: You must specify at least one filter (--domain, --type, or --all).")

    # Dispatch to the function set by set_defaults()
    # Pass the 'args' object to commands that need to inspect them further.
    if args.command in ['create', 'remove', 'delete-markers']:
        args.func(args)
    else:
        # For simple commands that don't need arguments
        args.func()
