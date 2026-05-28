#!/usr/bin/env python3
"""
WFChessReviewerTdev - Chess.com Match Review Helper
https://github.com/Taam-dev/WFChessReviewerTdev
"""

__version__ = "1.0.0"
__author__ = "Taam-dev"
__repo__ = "https://github.com/Taam-dev/WFChessReviewerTdev"

import tkinter as tk
from tkinter import messagebox, filedialog
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
    "bg_opacity": 30,
}
BG = "#1e1e2e"
BG2 = "#313244"
FG = "#cdd6f4"
FG2 = "#a6adc8"
FG3 = "#585b70"
ACCENT = "#89b4fa"
WIN_W, WIN_H = 640, 640


def load_config():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                c = DEFAULT_CONFIG.copy()
                c.update(json.load(f))
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
    px = ["x","z","q","v","k","j","w","n","m","r","p","d",
          "fx","zx","qv","kj","xr","vn","wz","mk","pj","dr"]
    return f"{random.choice(px)}{uuid.uuid4().hex[:10]}"


def generate_random_password():
    ln = random.randint(8, 12)
    pw = [random.choice(string.ascii_uppercase),
          random.choice(string.ascii_lowercase),
          random.choice(string.digits)]
    pw += random.choices(string.ascii_letters + string.digits, k=ln - 3)
    random.shuffle(pw)
    return ''.join(pw)


BOARD_POSITIONS = {"Top Left":1,"Top Right":2,"Bottom Left":3,"Bottom Right":4}


