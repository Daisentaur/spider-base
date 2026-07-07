"""The class every task subclasses. tiny.

A task gets `self.page` (a Playwright page — the browser tab) and
overrides run(). Everything else here is convenience.
"""

import logging
import time

import notify


class Task:
    name = "unnamed-task"
    notify_on_success = True  # phone ping when run() finishes cleanly
    notify_on_failure = True  # phone ping when run() blows up
    browser = None  # "chromium" or "firefox"; None = BROWSER from .env
    needs_browser = True  # set False for plain-HTTP tasks (no self.page)

    def __init__(self, page):
        self.page = page
        self.log = logging.getLogger(self.name)

    def run(self):
        raise NotImplementedError("override run() in your task file")

    # ---- helpers ---------------------------------------------------------

    def watch(self, check, every: float = 30, max_wait: float | None = None):
        """Call check() every `every` seconds until it returns something
        truthy, then return that value.

        This is the workhorse for "act the moment it becomes available"
        tasks: check() should reload the page and return True when the
        buy/register button is finally there.
        """
        start = time.time()
        while True:
            result = check()
            if result:
                return result
            if max_wait is not None and time.time() - start > max_wait:
                raise TimeoutError(f"watch() gave up after {max_wait}s")
            self.log.info("condition not met, next check in %ss", every)
            time.sleep(every)

    def notify(self, text: str):
        notify.send(f"[{self.name}] {text}")
