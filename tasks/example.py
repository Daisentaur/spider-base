"""Read-only example: scrape quotes from a practice site built for this.

    python run.py example --visible
"""
from base_task import Task


class ScrapeQuotes(Task):
    name = "example"
    notify_on_success = False  # nothing here is worth a phone ping

    def run(self):
        self.page.goto("https://quotes.toscrape.com")
        for quote in self.page.locator(".quote").all():
            text = quote.locator(".text").inner_text()
            author = quote.locator(".author").inner_text()
            self.log.info("%s — %s", author, text)