class ChessAutomationApp:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.bg_photo_ref = None
        self.bg_raw = None
        self._opacity_job = None

        self.root.title(f"WFChessReviewerTdev v{__version__}")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self._set_icon()
        self._build_ui()

        # Load saved bg
        p = self.config.get("bg_image_path", "")
        if p and os.path.exists(p):
            self.bg_raw = self._load_image(p)
            if self.bg_raw:
                self._render_bg(self.config.get("bg_opacity", 30))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_icon(self):
        for ext, method in [("ico", "iconbitmap"), ("png", "iconphoto")]:
            try:
                p = resource_path(os.path.join("assets", f"icon.{ext}"))
                if os.path.exists(p):
                    if ext == "ico":
                        self.root.iconbitmap(p)
                    elif HAS_PIL:
                        img = ImageTk.PhotoImage(Image.open(p))
                        self.root.iconphoto(True, img)
                        self._icon_ref = img
                    return
            except Exception:
                continue

    def _build_ui(self):
        # Full-window canvas
        self.c = tk.Canvas(self.root, width=WIN_W, height=WIN_H, bg=BG, highlightthickness=0)
        self.c.pack(fill="both", expand=True)

        # Background image item (will be created when image is loaded)
        self.bg_item = None

        # All UI elements placed on canvas with create_window
        # Each widget has bg=BG but when background image is shown,
        # widgets are narrow so the bg image peeks around them

        y = 15
        # Title
        self._cw(y, tk.Label(self.c, text="♟ WFChessReviewerTdev",
                              font=("Segoe UI", 18, "bold"), bg=BG, fg=FG))
        y += 35
        self._cw(y, tk.Label(self.c, text=f"v{__version__} — Auto sign-up → onboarding → review",
                              font=("Segoe UI", 9), bg=BG, fg=FG3))
        y += 25

        # URL
        self._cw(y, tk.Label(self.c, text="Chess.com Match History URL:",
                              font=("Segoe UI", 10), bg=BG, fg=FG2), w=540)
        y += 22
        self.url_entry = tk.Entry(self.c, font=("Segoe UI", 10), bg=BG2, fg=FG,
                                   insertbackground=FG, relief="flat", highlightthickness=2,
                                   highlightbackground="#45475a", highlightcolor=ACCENT)
        self.url_entry.insert(0, self.config.get("url", DEFAULT_CONFIG["url"]))
        self._cw(y, self.url_entry, w=540, h=32)
        y += 40

        # Options frame
        opt = tk.Frame(self.c, bg=BG)
        self._cw(y + 30, opt, w=540, h=80)

        # Temp-mail
        mf = tk.LabelFrame(opt, text=" Temp-mail ", font=("Segoe UI", 9),
                            bg=BG, fg=FG2, relief="groove", bd=1)
        mf.pack(side="left", fill="y", padx=(0, 8))
        self.provider_var = tk.StringVar(value=self.config.get("provider", "temp-mail.org"))
        for p in ["temp-mail.org", "temp-mail.io"]:
            tk.Radiobutton(mf, text=p, variable=self.provider_var, value=p,
                           font=("Segoe UI", 8), bg=BG, fg=FG, selectcolor=BG2,
                           activebackground=BG).pack(anchor="w", padx=6)

        # Board
        bf = tk.LabelFrame(opt, text=" Board Theme ", font=("Segoe UI", 9),
                            bg=BG, fg=FG2, relief="groove", bd=1)
        bf.pack(side="left", fill="both", expand=True)
        gf = tk.Frame(bf, bg=BG)
        gf.pack(padx=4, pady=2)
        self.board_var = tk.StringVar(value=self.config.get("board_position", "Top Left"))
        for lbl, r, col in [("Top Left",0,0),("Top Right",0,1),("Bottom Left",1,0),("Bottom Right",1,1)]:
            tk.Radiobutton(gf, text=lbl, variable=self.board_var, value=lbl,
                           font=("Segoe UI", 8), bg=BG, fg=FG, selectcolor=BG2,
                           activebackground=BG, indicatoron=0, width=11,
                           relief="groove", bd=1).grid(row=r, column=col, padx=2, pady=1)
        y += 80

        # Auto-review
        y += 10
        self.auto_review_var = tk.BooleanVar(value=self.config.get("auto_review", True))
        self._cw(y, tk.Checkbutton(self.c, text="  Auto-click Review (most recent match)",
                                    variable=self.auto_review_var, font=("Segoe UI", 10),
                                    bg=BG, fg=FG, selectcolor=BG2, activebackground=BG), w=540)
        y += 30

        # ── Background settings ──
        bgf = tk.Frame(self.c, bg=BG, highlightbackground="#45475a",
                        highlightthickness=1)
        self._cw(y + 40, bgf, w=540, h=85)

        tk.Label(bgf, text="🎨 Background", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=FG2).pack(anchor="w", padx=8, pady=(4, 2))

        r1 = tk.Frame(bgf, bg=BG)
        r1.pack(fill="x", padx=8, pady=1)

        self.bg_path_var = tk.StringVar(value=self.config.get("bg_image_path", ""))
        self.bg_path_lbl = tk.Label(r1, text=self._short(self.bg_path_var.get()),
                                     font=("Segoe UI", 8), bg=BG, fg=FG3, anchor="w")
        self.bg_path_lbl.pack(side="left", fill="x", expand=True)

        tk.Button(r1, text="📂 Browse", font=("Segoe UI", 8, "bold"), bg="#45475a",
                  fg=FG, relief="flat", padx=6, cursor="hand2",
                  command=self._browse_bg).pack(side="left", padx=2)
        tk.Button(r1, text="✕ Clear", font=("Segoe UI", 8, "bold"), bg="#45475a",
                  fg="#f38ba8", relief="flat", padx=6, cursor="hand2",
                  command=self._clear_bg).pack(side="left", padx=2)

        r2 = tk.Frame(bgf, bg=BG)
        r2.pack(fill="x", padx=8, pady=(1, 4))

        tk.Label(r2, text="Opacity:", font=("Segoe UI", 8), bg=BG, fg=FG2).pack(side="left")
        self.opacity_var = tk.IntVar(value=self.config.get("bg_opacity", 30))
        tk.Scale(r2, from_=5, to=100, orient="horizontal", variable=self.opacity_var,
                 showvalue=False, bg=BG, fg=ACCENT, troughcolor=BG2,
                 activebackground=ACCENT, highlightthickness=0, sliderlength=16,
                 length=220, bd=0, command=self._on_opacity).pack(side="left", padx=4)
        self.opacity_lbl = tk.Label(r2, text=f"{self.opacity_var.get()}%",
                                     font=("Segoe UI", 9, "bold"), bg=BG, fg=ACCENT, width=5)
        self.opacity_lbl.pack(side="left")

        y += 90

        # Start button
        y += 40
        self.start_button = tk.Button(self.c, text="▶  START", font=("Segoe UI", 13, "bold"),
                                       bg=ACCENT, fg="#1e1e2e", activebackground="#74c7ec",
                                       relief="flat", cursor="hand2", width=20,
                                       command=self._on_start_click)
        self._cw(y, self.start_button, h=40)
        y += 40

        # Status
        self.status_var = tk.StringVar(value="Ready. Enter a URL and click START.")
        self.status_label = tk.Label(self.c, textvariable=self.status_var,
                                      font=("Segoe UI", 9), bg=BG, fg="#a6e3a1", wraplength=540)
        self._cw(y + 10, self.status_label, w=560)

        # Footer
        self._cw(WIN_H - 15, tk.Label(self.c, text="github.com/Taam-dev/WFChessReviewerTdev",
                                        font=("Segoe UI", 8, "italic"), bg=BG, fg="#45475a"))

    def _cw(self, y, widget, w=None, h=None):
        """Place widget on canvas at center-x, given y."""
        kw = {"window": widget, "anchor": "n"}
        if w: kw["width"] = w
        if h: kw["height"] = h
        self.c.create_window(WIN_W // 2, y, **kw)

    # ── Background ──

    def _short(self, p):
        if not p: return "No image selected"
        n = os.path.basename(p)
        return f"...{n[-30:]}" if len(n) > 33 else n

    def _load_image(self, path):
        if not HAS_PIL or not os.path.exists(path): return None
        try:
            return Image.open(path).convert("RGBA").resize((WIN_W, WIN_H), Image.LANCZOS)
        except: return None

    def _render_bg(self, opacity_pct):
        if not self.bg_raw: return
        try:
            alpha = max(5, min(100, int(opacity_pct)))
            dark = Image.new("RGBA", (WIN_W, WIN_H), (30, 30, 46, int(255 * (1 - alpha / 100))))
            blended = Image.alpha_composite(self.bg_raw, dark).convert("RGB")
            self.bg_photo_ref = ImageTk.PhotoImage(blended)

            if self.bg_item:
                self.c.itemconfig(self.bg_item, image=self.bg_photo_ref)
            else:
                self.bg_item = self.c.create_image(0, 0, anchor="nw", image=self.bg_photo_ref)

            # Push bg image to the very back so all widgets are on top
            self.c.tag_lower(self.bg_item)
        except Exception as e:
            self._update_status(f"BG error: {e}", "#f38ba8")

    def _browse_bg(self):
        p = filedialog.askopenfilename(title="Select Background Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("All", "*.*")])
        if p:
            self.bg_path_var.set(p)
            self.bg_path_lbl.config(text=self._short(p))
            self.bg_raw = self._load_image(p)
            if self.bg_raw:
                self._render_bg(self.opacity_var.get())
            else:
                self._update_status("Failed to load image.", "#f38ba8")

    def _clear_bg(self):
        self.bg_path_var.set("")
        self.bg_path_lbl.config(text="No image selected")
        self.bg_raw = None
        self.bg_photo_ref = None
        if self.bg_item:
            self.c.delete(self.bg_item)
            self.bg_item = None

    def _on_opacity(self, val):
        v = int(float(val))
        self.opacity_lbl.config(text=f"{v}%")
        if self._opacity_job:
            self.root.after_cancel(self._opacity_job)
        self._opacity_job = self.root.after(30, lambda: self._render_bg(v))

    # ── Config ──

    def _save(self):
        save_config({
            "url": self.url_entry.get().strip(),
            "provider": self.provider_var.get(),
            "board_position": self.board_var.get(),
            "auto_review": self.auto_review_var.get(),
            "bg_image_path": self.bg_path_var.get(),
            "bg_opacity": self.opacity_var.get(),
        })

    def _on_close(self):
        self._save()
        self.root.destroy()

    def _update_status(self, msg, color="#a6e3a1"):
        self.root.after(0, lambda: self.status_var.set(msg))
        self.root.after(0, lambda: self.status_label.configure(fg=color))

    def _on_start_click(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input", "Enter a URL.")
            return
        if "chess.com" not in url.lower():
            if not messagebox.askyesno("URL", "Not Chess.com. Continue?"): return
        self._save()
        self.start_button.configure(state="disabled", bg="#585b70", text="⏳ RUNNING...")
        threading.Thread(target=self._run_automation,
            args=(url, self.provider_var.get(), self.board_var.get(),
                  self.auto_review_var.get()), daemon=True).start()

    # ── Automation ──

    def _grab_email(self, tab, prov):
        ss = (["#mail","input#mail",".email-address input"] if prov == "temp-mail.org"
              else ["#email","input#email",".email-box input","input[name='email']"])
        for _ in range(12):
            for s in ss:
                try:
                    e = tab.locator(s).first
                    if e.count() > 0:
                        v = e.input_value(timeout=1500)
                        if v and "@" in v and "loading" not in v.lower(): return v.strip()
                except: continue
            time.sleep(2)
        return None

    def _fast_fill(self, pg, sel, txt):
        for a in range(3):
            try:
                f = pg.locator(sel).first
                if f.count()==0 or not f.is_visible(timeout=2000): return False
                f.wait_for(state="visible",timeout=3000); time.sleep(0.2)
                f.click(timeout=2000); time.sleep(0.2)
                f.fill("",timeout=1000); time.sleep(0.1)
                f.fill(txt,timeout=2000); time.sleep(0.1)
                for ev in ["input","change","keydown","keyup"]: f.dispatch_event(ev)
                f.press("a"); time.sleep(0.05); f.press("Backspace"); time.sleep(0.1)
                f.dispatch_event("input"); f.dispatch_event("change")
                if f.input_value(timeout=1000): return True
                time.sleep(0.5)
            except:
                if a<2: time.sleep(0.5)
        return False

    def _human_type(self, pg, sel, txt, verify=True):
        for a in range(3):
            try:
                f = pg.locator(sel).first
                if f.count()==0 or not f.is_visible(timeout=2000): return False
                f.wait_for(state="visible",timeout=3000); time.sleep(0.3)
                f.click(timeout=2000); time.sleep(0.3)
                f.press("Control+a"); time.sleep(0.1); f.press("Backspace"); time.sleep(0.2)
                for ch in txt:
                    f.press(ch if len(ch)==1 else ch, timeout=1000)
                    time.sleep(random.uniform(0.04,0.09))
                time.sleep(0.2)
                f.dispatch_event("input"); f.dispatch_event("change"); time.sleep(0.2)
                if verify:
                    if f.input_value(timeout=1000): return True
                    time.sleep(1); continue
                return True
            except:
                if a<2: time.sleep(1)
        return False

    def _find_sel(self, pg, ss):
        for s in ss:
            try:
                l = pg.locator(s).first
                if l.count()>0 and l.is_visible(timeout=800): return s
            except: continue
        return None

    def _click_fast(self, pg, ss, mw=15):
        end = time.time()+mw
        while time.time()<end:
            for s in ss:
                try:
                    e = pg.locator(s).first
                    if e.count()>0 and e.is_visible(timeout=200):
                        e.click(timeout=2000); return True
                except: continue
            time.sleep(0.3)
        return False

    def _auto_review(self, tab):
        ss = ['a[href*="/analysis/game/live"]','a[href*="/analysis/game/daily"]',
              'a[href*="/analysis/game/"]','a:has-text("Review")','a:has-text("Đánh giá")']
        self._update_status("Auto-review: Looking...", "#89b4fa")
        if self._click_fast(tab,ss,30):
            self._update_status("Auto-review ✓","#a6e3a1"); return True
        self._update_status("Auto-review: Not found.","#fab387"); return False

    def _onboarding(self, tab, bi):
        exp=['[data-cy="level-intermediate-label"]','[data-cy="level-beginner-label"]',
             '[data-cy="level-advanced-label"]','[data-cy="level-new-label"]','button[data-cy*="level"]']
        con=['[data-cy="continue"]','button[data-cy*="continue"]',
             'button:has-text("Continue")','button:has-text("Tiếp tục")','button.cc-button-primary']
        skp=['[data-cy="skip"]','button[data-cy*="skip"]','button:has-text("Skip")',
             'button:has-text("Bỏ qua")','a:has-text("Skip")','a:has-text("Bỏ qua")']
        nty=['button:has-text("No, thank you")','button:has-text("No, Thank You")',
             'button:has-text("Không, cảm ơn")','a:has-text("No, thank you")',
             'a:has-text("Không, cảm ơn")','[data-cy="no-thanks"]','button:has-text("No thanks")']
        steps=[("1/8 Experience",exp,20),("2/8 Continue",con,10),("3/8 Coach→Continue",con,10),
               ("4/8 Board",None,10),("5/8 Continue",con,10),("6/8 Skip",skp,10),
               ("7/8 No thanks",nty,15),("8/8 No thanks",nty,15)]
        for i,(lbl,ss,w) in enumerate(steps):
            self._update_status(f"Onboarding {lbl}...","#89b4fa")
            if i==3:
                bs=[f'.theme-item-minimalist-theme:nth-of-type({bi})',
                    f'div.theme-item-minimalist-theme:nth-child({bi})',
                    f'div[class*="theme-item"]:nth-of-type({bi})']
                if not self._click_fast(tab,bs,w):
                    try:
                        tab.evaluate(f"""()=>{{const it=document.querySelectorAll('.theme-item-minimalist-theme,div[class*="theme-item"]');if(it.length>={bi})it[{bi-1}].click()}}""")
                    except: self._update_status(f"{lbl}—manual.","#fab387")
                self._update_status(f"{lbl} ✓","#a6e3a1")
            else:
                if self._click_fast(tab,ss,w): self._update_status(f"{lbl} ✓","#a6e3a1")
                else: self._update_status(f"{lbl}—manual.","#fab387")
            time.sleep(0.8)
        self._update_status("✅ Onboarding complete!","#a6e3a1")

    def _signup(self, tab, email, bi):
        user=generate_random_username(); pw=generate_random_password()
        us=['input[data-cy="registration-username"]','input[name="registration[username]"]',
            'input[id*="username"]','input[autocomplete="username"]']
        es=['input[data-cy="registration-email"]','input[name="registration[email]"]',
            'input[type="email"]','input[id*="email"]']
        ps=['input[data-cy="registration-password"]','input[name="registration[password]"]',
            'input[type="password"]','input[id*="password"]']
        sb=['button[data-cy="registration-submit"]','button[type="submit"]',
            'button:has-text("Sign Up")','button:has-text("Đăng ký")']
        self._update_status("Waiting for sign-up...","#f9e2af")
        el=0
        while el<600:
            try:
                found=False
                for s in us+es+ps:
                    try:
                        if tab.locator(s).first.is_visible(timeout=500): found=True; break
                    except: continue
                if found:
                    self._update_status("Sign-up detected!","#89b4fa"); time.sleep(1.5)
                    u=self._find_sel(tab,us); e=self._find_sel(tab,es); p=self._find_sel(tab,ps)
                    if u and self._fast_fill(tab,u,user):
                        self._update_status(f"User: {user} ✓","#a6e3a1")
                    time.sleep(0.3); tab.keyboard.press("Tab"); time.sleep(0.3)
                    if email and e and self._human_type(tab,e,email):
                        self._update_status(f"Email ✓","#a6e3a1")
                    elif not email: self._update_status("No email—paste from Tab 1.","#fab387")
                    time.sleep(0.3); tab.keyboard.press("Tab"); time.sleep(0.3)
                    if p and self._human_type(tab,p,pw):
                        self._update_status("Pass ✓","#a6e3a1")
                    time.sleep(0.3)
                    try: tab.locator(p).first.dispatch_event("blur")
                    except: pass
                    time.sleep(0.5)
                    self._update_status("Sign Up...","#89b4fa")
                    if not self._click_fast(tab,sb,5): tab.keyboard.press("Enter")
                    self._update_status(f"✅ User: {user} | Pass: {pw}","#a6e3a1")
                    time.sleep(2); self._onboarding(tab,bi); return
            except: pass
            time.sleep(2); el+=2
        self._update_status(f"No form. User:{user} Pass:{pw}","#fab387")

    def _run_automation(self, url, prov, board, auto):
        try:
            from playwright.sync_api import sync_playwright
            bi=BOARD_POSITIONS.get(board,1)
            self._update_status("Launching...","#89b4fa")
            with sync_playwright() as pw:
                br=pw.chromium.launch(headless=False,
                    args=["--start-maximized","--disable-blink-features=AutomationControlled"])
                ctx=br.new_context(viewport=None,no_viewport=True)
                mu="https://temp-mail.org/en/" if prov=="temp-mail.org" else "https://temp-mail.io/en"
                self._update_status(f"Temp-mail ({prov})...","#89b4fa")
                t1=ctx.new_page()
                try: t1.goto(mu,wait_until="domcontentloaded",timeout=30000)
                except Exception as e: self._update_status(f"Mail:{e}","#fab387")
                self._update_status("Fetching email...","#f9e2af")
                email=self._grab_email(t1,prov)
                if email: self._update_status(f"Email→{email}","#a6e3a1")
                else: self._update_status("No email. Copy Tab 1.","#fab387")
                time.sleep(1)
                self._update_status("Opening history...","#89b4fa")
                t2=ctx.new_page()
                try: t2.goto(url,wait_until="domcontentloaded",timeout=30000); t2.bring_to_front()
                except Exception as e: self._update_status(f"Page:{e}","#fab387")
                time.sleep(1)
                if auto: self._auto_review(t2); time.sleep(1)
                else: self._update_status("Click Review yourself.","#f9e2af")
                self._signup(t2,email,bi)
                self._update_status("✅ Done! Close browser when finished.","#a6e3a1")
                self.root.after(0,lambda:self.start_button.configure(
                    state="disabled",bg="#45475a",text="✅ BROWSER OPEN"))
                try:
                    while br.contexts: time.sleep(1)
                except: pass
                self._update_status("Browser closed.","#6c7086")
                self.root.after(0,lambda:self.start_button.configure(
                    state="normal",bg=ACCENT,text="▶  START"))
        except ImportError:
            self._update_status("Playwright missing.","#f38ba8")
            self.root.after(0,lambda:messagebox.showerror("Missing",
                "pip install playwright\npython -m playwright install chromium"))
            self.root.after(0,lambda:self.start_button.configure(state="normal",bg=ACCENT,text="▶  START"))
        except Exception as e:
            self._update_status(f"Error:{e}","#f38ba8")
            self.root.after(0,lambda:messagebox.showerror("Error",str(e)))
            self.root.after(0,lambda:self.start_button.configure(state="normal",bg=ACCENT,text="▶  START"))


def main():
    root = tk.Tk()
    ChessAutomationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()