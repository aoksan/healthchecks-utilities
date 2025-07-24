# domain_checker/logger.py
import datetime
from . import config

# Name: ideolog [Log Format] configuration
# Message pattern: ^\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]\s\[([A-Z]+)\]\s(.*)$
# Message start pattern: ^\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]
# Time format: yyyy-MM-dd HH:mm:ss
# Time capture group: 1
# Severity capture group: 2
# Category capture group: 0

def log(level, message):
    if not getattr(config, "LOGGING_ACTIVE", True):
        return
    if level == "DEBUG" and not getattr(config, "DEBUG_MODE", False):
        return
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    try:
        with open(config.LOG_FILE, "a") as f:
            f.write(log_line + "\n")
    except IOError as e:
        print(f"Warning: Could not write to log file: {e}")

def info(message):  log("INFO", message)
def debug(message): log("DEBUG", message)
def warn(message):  log("WARN", message)
def error(message): log("ERROR", message)
