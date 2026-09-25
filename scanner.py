"""
scanner.py
----------
Sentinel - File Integrity Monitoring System

Responsible for recursively walking a target folder, computing a
SHA-256 hash for every file found, and returning a structured
dictionary describing the current state of the folder.

This module does not compare results or store them permanently --
that is the responsibility of baseline.py. scanner.py only produces
a fresh snapshot of "what exists right now".
"""

import os
import logging
from pathlib import Path
from typing import Dict

import hashing
import utils


def scan_folder(folder_path: str, log: logging.Logger) -> Dict[str, Dict[str, str]]:
    """
    Recursively scan a folder and hash every file inside it.

    Args:
        folder_path: The root folder to scan.
        log: Logger instance used to record scan events and errors.

    Returns:
        A dictionary keyed by absolute file path, where each value is
        a dict with "hash" and "last_scan" keys, e.g.:

        {
            "C:/Documents/report.pdf": {
                "hash": "ab349.....",
                "last_scan": "2026-07-14 12:10"
            }
        }
    """
    results: Dict[str, Dict[str, str]] = {}
    root = Path(folder_path)

    if not root.is_dir():
        raise NotADirectoryError(f"Not a valid directory: {folder_path}")

    # os.walk lets us skip inaccessible subdirectories gracefully instead
    # of crashing the whole scan when permission is denied somewhere.
    for current_dir, sub_dirs, file_names in os.walk(root):
        # Try to prune subdirectories we can't access before descending
        # into them, which avoids repeated PermissionErrors.
        accessible_subdirs = []
        for sd in sub_dirs:
            full_sub = os.path.join(current_dir, sd)
            if os.access(full_sub, os.R_OK):
                accessible_subdirs.append(sd)
            else:
                log.warning(f"SKIPPED (permission denied): {full_sub}")
        sub_dirs[:] = accessible_subdirs

        for file_name in file_names:
            file_path = os.path.join(current_dir, file_name)
            normalized_path = str(Path(file_path).as_posix())

            try:
                file_hash = hashing.compute_sha256(file_path)
                results[normalized_path] = {
                    "hash": file_hash,
                    "last_scan": utils.get_timestamp(),
                }
            except PermissionError:
                log.warning(f"SKIPPED (permission denied): {normalized_path}")
                continue
            except (FileNotFoundError, OSError) as exc:
                # File may have been deleted or locked mid-scan.
                log.warning(f"SKIPPED (unreadable): {normalized_path} | {exc}")
                continue

    log.info(f"Scan complete: {len(results)} files scanned in {folder_path}")
    return results
