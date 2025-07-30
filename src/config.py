# domain_checker/config.py
import os
from dotenv import load_dotenv

# Load environment variables from ../.env
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(dotenv_path)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Load environment variables ---
BASE_URL = os.getenv("BASE_URL", "https://hc-ping.com")
DOMAIN_FILE = os.getenv("DOMAIN_FILE", os.path.join(os.path.dirname(SCRIPT_DIR), "domains.txt"))
MARKER_DIR = "/tmp/hc-utilities/markers"
LOG_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "logs.log")
LOGGING_ACTIVE = os.getenv("LOGGING_ACTIVE", "true").lower() in ("true", "1", "yes")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

VERSION = os.getenv("VERSION", "unknown")

# --- Healthcheck API ---
USER_AGENT = f"hc-utilities/{VERSION}"
API_URL = os.getenv("API_URL", "https://healthchecks.io/api/v3/")
API_KEY = os.getenv("API_KEY")
API_HEADERS = {
    'User-Agent': USER_AGENT,
    'Authorization': f"Bearer {API_KEY}"
}

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
