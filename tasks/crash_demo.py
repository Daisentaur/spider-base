"""Deliberate failure - run this to see what a crash looks like end to end:
a FAILED ping in Telegram, a screenshot + page HTML in artifacts/, the
traceback in the terminal and logs/, and exit code 1 (what cron sees).

    python run.py crash_demo
"""

from base_task import Task


class CrashDemo(Task):
    name = "crash-demo"

    def run(self):
        self.page.goto("https://quotes.toscrape.com")
        # this button does not exist; Playwright waits 5s, then raises
        self.page.click("text=Buy Now", timeout=5000)
