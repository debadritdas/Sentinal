"""
hashing.py
----------
Sentinel - File Integrity Monitoring System

Responsible for one thing only: computing SHA-256 hashes of files.
Reads files in fixed-size chunks so large files never need to be
loaded fully into memory.
"""

import hashlib
from pathlib import Path

# Read files in 64 KB chunks. Large enough to be fast, small enough
# to keep memory usage low regardless of file size.
CHUNK_SIZE = 65536


def compute_sha256(file_path: str) -> str:
    """
    Compute the SHA-256 hash of a single file.

    Args:
        file_path: Full path to the file to hash.

    Returns:
        The hexadecimal SHA-256 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read due to permissions.
        OSError: For other I/O related failures (e.g. file locked).
    """
    sha256 = hashlib.sha256()
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(path, "rb") as f:
            # Stream the file in chunks instead of reading it whole,
            # this keeps memory usage constant even for very large files.
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                sha256.update(chunk)
    except PermissionError as exc:
        raise PermissionError(f"Permission denied while reading: {file_path}") from exc
    except OSError as exc:
        # Covers cases like the file being locked by another process.
        raise OSError(f"Could not read file (locked or inaccessible): {file_path}") from exc

    return sha256.hexdigest()
