"""Watch Bugcrowd for newly launched bug bounty programs; ping the new ones.

Bugcrowd serves its program list as JSON, so this skips the browser
entirely - it's a plain HTTP task, faster and lighter than driving a page.
Each run diffs against programs seen before and notifies only on new ones.

    python run.py bounty_watch
    # cron, every 6 hours:
    # 0 */6 * * * cd /path/to/scraper-base && .venv/bin/python run.py bounty_watch >> logs/cron.log 2>&1

HackerOne can be added the same way later - it also has a JSON directory.
"""

import json

import requests

import config
from base_task import Task

API = "https://bugcrowd.com/engagements.json?category=bug_bounty&sort_by=promoted&page="
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Firefox/151.0"}


class BountyWatch(Task):
    name = "bounty-watch"
    needs_browser = False  # pure HTTP, no page needed
    notify_on_success = False  # only new programs are news

    pages = 3  # how many pages of the directory to scan each run
    seen_file = config.ROOT / "output" / "bounty_seen.json"

    def run(self):
        current = self.fetch_programs()
        self.log.info("fetched %d programs", len(current))

        seen = set()
        if self.seen_file.exists():
            seen = set(json.loads(self.seen_file.read_text()))

        new = [p for p in current if p["url"] not in seen]

        # first run just establishes the baseline - don't ping 60 programs
        if not seen:
            self.log.info("first run, baseline of %d programs saved", len(current))
        elif new:
            for p in new:
                self.notify(f"new bounty: {p['name']} ({p['reward']})\n{p['url']}")
            self.log.info("notified %d new programs", len(new))
        else:
            self.log.info("no new programs")

        # remember everything seen now (union, so programs don't re-alert
        # if they drop off later pages)
        self.seen_file.parent.mkdir(exist_ok=True)
        all_urls = sorted(seen | {p["url"] for p in current})
        self.seen_file.write_text(json.dumps(all_urls))

    def fetch_programs(self):
        programs, seen_urls = [], set()
        for page in range(1, self.pages + 1):
            r = requests.get(API + str(page), headers=HEADERS, timeout=20)
            r.raise_for_status()
            engagements = r.json().get("engagements", [])
            if not engagements:
                break  # ran past the last page
            for e in engagements:
                url = "https://bugcrowd.com" + e["briefUrl"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                reward = (e.get("rewardSummary") or {}).get("summary") or "n/a"
                programs.append({"name": e["name"], "url": url, "reward": reward})
        return programs
