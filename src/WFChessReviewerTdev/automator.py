"""
automator.py — Playwright Automation Engine
============================================
Handles the entire browser-based automation workflow:
  1. Launch stealth Chromium browser
  2. Register on Chess.com with generated credentials
  3. Handle email verification (link or OTP)
  4. Navigate to the target URL

Key design principles:
  - All browser code runs in a new asyncio event loop inside
    a background thread (called via asyncio.run())
  - Status/log messages are sent back to the GUI via a thread-safe
    callback function (queue-based, never touches Tkinter directly)
  - Screenshots are taken at each major step for debugging
  - Multiple CSS selectors are tried per element for UI resilience
  - Human-like typing with randomized inter-keystroke delays
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from loguru import logger

from .config import config
from .credentials import Credentials, CredentialGenerator
from .email_client import GuerrillaMailClient
from .verification import VerificationExtractor

# Try to import playwright; provide helpful error if not installed
try:
    from playwright.async_api import (
        async_playwright,
        Browser,
        BrowserContext,
        Page,
        TimeoutError as PWTimeoutError,
    )
except ImportError as _pw_err:
    raise ImportError(
        "Playwright is not installed. Run: pip install playwright && "
        "playwright install chromium"
    ) from _pw_err

# Try to import playwright-stealth
try:
    from playwright_stealth import stealth_async  # type: ignore[import]

    _STEALTH_AVAILABLE = True
except ImportError:
    _STEALTH_AVAILABLE = False
    logger.warning(
        "playwright-stealth not found. Stealth mode will be partially applied "
        "via manual JS injection only. Install with: pip install playwright-stealth"
    )

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
LogCallback = Callable[[str], None]
StepCallback = Callable[[int, int], None]  # (current_step, total_steps)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOTAL_STEPS = 5

# Randomized user agents to rotate through
_USER_AGENTS: List[str] = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
]

# Randomized viewport sizes (common resolutions)
_VIEWPORTS: List[Tuple[int, int]] = [
    (1920, 1080),
    (1366, 768),
    (1440, 900),
    (1280, 800),
    (1600, 900),
    (1536, 864),
]

# Chess.com registration form selectors (multiple fallbacks per element)
_SELECTORS = {
    "email_input": [
        'input[name="email"]',
        'input[type="email"]',
        "#email",
        '[placeholder*="email" i]',
        '[data-testid="email-input"]',
    ],
    "username_input": [
        'input[name="username"]',
        "#username",
        '[placeholder*="username" i]',
        '[placeholder*="Username" ]',
        '[data-testid="username-input"]',
    ],
    "password_input": [
        'input[name="password"]',
        'input[type="password"]',
        "#password",
        '[placeholder*="password" i]',
        '[data-testid="password-input"]',
    ],
    "next_button": [
        'button[type="submit"]',
        'button:has-text("Next")',
        'button:has-text("Continue")',
        '[data-cy="next-button"]',
        ".registration-button",
        "button.submit",
    ],
    "submit_button": [
        'button[type="submit"]',
        'button:has-text("Create Account")',
        'button:has-text("Register")',
        'button:has-text("Sign Up")',
        '[data-cy="submit-button"]',
    ],
    "cookie_consent": [
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("OK")',
        '[id*="accept" i]',
        '[class*="accept" i]',
        ".cookie-accept",
        "#cookie-accept",
    ],
    "skip_button": [
        'button:has-text("Skip")',
        'button:has-text("Maybe Later")',
        'button:has-text("Not Now")',
        '[data-cy="skip"]',
        ".skip-button",
    ],
    "username_error": [
        ".error-message",
        ".field-error",
        '[class*="error" i]',
        '[role="alert"]',
        ".validation-error",
    ],
    "otp_input": [
        'input[name="code"]',
        'input[name="otp"]',
        'input[name="verification_code"]',
        '[placeholder*="code" i]',
        'input[type="number"]',
        'input[inputmode="numeric"]',
    ],
}

# Anti-detection JavaScript to inject into browser pages
_STEALTH_JS = """
    // Override navigator.webdriver to hide automation
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
    });

    // Fake chrome.runtime object
    if (!window.chrome) {
        window.chrome = {
            runtime: {
                PlatformOs: {MAC: 'mac', WIN: 'win', ANDROID: 'android'},
                PlatformArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64'},
                PlatformNaclArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64'},
                RequestUpdateCheckStatus: {THROTTLED: 'throttled'},
                OnInstalledReason: {INSTALL: 'install', UPDATE: 'update'},
                OnRestartRequiredReason: {APP_UPDATE: 'app_update'},
            },
        };
    }

    // Fake navigator.plugins (non-empty array signals real browser)
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'},
        ],
        configurable: true,
    });

    // Set realistic languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'es'],
        configurable: true,
    });

    // Mask automation-related permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({state: Notification.permission})
            : originalQuery(parameters)
    );
