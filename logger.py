"""
logger.py
---------
Sentinel - File Integrity Monitoring System

Responsible for configuring the application-wide logger that writes
security events to logs/security.log. Every scan, baseline creation,
and detected change is recorded here for auditability.
"""

import logging
from pathlib import Path

# Logs always live in a "logs" folder next to this module.
LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "security.log"


def setup_logger() -> logging.Logger:
    """
    Create and configure the "sentinel" logger.

    Ensures the logs/ directory exists, attaches a file handler that
    writes timestamped entries to logs/security.log, and avoids adding
    duplicate handlers if called more than once.

    Returns:
        A configured logging.Logger instance.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger("sentinel")
    log.setLevel(logging.INFO)

    # Guard against attaching multiple handlers if setup_logger() is
    # ever called more than once during the app's lifetime.
    if not log.handlers:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        # Structured, fixed-width fields make the audit trail easy to
        # scan visually and easy to parse with a simple split on "|"
        # (Timestamp | Severity | Action/Filename/Result message body).
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

        # Prevent log messages from also being duplicated by Python's
        # root logger (e.g. printed twice to console).
        log.propagate = False

    return log
