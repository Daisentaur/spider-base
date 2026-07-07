"""Central place for paths and settings. Everything else imports from here."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

PROFILE_DIR = ROOT / "profile"      # persistent browser profile (logins live here)
ARTIFACTS_DIR = ROOT / "artifacts"  # crash screenshots and page dumps
LOGS_DIR = ROOT / "logs"

# 1 = invisible browser (server default), 0 = show the window
HEADLESS = os.getenv("HEADLESS", "1") == "1"

# default engine: "firefox" or "chromium"; tasks can pin one with a
# `browser = "..."` class attribute (each engine keeps its own profile)
BROWSER = os.getenv("BROWSER", "firefox")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

for _d in (PROFILE_DIR, ARTIFACTS_DIR, LOGS_DIR):
    _d.mkdir(exist_ok=True)
