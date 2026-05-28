# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-05-29

### 🎉 Initial Release

#### Features
- Tkinter GUI with dark theme
- Temp-mail integration (temp-mail.org & temp-mail.io)
- Auto-fill Chess.com sign-up form
  - UUID-based unique username generation
  - Secure random password (uppercase + lowercase + digit)
  - Human-like typing simulation for email/password
  - Fast-fill for username
- Board theme position picker (2x2 grid)
- Auto-click Review (most recent match) toggle
- Full onboarding automation (8 steps in ~7 seconds)
- Fast polling (300ms) for button detection
- Threaded automation (UI never freezes)
- Comprehensive error handling with fallbacks

#### Technical
- Single-file architecture (`main.py`)
- Playwright with Chromium (non-headless)
- No anti-bot stealth libraries (keeps it simple & stable)
- Supports both English and Vietnamese Chess.com UI