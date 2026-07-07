"""Push a message to your phone via Telegram.

If the token/chat id aren't set in .env, messages just go to the log
instead of failing, so tasks work fine before you set Telegram up.
"""
import logging

import requests

import config

log = logging.getLogger("notify")


def send(text: str):
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        log.info("(telegram not configured) %s", text)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        ).raise_for_status()
    except Exception:
        # A dead notification should never kill the task itself.
        log.exception("telegram send failed, message was: %s", text)


def send_photo(photo_path, caption: str = ""):
    """Send an image (e.g. a crash screenshot) with a caption.

    Falls back to a plain text message if the photo can't be sent, so the
    alert still gets through one way or another.
    """
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        log.info("(telegram not configured) photo %s: %s", photo_path, caption)
        return
    try:
        with open(photo_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto",
                # telegram caps captions at 1024 chars
                data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption[:1024]},
                files={"photo": f},
                timeout=30,
            ).raise_for_status()
    except Exception:
        log.exception("telegram photo send failed: %s", photo_path)
        send(caption)
