"""Generic page-change watcher - pings your phone when part of a page changes.

Single-shot and cron-friendly: each run fetches the page, compares what the
selector matches against the previous run, notifies only on change. Copy
this file per thing you want watched and adjust URL + SELECTOR.

    python run.py page_watch
    # cron, every 30 min:
    # */30 * * * * cd /path/to/scraper-base && .venv/bin/python run.py page_watch >> logs/cron.log 2>&1
"""

import hashlib

import config
from base_task import Task

URL = "https://quotes.toscrape.com"
SELECTOR = ".quote .text"  # the part of the page that matters


class PageWatch(Task):
    name = "page-watch"
    notify_on_success = False  # only the change is news

    state_file = config.ROOT / "output" / "page_watch.state"

    def run(self):
        self.page.goto(URL)
        texts = self.page.locator(SELECTOR).all_inner_texts()
        digest = hashlib.sha256("\n".join(t.strip() for t in texts).encode()).hexdigest()

        self.state_file.parent.mkdir(exist_ok=True)
        if not self.state_file.exists():
            self.state_file.write_text(digest)
            self.log.info("first run, baseline saved (%d elements)", len(texts))
            return
        if self.state_file.read_text() == digest:
            self.log.info("no change")
            return
        self.state_file.write_text(digest)
        self.notify(f"page changed: {URL}")
