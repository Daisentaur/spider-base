"""Open a visible browser so you can log into a site by hand.

    python login.py https://the-site.com/login
    python login.py https://the-site.com/login --browser chromium

Log in normally in the window that opens, then press Enter in the
terminal. The session lands in that engine's profile and every future
run of every task using the same engine reuses it. Log in once per
engine per site - chromium and firefox keep separate profiles.
"""

import argparse

from browser import open_browser

parser = argparse.ArgumentParser()
parser.add_argument("url", nargs="?", default="about:blank")
parser.add_argument("--browser", choices=["chromium", "firefox"], default=None,
                    help="engine whose profile to log into (default: BROWSER from .env)")
args = parser.parse_args()

with open_browser(visible=True, engine=args.browser) as page:
    page.goto(args.url)
    input("Log in in the browser window, then press Enter here to save and exit... ")
