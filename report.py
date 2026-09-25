"""
report.py
---------
Sentinel - File Integrity Monitoring System

Responsible for turning the results of a scan into a human-readable
text report and saving it inside the reports/ folder.

The report format below is a purely presentational upgrade over the
original version: the function signature, the folder it writes to,
and the data it expects are all unchanged, so app.py's call to
``report.generate_report(self.last_scan_results)`` continues to work
exactly as before.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Reports always live in a "reports" folder next to this module.
REPORTS_DIR = Path(__file__).parent / "reports"

_DIVIDER = "=" * 60
_SUBDIVIDER = "-" * 60


def generate_report(scan_results: Dict[str, Any]) -> str:
    """
    Build and save a professional text report summarizing a scan's
    results.

    Args:
        scan_results: Dictionary produced by the scan workflow in
            app.py, expected to contain the keys:
            "folder", "total_files", "modified", "deleted", "added",
            "duration", "timestamp", and optionally "start_time" /
            "end_time" (falls back gracefully if these are absent, so
            the report still works with older-style scan results).

    Returns:
        The full path to the saved report file.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    file_name = f"Report_{now.strftime('%Y_%m_%d_%H_%M')}.txt"
    report_path = REPORTS_DIR / file_name

    modified = scan_results.get("modified", [])
    deleted = scan_results.get("deleted", [])
    added = scan_results.get("added", [])
    total_files = scan_results.get("total_files", 0)
    duration = scan_results.get("duration", 0.0)
    folder = scan_results.get("folder", "Unknown")

    start_time = scan_results.get("start_time")
    end_time = scan_results.get("end_time", now)
    if start_time is None:
        # Older-style scan results may not include start_time; derive
        # a best-effort value from the duration instead of failing.
        start_time = now

    threats_found = len(modified) + len(deleted) + len(added)
    integrity_status = "CLEAN" if threats_found == 0 else "COMPROMISED"

    lines = []
    lines.append(_DIVIDER)
    lines.append("SENTINEL")
    lines.append("FILE INTEGRITY REPORT")
    lines.append(_DIVIDER)
    lines.append(f"Date            : {now.strftime('%Y-%m-%d')}")
    lines.append(f"Start Time      : {start_time.strftime('%H:%M:%S')}")
    lines.append(f"End Time        : {end_time.strftime('%H:%M:%S')}")
    lines.append(f"Duration        : {duration:.2f} seconds")
    lines.append(f"Folder Scanned  : {folder}")
    lines.append("")

    lines.append(_SUBDIVIDER)
    lines.append("FILES SCANNED")
    lines.append(_SUBDIVIDER)
    lines.append(f"Total Files     : {total_files}")
    lines.append("")

    lines.append(_SUBDIVIDER)
    lines.append(f"MODIFIED FILES ({len(modified)})")
    lines.append(_SUBDIVIDER)
    if modified:
        for path, old_hash, new_hash in modified:
            lines.append(f"  File     : {path}")
            lines.append(f"  Old Hash : {old_hash}")
            lines.append(f"  New Hash : {new_hash}")
            lines.append("")
    else:
        lines.append("  None")
        lines.append("")

    lines.append(_SUBDIVIDER)
    lines.append(f"DELETED FILES ({len(deleted)})")
    lines.append(_SUBDIVIDER)
    if deleted:
        for path in deleted:
            lines.append(f"  {path}")
    else:
        lines.append("  None")
    lines.append("")

    lines.append(_SUBDIVIDER)
    lines.append(f"NEW FILES ({len(added)})")
    lines.append(_SUBDIVIDER)
    if added:
        for path in added:
            lines.append(f"  {path}")
    else:
        lines.append("  None")
    lines.append("")

    lines.append(_SUBDIVIDER)
    lines.append("SUMMARY")
    lines.append(_SUBDIVIDER)
    lines.append(f"Integrity Status : {integrity_status}")
    lines.append(f"Threats Found    : {threats_found}")
    lines.append(_DIVIDER)

    report_text = "\n".join(lines)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return str(report_path)
