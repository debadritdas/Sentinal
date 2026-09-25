"""
baseline.py
-----------
Sentinel - File Integrity Monitoring System

Responsible for everything related to the baseline snapshot:
  - Creating a new baseline from a folder scan
  - Saving it to baseline.json
  - Loading an existing baseline from disk
  - Comparing an old baseline against a fresh scan to detect
    modified, deleted, and newly added files.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

import scanner

# baseline.json always lives next to this module, regardless of the
# current working directory the app was launched from.
BASELINE_PATH = Path(__file__).parent / "baseline.json"


def create_baseline(folder_path: str, log: logging.Logger) -> int:
    """
    Scan a folder and save the results as the new baseline.json.

    Args:
        folder_path: Folder to build the baseline from.
        log: Logger instance for recording the event.

    Returns:
        The number of files included in the baseline.
    """
    data = scanner.scan_folder(folder_path, log)
    save_baseline(data)
    log.info(f"Baseline created for '{folder_path}' with {len(data)} files.")
    return len(data)


def save_baseline(data: Dict[str, Dict[str, str]]) -> None:
    """
    Write baseline data to baseline.json as nicely formatted JSON.

    Args:
        data: The baseline dictionary to persist.
    """
    try:
        with open(BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except OSError as exc:
        raise OSError(f"Could not write baseline.json: {exc}") from exc


def load_baseline() -> Dict[str, Dict[str, str]]:
    """
    Load the existing baseline.json file from disk.

    Returns:
        The parsed baseline dictionary.

    Raises:
        FileNotFoundError: If baseline.json does not exist yet.
        ValueError: If baseline.json exists but contains invalid JSON
            (i.e. it is corrupted).
    """
    if not BASELINE_PATH.exists():
        raise FileNotFoundError("baseline.json does not exist. Create a baseline first.")

    try:
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "baseline.json is corrupted or not valid JSON. "
            "Please create a new baseline."
        ) from exc


def compare_baseline(
    old_data: Dict[str, Dict[str, str]],
    new_data: Dict[str, Dict[str, str]],
) -> Tuple[List[Tuple[str, str, str]], List[str], List[str]]:
    """
    Compare an old baseline snapshot against a fresh scan.

    Args:
        old_data: The previously saved baseline.
        new_data: The results of a fresh folder scan.

    Returns:
        A tuple of (modified, deleted, added):
          - modified: list of (file_path, old_hash, new_hash)
          - deleted: list of file_paths present in old_data but not new_data
          - added: list of file_paths present in new_data but not old_data
    """
    modified: List[Tuple[str, str, str]] = []
    deleted: List[str] = []
    added: List[str] = []

    old_paths = set(old_data.keys())
    new_paths = set(new_data.keys())

    # Files present in both -> check if the hash changed.
    for path in old_paths & new_paths:
        old_hash = old_data[path].get("hash")
        new_hash = new_data[path].get("hash")
        if old_hash != new_hash:
            modified.append((path, old_hash, new_hash))

    # Files only in the old baseline -> deleted.
    for path in old_paths - new_paths:
        deleted.append(path)

    # Files only in the new scan -> newly added.
    for path in new_paths - old_paths:
        added.append(path)

    return modified, deleted, added
