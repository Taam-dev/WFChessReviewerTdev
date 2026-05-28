"""
app.py — CustomTkinter GUI Application
=======================================
Provides the desktop GUI for WFChessReviewerTdev.

Layout (top to bottom):
  ┌─────────────────────────────────────┐
  │  🏆  WFChessReviewerTdev  [logo]   │  ← Header
  ├─────────────────────────────────────┤
  │  Chess.com URL: [_______________]   │  ← URL input
  │         [▶ Start]  [⏹ Stop]        │  ← Action buttons
  ├─────────────────────────────────────┤
  │  Step: ██████░░░░ 3/5              │  ← Progress bar
  ├─────────────────────────────────────┤
  │  📋 Console Log                    │  ← Scrollable log
  │  > Generating email...             │
  │  > Registering account...          │
  ├─────────────────────────────────────┤
  │  📧 Email:    temp@grr.la           │  ← Credentials panel
  │  👤 Username: swift_knight_a3x9k2  │
  │  🔑 Password: ****************     │
  │         [📋 Copy Credentials]      │
  ├─────────────────────────────────────┤
  │  Status: ● Running                 │  ← Status bar
  └─────────────────────────────────────┘

Thread safety:
  - Automation runs in a background threading.Thread
  - Log messages are queued and processed by root.after() polling
  - GUI updates are NEVER called directly from background threads
"""

from __future__ import annotations

import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from loguru import logger

from .config import config, PROJECT_ROOT
from .automator import ChessAutomator, TOTAL_STEPS
from .credentials import Credentials

# ---------------------------------------------------------------------------
# Configure loguru for file logging (rotating, 10MB, 7-day retention)
# ---------------------------------------------------------------------------
_LOG_FILE = config.logs_dir / "app_{time:YYYY-MM-DD}.log"
logger.add(
    str(_LOG_FILE),
    rotation="10 MB",
    retention="7 days",
    level=config.log_level,
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} — {message}"
    ),
    enqueue=True,  # Thread-safe logging
    backtrace=True,
    diagnose=True,
)

# ---------------------------------------------------------------------------
# CustomTkinter global settings
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")  # "dark" / "light" / "system"
ctk.set_default_color_theme("blue")  # "blue" / "green" / "dark-blue"


