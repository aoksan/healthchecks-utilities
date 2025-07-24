# domain_checker/file_handler.py
import os
import re
from . import config
from .logger import info, warn, error

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
