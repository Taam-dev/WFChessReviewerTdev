#!/usr/bin/env python3
"""
WFChessReviewerTdev - Chess.com Match Review Helper
https://github.com/Taam-dev/WFChessReviewerTdev
"""

__version__ = "1.1.0"
__author__ = "Taam-dev"
__repo__ = "https://github.com/Taam-dev/WFChessReviewerTdev"

import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import string
import random
import time
import uuid
import json
import os
import sys
from pathlib import Path

# PIL for background image
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Config ──
CONFIG_DIR = Path.home() / ".wfchessreviewer"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "url": "https://www.chess.com/member/tamle111/games",
    "provider": "temp-mail.org",
    "board_position": "Top Left",
    "auto_review": True,
    "bg_image_path": "",
    "bg_opacity": 0.3,
}


def load_config():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(saved)
            return config
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def resource_path(relative_path):
    """Get path for bundled resources (works with PyInstaller)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def generate_random_username():
    prefixes = ["x", "z", "q", "v", "k", "j", "w", "n", "m", "r", "p", "d",
                "fx", "zx", "qv", "kj", "xr", "vn", "wz", "mk", "pj", "dr"]
    unique_id = uuid.uuid4().hex[:10]
    prefix = random.choice(prefixes)
    return f"{prefix}{unique_id}"


def generate_random_password():
    length = random.randint(8, 12)
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
    ]
    password += random.choices(string.ascii_letters + string.digits, k=length - 3)
    random.shuffle(password)
    return ''.join(password)


BOARD_POSITIONS = {
    "Top Left": 1, "Top Right": 2,
    "Bottom Left": 3, "Bottom Right": 4,
}


class ChessAutomationApp:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.bg_photo = None
        self.bg_label = None

        self.root.title(f"WFChessReviewerTdev v{__version__}")
        self.root.geometry("640x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        # Set window icon
        self._set_icon()

        # Build UI
        self._build_ui()

        # Apply saved background
        if self.config.get("bg_image_path"):
            self._apply_background(self.config["bg_image_path"], self.config.get("bg_opacity", 0.3))

        # Save on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self):
        """Set window icon — try .ico file first, fallback to built-in."""
        try:
            ico_path = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
                return
        except Exception:
            pass

        try:
            png_path = resource_path(os.path.join("assets", "icon.png"))
            if os.path.exists(png_path) and HAS_PIL:
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                self._icon_photo = photo  # keep reference
                return
        except Exception:
            pass

    def _build_ui(self):
        # Background canvas (behind everything)
        self.canvas = tk.Canvas(self.root, width=640, height=620,
                                 bg="#1e1e2e", highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Main frame on top of canvas
        self.main_frame = tk.Frame(self.root, bg="#1e1e2e")
        self.main_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Title
        tk.Label(
            self.main_frame, text="♟ WFChessReviewerTdev",
            font=("Segoe UI", 18, "bold"), bg="#1e1e2e", fg="#cdd6f4",
        ).pack(pady=(12, 2))

        tk.Label(
            self.main_frame, text=f"v{__version__} — Auto sign-up → onboarding → review",
            font=("Segoe UI", 10), bg="#1e1e2e", fg="#6c7086",
        ).pack(pady=(0, 8))

        # URL Input
        input_frame = tk.Frame(self.main_frame, bg="#1e1e2e")
        input_frame.pack(pady=4, padx=40, fill="x")

        tk.Label(
            input_frame, text="Chess.com Match History URL:",
            font=("Segoe UI", 10), bg="#1e1e2e", fg="#a6adc8", anchor="w",
        ).pack(fill="x", pady=(0, 3))

        self.url_entry = tk.Entry(
            input_frame, font=("Segoe UI", 10),
            bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
            relief="flat", highlightthickness=2,
            highlightbackground="#45475a", highlightcolor="#89b4fa",
        )
        self.url_entry.pack(fill="x", ipady=6)
        self.url_entry.insert(0, self.config.get("url", DEFAULT_CONFIG["url"]))

        # Options Row
        options_frame = tk.Frame(self.main_frame, bg="#1e1e2e")
        options_frame.pack(pady=(8, 4), padx=40, fill="x")

        # Temp-mail
        mail_frame = tk.LabelFrame(
            options_frame, text=" Temp-mail ",
            font=("Segoe UI", 9), bg="#1e1e2e", fg="#a6adc8",
            relief="groove", bd=1,
        )
        mail_frame.pack(side="left", fill="y", padx=(0, 8))

        self.provider_var = tk.StringVar(value=self.config.get("provider", "temp-mail.org"))
        for prov in ["temp-mail.org", "temp-mail.io"]:
            tk.Radiobutton(
                mail_frame, text=prov, variable=self.provider_var, value=prov,
                font=("Segoe UI", 8), bg="#1e1e2e", fg="#cdd6f4",
                selectcolor="#313244", activebackground="#1e1e2e",
            ).pack(anchor="w", padx=6, pady=0)

        # Board theme
        board_frame = tk.LabelFrame(
            options_frame, text=" Board Theme ",
            font=("Segoe UI", 9), bg="#1e1e2e", fg="#a6adc8",
            relief="groove", bd=1,
        )
        board_frame.pack(side="left", fill="both", expand=True)

        grid_frame = tk.Frame(board_frame, bg="#1e1e2e")
        grid_frame.pack(padx=6, pady=3)

        self.board_var = tk.StringVar(value=self.config.get("board_position", "Top Left"))
        for label, row, col in [("Top Left", 0, 0), ("Top Right", 0, 1),
                                  ("Bottom Left", 1, 0), ("Bottom Right", 1, 1)]:
            tk.Radiobutton(
                grid_frame, text=label, variable=self.board_var, value=label,
                font=("Segoe UI", 8), bg="#1e1e2e", fg="#cdd6f4",
                selectcolor="#313244", activebackground="#1e1e2e",
                indicatoron=0, width=11, relief="groove", bd=1, padx=3, pady=2,
            ).grid(row=row, column=col, padx=2, pady=1)

        # Auto-review
        auto_frame = tk.Frame(self.main_frame, bg="#1e1e2e")
        auto_frame.pack(pady=(6, 3), padx=40, fill="x")

        self.auto_review_var = tk.BooleanVar(value=self.config.get("auto_review", True))
        tk.Checkbutton(
            auto_frame, text="  Auto-click Review (most recent match)",
            variable=self.auto_review_var,
            font=("Segoe UI", 10), bg="#1e1e2e", fg="#cdd6f4",
            selectcolor="#313244", activebackground="#1e1e2e",
        ).pack(anchor="w")

        # ── Background Settings ──
        bg_frame = tk.LabelFrame(
            self.main_frame, text=" 🎨 Background ",
            font=("Segoe UI", 9), bg="#1e1e2e", fg="#a6adc8",
            relief="groove", bd=1,
        )
        bg_frame.pack(pady=(6, 3), padx=40, fill="x")

        bg_row1 = tk.Frame(bg_frame, bg="#1e1e2e")
        bg_row1.pack(fill="x", padx=8, pady=(4, 2))

        self.bg_path_var = tk.StringVar(value=self.config.get("bg_image_path", ""))
        self.bg_path_label = tk.Label(
            bg_row1,
            textvariable=self.bg_path_var,
            font=("Segoe UI", 8), bg="#1e1e2e", fg="#585b70",
            anchor="w", width=40,
        )
        self.bg_path_label.pack(side="left", fill="x", expand=True)

        tk.Button(
            bg_row1, text="Browse", font=("Segoe UI", 8, "bold"),
            bg="#45475a", fg="#cdd6f4", relief="flat", padx=8,
            command=self._browse_bg_image,
        ).pack(side="left", padx=(4, 2))

        tk.Button(
            bg_row1, text="Clear", font=("Segoe UI", 8, "bold"),
            bg="#45475a", fg="#f38ba8", relief="flat", padx=8,
            command=self._clear_bg_image,
        ).pack(side="left", padx=2)

        bg_row2 = tk.Frame(bg_frame, bg="#1e1e2e")
        bg_row2.pack(fill="x", padx=8, pady=(2, 6))

        tk.Label(
            bg_row2, text="Opacity:", font=("Segoe UI", 8),
            bg="#1e1e2e", fg="#a6adc8",
        ).pack(side="left")

        self.opacity_var = tk.DoubleVar(value=self.config.get("bg_opacity", 0.3))
        self.opacity_scale = ttk.Scale(
            bg_row2, from_=0.05, to=1.0, variable=self.opacity_var,
            orient="horizontal", length=200,
            command=self._on_opacity_change,
        )
        self.opacity_scale.pack(side="left", padx=(4, 4), fill="x", expand=True)

        self.opacity_label = tk.Label(
            bg_row2, text=f"{self.opacity_var.get():.0%}",
            font=("Segoe UI", 8, "bold"), bg="#1e1e2e", fg="#89b4fa", width=5,
        )
        self.opacity_label.pack(side="left")

        # ── Start Button ──
        self.start_button = tk.Button(
            self.main_frame, text="▶  START",
            font=("Segoe UI", 13, "bold"),
            bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec", activeforeground="#1e1e2e",
            relief="flat", cursor="hand2",
            command=self._on_start_click, width=20, height=1,
        )
        self.start_button.pack(pady=10)

        # Status
        self.status_var = tk.StringVar(value="Ready. Enter a URL and click START.")
        self.status_label = tk.Label(
            self.main_frame, textvariable=self.status_var,
            font=("Segoe UI", 9), bg="#1e1e2e", fg="#a6e3a1", wraplength=560,
        )
        self.status_label.pack(pady=(0, 4))

        tk.Label(
            self.main_frame,
            text="github.com/Taam-dev/WFChessReviewerTdev",
            font=("Segoe UI", 8, "italic"), bg="#1e1e2e", fg="#45475a",
        ).pack(side="bottom", pady=4)

    # ── Background Image Methods ──

    def _browse_bg_image(self):
        path = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.bg_path_var.set(path)
            self._apply_background(path, self.opacity_var.get())

    def _clear_bg_image(self):
        self.bg_path_var.set("")
        self.bg_photo = None
        if self.bg_label:
            self.bg_label.destroy()
            self.bg_label = None
        self.canvas.delete("bg")

    def _on_opacity_change(self, val):
        opacity = float(val)
        self.opacity_label.config(text=f"{opacity:.0%}")
        path = self.bg_path_var.get()
        if path:
            self._apply_background(path, opacity)

    def _apply_background(self, image_path, opacity):
        if not HAS_PIL:
            self._update_status("Install Pillow for background: pip install Pillow", "#fab387")
            return
        if not os.path.exists(image_path):
            return

        try:
            img = Image.open(image_path).convert("RGBA")
            # Resize to fit window
            img = img.resize((640, 620), Image.LANCZOS)

            # Create dark overlay for opacity effect
            overlay = Image.new("RGBA", img.size, (30, 30, 46, int(255 * (1 - opacity))))
            blended = Image.alpha_composite(img, overlay)
            blended = blended.convert("RGB")

            self.bg_photo = ImageTk.PhotoImage(blended)

            if self.bg_label:
                self.bg_label.destroy()

            self.bg_label = tk.Label(self.canvas, image=self.bg_photo)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower()

            # Make main frame transparent-looking
            self._set_frame_transparent(self.main_frame)

        except Exception as e:
            self._update_status(f"Background error: {e}", "#f38ba8")

    def _set_frame_transparent(self, frame):
        """Make frame and its label children semi-transparent by removing bg."""
        # We can't truly make tkinter transparent, but we can set bg to empty
        # The visual effect works because the bg_label is behind main_frame
        pass  # Tkinter limitation — the dark bg still looks good with the overlay

    # ── Save / Close ──

    def _save_current_config(self):
        self.config = {
            "url": self.url_entry.get().strip(),
            "provider": self.provider_var.get(),
            "board_position": self.board_var.get(),
            "auto_review": self.auto_review_var.get(),
            "bg_image_path": self.bg_path_var.get(),
            "bg_opacity": round(self.opacity_var.get(), 2),
        }
        save_config(self.config)

    def _on_close(self):
        self._save_current_config()
        self.root.destroy()

    # ── Status ──

    def _update_status(self, message, color="#a6e3a1"):
        self.root.after(0, lambda: self.status_var.set(message))
        self.root.after(0, lambda: self.status_label.configure(fg=color))

    def _on_start_click(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a Chess.com match history URL.")
            return
        if "chess.com" not in url.lower():
            if not messagebox.askyesno("URL Check",
                    "The URL doesn't look like Chess.com. Continue anyway?"):
                return
        self._save_current_config()
        self.start_button.configure(state="disabled", bg="#585b70", text="⏳ RUNNING...")
        board_choice = self.board_var.get()
        auto_review = self.auto_review_var.get()
        threading.Thread(
            target=self._run_automation,
            args=(url, self.provider_var.get(), board_choice, auto_review),
            daemon=True,
        ).start()

    # ── Automation Methods ──

    def _grab_temp_email(self, tab_mail, provider):
        if provider == "temp-mail.org":
            selectors = ["#mail", "input#mail", ".email-address input"]
        else:
            selectors = ["#email", "input#email", ".email-box input", "input[name='email']"]
        for _ in range(12):
            for sel in selectors:
                try:
                    el = tab_mail.locator(sel).first
                    if el.count() > 0:
                        val = el.input_value(timeout=1500)
                        if val and "@" in val and "loading" not in val.lower():
                            return val.strip()
                except Exception:
                    continue
            time.sleep(2)
        return None

    def _fast_fill_field(self, page, selector, text):
        for attempt in range(3):
            try:
                field = page.locator(selector).first
                if field.count() == 0 or not field.is_visible(timeout=2000):
                    return False
                field.wait_for(state="visible", timeout=3000)
                time.sleep(0.2)
                field.click(timeout=2000)
                time.sleep(0.2)
                field.fill("", timeout=1000)
                time.sleep(0.1)
                field.fill(text, timeout=2000)
                time.sleep(0.1)
                field.dispatch_event("input")
                field.dispatch_event("change")
                field.dispatch_event("keydown")
                field.dispatch_event("keyup")
                field.press("a")
                time.sleep(0.05)
                field.press("Backspace")
                time.sleep(0.1)
                field.dispatch_event("input")
                field.dispatch_event("change")
                actual = field.input_value(timeout=1000)
                if actual and len(actual) > 0:
                    return True
                time.sleep(0.5)
            except Exception:
                if attempt < 2:
                    time.sleep(0.5)
        return False

    def _human_type_field(self, page, selector, text, verify=True):
        for attempt in range(3):
            try:
                field = page.locator(selector).first
                if field.count() == 0 or not field.is_visible(timeout=2000):
                    return False
                field.wait_for(state="visible", timeout=3000)
                time.sleep(0.3)
                field.click(timeout=2000)
                time.sleep(0.3)
                field.press("Control+a")
                time.sleep(0.1)
                field.press("Backspace")
                time.sleep(0.2)
                for char in text:
                    field.press(char if len(char) == 1 else char, timeout=1000)
                    time.sleep(random.uniform(0.04, 0.09))
                time.sleep(0.2)
                field.dispatch_event("input")
                field.dispatch_event("change")
                time.sleep(0.2)
                if verify:
                    actual = field.input_value(timeout=1000)
                    if actual and len(actual) > 0:
                        return True
                    time.sleep(1)
                    continue
                return True
            except Exception:
                if attempt < 2:
                    time.sleep(1)
        return False

    def _find_visible_selector(self, page, selectors):
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=800):
                    return sel
            except Exception:
                continue
        return None

    def _click_fast(self, page, selectors, max_wait=15):
        deadline = time.time() + max_wait
        while time.time() < deadline:
            for sel in selectors:
                try:
                    el = page.locator(sel).first
                    if el.count() > 0 and el.is_visible(timeout=200):
                        el.click(timeout=2000)
                        return True
                except Exception:
                    continue
            time.sleep(0.3)
        return False

    def _auto_click_review(self, tab_game):
        review_selectors = [
            'a[href*="/analysis/game/live"]',
            'a[href*="/analysis/game/daily"]',
            'a[href*="/analysis/game/"]',
            'a:has-text("Review")',
            'a:has-text("Đánh giá")',
        ]
        self._update_status("Auto-review: Looking for Review button...", "#89b4fa")
        if self._click_fast(tab_game, review_selectors, max_wait=30):
            self._update_status("Auto-review: Clicked ✓", "#a6e3a1")
            return True
        self._update_status("Auto-review: Not found. Click manually.", "#fab387")
        return False

    def _complete_onboarding(self, tab_game, board_index):
        experience_selectors = [
            '[data-cy="level-intermediate-label"]',
            '[data-cy="level-beginner-label"]',
            '[data-cy="level-advanced-label"]',
            '[data-cy="level-new-label"]',
            'button[data-cy*="level"]',
        ]
        continue_selectors = [
            '[data-cy="continue"]',
            'button[data-cy*="continue"]',
            'button:has-text("Continue")',
            'button:has-text("Tiếp tục")',
            'button.cc-button-primary',
        ]
        skip_selectors = [
            '[data-cy="skip"]',
            'button[data-cy*="skip"]',
            'button:has-text("Skip")',
            'button:has-text("Bỏ qua")',
            'a:has-text("Skip")',
            'a:has-text("Bỏ qua")',
        ]
        no_thanks_selectors = [
            'button:has-text("No, thank you")',
            'button:has-text("No, Thank You")',
            'button:has-text("Không, cảm ơn")',
            'a:has-text("No, thank you")',
            'a:has-text("Không, cảm ơn")',
            '[data-cy="no-thanks"]',
            'button:has-text("No thanks")',
        ]

        steps = [
            ("1/8 Experience",       experience_selectors, 20),
            ("2/8 Continue",         continue_selectors,   10),
            ("3/8 Coach → Continue", continue_selectors,   10),
            ("4/8 Board theme",      None,                 10),
            ("5/8 Continue",         continue_selectors,   10),
            ("6/8 Skip",             skip_selectors,       10),
            ("7/8 No thanks (ad 1)", no_thanks_selectors,  15),
            ("8/8 No thanks (ad 2)", no_thanks_selectors,  15),
        ]

        for i, (label, selectors, wait) in enumerate(steps):
            self._update_status(f"Onboarding {label}...", "#89b4fa")
            if i == 3:
                board_selectors = [
                    f'.theme-item-minimalist-theme:nth-of-type({board_index})',
                    f'div.theme-item-minimalist-theme:nth-child({board_index})',
                    f'div[class*="theme-item"]:nth-of-type({board_index})',
                ]
                if self._click_fast(tab_game, board_selectors, max_wait=wait):
                    self._update_status(f"{label} ✓", "#a6e3a1")
                else:
                    try:
                        tab_game.evaluate(f"""
                        () => {{
                            const items = document.querySelectorAll('.theme-item-minimalist-theme, div[class*="theme-item"]');
                            if (items.length >= {board_index}) {{ items[{board_index - 1}].click(); }}
                        }}
                        """)
                        self._update_status(f"{label} (JS) ✓", "#a6e3a1")
                    except Exception:
                        self._update_status(f"{label} — do manually.", "#fab387")
            else:
                if self._click_fast(tab_game, selectors, max_wait=wait):
                    self._update_status(f"{label} ✓", "#a6e3a1")
                else:
                    self._update_status(f"{label} — do manually.", "#fab387")
            time.sleep(0.8)

        self._update_status("✅ Onboarding complete!", "#a6e3a1")

    def _wait_and_fill_signup(self, tab_game, email, board_index):
        username = generate_random_username()
        password = generate_random_password()

        username_selectors = [
            'input[data-cy="registration-username"]',
            'input[name="registration[username]"]',
            'input[id*="username"]',
            'input[autocomplete="username"]',
        ]
        email_selectors = [
            'input[data-cy="registration-email"]',
            'input[name="registration[email]"]',
            'input[type="email"]',
            'input[id*="email"]',
        ]
        password_selectors = [
            'input[data-cy="registration-password"]',
            'input[name="registration[password]"]',
            'input[type="password"]',
            'input[id*="password"]',
        ]
        signup_selectors = [
            'button[data-cy="registration-submit"]',
            'button[type="submit"]',
            'button:has-text("Sign Up")',
            'button:has-text("Đăng ký")',
        ]

        all_field_selectors = username_selectors + email_selectors + password_selectors
        self._update_status("Waiting for sign-up form...", "#f9e2af")

        max_wait = 600
        elapsed = 0

        while elapsed < max_wait:
            try:
                modal_present = False
                for sel in all_field_selectors:
                    try:
                        loc = tab_game.locator(sel).first
                        if loc.count() > 0 and loc.is_visible(timeout=500):
                            modal_present = True
                            break
                    except Exception:
                        continue

                if modal_present:
                    self._update_status("Sign-up form detected! Filling...", "#89b4fa")
                    time.sleep(1.5)

                    usel = self._find_visible_selector(tab_game, username_selectors)
                    esel = self._find_visible_selector(tab_game, email_selectors)
                    psel = self._find_visible_selector(tab_game, password_selectors)

                    if usel:
                        if self._fast_fill_field(tab_game, usel, username):
                            self._update_status(f"Username: {username} ✓", "#a6e3a1")

                    time.sleep(0.3)
                    tab_game.keyboard.press("Tab")
                    time.sleep(0.3)

                    if email and esel:
                        if self._human_type_field(tab_game, esel, email, verify=True):
                            self._update_status(f"Email: {email} ✓", "#a6e3a1")
                    elif not email:
                        self._update_status("No temp email — paste from Tab 1.", "#fab387")

                    time.sleep(0.3)
                    tab_game.keyboard.press("Tab")
                    time.sleep(0.3)

                    if psel:
                        if self._human_type_field(tab_game, psel, password, verify=True):
                            self._update_status("Password ✓", "#a6e3a1")

                    time.sleep(0.3)
                    if psel:
                        try:
                            tab_game.locator(psel).first.dispatch_event("blur")
                        except Exception:
                            pass

                    time.sleep(0.5)

                    self._update_status("Clicking Sign Up...", "#89b4fa")
                    if not self._click_fast(tab_game, signup_selectors, max_wait=5):
                        tab_game.keyboard.press("Enter")

                    self._update_status(
                        f"✅ Signed up!  User: {username}  |  Pass: {password}", "#a6e3a1")
                    time.sleep(2)

                    self._complete_onboarding(tab_game, board_index)
                    return

            except Exception:
                pass

            time.sleep(2)
            elapsed += 2

        self._update_status(
            f"No sign-up form appeared. User: {username} | Pass: {password}", "#fab387")

    def _run_automation(self, match_history_url, provider, board_choice, auto_review):
        try:
            from playwright.sync_api import sync_playwright

            board_index = BOARD_POSITIONS.get(board_choice, 1)
            self._update_status("Launching browser...", "#89b4fa")

            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=False,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(viewport=None, no_viewport=True)

                mail_url = ("https://temp-mail.org/en/" if provider == "temp-mail.org"
                            else "https://temp-mail.io/en")
                self._update_status(f"Opening temp-mail ({provider})...", "#89b4fa")
                tab_mail = context.new_page()
                try:
                    tab_mail.goto(mail_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    self._update_status(f"Temp-mail issue: {e}.", "#fab387")

                self._update_status("Fetching temp email...", "#f9e2af")
                temp_email = self._grab_temp_email(tab_mail, provider)
                if temp_email:
                    self._update_status(f"Temp email → {temp_email}", "#a6e3a1")
                else:
                    self._update_status("Couldn't read email. Copy from Tab 1.", "#fab387")

                time.sleep(1)

                self._update_status("Opening match history...", "#89b4fa")
                tab_game = context.new_page()
                try:
                    tab_game.goto(match_history_url, wait_until="domcontentloaded", timeout=30000)
                    tab_game.bring_to_front()
                except Exception as e:
                    self._update_status(f"Page load issue: {e}.", "#fab387")

                time.sleep(1)

                if auto_review:
                    self._auto_click_review(tab_game)
                    time.sleep(1)
                else:
                    self._update_status("Auto-review OFF — click Review yourself.", "#f9e2af")

                self._wait_and_fill_signup(tab_game, temp_email, board_index)

                self._update_status(
                    "✅ All done! Browser stays open. Close when finished.", "#a6e3a1")
                self.root.after(0, lambda: self.start_button.configure(
                    state="disabled", bg="#45475a", text="✅ BROWSER OPEN"))

                try:
                    while browser.contexts:
                        time.sleep(1)
                except Exception:
                    pass

                self._update_status("Browser closed. You may start again.", "#6c7086")
                self.root.after(0, lambda: self.start_button.configure(
                    state="normal", bg="#89b4fa", text="▶  START"))

        except ImportError:
            self._update_status("Error: Playwright not installed.", "#f38ba8")
            self.root.after(0, lambda: messagebox.showerror("Missing Dependency",
                "Run:\n  pip install playwright\n  python -m playwright install chromium"))
            self.root.after(0, lambda: self.start_button.configure(
                state="normal", bg="#89b4fa", text="▶  START"))

        except Exception as e:
            self._update_status(f"Error: {e}", "#f38ba8")
            self.root.after(0, lambda: messagebox.showerror("Error", f"{type(e).__name__}: {e}"))
            self.root.after(0, lambda: self.start_button.configure(
                state="normal", bg="#89b4fa", text="▶  START"))


def main():
    root = tk.Tk()
    ChessAutomationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()