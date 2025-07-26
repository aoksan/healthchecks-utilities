# src/logger.py
import logging
import sys
from . import config

# --- 1. Define ANSI color codes ---
class Color:
    RESET = '\033[0m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'

# --- 2. Create the Custom Colored Formatter ---
class ColoredFormatter(logging.Formatter):
    """
    A custom log formatter that adds color to log messages based on their level.
    """
    LEVEL_COLORS = {
        logging.DEBUG: Color.CYAN,
        logging.INFO: Color.BLUE,
        logging.WARNING: Color.YELLOW,
        logging.ERROR: Color.RED,
        logging.CRITICAL: Color.RED,
    }

    def format(self, record):
        """
        Overrides the default format method to add color.
        """
        # Get the color for the log level
        log_level_color = self.LEVEL_COLORS.get(record.levelno, Color.RESET)

        # Use the parent class's formatter to do the initial formatting
        # This handles the complex parts like message formatting and exceptions
        formatted_message = super().format(record)

        # Now, wrap the levelname part of the formatted message with color
        # We replace '[LEVEL]' with '[COLOR_LEVEL_RESET]'
        levelname_str = f"[{record.levelname}]"
        colored_levelname = f"[{log_level_color}{record.levelname}{Color.RESET}]"

        # Also, color the timestamp green
        timestamp_str = self.formatTime(record, self.datefmt)
        colored_timestamp = f"[{Color.GREEN}{timestamp_str}{Color.RESET}]"

        # Reconstruct the final message
        # Start with the original message
        final_message = formatted_message
        # Replace the plain timestamp with the colored one
        final_message = final_message.replace(f"[{timestamp_str}]", colored_timestamp)
        # Replace the plain levelname with the colored one
        final_message = final_message.replace(levelname_str, colored_levelname)

        return final_message

# --- 3. Global On/Off Switch ---
if not getattr(config, "LOGGING_ACTIVE", True):
    logging.disable(logging.CRITICAL)

# --- 4. Configure the Root Logger ---
logger = logging.getLogger()

# Set the overall minimum level to process
if getattr(config, "DEBUG_MODE", False):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# --- 5. Create and Add Handlers with Appropriate Formatters ---

# A. Handler for the CONSOLE (with color)
console_handler = logging.StreamHandler(sys.stdout)
# Use our new ColoredFormatter for the console
color_formatter = ColoredFormatter(
    fmt="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(color_formatter)
logger.addHandler(console_handler)


# B. Handler for the LOG FILE (without color)
try:
    file_handler = logging.FileHandler(config.LOG_FILE)
    # Use a standard, non-colored formatter for the file
    plain_formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(plain_formatter)
    logger.addHandler(file_handler)
except (IOError, PermissionError) as e:
    logger.warning(f"Could not open or write to log file '{config.LOG_FILE}': {e}")


# --- 6. Define Convenience Functions ---
def info(message):  logger.info(message)
def debug(message): logger.debug(message)
def warn(message):  logger.warning(message)
def error(message): logger.error(message)
