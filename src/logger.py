import sys
from loguru import logger
from . import config

# --- 1. Configure Loguru ---
# Remove the default handler
logger.remove()

# Set the overall minimum level
log_level = "DEBUG" if getattr(config, "DEBUG_MODE", False) else "INFO"

# Customize level colors to match the original scheme
logger.level("DEBUG", color="<cyan>")
logger.level("INFO", color="<blue>")

# --- 2. Global On/Off Switch ---
if getattr(config, "LOGGING_ACTIVE", True):
    # A. Handler for the CONSOLE (with color)
    console_format = (
        "<green>[{time:YYYY-MM-DD HH:mm:ss}]</green> "
        "[<level>{level}</level>] {message}"
    )
    logger.add(
        sys.stdout,
        level=log_level,
        format=console_format,
        colorize=True,
    )

    # B. Handler for the LOG FILE (without color)
    try:
        file_format = "[{time:YYYY-MM-DD HH:mm:ss}] [{level}] {message}"
        logger.add(
            config.LOG_FILE,
            level=log_level,
            format=file_format,
            colorize=False,
        )
    except (IOError, PermissionError) as e:
        logger.warning(f"Could not open or write to log file '{config.LOG_FILE}': {e}")


# --- 3. Define Convenience Functions ---
def info(message):
    logger.info(message)


def debug(message):
    logger.debug(message)


def warn(message):
    logger.warning(message)


def error(message):
    logger.error(message)
