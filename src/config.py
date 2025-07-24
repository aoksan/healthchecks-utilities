# domain_checker/config.py
import os
from dotenv import load_dotenv

# Load environment variables from ../.env
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(dotenv_path)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuration ---
API_URL = os.getenv("API_URL", "https://healthchecks.io/api/v3/")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://hc-ping.com")
DOMAIN_FILE = os.getenv("DOMAIN_FILE", os.path.join(os.path.dirname(SCRIPT_DIR), "domains.txt"))
MARKER_DIR = "/tmp/domain-hc-markers"
LOG_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "logs.log")

# --- GoDaddy Config ---
GODADDY_API_KEY = os.getenv("GODADDY_API_KEY")
GODADDY_API_SECRET = os.getenv("GODADDY_API_SECRET")
GODADDY_API_URL = os.getenv("GODADDY_API_URL", "https://api.ote-godaddy.com/")

# --- Validation ---
def validate_config():
    """Validates essential configuration."""
    if not API_KEY:
        print("ERROR: API_KEY environment variable not set.")
        exit(1)
    if not GODADDY_API_KEY or not GODADDY_API_SECRET:
        print("WARN: GODADDY_API_KEY or GODADDY_API_SECRET not set. GoDaddy fallback is disabled.")
