"""browser startup

Uses a *persistent* profile stored in profile/ — same idea as your normal
Chrome profile. Log into a site once (see login.py) and every future run,
headless or not, is already logged in.
"""

from contextlib import contextmanager

from playwright.sync_api import sync_playwright

import config


@contextmanager
def open_browser(visible: bool = False, engine: str | None = None):
    """Yields a ready-to-use Playwright page. Closes cleanly afterwards.

    engine: "chromium" or "firefox"; None uses BROWSER from .env.
    Each engine keeps its own profile subdir (cookies aren't portable
    between them), so log in once per engine per site.
    """
    engine = engine or config.BROWSER
    headless = config.HEADLESS and not visible
    with sync_playwright() as p:
        if engine == "firefox":
            launcher, extra = p.firefox, {}
        else:
            # full Chromium even when headless - the default stripped-down
            # "headless shell" mishandles some popup/JS flows (PeopleSoft
            # report windows stay blank in it, for one)
            launcher, extra = p.chromium, {"channel": "chromium"}
        context = launcher.launch_persistent_context(
            user_data_dir=str(config.PROFILE_DIR / engine),
            headless=headless,
            viewport={"width": 1366, "height": 850},
            **extra,
        )
        # Sensible ceiling so a hung site fails loudly instead of forever.
        context.set_default_timeout(30_000)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            yield page
        finally:
            context.close()
