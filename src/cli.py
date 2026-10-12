from typing import Literal, Optional

import typer
from dotenv import load_dotenv

from . import commands, config

app = typer.Typer(
    help="Manage Healthchecks.io domain status and expiry checks.",
    no_args_is_help=True,
)


@app.command()
def create(
    domain: Optional[str] = typer.Argument(
        None,
        help="Optional: A specific domain to create/update checks for.",
    ),
    status_only: bool = typer.Option(
        False,
        "--status-only",
        help="Only create the status check.",
    ),
    expiry_only: bool = typer.Option(
        False,
        "--expiry-only",
        help="Only create the expiry check (ignores subdomain rule).",
    ),
):
    """Ensure checks exist for domains. Processes file if no domain is specified."""
    if status_only and expiry_only:
        raise typer.BadParameter("Cannot use both --status-only and --expiry-only.")
    commands.action_create(
        domain=domain,
        status_only=status_only,
        expiry_only=expiry_only,
    )


@app.command()
def check(
    force_update_tags: bool = typer.Option(
        False,
        "--force-update-tags",
        help="Force the script to update tags on the API, even if they appear to be correct.",
    ),
):
    """Check status/expiry for all configured domains."""
    commands.action_check_domains(force_update_tags=force_update_tags)


@app.command()
def remove(
    domain: Optional[str] = typer.Argument(
        None,
        help="A specific domain to remove.",
    ),
    remove_all: bool = typer.Option(
        False,
        "--all",
        help="DANGER: Remove ALL checks from API and clear local file.",
    ),
    unused: bool = typer.Option(
        False,
        "--unused",
        help="Remove API checks that are NOT listed in the local file.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Bypass confirmation prompts for deletion.",
    ),
):
    """Remove checks from API and/or file."""
    if sum([bool(domain), remove_all, unused]) != 1:
        raise typer.BadParameter("Specify exactly one of: domain, --all, or --unused.")
    commands.action_remove(
        domain=domain,
        remove_all=remove_all,
        unused=unused,
        force=force,
    )


@app.command("list-checks")
def list_checks():
    """List all checks from the Healthchecks.io API."""
    commands.action_list_checks()


@app.command("list-domains")
def list_domains():
    """List all domains configured in the local file."""
    commands.action_list_domains()


@app.command("delete-markers")
def delete_markers(
    domain: Optional[str] = typer.Option(
        None,
        "--domain",
        "-d",
        help="The specific domain to delete markers for.",
    ),
    marker_type: Optional[Literal["status", "expiry"]] = typer.Option(
        None,
        "--type",
        "-t",
        help="The type of marker to delete (can be combined with --domain).",
    ),
    all_markers: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Delete ALL marker files, ignoring other filters.",
    ),
):
    """Delete temporary expiry check marker file(s)."""
    if not (domain or marker_type or all_markers):
        raise typer.BadParameter(
            "You must specify at least one filter (--domain, --type, or --all)."
        )
    commands.action_delete_marker(
        domain=domain,
        marker_type=marker_type,
        all_markers=all_markers,
    )


@app.command("sync-file")
def sync_file():
    """Syncs local file with API (adds/removes checks)."""
    commands.action_sync_file()


def main():
    """Main entry point for the CLI tool."""
    load_dotenv()
    config.validate_config()
    app()
