"""
app.py
------
Sentinel - File Integrity Monitoring System
Main GUI application entry point.

This module builds the Tkinter interface and wires together the
scanner, baseline, hashing, logger, and report modules. It contains
no business logic of its own -- it only coordinates user actions and
displays results.

All original functionality (baseline creation, scanning, comparison,
logging, and reporting) is preserved exactly as it was. This version
only upgrades the presentation layer: a modern dark "security console"
theme, an application icon, a header, a live statistics dashboard, a
color-coded/timestamped log console, a progress bar, and professional
popup dialogs.

Author: (your name here)
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

# Local module imports (built in later steps of this project)
import baseline
import scanner
import logger
import report
import utils


# ----------------------------------------------------------------------
# THEME / DESIGN CONSTANTS
# ----------------------------------------------------------------------
# Centralizing colors and fonts here means the whole UI can be re-themed
# by changing values in one place, and keeps _build_widgets() readable.
class Theme:
    """Color palette and fonts for the Sentinel dark security console."""

    BG_MAIN = "#1E1E1E"        # Dark charcoal background
    BG_PANEL = "#2A2A2E"       # Slightly lighter panels/frames
    BG_PANEL_ALT = "#242428"   # Alternate panel shade (dashboard cards)
    BORDER = "#3A3A40"

    ACCENT_BLUE = "#2D7DFF"    # Primary buttons
    ACCENT_BLUE_HOVER = "#4C93FF"
    ACCENT_BLUE_DARK = "#1F5FCC"

    TEXT_PRIMARY = "#E8E8E8"
    TEXT_SECONDARY = "#A0A0A6"
    TEXT_MUTED = "#7A7A82"

    SUCCESS = "#3DDC84"        # Green
    WARNING = "#FFB020"        # Orange
    ERROR = "#FF5252"          # Red
    INFO = "#4FA8FF"           # Blue

    CONSOLE_BG = "#0C0F0B"     # Near-black terminal background
    CONSOLE_FG = "#39FF6A"     # Terminal green

    FONT_UI = ("Segoe UI", 10)
    FONT_UI_BOLD = ("Segoe UI", 10, "bold")
    FONT_HEADER = ("Segoe UI", 20, "bold")
    FONT_SUBHEADER = ("Segoe UI", 11)
    FONT_TAGLINE = ("Segoe UI", 9, "italic")
    FONT_DASH_LABEL = ("Segoe UI", 9)
    FONT_DASH_VALUE = ("Segoe UI", 14, "bold")
    FONT_CONSOLE = ("Consolas", 10)


class HoverButton(tk.Button):
    """
    A flat tk.Button with a simple hover-color effect, since ttk's
    styling of plain buttons is limited on some platforms and we want
    a consistent look across Windows/macOS/Linux.
    """

    def __init__(self, master, bg=Theme.ACCENT_BLUE, hover_bg=Theme.ACCENT_BLUE_HOVER,
                 fg="white", **kwargs):
        super().__init__(
            master,
            bg=bg,
            fg=fg,
            activebackground=Theme.ACCENT_BLUE_DARK,
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            font=Theme.FONT_UI_BOLD,
            cursor="hand2",
            padx=14,
            pady=8,
            **kwargs,
        )
        self._bg = bg
        self._hover_bg = hover_bg
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event) -> None:
        if str(self["state"]) != tk.DISABLED:
            self.configure(bg=self._hover_bg)

    def _on_leave(self, _event) -> None:
        if str(self["state"]) != tk.DISABLED:
            self.configure(bg=self._bg)


class SentinelApp:
    """
    Main application class for the Sentinel File Integrity Monitoring
    System. Handles all GUI construction, event bindings, and delegates
    real work (hashing, comparing, logging, reporting) to their
    respective modules.
    """

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the main window and all GUI widgets."""
        self.root = root
        self.root.title("Sentinel - File Integrity Monitoring System")
        self.root.geometry("960x720")
        self.root.minsize(860, 620)
        self.root.configure(bg=Theme.BG_MAIN)

        self._apply_icon()

        # Currently selected folder to monitor
        self.selected_folder: str = ""

        # Set up the logger as soon as the app starts so every action
        # is captured, even before a folder is selected.
        self.log = logger.setup_logger()

        # Keep a reference to the last scan results so Generate Report
        # can use them without re-scanning.
        self.last_scan_results = None

        # Dashboard state, refreshed after every scan.
        self.dashboard_vars = {
            "scanned": tk.StringVar(value="0"),
            "modified": tk.StringVar(value="0"),
            "deleted": tk.StringVar(value="0"),
            "added": tk.StringVar(value="0"),
            "last_scan": tk.StringVar(value="Never"),
            "baseline_status": tk.StringVar(value="Not Created"),
        }

        self._build_widgets()
        self._set_status("Ready")
        self._log_event("INFO", "Sentinel started", "System", "Ready")

    # ------------------------------------------------------------------
    # ICON
    # ------------------------------------------------------------------
    def _apply_icon(self) -> None:
        """Load icon.ico next to app.py if it exists; otherwise continue normally."""
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.isfile(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                # Some platforms (notably Linux) don't support .ico files;
                # this is purely cosmetic, so fail silently.
                pass

    # ------------------------------------------------------------------
    # GUI CONSTRUCTION
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        """Create and lay out all widgets in the main window."""
        self._build_header()
        self._build_folder_bar()
        self._build_action_bar()
        self._build_dashboard()
        self._build_progress_bar()
        self._build_console()
        self._build_status_bar()

    def _build_header(self) -> None:
        """Professional header banner with title and tagline."""
        header = tk.Frame(self.root, bg=Theme.BG_PANEL)
        header.pack(fill=tk.X, padx=20, pady=16)

        title_row = tk.Frame(header, bg=Theme.BG_PANEL)
        title_row.pack(fill=tk.X)

        tk.Label(
            title_row,
            text="\U0001F6E1",  # shield emoji, purely decorative
            font=("Segoe UI", 22),
            bg=Theme.BG_PANEL,
            fg=Theme.ACCENT_BLUE,
        ).pack(side=tk.LEFT, padx=(0, 10))

        title_text = tk.Frame(title_row, bg=Theme.BG_PANEL)
        title_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            title_text,
            text="Sentinel",
            font=Theme.FONT_HEADER,
            bg=Theme.BG_PANEL,
            fg=Theme.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            title_text,
            text="File Integrity Monitoring System",
            font=Theme.FONT_SUBHEADER,
            bg=Theme.BG_PANEL,
            fg=Theme.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Protecting File Integrity using SHA-256",
            font=Theme.FONT_TAGLINE,
            bg=Theme.BG_PANEL,
            fg=Theme.ACCENT_BLUE,
        ).pack(anchor="w", pady=(8, 0))

        tk.Frame(self.root, bg=Theme.BORDER, height=1).pack(fill=tk.X)

    def _build_folder_bar(self) -> None:
        """Top frame: folder path display + browse button."""
        top_frame = tk.Frame(self.root, bg=Theme.BG_MAIN)
        top_frame.pack(fill=tk.X, padx=20, pady=12)

        tk.Label(
            top_frame,
            text="Monitored Folder:",
            font=Theme.FONT_UI_BOLD,
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_PRIMARY,
        ).pack(side=tk.LEFT)

        self.folder_path_var = tk.StringVar(value="No folder selected")
        self.folder_label = tk.Label(
            top_frame,
            textvariable=self.folder_path_var,
            font=Theme.FONT_UI,
            bg=Theme.BG_MAIN,
            fg=Theme.TEXT_SECONDARY,
            anchor="w",
        )
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        HoverButton(top_frame, text="Browse Folder", command=self.browse_folder).pack(
            side=tk.RIGHT
        )

    def _build_action_bar(self) -> None:
        """Middle frame: primary action buttons."""
        button_frame = tk.Frame(self.root, bg=Theme.BG_MAIN)
        button_frame.pack(fill=tk.X, padx=20, pady=6)

        self.baseline_btn = HoverButton(
            button_frame, text="Create Baseline", width=16,
            command=self.create_baseline,
        )
        self.baseline_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.scan_btn = HoverButton(
            button_frame, text="Scan Folder", width=16,
            command=self.scan_folder,
        )
        self.scan_btn.pack(side=tk.LEFT, padx=8)

        self.report_btn = HoverButton(
            button_frame, text="Generate Report", width=16,
            command=self.generate_report,
        )
        self.report_btn.pack(side=tk.LEFT, padx=8)

        HoverButton(
            button_frame, text="Exit", width=10,
            bg="#3A3A40", hover_bg="#4A4A50",
            command=self.root.quit,
        ).pack(side=tk.RIGHT)

    def _build_dashboard(self) -> None:
        """Statistics dashboard panel, refreshed after every scan."""
        dash_outer = tk.Frame(self.root, bg=Theme.BG_MAIN)
        dash_outer.pack(fill=tk.X, padx=20, pady=6)

        dash = tk.Frame(dash_outer, bg=Theme.BG_PANEL)
        dash.pack(fill=tk.X)

        cards = [
            ("Files Scanned", "scanned", Theme.INFO),
            ("Modified", "modified", Theme.WARNING),
            ("Deleted", "deleted", Theme.ERROR),
            ("New Files", "added", Theme.SUCCESS),
            ("Last Scan", "last_scan", Theme.TEXT_PRIMARY),
            ("Baseline Status", "baseline_status", Theme.TEXT_PRIMARY),
        ]

        for col, (label_text, key, color) in enumerate(cards):
            card = tk.Frame(dash, bg=Theme.BG_PANEL_ALT, padx=14, pady=10)
            card.grid(row=0, column=col, sticky="nsew", padx=8, pady=10)
            dash.grid_columnconfigure(col, weight=1)

            tk.Label(
                card, text=label_text, font=Theme.FONT_DASH_LABEL,
                bg=Theme.BG_PANEL_ALT, fg=Theme.TEXT_MUTED,
            ).pack(anchor="w")

            value_font = Theme.FONT_UI_BOLD if key in ("last_scan", "baseline_status") \
                else Theme.FONT_DASH_VALUE
            tk.Label(
                card, textvariable=self.dashboard_vars[key], font=value_font,
                bg=Theme.BG_PANEL_ALT, fg=color,
            ).pack(anchor="w", pady=(2, 0))

    def _build_progress_bar(self) -> None:
        """Determinate-looking progress bar shown during scans."""
        progress_frame = tk.Frame(self.root, bg=Theme.BG_MAIN)
        progress_frame.pack(fill=tk.X, padx=20, pady=(4,8))

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Sentinel.Horizontal.TProgressbar",
            troughcolor=Theme.BG_PANEL,
            background=Theme.ACCENT_BLUE,
            bordercolor=Theme.BG_PANEL,
            lightcolor=Theme.ACCENT_BLUE,
            darkcolor=Theme.ACCENT_BLUE,
        )

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            style="Sentinel.Horizontal.TProgressbar",
            variable=self.progress_var,
            maximum=100,
            mode="indeterminate",
        )
        self.progress_bar.pack(fill=tk.X)

    def _build_console(self) -> None:
        """Black terminal-style console with green monospace, color-coded tags."""
        console_frame = tk.Frame(self.root, bg=Theme.BG_MAIN)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=4)

        tk.Label(
            console_frame, text="Live Event Console",
            font=Theme.FONT_UI_BOLD, bg=Theme.BG_MAIN, fg=Theme.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))

        self.output_area = scrolledtext.ScrolledText(
            console_frame,
            wrap=tk.WORD,
            font=Theme.FONT_CONSOLE,
            state=tk.DISABLED,
            bg=Theme.CONSOLE_BG,
            fg=Theme.CONSOLE_FG,
            insertbackground=Theme.CONSOLE_FG,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=8,
        )
        self.output_area.pack(fill=tk.BOTH, expand=True)

        # Color-coded severity tags for the console.
        self.output_area.tag_configure("OK", foreground=Theme.SUCCESS)
        self.output_area.tag_configure("WARNING", foreground=Theme.WARNING)
        self.output_area.tag_configure("THREAT", foreground=Theme.ERROR)
        self.output_area.tag_configure("INFO", foreground=Theme.INFO)
        self.output_area.tag_configure("TIMESTAMP", foreground=Theme.TEXT_MUTED)

    def _build_status_bar(self) -> None:
        """Bottom status bar."""
        status_frame = tk.Frame(self.root, bg=Theme.BG_PANEL, bd=0)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Frame(self.root, bg=Theme.BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            status_frame, textvariable=self.status_var, anchor="w",
            bg=Theme.BG_PANEL, fg=Theme.TEXT_SECONDARY, font=Theme.FONT_UI,
            padx=12, pady=6,
        ).pack(fill=tk.X)

    # ------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------
    def _log_event(self, severity: str, action: str, target: str, result: str) -> None:
        """
        Print a color-coded, timestamped line to the console.

        severity: one of "INFO", "OK", "WARNING", "THREAT" -- controls
            both the console color and the bracketed tag shown to the
            user (this is purely a presentation concern; the underlying
            logging.Logger records used by baseline.py/scanner.py are
            untouched).
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_area.configure(state=tk.NORMAL)
        self.output_area.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")
        self.output_area.insert(tk.END, f"{severity:<8}", severity)
        self.output_area.insert(tk.END, f"{action} | {target} | {result}\n")
        self.output_area.see(tk.END)
        self.output_area.configure(state=tk.DISABLED)

    def _print(self, message: str, severity: str = "INFO") -> None:
        """
        Append a raw line of text to the scrolling output area (kept for
        backward compatibility with the original plain-text style),
        with a timestamp and severity coloring applied.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_area.configure(state=tk.NORMAL)
        self.output_area.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")
        self.output_area.insert(tk.END, message + "\n", severity)
        self.output_area.see(tk.END)
        self.output_area.configure(state=tk.DISABLED)

    def _set_status(self, message: str) -> None:
        """Update the status bar text."""
        self.status_var.set(message)
        self.root.update_idletasks()

    def _require_folder(self) -> bool:
        """Check a folder has been selected; show an error if not."""
        if not self.selected_folder:
            messagebox.showerror("No Folder Selected", "Please select a folder first.")
            return False
        if not os.path.isdir(self.selected_folder):
            messagebox.showerror(
                "Invalid Folder", "The selected folder no longer exists."
            )
            return False
        return True

    def _start_progress(self) -> None:
        """Start the indeterminate progress bar animation."""
        self.progress_bar.start(12)

    def _stop_progress(self) -> None:
        """Stop the progress bar animation."""
        self.progress_bar.stop()

    def _set_button_state(self, state: str) -> None:
        """Enable/disable action buttons while a background task runs."""
        for btn in (self.baseline_btn, self.scan_btn, self.report_btn):
            btn.configure(state=state)

    # ------------------------------------------------------------------
    # BUTTON ACTIONS
    # ------------------------------------------------------------------
    def browse_folder(self) -> None:
        """Open a folder selection dialog and store the chosen path."""
        folder = filedialog.askdirectory(title="Select Folder to Monitor")
        if folder:
            self.selected_folder = folder
            self.folder_path_var.set(folder)
            self._print(f"[INFO] Folder selected: {folder}", "INFO")
            self._set_status("Ready")

    def create_baseline(self) -> None:
        """Create a new baseline for the selected folder (in a thread)."""
        if not self._require_folder():
            return
        self._set_button_state(tk.DISABLED)
        self._start_progress()
        threading.Thread(target=self._create_baseline_worker, daemon=True).start()

    def _create_baseline_worker(self) -> None:
        """Background worker that performs the baseline creation."""
        self._set_status("Scanning...")
        self._print(f"\n[BASELINE] Creating baseline for: {self.selected_folder}", "INFO")
        try:
            file_count = baseline.create_baseline(self.selected_folder, self.log)
            self._print(f"[BASELINE] Baseline created successfully ({file_count} files).", "OK")
            self.dashboard_vars["baseline_status"].set("Created")
            self._set_status("Baseline Created")
            self.root.after(
                0, lambda: messagebox.showinfo(
                    "Baseline Created Successfully",
                    f"Baseline created with {file_count} files.",
                )
            )
        except PermissionError as exc:
            self._print(f"[ERROR] Permission denied: {exc}", "THREAT")
            self.root.after(0, lambda: messagebox.showerror("Permission Denied", str(exc)))
            self._set_status("Ready")
        except Exception as exc:  # noqa: BLE001 - show all unexpected errors to user
            self._print(f"[ERROR] Failed to create baseline: {exc}", "THREAT")
            self.root.after(
                0, lambda: messagebox.showerror("Error", f"Failed to create baseline:\n{exc}")
            )
            self._set_status("Ready")
        finally:
            self._stop_progress()
            self._set_button_state(tk.NORMAL)

    def scan_folder(self) -> None:
        """Scan the selected folder and compare against the baseline."""
        if not self._require_folder():
            return
        self._set_button_state(tk.DISABLED)
        self._start_progress()
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        """Background worker that performs the scan-and-compare workflow."""
        self._set_status("Scanning...")
        self._print(f"\n[SCAN] Scanning folder: {self.selected_folder}", "INFO")
        start_time = datetime.now()

        try:
            old_baseline = baseline.load_baseline()
        except FileNotFoundError:
            self._print("[ERROR] baseline.json not found. Please create a baseline first.", "THREAT")
            self.root.after(
                0, lambda: messagebox.showerror(
                    "Missing Baseline",
                    "No baseline.json was found. Please create a baseline before scanning.",
                )
            )
            self._set_status("Ready")
            self._stop_progress()
            self._set_button_state(tk.NORMAL)
            return
        except ValueError as exc:
            self._print(f"[ERROR] Corrupted baseline file: {exc}", "THREAT")
            self.root.after(0, lambda: messagebox.showerror("Corrupted Baseline", str(exc)))
            self._set_status("Ready")
            self._stop_progress()
            self._set_button_state(tk.NORMAL)
            return

        try:
            current_scan = scanner.scan_folder(self.selected_folder, self.log)
            modified, deleted, added = baseline.compare_baseline(old_baseline, current_scan)

            for path, old_hash, new_hash in modified:
                self._print(f"[MODIFIED] {path}", "WARNING")
                self.log.info(f"MODIFIED | {path} | old={old_hash[:10]}... new={new_hash[:10]}...")

            for path in deleted:
                self._print(f"[DELETED] {path}", "THREAT")
                self.log.info(f"DELETED | {path}")

            for path in added:
                self._print(f"[NEW FILE DETECTED] {path}", "INFO")
                self.log.info(f"NEW FILE | {path}")

            duration = (datetime.now() - start_time).total_seconds()

            self.last_scan_results = {
                "folder": self.selected_folder,
                "total_files": len(current_scan),
                "modified": modified,
                "deleted": deleted,
                "added": added,
                "duration": duration,
                "timestamp": utils.get_timestamp(),
                "start_time": start_time,
                "end_time": datetime.now(),
            }

            # Refresh the dashboard with the latest results.
            self.dashboard_vars["scanned"].set(str(len(current_scan)))
            self.dashboard_vars["modified"].set(str(len(modified)))
            self.dashboard_vars["deleted"].set(str(len(deleted)))
            self.dashboard_vars["added"].set(str(len(added)))
            self.dashboard_vars["last_scan"].set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            severity = "OK" if not (modified or deleted or added) else "WARNING"
            self._print(
                f"[SCAN COMPLETE] {len(current_scan)} files scanned in {duration:.2f}s | "
                f"{len(modified)} modified, {len(deleted)} deleted, {len(added)} new",
                severity,
            )
            self._print("Scan Completed Successfully", "OK")
            self._set_status("Finished")

            if modified or deleted or added:
                self.root.after(
                    0, lambda: messagebox.showwarning(
                        "Threats Detected",
                        f"Changes detected:\n"
                        f"  Modified: {len(modified)}\n"
                        f"  Deleted:  {len(deleted)}\n"
                        f"  New:      {len(added)}",
                    )
                )
            else:
                self.root.after(
                    0, lambda: messagebox.showinfo(
                        "Folder Scan Completed", "No changes detected. Folder integrity intact."
                    )
                )
        except Exception as exc:  # noqa: BLE001 - never let a scan crash the app
            self._print(f"[ERROR] Scan failed: {exc}", "THREAT")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Scan failed:\n{exc}"))
            self._set_status("Ready")
        finally:
            self._stop_progress()
            self._set_button_state(tk.NORMAL)

    def generate_report(self) -> None:
        """Generate a text report from the most recent scan results."""
        if self.last_scan_results is None:
            messagebox.showwarning(
                "No Scan Data", "Please run a scan before generating a report."
            )
            return
        try:
            report_path = report.generate_report(self.last_scan_results)
            self._print(f"[REPORT] Report saved to: {report_path}", "OK")
            messagebox.showinfo("Report Saved Successfully", f"Report saved to:\n{report_path}")
        except Exception as exc:  # noqa: BLE001
            self._print(f"[ERROR] Failed to generate report: {exc}", "THREAT")
            messagebox.showerror("Error", f"Failed to generate report:\n{exc}")


def main() -> None:
    """Application entry point."""
    root = tk.Tk()
    SentinelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