class WFChessApp(ctk.CTk):
    """
    Main application window.

    Inherits from ctk.CTk (CustomTkinter's Tk replacement).
    All GUI construction happens in __init__; automation runs
    in a background thread managed by _automation_thread.
    """

    # ------------------------------------------------------------------
    # Window & layout constants
    # ------------------------------------------------------------------
    WINDOW_TITLE = "WFChessReviewerTdev v1.0.0"
    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 700
    WINDOW_DEFAULT_WIDTH = 950
    WINDOW_DEFAULT_HEIGHT = 800

    # GUI update polling interval in milliseconds
    _QUEUE_POLL_MS = 100

    # Status colors (hex or named colors)
    _STATUS_COLORS = {
        "idle": "#6B7280",  # gray
        "running": "#3B82F6",  # blue
        "done": "#10B981",  # green
        "error": "#EF4444",  # red
        "stopped": "#F59E0B",  # amber
    }

    def __init__(self) -> None:
        super().__init__()

        # ── Window configuration ──────────────────────────────────────
        self.title(self.WINDOW_TITLE)
        self.geometry(f"{self.WINDOW_DEFAULT_WIDTH}x{self.WINDOW_DEFAULT_HEIGHT}")
        self.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)

        # Set window icon if available
        icon_path = config.icon_path()
        if icon_path:
            try:
                self.iconphoto(True, ctk.CTkImage(light_image=None, dark_image=None))
            except Exception:
                pass  # Icon loading failures are non-critical

        # ── Internal state ────────────────────────────────────────────
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._automation_thread: Optional[threading.Thread] = None
        self._automator: Optional[ChessAutomator] = None
        self._credentials: Optional[Credentials] = None
        self._is_running = False
        self._current_step = 0

        # ── Build UI ──────────────────────────────────────────────────
        self._configure_grid()
        self._build_header()
        self._build_url_input()
        self._build_action_buttons()
        self._build_progress()
        self._build_log_area()
        self._build_credentials_panel()
        self._build_status_bar()

        # ── Start queue polling loop ──────────────────────────────────
        self._poll_log_queue()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info("WFChessReviewerTdev GUI initialized")
        self._log_message(
            "🏆 WFChessReviewerTdev ready. Paste a Chess.com URL and click Start."
        )
        self._set_status("idle")

    # ==================================================================
    # UI CONSTRUCTION
    # ==================================================================

    def _configure_grid(self) -> None:
        """Configure the root window's grid layout."""
        self.grid_columnconfigure(0, weight=1)
        # Row weights: header=0, url=0, buttons=0, progress=0,
        #              log=1 (expandable), creds=0, status=0
        self.grid_rowconfigure(4, weight=1)  # Log area expands

    def _build_header(self) -> None:
        """Build the application header with title and branding."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(1, weight=1)

        # App icon placeholder (chess knight emoji as text icon)
        icon_label = ctk.CTkLabel(
            header_frame,
            text="♞",
            font=ctk.CTkFont(size=48),
            text_color="#3B82F6",
        )
        icon_label.grid(row=0, column=0, rowspan=2, padx=(0, 15))

        # App title
        title_label = ctk.CTkLabel(
            header_frame,
            text="WFChessReviewerTdev",
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w",
        )
        title_label.grid(row=0, column=1, sticky="w")

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Chess.com Account Automation & Match History Reviewer",
            font=ctk.CTkFont(size=13),
            text_color="#9CA3AF",
            anchor="w",
        )
        subtitle_label.grid(row=1, column=1, sticky="w")

        # Separator line
        separator = ctk.CTkFrame(self, height=2, fg_color="#374151")
        separator.grid(row=1, column=0, sticky="ew", padx=20)

    def _build_url_input(self) -> None:
        """Build the Chess.com URL input section."""
        url_frame = ctk.CTkFrame(self, corner_radius=10)
        url_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        url_frame.grid_columnconfigure(1, weight=1)

        # Label
        url_label = ctk.CTkLabel(
            url_frame,
            text="♟  Chess.com URL:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        url_label.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="w")

        # URL input entry
        self._url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://www.chess.com/member/yourname/games",
            height=40,
            font=ctk.CTkFont(size=13),
            border_width=2,
            border_color="#374151",
        )
        self._url_entry.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ew")

    def _build_action_buttons(self) -> None:
        """Build the Start and Stop action buttons."""
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=3, column=0, pady=(0, 5))

        # Start button
        self._start_button = ctk.CTkButton(
            button_frame,
            text="▶  Start Automation",
            font=ctk.CTkFont(size=15, weight="bold"),
            width=200,
            height=45,
            corner_radius=10,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self._on_start_clicked,
        )
        self._start_button.grid(row=0, column=0, padx=10)

        # Stop button
        self._stop_button = ctk.CTkButton(
            button_frame,
            text="⏹  Stop",
            font=ctk.CTkFont(size=15, weight="bold"),
            width=140,
            height=45,
            corner_radius=10,
            fg_color="#6B7280",
            hover_color="#4B5563",
            state="disabled",
            command=self._on_stop_clicked,
        )
        self._stop_button.grid(row=0, column=1, padx=10)

    def _build_progress(self) -> None:
        """Build the step progress bar and indicator."""
        progress_frame = ctk.CTkFrame(self, corner_radius=10)
        progress_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(5, 5))
        progress_frame.grid_columnconfigure(1, weight=1)

        # "Step:" label
        step_label = ctk.CTkLabel(
            progress_frame,
            text="Progress:",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=80,
        )
        step_label.grid(row=0, column=0, padx=(15, 10), pady=12)

        # Progress bar
        self._progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=18,
            corner_radius=9,
            progress_color="#3B82F6",
        )
        self._progress_bar.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=12)
        self._progress_bar.set(0)

        # Step counter label (e.g., "Step 3 / 5")
        self._step_label = ctk.CTkLabel(
            progress_frame,
            text="Step 0 / 5",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
            width=90,
        )
        self._step_label.grid(row=0, column=2, padx=(0, 15), pady=12)

    def _build_log_area(self) -> None:
        """Build the scrollable real-time log/console area."""
        log_frame = ctk.CTkFrame(self, corner_radius=10)
        log_frame.grid(row=5, column=0, sticky="nsew", padx=20, pady=5)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        # Log header with clear button
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        log_header.grid_columnconfigure(0, weight=1)

        log_title = ctk.CTkLabel(
            log_header,
            text="📋  Console Log",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        log_title.grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
            log_header,
            text="Clear",
            width=60,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#374151",
            hover_color="#4B5563",
            command=self._clear_log,
        )
        clear_btn.grid(row=0, column=1, sticky="e")

        # Scrollable text area for log messages
        self._log_textbox = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Courier New", size=12),
            wrap="word",
            state="disabled",
            fg_color="#111827",
            text_color="#D1FAE5",
            border_width=1,
            border_color="#374151",
            scrollbar_button_color="#374151",
        )
        self._log_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.grid_rowconfigure(5, weight=1)

    def _build_credentials_panel(self) -> None:
        """Build the panel displaying generated credentials after registration."""
        creds_frame = ctk.CTkFrame(self, corner_radius=10)
        creds_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=5)
        creds_frame.grid_columnconfigure(1, weight=1)

        # Panel title
        creds_title = ctk.CTkLabel(
            creds_frame,
            text="🔐  Generated Credentials",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        creds_title.grid(
            row=0, column=0, columnspan=3, padx=15, pady=(12, 5), sticky="w"
        )

        # Email row
        ctk.CTkLabel(
            creds_frame,
            text="📧 Email:",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
            width=100,
            anchor="e",
        ).grid(row=1, column=0, padx=(15, 5), pady=4, sticky="e")

        self._cred_email_var = ctk.StringVar(value="—")
        ctk.CTkLabel(
            creds_frame,
            textvariable=self._cred_email_var,
            font=ctk.CTkFont(family="Courier New", size=12),
            anchor="w",
        ).grid(row=1, column=1, sticky="w", pady=4)

        # Username row
        ctk.CTkLabel(
            creds_frame,
            text="👤 Username:",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
            width=100,
            anchor="e",
        ).grid(row=2, column=0, padx=(15, 5), pady=4, sticky="e")

        self._cred_username_var = ctk.StringVar(value="—")
        ctk.CTkLabel(
            creds_frame,
            textvariable=self._cred_username_var,
            font=ctk.CTkFont(family="Courier New", size=12),
            anchor="w",
        ).grid(row=2, column=1, sticky="w", pady=4)

        # Password row
        ctk.CTkLabel(
            creds_frame,
            text="🔑 Password:",
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
            width=100,
            anchor="e",
        ).grid(row=3, column=0, padx=(15, 5), pady=4, sticky="e")

        self._cred_password_var = ctk.StringVar(value="—")
        self._password_label = ctk.CTkLabel(
            creds_frame,
            textvariable=self._cred_password_var,
            font=ctk.CTkFont(family="Courier New", size=12),
            anchor="w",
        )
        self._password_label.grid(row=3, column=1, sticky="w", pady=4)

        # Toggle password visibility button
        self._show_password = False
        self._toggle_pw_btn = ctk.CTkButton(
            creds_frame,
            text="👁",
            width=35,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#374151",
            hover_color="#4B5563",
            command=self._toggle_password_visibility,
        )
        self._toggle_pw_btn.grid(row=3, column=2, padx=(5, 15), pady=4)

        # Copy credentials button
        self._copy_btn = ctk.CTkButton(
            creds_frame,
            text="📋  Copy Credentials",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=200,
            height=36,
            corner_radius=8,
            fg_color="#374151",
            hover_color="#4B5563",
            state="disabled",
            command=self._copy_credentials,
        )
        self._copy_btn.grid(row=4, column=0, columnspan=3, pady=(8, 15))

    def _build_status_bar(self) -> None:
        """Build the bottom status bar."""
        status_frame = ctk.CTkFrame(self, corner_radius=0, height=36)
        status_frame.grid(row=7, column=0, sticky="ew")
        status_frame.grid_propagate(False)
        status_frame.grid_columnconfigure(1, weight=1)

        # Status indicator dot
        self._status_dot = ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color=self._STATUS_COLORS["idle"],
            width=20,
        )
        self._status_dot.grid(row=0, column=0, padx=(15, 5), pady=5)

        # Status text
        self._status_var = ctk.StringVar(value="Idle")
        self._status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self._status_var,
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self._status_label.grid(row=0, column=1, sticky="w", pady=5)

        # Version / right-side label
        ver_label = ctk.CTkLabel(
            status_frame,
            text="v1.0.0  |  WFChessReviewerTdev",
            font=ctk.CTkFont(size=11),
            text_color="#6B7280",
        )
        ver_label.grid(row=0, column=2, padx=15, pady=5)

    # ==================================================================
    # EVENT HANDLERS
    # ==================================================================

    def _on_start_clicked(self) -> None:
        """Handle the Start button click event."""
        if self._is_running:
            self._log_message("⚠️  Automation is already running.")
            return

        target_url = self._url_entry.get().strip()
        if not target_url:
            self._log_message("⚠️  Please enter a Chess.com URL before clicking Start.")
            self._url_entry.focus()
            return

        # Validate URL looks like Chess.com
        if "chess.com" not in target_url.lower():
            self._log_message(
                "⚠️  URL doesn't appear to be a Chess.com URL. "
                "Please check and try again."
            )
            return

        # Reset state
        self._clear_credentials_display()
        self._reset_progress()
        self._set_status("running")
        self._start_button.configure(state="disabled")
        self._stop_button.configure(
            state="normal", fg_color="#EF4444", hover_color="#DC2626"
        )

        self._is_running = True
        self._log_message(f"🚀 Starting automation for URL: {target_url}")
        logger.info(f"Automation started for target: {target_url}")

        # Create automator with thread-safe callbacks
        self._automator = ChessAutomator(
            log_callback=self._queue_log_message,
            step_callback=self._queue_step_update,
            target_url=target_url,
        )

        # Launch background thread
        self._automation_thread = threading.Thread(
            target=self._run_automation,
            name="AutomationThread",
            daemon=True,
        )
        self._automation_thread.start()

    def _on_stop_clicked(self) -> None:
        """Handle the Stop button click event."""
        if not self._is_running:
            return

        self._log_message("⏹️  Stop requested — finishing current step...")
        self._set_status("stopped")

        if self._automator:
            self._automator.request_stop()

        self._stop_button.configure(state="disabled")

    def _on_close(self) -> None:
        """Handle window close event — ensure clean shutdown."""
        if self._is_running and self._automator:
            self._automator.request_stop()
            # Give thread a moment to clean up
            if self._automation_thread:
                self._automation_thread.join(timeout=3.0)
        self.destroy()

    # ==================================================================
    # AUTOMATION THREAD RUNNER
    # ==================================================================

    def _run_automation(self) -> None:
        """
        Target function for the background automation thread.

        Runs the full automation workflow and updates GUI state
        on completion via root.after() (thread-safe).
        """
        try:
            assert self._automator is not None
            self._automator.run()

            # Success — update GUI from main thread
            self.after(0, self._on_automation_success)

        except Exception as exc:
            error_msg = str(exc)
            logger.exception(f"Automation thread error: {error_msg}")
            self.after(0, lambda: self._on_automation_error(error_msg))

        finally:
            self._is_running = False

    def _on_automation_success(self) -> None:
        """Called on the main thread when automation completes successfully."""
        self._set_status("done")
        self._start_button.configure(state="normal")
        self._stop_button.configure(
            state="disabled",
            fg_color="#6B7280",
            hover_color="#4B5563",
        )
        self._update_progress_bar(TOTAL_STEPS, TOTAL_STEPS)

        # Show credentials if available
        if self._automator and self._automator.credentials:
            self._show_credentials(self._automator.credentials)

        self._log_message("✅ All steps completed! Browser stays open for your review.")

    def _on_automation_error(self, error_msg: str) -> None:
        """Called on the main thread when automation encounters an error."""
        self._set_status("error")
        self._start_button.configure(state="normal")
        self._stop_button.configure(
            state="disabled",
            fg_color="#6B7280",
            hover_color="#4B5563",
        )
        self._log_message(f"❌ Automation failed: {error_msg}")

        # Show partial credentials if any were generated
        if self._automator and self._automator.credentials:
            self._show_credentials(self._automator.credentials)

    # ==================================================================
    # THREAD-SAFE MESSAGE QUEUING
    # ==================================================================

    def _queue_log_message(self, message: str) -> None:
        """
        Thread-safe: enqueue a log message from the automation thread.

        Parameters
        ----------
        message : str
            The log message string to display.
        """
        self._log_queue.put(("log", message))

    def _queue_step_update(self, current: int, total: int) -> None:
        """
        Thread-safe: enqueue a step update from the automation thread.

        Parameters
        ----------
        current : int
            Current step number (1-based).
        total : int
            Total number of steps.
        """
        self._log_queue.put(("step", (current, total)))

    def _poll_log_queue(self) -> None:
        """
        Poll the message queue and process pending GUI updates.

        Called repeatedly by root.after() — runs on the main thread.
        This is the ONLY place where log messages and step updates
        from the background thread are applied to the GUI.
        """
        try:
            while True:  # Process all pending messages in one poll
                msg_type, payload = self._log_queue.get_nowait()

                if msg_type == "log":
                    self._log_message(payload)
                elif msg_type == "step":
                    current, total = payload
                    self._update_progress_bar(current, total)

        except queue.Empty:
            pass  # No more messages this poll cycle
        finally:
            # Schedule next poll
            self.after(self._QUEUE_POLL_MS, self._poll_log_queue)

    # ==================================================================
    # GUI UPDATE HELPERS (main thread only)
    # ==================================================================

    def _log_message(self, message: str) -> None:
        """
        Append a timestamped message to the scrollable log area.

        Must only be called from the main thread.

        Parameters
        ----------
        message : str
            Message text to append.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"

        self._log_textbox.configure(state="normal")
        self._log_textbox.insert("end", formatted)
        self._log_textbox.configure(state="disabled")
        self._log_textbox.see("end")  # Auto-scroll to bottom

        # Also log to loguru
        logger.info(message.replace("━━━", "---").strip())

    def _clear_log(self) -> None:
        """Clear all text from the log area."""
        self._log_textbox.configure(state="normal")
        self._log_textbox.delete("1.0", "end")
        self._log_textbox.configure(state="disabled")

    def _set_status(self, status: str) -> None:
        """
        Update the status bar indicator dot and text.

        Parameters
        ----------
        status : str
            One of: "idle", "running", "done", "error", "stopped".
        """
        color = self._STATUS_COLORS.get(status, "#6B7280")
        status_text = status.capitalize()

        self._status_dot.configure(text_color=color)
        self._status_var.set(f"Status: {status_text}")

    def _update_progress_bar(self, current: int, total: int) -> None:
        """
        Update the progress bar and step label.

        Parameters
        ----------
        current : int
            Current step (0-based means "before step 1").
        total : int
            Total number of steps.
        """
        self._current_step = current
        progress = current / total if total > 0 else 0
        self._progress_bar.set(progress)
        self._step_label.configure(text=f"Step {current} / {total}")

    def _reset_progress(self) -> None:
        """Reset progress bar to zero."""
        self._progress_bar.set(0)
        self._step_label.configure(text="Step 0 / 5")

    def _show_credentials(self, creds: Credentials) -> None:
        """
        Display generated credentials in the credentials panel.

        Parameters
        ----------
        creds : Credentials
            The credentials to display.
        """
        self._credentials = creds
        self._cred_email_var.set(creds.email)
        self._cred_username_var.set(creds.username)

        # Show masked password initially
        self._show_password = False
        self._cred_password_var.set("●" * len(creds.password))

        # Enable copy button
        self._copy_btn.configure(
            state="normal",
            fg_color="#3B82F6",
            hover_color="#2563EB",
        )
        self._toggle_pw_btn.configure(state="normal")

        self._log_message(
            f"🔐 Credentials displayed — click '📋 Copy Credentials' to copy"
        )

    def _clear_credentials_display(self) -> None:
        """Reset credentials panel to empty state."""
        self._credentials = None
        self._cred_email_var.set("—")
        self._cred_username_var.set("—")
        self._cred_password_var.set("—")
        self._copy_btn.configure(
            state="disabled",
            fg_color="#374151",
            hover_color="#4B5563",
        )
        self._toggle_pw_btn.configure(state="disabled")

    def _toggle_password_visibility(self) -> None:
        """Toggle between masked and visible password display."""
        if not self._credentials:
            return

        self._show_password = not self._show_password
        if self._show_password:
            self._cred_password_var.set(self._credentials.password)
            self._toggle_pw_btn.configure(text="🙈")
        else:
            self._cred_password_var.set("●" * len(self._credentials.password))
            self._toggle_pw_btn.configure(text="👁")

    def _copy_credentials(self) -> None:
        """Copy credentials to system clipboard."""
        if not self._credentials:
            return

        text = self._credentials.display_string()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

        # Temporarily change button text to confirm copy
        self._copy_btn.configure(text="✅  Copied!")
        self.after(2000, lambda: self._copy_btn.configure(text="📋  Copy Credentials"))

        self._log_message("📋 Credentials copied to clipboard!")


def run_app() -> None:
    """
    Entry point function: create and run the GUI application.

    This is registered as the console script in pyproject.toml.
    """
    logger.info("Starting WFChessReviewerTdev application...")
    app = WFChessApp()
    app.mainloop()
    logger.info("Application closed.")


if __name__ == "__main__":
    run_app()
