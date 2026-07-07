"""The 'act the moment it becomes available' pattern — the skeleton for
every auto-buy / auto-register task. Points at a practice site so it
actually runs end to end:

    python run.py example_watch --visible

To make a real task: copy this file, change the URL, change available()
to detect your real condition (a Register button appearing, Add-to-cart
no longer disabled), and change act() to do the real clicks.
"""
from base_task import Task


class WatchAndAct(Task):
    name = "example-watch"

    def run(self):
        self.page.goto("https://quotes.toscrape.com")
        self.watch(self.available, every=10, max_wait=3600)
        self.act()

    def available(self):
        # Reload so we see fresh state, then check for the trigger element.
        # On the practice site the "Next" link always exists, so this
        # succeeds on the first check — which is the point of a demo.
        self.page.reload()
        return self.page.locator("text=Next").count() > 0

    def act(self):
        # Stand-in for the real buy/register click sequence.
        self.page.click("text=Next")
        self.notify("condition met, action performed: " + self.page.url)
