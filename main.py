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

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

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

BG_COLOR = "#1e1e2e"
WIN_W, WIN_H = 640, 620


def load_config():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            c = DEFAULT_CONFIG.copy()
            c.update(saved)
            return c
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


def resource_path(rel):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.abspath("."), rel)


def generate_random_username():
    prefixes = ["x", "z", "q", "v", "k", "j", "w", "n", "m", "r", "p", "d",
                "fx", "zx", "qv", "kj", "xr", "vn", "wz", "mk", "pj", "dr"]
    return f"{random.choice(prefixes)}{uuid.uuid4().hex[:10]}"


def generate_random_password():
    length = random.randint(8, 12)
    pw = [random.choice(string.ascii_uppercase),
          random.choice(string.ascii_lowercase),
          random.choice(string.digits)]
    pw += random.choices(string.ascii_letters + string.digits, k=length - 3)
    random.shuffle(pw)
    return ''.join(pw)


BOARD_POSITIONS = {"Top Left": 1, "Top Right": 2, "Bottom Left": 3, "Bottom Right": 4}


class ChessAutomationApp:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.bg_photo_ref = None
        self.bg_original_image = None
        self._opacity_job = None

        self.root.title(f"WFChessReviewerTdev v{__version__}")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)
        self._set_icon()

        # Canvas as root background
        self.canvas = tk.Canvas(self.root, width=WIN_W, height=WIN_H,
                                bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Background image on canvas
        self.bg_canvas_item = None

        # All UI widgets placed directly on canvas via create_window
        self._build_ui()

        # Load saved background
        if self.config.get("bg_image_path") and os.path.exists(self.config["bg_image_path"]):
            self.bg_original_image = self._load_bg_image(self.config["bg_image_path"])
            if self.bg_original_image:
                self._render_background(self.config.get("bg_opacity", 0.3))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self):
        try:
            ico = resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
                return
        except Exception:
            pass
        try:
            png = resource_path(os.path.join("assets", "icon.png"))
            if os.path.exists(png) and HAS_PIL:
                img = Image.open(png)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                self._icon_ref = photo
        except Exception:
            pass

    def _build_ui(self):
        # Main frame — transparent bg so canvas background shows through
        self.main_frame = tk.Frame(self.canvas, bg="", bd=0, highlightthickness=0)
        self.canvas.create_window(WIN_W // 2, WIN_H // 2, window=self.main_frame,
                                  width=WIN_W, height=WIN_H)

        # We need all child widgets to NOT have solid bg so the background shows
        # But tkinter can't do true transparency, so we use a trick:
        # When bg image is set, we make widgets use a slightly transparent-looking dark color
        # When no bg image, we use solid dark

        # Title
        tk.Label(
            self.main_frame, text="♟ WFChessReviewerTdev",
            font=("Segoe UI", 18, "bold"), bg=BG_COLOR, fg="#cdd6f4",
        ).pack(pady=(10, 1))

        tk.Label(
            self.main_frame, text=f"v{__version__} — Auto sign-up → onboarding → review",
            font=("Segoe UI", 9), bg=BG_COLOR, fg="#6c7086",
        ).pack(pady=(0, 6))

        # URL
        f1 = tk.Frame(self.main_frame, bg=BG_COLOR)
        f1.pack(pady=3, padx=40, fill="x")
        tk.Label(f1, text="Chess.com Match History URL:", font=("Segoe UI", 10),
                 bg=BG_COLOR, fg="#a6adc8", anchor="w").pack(fill="x", pady=(0, 2))
        self.url_entry = tk.Entry(f1, font=("Segoe UI", 10), bg="#313244", fg="#cdd6f4",
                                  insertbackground="#cdd6f4", relief="flat",
                                  highlightthickness=2, highlightbackground="#45475a",
                                  highlightcolor="#89b4fa")
        self.url_entry.pack(fill="x", ipady=6)
        self.url_entry.insert(0, self.config.get("url", DEFAULT_CONFIG["url"]))

        # Options row
        oframe = tk.Frame(self.main_frame, bg=BG_COLOR)
        oframe.pack(pady=(6, 3), padx=40, fill="x")

        mf = tk.LabelFrame(oframe, text=" Temp-mail ", font=("Segoe UI", 9),
                            bg=BG_COLOR, fg="#a6adc8", relief="groove", bd=1)
        mf.pack(side="left", fill="y", padx=(0, 8))
        self.provider_var = tk.StringVar(value=self.config.get("provider", "temp-mail.org"))
        for p in ["temp-mail.org", "temp-mail.io"]:
            tk.Radiobutton(mf, text=p, variable=self.provider_var, value=p,
                           font=("Segoe UI", 8), bg=BG_COLOR, fg="#cdd6f4",
                           selectcolor="#313244", activebackground=BG_COLOR).pack(anchor="w", padx=6)

        bf = tk.LabelFrame(oframe, text=" Board Theme ", font=("Segoe UI", 9),
                            bg=BG_COLOR, fg="#a6adc8", relief="groove", bd=1)
        bf.pack(side="left", fill="both", expand=True)
        gf = tk.Frame(bf, bg=BG_COLOR)
        gf.pack(padx=6, pady=2)
        self.board_var = tk.StringVar(value=self.config.get("board_position", "Top Left"))
        for lbl, r, c in [("Top Left",0,0),("Top Right",0,1),("Bottom Left",1,0),("Bottom Right",1,1)]:
            tk.Radiobutton(gf, text=lbl, variable=self.board_var, value=lbl,
                           font=("Segoe UI", 8), bg=BG_COLOR, fg="#cdd6f4",
                           selectcolor="#313244", activebackground=BG_COLOR,
                           indicatoron=0, width=11, relief="groove", bd=1,
                           padx=3, pady=1).grid(row=r, column=c, padx=2, pady=1)

        # Auto-review
        af = tk.Frame(self.main_frame, bg=BG_COLOR)
        af.pack(pady=(4, 2), padx=40, fill="x")
        self.auto_review_var = tk.BooleanVar(value=self.config.get("auto_review", True))
        tk.Checkbutton(af, text="  Auto-click Review (most recent match)",
                       variable=self.auto_review_var, font=("Segoe UI", 10),
                       bg=BG_COLOR, fg="#cdd6f4", selectcolor="#313244",
                       activebackground=BG_COLOR).pack(anchor="w")

        # ── Background Settings ──
        bgf = tk.LabelFrame(self.main_frame, text=" 🎨 Background ", font=("Segoe UI", 9),
                             bg=BG_COLOR, fg="#a6adc8", relief="groove", bd=1)
        bgf.pack(pady=(4, 2), padx=40, fill="x")

        row1 = tk.Frame(bgf, bg=BG_COLOR)
        row1.pack(fill="x", padx=8, pady=(3, 1))
        self.bg_path_var = tk.StringVar(value=self.config.get("bg_image_path", ""))

        self.bg_path_display = tk.Label(row1, text=self._short_path(self.bg_path_var.get()),
                                         font=("Segoe UI", 8), bg=BG_COLOR, fg="#585b70",
                                         anchor="w")
        self.bg_path_display.pack(side="left", fill="x", expand=True)
        tk.Button(row1, text="📂 Browse", font=("Segoe UI", 8, "bold"),
                  bg="#45475a", fg="#cdd6f4", relief="flat", padx=6, cursor="hand2",
                  command=self._browse_bg).pack(side="left", padx=(4, 2))
        tk.Button(row1, text="✕ Clear", font=("Segoe UI", 8, "bold"),
                  bg="#45475a", fg="#f38ba8", relief="flat", padx=6, cursor="hand2",
                  command=self._clear_bg).pack(side="left", padx=2)

        row2 = tk.Frame(bgf, bg=BG_COLOR)
        row2.pack(fill="x", padx=8, pady=(1, 4))
        tk.Label(row2, text="Opacity:", font=("Segoe UI", 8),
                 bg=BG_COLOR, fg="#a6adc8").pack(side="left")

        self.opacity_var = tk.IntVar(value=int(self.config.get("bg_opacity", 0.3) * 100))
        self.opacity_scale = tk.Scale(
            row2, from_=5, to=100, orient="horizontal",
            variable=self.opacity_var, showvalue=False,
            bg=BG_COLOR, fg="#89b4fa", troughcolor="#313244",
            activebackground="#89b4fa", highlightthickness=0,
            sliderlength=18, length=220, bd=0,
            command=self._on_opacity_drag,
        )
        self.opacity_scale.pack(side="left", padx=(4, 4))

        self.opacity_label = tk.Label(row2, text=f"{self.opacity_var.get()}%",
                                       font=("Segoe UI", 9, "bold"),
                                       bg=BG_COLOR, fg="#89b4fa", width=5)
        self.opacity_label.pack(side="left")

        # Start button
        self.start_button = tk.Button(
            self.main_frame, text="▶  START", font=("Segoe UI", 13, "bold"),
            bg="#89b4fa", fg="#1e1e2e", activebackground="#74c7ec",
            activeforeground="#1e1e2e", relief="flat", cursor="hand2",
            command=self._on_start_click, width=20, height=1)
        self.start_button.pack(pady=8)

        # Status
        self.status_var = tk.StringVar(value="Ready. Enter a URL and click START.")
        self.status_label = tk.Label(self.main_frame, textvariable=self.status_var,
                                      font=("Segoe UI", 9), bg=BG_COLOR, fg="#a6e3a1",
                                      wraplength=560)
        self.status_label.pack(pady=(0, 4))

        tk.Label(self.main_frame, text="github.com/Taam-dev/WFChessReviewerTdev",
                 font=("Segoe UI", 8, "italic"), bg=BG_COLOR, fg="#45475a").pack(side="bottom", pady=3)

    # ── Background ──

    def _short_path(self, path):
        if not path:
            return "No image selected"
        name = os.path.basename(path)
        if len(name) > 35:
            return f"...{name[-32:]}"
        return name

    def _load_bg_image(self, path):
        if not HAS_PIL or not os.path.exists(path):
            return None
        try:
            return Image.open(path).convert("RGBA").resize((WIN_W, WIN_H), Image.LANCZOS)
        except Exception:
            return None

    def _render_background(self, opacity):
        if not self.bg_original_image:
            return
        try:
            overlay = Image.new("RGBA", (WIN_W, WIN_H),
                                (30, 30, 46, int(255 * (1.0 - opacity))))
            blended = Image.alpha_composite(self.bg_original_image, overlay).convert("RGB")
            self.bg_photo_ref = ImageTk.PhotoImage(blended)

            if self.bg_canvas_item:
                self.canvas.itemconfig(self.bg_canvas_item, image=self.bg_photo_ref)
            else:
                self.bg_canvas_item = self.canvas.create_image(0, 0, anchor="nw",
                                                                image=self.bg_photo_ref)
                # Lower bg image behind the main_frame window
                self.canvas.tag_lower(self.bg_canvas_item)

        except Exception as e:
            self._update_status(f"Background error: {e}", "#f38ba8")

    def _browse_bg(self):
        path = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("All", "*.*")])
        if path:
            self.bg_path_var.set(path)
            self.bg_path_display.config(text=self._short_path(path))
            self.bg_original_image = self._load_bg_image(path)
            if self.bg_original_image:
                self._render_background(self.opacity_var.get() / 100.0)
            else:
                self._update_status("Failed to load image.", "#f38ba8")

    def _clear_bg(self):
        self.bg_path_var.set("")
        self.bg_path_display.config(text="No image selected")
        self.bg_original_image = None
        self.bg_photo_ref = None
        if self.bg_canvas_item:
            self.canvas.delete(self.bg_canvas_item)
            self.bg_canvas_item = None

    def _on_opacity_drag(self, val):
        v = int(float(val))
        self.opacity_label.config(text=f"{v}%")

        # Debounce: cancel previous pending render, schedule new one in 50ms
        if self._opacity_job:
            self.root.after_cancel(self._opacity_job)
        self._opacity_job = self.root.after(50, self._apply_opacity_debounced)

    def _apply_opacity_debounced(self):
        self._opacity_job = None
        if self.bg_original_image:
            self._render_background(self.opacity_var.get() / 100.0)

    # ── Save / Close ──

    def _save_current_config(self):
        self.config = {
            "url": self.url_entry.get().strip(),
            "provider": self.provider_var.get(),
            "board_position": self.board_var.get(),
            "auto_review": self.auto_review_var.get(),
            "bg_image_path": self.bg_path_var.get(),
            "bg_opacity": self.opacity_var.get() / 100.0,
        }
        save_config(self.config)

    def _on_close(self):
        self._save_current_config()
        self.root.destroy()

    def _update_status(self, message, color="#a6e3a1"):
        self.root.after(0, lambda: self.status_var.set(message))
        self.root.after(0, lambda: self.status_label.configure(fg=color))

    def _on_start_click(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a Chess.com match history URL.")
            return
        if "chess.com" not in url.lower():
            if not messagebox.askyesno("URL Check", "Not a Chess.com URL. Continue?"):
                return
        self._save_current_config()
        self.start_button.configure(state="disabled", bg="#585b70", text="⏳ RUNNING...")
        threading.Thread(
            target=self._run_automation,
            args=(url, self.provider_var.get(), self.board_var.get(), self.auto_review_var.get()),
            daemon=True).start()

    # ── Automation ──

    def _grab_temp_email(self, tab, provider):
        sels = (["#mail", "input#mail", ".email-address input"] if provider == "temp-mail.org"
                else ["#email", "input#email", ".email-box input", "input[name='email']"])
        for _ in range(12):
            for s in sels:
                try:
                    el = tab.locator(s).first
                    if el.count() > 0:
                        v = el.input_value(timeout=1500)
                        if v and "@" in v and "loading" not in v.lower():
                            return v.strip()
                except Exception:
                    continue
            time.sleep(2)
        return None

    def _fast_fill(self, page, sel, text):
        for attempt in range(3):
            try:
                f = page.locator(sel).first
                if f.count() == 0 or not f.is_visible(timeout=2000):
                    return False
                f.wait_for(state="visible", timeout=3000)
                time.sleep(0.2)
                f.click(timeout=2000); time.sleep(0.2)
                f.fill("", timeout=1000); time.sleep(0.1)
                f.fill(text, timeout=2000); time.sleep(0.1)
                for evt in ["input", "change", "keydown", "keyup"]:
                    f.dispatch_event(evt)
                f.press("a"); time.sleep(0.05); f.press("Backspace"); time.sleep(0.1)
                f.dispatch_event("input"); f.dispatch_event("change")
                if (f.input_value(timeout=1000) or ""):
                    return True
                time.sleep(0.5)
            except Exception:
                if attempt < 2: time.sleep(0.5)
        return False

    def _human_type(self, page, sel, text, verify=True):
        for attempt in range(3):
            try:
                f = page.locator(sel).first
                if f.count() == 0 or not f.is_visible(timeout=2000):
                    return False
                f.wait_for(state="visible", timeout=3000)
                time.sleep(0.3)
                f.click(timeout=2000); time.sleep(0.3)
                f.press("Control+a"); time.sleep(0.1)
                f.press("Backspace"); time.sleep(0.2)
                for ch in text:
                    f.press(ch if len(ch) == 1 else ch, timeout=1000)
                    time.sleep(random.uniform(0.04, 0.09))
                time.sleep(0.2)
                f.dispatch_event("input"); f.dispatch_event("change"); time.sleep(0.2)
                if verify:
                    if f.input_value(timeout=1000):
                        return True
                    time.sleep(1); continue
                return True
            except Exception:
                if attempt < 2: time.sleep(1)
        return False

    def _find_sel(self, page, sels):
        for s in sels:
            try:
                l = page.locator(s).first
                if l.count() > 0 and l.is_visible(timeout=800):
                    return s
            except Exception:
                continue
        return None

    def _click_fast(self, page, sels, max_wait=15):
        end = time.time() + max_wait
        while time.time() < end:
            for s in sels:
                try:
                    el = page.locator(s).first
                    if el.count() > 0 and el.is_visible(timeout=200):
                        el.click(timeout=2000)
                        return True
                except Exception:
                    continue
            time.sleep(0.3)
        return False

    def _auto_click_review(self, tab):
        sels = ['a[href*="/analysis/game/live"]', 'a[href*="/analysis/game/daily"]',
                'a[href*="/analysis/game/"]', 'a:has-text("Review")', 'a:has-text("Đánh giá")']
        self._update_status("Auto-review: Looking...", "#89b4fa")
        if self._click_fast(tab, sels, 30):
            self._update_status("Auto-review ✓", "#a6e3a1"); return True
        self._update_status("Auto-review: Not found. Click manually.", "#fab387"); return False

    def _onboarding(self, tab, bi):
        exp = ['[data-cy="level-intermediate-label"]', '[data-cy="level-beginner-label"]',
               '[data-cy="level-advanced-label"]', '[data-cy="level-new-label"]', 'button[data-cy*="level"]']
        cont = ['[data-cy="continue"]', 'button[data-cy*="continue"]',
                'button:has-text("Continue")', 'button:has-text("Tiếp tục")', 'button.cc-button-primary']
        skip = ['[data-cy="skip"]', 'button[data-cy*="skip"]', 'button:has-text("Skip")',
                'button:has-text("Bỏ qua")', 'a:has-text("Skip")', 'a:has-text("Bỏ qua")']
        noty = ['button:has-text("No, thank you")', 'button:has-text("No, Thank You")',
                'button:has-text("Không, cảm ơn")', 'a:has-text("No, thank you")',
                'a:has-text("Không, cảm ơn")', '[data-cy="no-thanks"]', 'button:has-text("No thanks")']

        steps = [("1/8 Experience", exp, 20), ("2/8 Continue", cont, 10),
                 ("3/8 Coach→Continue", cont, 10), ("4/8 Board", None, 10),
                 ("5/8 Continue", cont, 10), ("6/8 Skip", skip, 10),
                 ("7/8 No thanks", noty, 15), ("8/8 No thanks", noty, 15)]

        for i, (lbl, sels, w) in enumerate(steps):
            self._update_status(f"Onboarding {lbl}...", "#89b4fa")
            if i == 3:
                bs = [f'.theme-item-minimalist-theme:nth-of-type({bi})',
                      f'div.theme-item-minimalist-theme:nth-child({bi})',
                      f'div[class*="theme-item"]:nth-of-type({bi})']
                if self._click_fast(tab, bs, w):
                    self._update_status(f"{lbl} ✓", "#a6e3a1")
                else:
                    try:
                        tab.evaluate(f"""() => {{
                            const it = document.querySelectorAll('.theme-item-minimalist-theme, div[class*="theme-item"]');
                            if(it.length>={bi}) it[{bi-1}].click();
                        }}""")
                        self._update_status(f"{lbl} (JS) ✓", "#a6e3a1")
                    except Exception:
                        self._update_status(f"{lbl} — manual.", "#fab387")
            else:
                if self._click_fast(tab, sels, w):
                    self._update_status(f"{lbl} ✓", "#a6e3a1")
                else:
                    self._update_status(f"{lbl} — manual.", "#fab387")
            time.sleep(0.8)
        self._update_status("✅ Onboarding complete!", "#a6e3a1")

    def _signup_flow(self, tab, email, bi):
        user = generate_random_username()
        pw = generate_random_password()
        usels = ['input[data-cy="registration-username"]', 'input[name="registration[username]"]',
                 'input[id*="username"]', 'input[autocomplete="username"]']
        esels = ['input[data-cy="registration-email"]', 'input[name="registration[email]"]',
                 'input[type="email"]', 'input[id*="email"]']
        psels = ['input[data-cy="registration-password"]', 'input[name="registration[password]"]',
                 'input[type="password"]', 'input[id*="password"]']
        ssels = ['button[data-cy="registration-submit"]', 'button[type="submit"]',
                 'button:has-text("Sign Up")', 'button:has-text("Đăng ký")']

        self._update_status("Waiting for sign-up form...", "#f9e2af")
        elapsed = 0
        while elapsed < 600:
            try:
                found = False
                for s in usels + esels + psels:
                    try:
                        if tab.locator(s).first.is_visible(timeout=500):
                            found = True; break
                    except Exception:
                        continue
                if found:
                    self._update_status("Sign-up detected! Filling...", "#89b4fa")
                    time.sleep(1.5)
                    us = self._find_sel(tab, usels)
                    es = self._find_sel(tab, esels)
                    ps = self._find_sel(tab, psels)

                    if us and self._fast_fill(tab, us, user):
                        self._update_status(f"Username: {user} ✓", "#a6e3a1")
                    time.sleep(0.3); tab.keyboard.press("Tab"); time.sleep(0.3)

                    if email and es and self._human_type(tab, es, email):
                        self._update_status(f"Email: {email} ✓", "#a6e3a1")
                    elif not email:
                        self._update_status("No email — paste from Tab 1.", "#fab387")
                    time.sleep(0.3); tab.keyboard.press("Tab"); time.sleep(0.3)

                    if ps and self._human_type(tab, ps, pw):
                        self._update_status("Password ✓", "#a6e3a1")
                    time.sleep(0.3)
                    try: tab.locator(ps).first.dispatch_event("blur")
                    except: pass
                    time.sleep(0.5)

                    self._update_status("Clicking Sign Up...", "#89b4fa")
                    if not self._click_fast(tab, ssels, 5):
                        tab.keyboard.press("Enter")
                    self._update_status(f"✅ Signed up! User: {user} | Pass: {pw}", "#a6e3a1")
                    time.sleep(2)
                    self._onboarding(tab, bi)
                    return
            except Exception:
                pass
            time.sleep(2); elapsed += 2
        self._update_status(f"No form. User: {user} | Pass: {pw}", "#fab387")

    def _run_automation(self, url, provider, board_choice, auto_review):
        try:
            from playwright.sync_api import sync_playwright
            bi = BOARD_POSITIONS.get(board_choice, 1)
            self._update_status("Launching browser...", "#89b4fa")

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
                ctx = browser.new_context(viewport=None, no_viewport=True)

                murl = "https://temp-mail.org/en/" if provider == "temp-mail.org" else "https://temp-mail.io/en"
                self._update_status(f"Opening temp-mail ({provider})...", "#89b4fa")
                t1 = ctx.new_page()
                try: t1.goto(murl, wait_until="domcontentloaded", timeout=30000)
                except Exception as e: self._update_status(f"Temp-mail: {e}", "#fab387")

                self._update_status("Fetching temp email...", "#f9e2af")
                email = self._grab_temp_email(t1, provider)
                if email: self._update_status(f"Email → {email}", "#a6e3a1")
                else: self._update_status("Couldn't read email. Copy from Tab 1.", "#fab387")
                time.sleep(1)

                self._update_status("Opening match history...", "#89b4fa")
                t2 = ctx.new_page()
                try:
                    t2.goto(url, wait_until="domcontentloaded", timeout=30000)
                    t2.bring_to_front()
                except Exception as e: self._update_status(f"Page: {e}", "#fab387")
                time.sleep(1)

                if auto_review: self._auto_click_review(t2); time.sleep(1)
                else: self._update_status("Auto-review OFF — click Review yourself.", "#f9e2af")

                self._signup_flow(t2, email, bi)

                self._update_status("✅ Done! Close browser when finished.", "#a6e3a1")
                self.root.after(0, lambda: self.start_button.configure(
                    state="disabled", bg="#45475a", text="✅ BROWSER OPEN"))
                try:
                    while browser.contexts: time.sleep(1)
                except: pass
                self._update_status("Browser closed. Start again.", "#6c7086")
                self.root.after(0, lambda: self.start_button.configure(
                    state="normal", bg="#89b4fa", text="▶  START"))

        except ImportError:
            self._update_status("Playwright not installed.", "#f38ba8")
            self.root.after(0, lambda: messagebox.showerror("Missing",
                "pip install playwright\npython -m playwright install chromium"))
            self.root.after(0, lambda: self.start_button.configure(
                state="normal", bg="#89b4fa", text="▶  START"))
        except Exception as e:
            self._update_status(f"Error: {e}", "#f38ba8")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.start_button.configure(
                state="normal", bg="#89b4fa", text="▶  START"))


def main():
    root = tk.Tk()
    ChessAutomationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()