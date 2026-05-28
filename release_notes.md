## 🎉 v1.0.0 — Initial Release

### Features
- 🔗 Paste any Chess.com match history URL
- 📧 Auto-fetch temp email (temp-mail.org / temp-mail.io)
- ✍️ Auto-fill sign-up form (unique UUID username + random password)
- 🎨 Board theme picker (4 positions)
- 🚀 Auto-click Review on most recent match (toggleable)
- 🧭 Full 8-step onboarding automation (~7 seconds)
- ⚡ Fast 300ms polling for instant button clicks
- 🖥️ Dark-themed Tkinter GUI (never freezes)
- 🌐 Supports English + Vietnamese Chess.com UI

### Requirements
- Python 3.8+
- `pip install playwright && python -m playwright install chromium`

### Quick Start
```bash
git clone https://github.com/Taam-dev/WFChessReviewerTdev.git
cd WFChessReviewerTdev
pip install -r requirements.txt
python -m playwright install chromium
python main.py