"""


class StopRequested(Exception):
    """Raised internally when the user requests the automation to stop."""

    pass


class AutomationError(Exception):
    """Raised when a non-recoverable automation error occurs."""

    pass


class ChessAutomator:
    """
    Orchestrates the complete Chess.com registration automation workflow.

    Parameters
    ----------
    log_callback : LogCallback
        Thread-safe function to send log strings to the GUI.
    step_callback : StepCallback
        Thread-safe function to update the step indicator in the GUI.
    target_url : str
        The Chess.com URL to navigate to after registration.

    Attributes
    ----------
    credentials : Optional[Credentials]
        Set after Step 1 & 3 complete successfully.
    _stop_flag : bool
        Set to True by request_stop() to signal the workflow to halt.
    """

    def __init__(
        self,
        log_callback: LogCallback,
        step_callback: StepCallback,
        target_url: str,
    ) -> None:
        self._log = log_callback
        self._step = step_callback
        self._target_url = target_url
        self._stop_flag = False

        self.credentials: Optional[Credentials] = None
        self._screenshot_counter = 0
        self._page: Optional[Page] = None
        self._context: Optional[BrowserContext] = None
        self._browser: Optional[Browser] = None

    # ------------------------------------------------------------------
    # Public control methods
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Entry point: run the full automation workflow synchronously.

        This is designed to be called from a background threading.Thread.
        It creates a new asyncio event loop for Playwright's async API.
        """
        try:
            asyncio.run(self._run_async())
        except StopRequested:
            self._log("⏹️  Automation stopped by user request.")
            logger.info("Automation stopped by user.")
        except AutomationError as exc:
            self._log(f"❌ Automation error: {exc}")
            logger.error(f"Automation error: {exc}")
        except Exception as exc:
            self._log(f"❌ Unexpected error: {exc}")
            logger.exception(f"Unexpected automation error: {exc}")

    def request_stop(self) -> None:
        """Signal the automation to stop at the next safe checkpoint."""
        self._stop_flag = True
        logger.info("Stop requested by user.")

    # ------------------------------------------------------------------
    # Main async workflow
    # ------------------------------------------------------------------

    async def _run_async(self) -> None:
        """Async entry point — runs all five automation steps."""
        async with async_playwright() as playwright:
            # ---- Step 1: Generate temp email ----
            self._check_stop()
            self._step(1, TOTAL_STEPS)
            self._log("━━━ Step 1/5: Generating temporary email ━━━")
            email, session_token = await self._step1_generate_email()

            # ---- Step 2: Launch stealth browser ----
            self._check_stop()
            self._step(2, TOTAL_STEPS)
            self._log("━━━ Step 2/5: Launching stealth browser ━━━")
            page = await self._step2_launch_browser(playwright)

            try:
                # ---- Step 3: Register on Chess.com ----
                self._check_stop()
                self._step(3, TOTAL_STEPS)
                self._log("━━━ Step 3/5: Registering on Chess.com ━━━")
                await self._step3_register(page, email, session_token)

                # ---- Step 4: Email verification ----
                self._check_stop()
                self._step(4, TOTAL_STEPS)
                self._log("━━━ Step 4/5: Handling email verification ━━━")
                await self._step4_verify_email(page, session_token)

                # ---- Step 5: Navigate to target URL ----
                self._check_stop()
                self._step(5, TOTAL_STEPS)
                self._log("━━━ Step 5/5: Navigating to target URL ━━━")
                await self._step5_navigate_to_target(page)

                self._step(TOTAL_STEPS, TOTAL_STEPS)
                self._log("✅ Automation completed successfully!")
                logger.success("Full automation workflow completed.")

                # Keep browser open for user inspection
                self._log("ℹ️  Browser will stay open. Close it manually when done.")
                # Wait indefinitely (or until stop is requested)
                while not self._stop_flag:
                    await asyncio.sleep(1)

            except StopRequested:
                raise
            except Exception as exc:
                await self._take_screenshot(page, "error_final")
                raise AutomationError(str(exc)) from exc
            finally:
                # Cleanup on stop
                if self._stop_flag:
                    await self._cleanup()

    # ------------------------------------------------------------------
    # Step 1 — Generate temporary email
    # ------------------------------------------------------------------

    async def _step1_generate_email(self) -> Tuple[str, str]:
        """
        Use Guerrilla Mail API to get a temporary email address.

        Returns
        -------
        Tuple[str, str]
            (email_address, session_token)
        """
        # Run blocking HTTP call in thread executor
        loop = asyncio.get_event_loop()
        client = GuerrillaMailClient()

        try:
            email, token = await loop.run_in_executor(None, client.get_email_address)
            self._log(f"📧 Temporary email: {email}")

            # Build full credentials now (browser not yet needed)
            self.credentials = CredentialGenerator.generate(
                email=email,
                session_token=token,
            )
            self._log(f"👤 Generated username: {self.credentials.username}")
            self._log(f"🔑 Generated password: {'*' * len(self.credentials.password)}")

            # Save credentials to JSON immediately
            await loop.run_in_executor(None, self._save_credentials_to_file)

            return email, token

        finally:
            client.close()

    # ------------------------------------------------------------------
    # Step 2 — Launch stealth browser
    # ------------------------------------------------------------------

    async def _step2_launch_browser(self, playwright) -> Page:
        """
        Launch a stealth Chromium browser with anti-detection settings.

        Parameters
        ----------
        playwright : AsyncPlaywright
            The Playwright context manager object.

        Returns
        -------
        Page
            The active Playwright page ready for navigation.
        """
        user_agent = random.choice(_USER_AGENTS)
        viewport_w, viewport_h = random.choice(_VIEWPORTS)

        self._log(f"🌐 User-Agent: {user_agent[:60]}...")
        self._log(f"📐 Viewport: {viewport_w}×{viewport_h}")

        # Build Chromium launch args for anti-detection
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-extensions",
            f"--window-size={viewport_w},{viewport_h}",
            "--lang=en-US,en",
        ]

        self._log(
            f"🚀 Launching {'headless' if config.browser_headless else 'visible'} "
            "Chromium (stealth mode)..."
        )

        self._browser = await playwright.chromium.launch(
            headless=config.browser_headless,
            slow_mo=config.slow_mo,
            args=launch_args,
        )

        # Create incognito context with custom headers
        self._context = await self._browser.new_context(
            user_agent=user_agent,
            viewport={"width": viewport_w, "height": viewport_h},
            locale="en-US",
            timezone_id="America/New_York",
            permissions=[],
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            },
        )

        # Set default timeouts
        self._context.set_default_timeout(config.default_timeout)
        self._context.set_default_navigation_timeout(config.navigation_timeout)

        # Inject anti-detection script on every new page/frame
        await self._context.add_init_script(_STEALTH_JS)

        page = await self._context.new_page()
        self._page = page

        # Apply playwright-stealth if available
        if _STEALTH_AVAILABLE:
            await stealth_async(page)
            self._log("🛡️  playwright-stealth applied")
        else:
            self._log(
                "⚠️  playwright-stealth not available — using manual JS injection"
            )

        self._log("✅ Stealth browser launched successfully")
        await self._take_screenshot(page, "01_browser_launched")
        return page

    # ------------------------------------------------------------------
    # Step 3 — Register on Chess.com
    # ------------------------------------------------------------------

    async def _step3_register(
        self,
        page: Page,
        email: str,
        session_token: str,
    ) -> None:
        """
        Navigate to Chess.com registration and complete the multi-step form.

        Parameters
        ----------
        page : Page
            Active Playwright page.
        email : str
            Temporary email address to use for registration.
        session_token : str
            Guerrilla Mail session token (stored in credentials).
        """
        self._log(f"🔗 Navigating to {config.chess_register_url}")
        await page.goto(
            config.chess_register_url,
            wait_until="domcontentloaded",
        )

        await self._take_screenshot(page, "02_register_page_loaded")
        await self._dismiss_cookie_consent(page)

        # ---- Sub-step 3a: Enter email ----
        self._log(f"📧 Entering email: {email}")
        await self._fill_field(
            page,
            _SELECTORS["email_input"],
            email,
            label="email input",
        )
        await self._click_next(page)
        await asyncio.sleep(1.5)  # Brief pause for form transition
        await self._take_screenshot(page, "03_after_email_step")

        # ---- Sub-step 3b: Enter username (with retry on taken) ----
        assert self.credentials is not None
        username = self.credentials.username
        max_username_retries = 5

        for attempt in range(max_username_retries):
            self._check_stop()
            self._log(
                f"👤 Entering username: {username!r} "
                f"(attempt {attempt + 1}/{max_username_retries})"
            )

            username_field = await self._find_element(
                page, _SELECTORS["username_input"]
            )
            if username_field:
                await username_field.clear()
                await self._human_type(username_field, username)
            else:
                self._log("⚠️  Username field not found — may be on different step")
                break

            # Wait briefly to let validation run
            await asyncio.sleep(0.8)

            # Check for "username taken" error message
            if await self._username_is_taken(page):
                self._log(
                    f"⚠️  Username {username!r} already taken, generating new one..."
                )
                username = CredentialGenerator.generate_username()
                self.credentials = Credentials(
                    email=self.credentials.email,
                    username=username,
                    password=self.credentials.password,
                    session_token=self.credentials.session_token,
                )
                await asyncio.sleep(0.5)
                continue

            # No error — proceed to next step
            self._log(f"✅ Username {username!r} accepted")
            await self._click_next(page)
            await asyncio.sleep(1.5)
            break
        else:
            raise AutomationError(
                f"All {max_username_retries} username attempts failed"
            )

        await self._take_screenshot(page, "04_after_username_step")

        # ---- Sub-step 3c: Enter password ----
        self._log("🔑 Entering password...")
        password_field = await self._find_element(page, _SELECTORS["password_input"])
        if password_field:
            await self._human_type(password_field, self.credentials.password)
        else:
            self._log("⚠️  Password field not found — trying alternate approach")

        await self._take_screenshot(page, "05_password_entered")

        # ---- Sub-step 3d: Submit form ----
        self._log("📤 Submitting registration form...")
        await self._click_submit(page)

        # Wait for navigation after submit
        try:
            await page.wait_for_load_state("networkidle", timeout=20_000)
        except PWTimeoutError:
            self._log("⚠️  Network idle timeout — continuing anyway")

        await self._take_screenshot(page, "06_after_submit")

        # ---- Sub-step 3e: Handle post-registration modals ----
        await self._dismiss_onboarding_modals(page)
        await self._take_screenshot(page, "07_after_onboarding")

        self._log(
            f"✅ Registration submitted for {email!r} "
            f"/ {self.credentials.username!r}"
        )

    # ------------------------------------------------------------------
    # Step 4 — Email Verification
    # ------------------------------------------------------------------

    async def _step4_verify_email(
        self,
        page: Page,
        session_token: str,
    ) -> None:
        """
        Poll Guerrilla Mail inbox and handle the Chess.com verification email.

        Parameters
        ----------
        page : Page
            Active Playwright page.
        session_token : str
            Guerrilla Mail session token.
        """
        self._log("📬 Polling inbox for verification email...")

        loop = asyncio.get_event_loop()
        client = GuerrillaMailClient()

        attempt_counter = {"value": 0}

        def progress_callback(attempt: int, max_attempts: int) -> None:
            attempt_counter["value"] = attempt
            if attempt % 3 == 0:  # Log every 3rd attempt to avoid spam
                self._log(
                    f"⏳ Waiting for verification email... "
                    f"({attempt}/{max_attempts})"
                )
            self._check_stop()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: client.wait_for_email_from(
                    session_token=session_token,
                    sender_keyword="chess.com",
                    progress_callback=progress_callback,
                ),
            )
        finally:
            client.close()

        if result is None:
            self._log(
                "⚠️  No verification email received within timeout. "
                "Continuing without email verification."
            )
            return

        mail_id, email_body = result
        self._log("📩 Verification email received! Extracting verification method...")

        if not email_body:
            self._log("⚠️  Email body is empty — cannot extract verification info")
            return

        # Parse verification link or OTP
        extractor = VerificationExtractor()
        verification = extractor.extract(email_body)

        if verification.has_link:
            self._log(f"🔗 Verification link found: {verification.verification_link!r}")
            self._log("🌐 Navigating to verification link...")
            try:
                await page.goto(
                    verification.verification_link,
                    wait_until="domcontentloaded",
                    timeout=config.navigation_timeout,
                )
                await asyncio.sleep(2)
                await self._take_screenshot(page, "08_after_verification_link")
                await self._dismiss_onboarding_modals(page)
                self._log("✅ Email verified via link!")
            except PWTimeoutError:
                self._log("⚠️  Verification link navigation timed out — continuing")

        elif verification.has_otp:
            self._log(f"🔢 OTP code found: {verification.otp_code!r}")
            await self._enter_otp(page, verification.otp_code)
            self._log("✅ Email verified via OTP code!")

        else:
            self._log(
                "⚠️  Could not extract verification link or OTP from email body. "
                f"Raw chess.com links found: {verification.raw_links}"
            )

    # ------------------------------------------------------------------
    # Step 5 — Navigate to target URL
    # ------------------------------------------------------------------

    async def _step5_navigate_to_target(self, page: Page) -> None:
        """
        Navigate the browser to the user-specified Chess.com URL.

        Handles login-page redirects by re-logging in with
        the generated credentials.

        Parameters
        ----------
        page : Page
            Active Playwright page.
        """
        target = self._target_url.strip()
        if not target:
            self._log("⚠️  No target URL provided — skipping navigation")
            return

        self._log(f"🎯 Navigating to target: {target}")

        try:
            await page.goto(target, wait_until="domcontentloaded")
            await asyncio.sleep(2)
        except PWTimeoutError:
            self._log("⚠️  Target navigation timed out, checking current page...")

        current_url = page.url
        self._log(f"📍 Current URL: {current_url}")

        # Detect if redirected to login page
        if "login" in current_url.lower() or "sign_in" in current_url.lower():
            self._log(
                "🔐 Redirected to login page — attempting re-login with "
                "generated credentials..."
            )
            await self._attempt_login(page)

            # Retry navigation after login
            try:
                await page.goto(target, wait_until="domcontentloaded")
                await asyncio.sleep(2)
                self._log(f"✅ Navigated to target after re-login: {page.url}")
            except PWTimeoutError:
                self._log("⚠️  Target navigation timed out after re-login")
        else:
            self._log(f"✅ Successfully navigated to: {current_url}")

        await self._dismiss_onboarding_modals(page)
        await self._take_screenshot(page, "09_target_url_reached")

    # ------------------------------------------------------------------
    # Helper: Attempt login
    # ------------------------------------------------------------------

    async def _attempt_login(self, page: Page) -> None:
        """
        Attempt to log into Chess.com with the generated credentials.

        Parameters
        ----------
        page : Page
            Active Playwright page (should be on the login page).
        """
        if not self.credentials:
            self._log("❌ No credentials available for login attempt")
            return

        try:
            await page.goto(config.chess_login_url, wait_until="domcontentloaded")

            # Try username field (Chess.com login accepts username or email)
            username_field = await self._find_element(
                page, _SELECTORS["username_input"] + ['input[name="login"]']
            )
            if username_field:
                await self._human_type(username_field, self.credentials.username)

            password_field = await self._find_element(
                page, _SELECTORS["password_input"]
            )
            if password_field:
                await self._human_type(password_field, self.credentials.password)

            await self._click_submit(page)
            await page.wait_for_load_state("networkidle", timeout=15_000)
            self._log(f"🔐 Login attempted for {self.credentials.username!r}")

        except Exception as exc:
            self._log(f"⚠️  Login attempt failed: {exc}")

    # ------------------------------------------------------------------
    # Form interaction helpers
    # ------------------------------------------------------------------

    async def _fill_field(
        self,
        page: Page,
        selectors: List[str],
        value: str,
        label: str = "field",
    ) -> bool:
        """
        Try multiple selectors and fill the first matching field.

        Parameters
        ----------
        page : Page
            Active Playwright page.
        selectors : List[str]
            CSS selectors to try in order.
        value : str
            Text value to type into the field.
        label : str
            Human-readable field name for log messages.

        Returns
        -------
        bool
            True if field was found and filled, False otherwise.
        """
        element = await self._find_element(page, selectors)
        if element is None:
            self._log(f"⚠️  Could not find {label}")
            return False

        await element.clear()
        await self._human_type(element, value)
        return True

    async def _find_element(self, page: Page, selectors: List[str]):
        """
        Try multiple CSS selectors and return the first visible match.

        Parameters
        ----------
        page : Page
            Active Playwright page.
        selectors : List[str]
            CSS selectors to try in order.

        Returns
        -------
        ElementHandle or None
            The first matching visible element, or None if none found.
        """
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=2000):
                    return locator
            except Exception:
                continue
        return None

    async def _human_type(self, element, text: str) -> None:
        """
        Type text into an element with human-like randomized delays.

        Each character is typed individually with a random delay between
        30ms and 120ms to simulate natural typing speed.

        Parameters
        ----------
        element : Locator
            Playwright locator for the target input element.
        text : str
            Text to type.
        """
        await element.click()
        for char in text:
            await element.type(char, delay=random.randint(30, 120))
            # Occasional longer pause (simulates thinking/hesitation)
            if random.random() < 0.05:  # 5% chance of a longer pause
                await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _click_next(self, page: Page) -> None:
        """Click a "Next" / "Continue" type button."""
        button = await self._find_element(page, _SELECTORS["next_button"])
        if button:
            await button.click()
        else:
            self._log("⚠️  Next button not found — trying keyboard Enter")
            await page.keyboard.press("Enter")

    async def _click_submit(self, page: Page) -> None:
        """Click the final form submission button."""
        button = await self._find_element(
            page,
            _SELECTORS["submit_button"] + _SELECTORS["next_button"],
        )
        if button:
            await button.click()
        else:
            self._log("⚠️  Submit button not found — trying keyboard Enter")
            await page.keyboard.press("Enter")

    async def _username_is_taken(self, page: Page) -> bool:
        """
        Check if any username-taken error message is visible on the page.

        Returns
        -------
        bool
            True if an error message containing "taken" or "unavailable"
            is visible.
        """
        for selector in _SELECTORS["username_error"]:
            try:
                locators = page.locator(selector)
                count = await locators.count()
                for i in range(count):
                    elem = locators.nth(i)
                    if await elem.is_visible(timeout=1000):
                        text = (await elem.text_content() or "").lower()
                        if any(
                            keyword in text
                            for keyword in ["taken", "unavailable", "exists", "already"]
                        ):
                            return True
            except Exception:
                continue
        return False

    async def _enter_otp(self, page: Page, otp: str) -> None:
        """
        Enter an OTP code into the verification input field.

        Parameters
        ----------
        page : Page
            Active Playwright page.
        otp : str
            The OTP code string to enter.
        """
        otp_field = await self._find_element(page, _SELECTORS["otp_input"])
        if otp_field:
            await self._human_type(otp_field, otp)
            await self._click_submit(page)
            await asyncio.sleep(2)
            await self._take_screenshot(page, "08_after_otp_entry")
        else:
            self._log("⚠️  OTP input field not found on page")

    async def _dismiss_cookie_consent(self, page: Page) -> None:
        """Dismiss cookie consent banners if present."""
        for selector in _SELECTORS["cookie_consent"]:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=2000):
                    await locator.click()
                    self._log("🍪 Cookie consent dismissed")
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                continue

    async def _dismiss_onboarding_modals(self, page: Page) -> None:
        """
        Dismiss any post-registration onboarding modals or skill pickers.

        Tries multiple rounds since dismissing one modal may reveal another.
        """
        modal_selectors = _SELECTORS["skip_button"] + [
            'button:has-text("Got it")',
            'button:has-text("OK")',
            'button:has-text("Close")',
            'button:has-text("Done")',
            'button:has-text("Let\'s Go")',
            'button:has-text("Start Playing")',
            '[aria-label="Close"]',
            ".modal-close",
            ".close-button",
        ]

        for _ in range(5):  # Try up to 5 rounds of modal dismissal
            dismissed_any = False
            for selector in modal_selectors:
                try:
                    locator = page.locator(selector).first
                    if await locator.is_visible(timeout=1500):
                        await locator.click()
                        self._log(f"🗙 Dismissed modal ({selector!r})")
                        await asyncio.sleep(0.8)
                        dismissed_any = True
                        break  # One dismiss per round — then re-check
                except Exception:
                    continue
            if not dismissed_any:
                break  # No more modals to dismiss

    # ------------------------------------------------------------------
    # Screenshot helper
    # ------------------------------------------------------------------

    async def _take_screenshot(self, page: Page, label: str) -> None:
        """
        Save a numbered debug screenshot to the screenshots directory.

        Parameters
        ----------
        page : Page
            Active Playwright page.
        label : str
            Descriptive label appended to the filename.
        """
        self._screenshot_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._screenshot_counter:02d}_{label}_{timestamp}.png"
        path = config.screenshots_dir / filename

        try:
            await page.screenshot(path=str(path), full_page=False)
            logger.debug(f"Screenshot saved: {path}")
        except Exception as exc:
            logger.debug(f"Screenshot failed ({label}): {exc}")

    # ------------------------------------------------------------------
    # Credentials persistence
    # ------------------------------------------------------------------

    def _save_credentials_to_file(self) -> None:
        """Save current credentials to a timestamped JSON file."""
        if not self.credentials:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"credentials_{timestamp}.json"
        path = config.credentials_dir / filename

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.credentials.to_dict(), f, indent=2)
            logger.info(f"Credentials saved to: {path}")
        except OSError as exc:
            logger.warning(f"Failed to save credentials: {exc}")

    # ------------------------------------------------------------------
    # Stop check helper
    # ------------------------------------------------------------------

    def _check_stop(self) -> None:
        """
        Raise StopRequested if the stop flag has been set.

        Call this at the start of each major step and at safe
        checkpoints within long operations.
        """
        if self._stop_flag:
            raise StopRequested("User requested stop")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def _cleanup(self) -> None:
        """Close browser context and browser cleanly."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            logger.debug("Browser cleaned up successfully")
        except Exception as exc:
            logger.debug(f"Cleanup error (non-critical): {exc}")
