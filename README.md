# ♞ WFChessReviewerTdev

> **Chess.com Account Automation & Match History Reviewer Desktop Tool**

[![CI](https://github.com/Taam-dev/WFChessReviewerTdev/actions/workflows/ci.yml/badge.svg)](https://github.com/Taam-dev/WFChessReviewerTdev/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready desktop GUI application that automates:

1. 📧 Generating a temporary email via [Guerrilla Mail API](https://www.guerrillamail.com/)
2. 🌐 Launching a stealth Chromium browser with anti-detection measures
3. ♟ Registering a new account on Chess.com
4. ✉️ Verifying the email automatically (link or OTP code)
5. 🎯 Navigating to any Chess.com match history URL you specify

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🖥️ Modern GUI | Dark/light CustomTkinter interface |
| 📧 Temp Email | Auto-generated via Guerrilla Mail API (no manual action) |
| 🛡️ Stealth Browser | Playwright + playwright-stealth + manual JS injection |
| 🤖 Smart Registration | Human-like typing, auto-retry on taken usernames |
| ✉️ Auto Verification | Parses link or OTP from Chess.com email |
| 📋 Credentials Display | Shows email/username/password with copy button |
| 📊 Progress Tracking | Step indicator (1/5 → 5/5) with progress bar |
| 📝 Real-time Logs | Scrollable console log with timestamps |
| 💾 Auto-save | Credentials saved to JSON files automatically |
| 📸 Debug Screenshots | Numbered screenshots saved at each step |

---

## 🖥️ GUI Preview

```
┌─────────────────────────────────────────────────────┐
│  ♞  WFChessReviewerTdev                             │
│     Chess.com Account Automation & Match History     │
├─────────────────────────────────────────────────────┤
│  ♟ Chess.com URL: [https://chess.com/member/... ]   │
│          [ ▶ Start Automation ]  [ ⏹ Stop ]        │
├─────────────────────────────────────────────────────┤
│  Progress: ████████░░  Step 4 / 5                   │
├─────────────────────────────────────────────────────┤
│  📋 Console Log                          [ Clear ]  │
│  [10:23:01] 🚀 Starting automation...               │
│  [10:23:02] 📧 Temporary email: user@grr.la         │
│  [10:23:04] 🌐 Launching stealth browser...         │
│  [10:23:08] ♟ Navigating to Chess.com register...  │
│  [10:23:15] 📬 Polling inbox for verification...    │
├─────────────────────────────────────────────────────┤
│  🔐 Generated Credentials                           │
│  📧 Email:    user@grr.la                           │
│  👤 Username: swift_knight_a3x9                     │
│  🔑 Password: ●●●●●●●●●●●●●●●●   [👁]             │
│          [ 📋 Copy Credentials ]                    │
├─────────────────────────────────────────────────────┤
│  ●  Status: Running            v1.0.0 │ WFChess    │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Taam-dev/WFChessReviewerTdev.git
cd WFChessReviewerTdev
```

### 2. Create virtual environment

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Install Playwright browsers

```bash
playwright install chromium
```

### 5. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env to customize settings (headless mode, timeouts, etc.)
```

### 6. Run the application

```bash
# Via the installed entry point:
wfchess

# Or directly:
python -m WFChessReviewerTdev.app
```

---

## 📖 Usage Guide

### Basic Usage

1. **Launch the app** using `wfchess` command
2. **Paste a Chess.com URL** in the input field
   - Example: `https://www.chess.com/member/yourname/games`
3. **Click "▶ Start Automation"**
4. Watch the console log for real-time progress
5. After completion, view/copy the generated credentials
6. The browser remains open for manual review

### Understanding the Steps

| Step | What Happens |
|------|-------------|
| **1/5** | Guerrilla Mail API generates a temporary email address |
| **2/5** | Stealth Chromium browser launches with anti-detection |
| **3/5** | Chess.com registration form is filled and submitted |
| **4/5** | Inbox is polled until Chess.com verification email arrives |
| **5/5** | Browser navigates to your specified Chess.com URL |

### Stopping the Automation

Click **"⏹ Stop"** at any time. The automation finishes its current atomic operation cleanly, closes the browser, and resets to Idle state.

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BROWSER_HEADLESS` | `false` | Run browser without visible window |
| `SLOW_MO` | `50` | Milliseconds between Playwright actions |
| `DEFAULT_TIMEOUT` | `30000` | Element wait timeout (ms) |
| `NAVIGATION_TIMEOUT` | `60000` | Page load timeout (ms) |
| `EMAIL_POLL_INTERVAL` | `5` | Seconds between inbox polls |
| `EMAIL_POLL_MAX_ATTEMPTS` | `60` | Max polls before giving up (5 min) |
| `LOG_LEVEL` | `INFO` | Log verbosity: DEBUG/INFO/WARNING/ERROR |

---

## 📁 Project Structure

```
WFChessReviewerTdev/
├── src/WFChessReviewerTdev/
│   ├── __init__.py          # Package metadata & exports
│   ├── app.py               # CustomTkinter GUI application
│   ├── automator.py         # Playwright automation engine (5 steps)
│   ├── email_client.py      # Guerrilla Mail REST API client
│   ├── credentials.py       # Cryptographic credential generator
│   ├── verification.py      # Email verification link/OTP extractor
│   └── config.py            # AppConfig with env var loading
├── tests/
│   ├── test_credentials.py  # Unit tests for credential generator
│   ├── test_email_client.py # Unit tests for Guerrilla Mail client
│   ├── test_verification.py # Unit tests for verification extractor
│   └── test_config.py       # Unit tests for configuration loading
├── assets/
│   └── icon.png             # App icon (512×512 chess knight PNG)
├── screenshots/             # Auto-generated debug screenshots
├── logs/                    # Auto-generated rotating log files
├── credentials/             # Auto-generated credential JSON files
├── .github/workflows/ci.yml # GitHub Actions CI/CD pipeline
├── pyproject.toml           # Package metadata and tool configuration
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Development & test dependencies
├── .env.example             # Environment variable documentation
└── README.md                # This file
```

---

## 🔧 Troubleshooting

### Browser doesn't launch
```bash
# Reinstall Playwright browsers
playwright install chromium --force

# Test Playwright works
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); b.close(); p.stop(); print('OK')"
```

### Registration form selectors fail
Chess.com updates their UI periodically. If Step 3 fails:
1. Set `BROWSER_HEADLESS=false` to watch the browser
2. Set `SLOW_MO=500` to slow down actions
3. Check `screenshots/` for debug images
4. Update selectors in `automator.py → _SELECTORS`

### No verification email received
- Guerrilla Mail emails occasionally filter Chess.com mail
- Increase `EMAIL_POLL_MAX_ATTEMPTS=120` for longer waiting
- The app continues anyway — manual verification may be needed

### GUI appears frozen
The automation always runs in a background thread. If the GUI appears frozen, check:
- `logs/` directory for error messages
- Ensure you're running Python 3.10+ (not 3.9 or older)

### `playwright-stealth` not found warning
```bash
pip install playwright-stealth
```
The app works without it (falls back to manual JS injection) but stealth mode is less comprehensive.

---

## 🧪 Running Tests

```bash
# All unit tests
pytest tests/ -v

# Unit tests only (no network/browser)
pytest tests/ -m "not integration" -v

# With coverage report
pytest tests/ --cov=src/WFChessReviewerTdev --cov-report=html
open htmlcov/index.html
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
