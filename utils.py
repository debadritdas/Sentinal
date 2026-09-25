"""
utils.py
--------
Sentinel - File Integrity Monitoring System

Small, shared helper functions used across multiple modules. Keeping
these in one place avoids duplicating simple logic like timestamp
formatting throughout the codebase.
"""

from datetime import datetime


def get_timestamp() -> str:
    """
    Return the current date and time formatted as a consistent string.

    Returns:
        A string in the format "YYYY-MM-DD HH:MM:SS".
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_file_size(size_bytes: int) -> str:
    """
    Convert a byte count into a human-readable string (e.g. "3.2 MB").

    Args:
        size_bytes: File size in bytes.

    Returns:
        A human-readable size string.
    """
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
