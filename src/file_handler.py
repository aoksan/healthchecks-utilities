# domain_checker/file_handler.py
import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone # <-- Add datetime imports
from . import config
from .logger import info, warn, error, debug

def load_domains_raw():
    """Loads raw lines and comments/blanks from the domain file."""
    lines_data = []
    try:
        with open(config.DOMAIN_FILE, 'r') as f:
            for idx, line in enumerate(f):
                lines_data.append({'line_num': idx + 1, 'raw_line': line.strip()})
    except FileNotFoundError:
        warn(f"Domains file '{config.DOMAIN_FILE}' not found.")
    except IOError as e:
        error(f"Could not read domains file '{config.DOMAIN_FILE}': {e}")
    return lines_data

def load_domains():
    """
    Loads domain configurations from the DOMAIN_FILE.
    A line is considered valid if it contains a domain and at least one UUID (s: or e:).
    """
    domains = []
    try:
        with open(config.DOMAIN_FILE, 'r') as f:
            for idx, line in enumerate(f):
                line_num = idx + 1
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                domain = parts[0]
                status_uuid, expiry_uuid = None, None

                for part in parts[1:]:
                    if part.startswith('s:'): status_uuid = part.split(':', 1)[1]
                    elif part.startswith('e:'): expiry_uuid = part.split(':', 1)[1]

                if domain and (status_uuid or expiry_uuid):
                    domains.append({
                        'domain': domain,
                        'status_uuid': status_uuid or "",
                        'expiry_uuid': expiry_uuid or ""
                    })
                else:
                    warn(f"Skipping invalid line {line_num}: '{line}' in {config.DOMAIN_FILE}.")
    except FileNotFoundError:
        warn(f"Domains file '{config.DOMAIN_FILE}' not found. No domains loaded.")
    except IOError as e:
        error(f"Could not read domains file '{config.DOMAIN_FILE}': {e}")
    return domains

def create_expiry_marker(domain: str):
    """Creates an empty marker file to indicate a recent expiry check."""
    try:
        marker_dir = Path(config.MARKER_DIR)
        marker_dir.mkdir(parents=True, exist_ok=True)
        marker_file = marker_dir / f"expiry_check_{domain}"
        marker_file.touch() # Creates or updates the file's timestamp
        debug(f"Created/updated expiry marker for {domain} at {marker_file}")
    except Exception as e:
        error(f"Failed to create expiry marker for {domain}: {e}")

def is_marker_valid(domain: str, max_age_hours: int = 23) -> bool:
    """
    Checks if a recent, valid marker file exists for the domain.
    A marker is valid if it exists and is newer than max_age_hours.
    It automatically deletes stale markers.
    """
    try:
        marker_file = Path(config.MARKER_DIR) / f"expiry_check_{domain}"

        if not marker_file.exists():
            return False # No marker, so it's not valid.

        # Check the file's age
        file_mod_time = datetime.fromtimestamp(marker_file.stat().st_mtime, tz=timezone.utc)
        calculated_age = datetime.now(timezone.utc) - file_mod_time
        debug(f"Marker for {domain} last modified at {file_mod_time}, age: {calculated_age}")
        if calculated_age < timedelta(hours=max_age_hours):
            return True # Marker exists and is recent.
        else:
            # Marker is old (stale), so delete it and report as invalid
            debug(f"Marker past {max_age_hours} hours for {file_mod_time} found for {domain}. Deleting it.")
            marker_file.unlink()
            return False

    except Exception as e:
        error(f"Error checking marker validity for {domain}: {e}")
        return False # Fail safe

def delete_one_marker(marker_filename: str) -> bool: # <-- Type hint fix
    """
    Deletes a single marker file by its full filename.
    Returns True if deleted, False if not found or error.
    """
    marker_file = Path(config.MARKER_DIR) / marker_filename
    if not marker_file.exists():
        debug(f"Marker file '{marker_file}' does not exist, cannot delete.")
        return False
    try:
        marker_file.unlink()
        info(f"  - Deleted marker file: {marker_file}")
        return True
    except OSError as e:
        error(f"  ✗ Could not delete marker file '{marker_file}': {e}")
        return False

def delete_markers_for_domain(domain: str) -> int:
    """Deletes all marker types for a specific domain. Returns count of deleted files."""
    info(f"Searching for markers for domain '{domain}'...")
    deleted_count = 0
    # Try to delete both potential marker types
    if delete_one_marker(f"status_check_{domain}"):
        deleted_count += 1
    if delete_one_marker(f"expiry_check_{domain}"):
        deleted_count += 1
    return deleted_count

def delete_markers_by_type(marker_type: str) -> int:
    """Deletes all markers of a specific type ('status' or 'expiry'). Returns count."""
    info(f"Searching for all '{marker_type}' type markers...")
    deleted_count = 0
    marker_dir = Path(config.MARKER_DIR)
    if not marker_dir.is_dir():
        return 0 # Nothing to do

    for marker_file in marker_dir.glob(f"{marker_type}_check_*"):
        if delete_one_marker(marker_file.name):
            deleted_count += 1
    return deleted_count

def delete_all_markers() -> int:
    """Deletes all marker files from the configured directory."""
    deleted_count = 0
    marker_dir = Path(config.MARKER_DIR)

    if not marker_dir.is_dir():
        info(f"Marker directory '{marker_dir}' does not exist. Nothing to delete.")
        return 0

    try:
        for file_path in marker_dir.glob("expiry_check_*"):
            try:
                file_path.unlink()
                info(f"  - Deleted marker: {file_path}")
                deleted_count += 1
            except OSError as e:
                error(f"Could not delete marker file '{file_path}': {e}")
    except OSError as e:
        error(f"Could not list files in marker directory '{marker_dir}': {e}")

    if deleted_count == 0:
        info(f"No marker files found in {marker_dir}.")

    # return the count of deleted markers for potential use
    return deleted_count

def rewrite_domain_file(processed_entries, new_entries=None):
    """
    Generic function to rewrite the domain file.
    'processed_entries' is a list of dicts for existing/modified lines.
    'new_entries' is an optional list of dicts for new lines to append.
    """
    info(f"Rewriting {config.DOMAIN_FILE}...")
    try:
        with open(config.DOMAIN_FILE, 'w') as outfile:
            # Write original/modified entries
            for entry in processed_entries:
                if entry['type'] == 'comment_or_blank':
                    outfile.write(entry['content'] + "\n")
                elif entry['type'] == 'domain':
                    line_parts = [entry['domain']]
                    if entry.get('status_uuid'): line_parts.append(f"s:{entry['status_uuid']}")
                    if entry.get('expiry_uuid'): line_parts.append(f"e:{entry['expiry_uuid']}")

                    if len(line_parts) > 1:
                        outfile.write(" ".join(line_parts) + "\n")
                    else:
                        warn(f"Skipping write for '{entry['domain']}' as it has no valid UUIDs.")

            # Append new entries if they exist
            if new_entries:
                outfile.write("\n# --- Checks Added by Sync Command ---\n")
                for entry in new_entries:
                    line_parts = [entry['domain']]
                    if entry.get('status_uuid'): line_parts.append(f"s:{entry['status_uuid']}")
                    if entry.get('expiry_uuid'): line_parts.append(f"e:{entry['expiry_uuid']}")
                    outfile.write(" ".join(line_parts) + "\n")

        info(f"Successfully updated {config.DOMAIN_FILE}.")
    except IOError as e:
        error(f"Failed to rewrite {config.DOMAIN_FILE}: {e}")
