# spider-base

A small base for bots that scrape sites and act on them: auto-buy, auto-register,
watch-for-availability, plain data scraping. Clone it (or just copy a file in
`tasks/`) per job.

It drives a real browser (Firefox or Chromium) via
[Playwright](https://playwright.dev/python/), so it works on any site a human
can use: JavaScript-heavy pages, logins, carts, forms.

**In all hoensty PLEASE read the GUIDE.md file its a proper step by step of how to work the tool, It'll be your best friend when setting up**

## How it fits together

```
run.py            entry point: python run.py <task-name>
browser.py        starts Firefox or Chromium with a persistent profile (logins stick)
base_task.py      the Task class you subclass; has the watch() poll helper
notify.py         Telegram pings (falls back to log output if unconfigured)
login.py          opens a visible browser so you log into a site once, by hand
config.py         paths + .env settings
tasks/            one file per job; copy an example to start a new one
profile/          the browser's saved state (cookies, logins) - never commit
artifacts/        crash screenshots + HTML dumps, one per failure
logs/             one log file per task
```

The flow of every run: `run.py` opens the browser, hands your task a `page`
(a browser tab you command in Python), calls your `run()`. If it crashes,
you get a screenshot of the exact moment plus the page HTML in `artifacts/`,
a Telegram ping, and a nonzero exit code so cron knows.

## One-time setup

```bash
cd spider-base
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install firefox chromium   # downloads the browsers (~250 MB)
cp .env.example .env                  # then fill in Telegram token (optional)
```

Smoke test:

```bash
python run.py example              # scrapes a practice site, logs quotes
python run.py example_watch        # demos the watch-then-act pattern
```

Add `--visible` to either to watch the browser work (needs a machine with a
display; on a headless server just read the logs/screenshots).

## Writing a task

Copy `tasks/example_watch.py`, rename the file and the `name`, and edit three
things: the URL, the condition, the action. That file is the skeleton for
every "grab it when it appears" job. For plain data scraping copy
`tasks/example.py` instead.

The API you'll actually use, 95% of the time:

```python
self.page.goto("https://...")
self.page.click("text=Register")            # click by visible text
self.page.fill("#email", "you@x.com")       # type into a field
self.page.locator(".price").inner_text()    # read text off the page
self.page.reload()
self.watch(self.available, every=30)        # poll until available() is truthy
self.notify("bought it")                    # phone ping
```

Playwright auto-waits for elements to exist and be clickable before acting,
which is why there are no sleep() calls sprinkled everywhere.

### Browser engines

The default engine comes from `BROWSER` in .env (firefox here). A task can
pin an engine with a class attribute - do this for sites that only behave
on chrome:

```python
class MyTask(Task):
    browser = "chromium"
```

Each engine keeps its own profile under `profile/`, so logins done in one
don't exist in the other - run `login.py` once per engine per site
(`python login.py <url> --browser chromium`). When recording with codegen
on a chromium-pinned site, point it at the right profile:
`playwright codegen --user-data-dir=profile/chromium <url>`.

### Finding selectors (the only real skill involved)

A selector is the address of an element on the page ("the button that says
Register"). Two ways to get them:

1. **The super simple mega easy way, use it:** record yourself doing the task once with
   `playwright codegen` and copy the code it writes. Full walkthrough below.
2. The manual way: right-click the element in Chrome, Inspect, right-click
   the highlighted HTML, Copy > Copy selector. Prefer `text=Register` or
   IDs (`#email`) over the long generated paths - they survive site
   redesigns better.

### Recording a task with codegen, step by step

```bash
source .venv/bin/activate
playwright codegen https://the-site.com
```

What happens: **two windows open**, and this is the part everyone misses.

1. A normal browser window - you do the task in here.
2. A smaller **Playwright Inspector** window - the recorder. It often opens
   *behind* the browser or off to the side; go find it. As you click and
   type in the browser, Python code appears here line by line, live.

The Inspector toolbar has: a Record button (red dot - clicking it pauses/
resumes recording), a Target dropdown (leave it on "Python" - that matches
this project's sync style), and a copy icon that copies all generated code.

The workflow:

1. Do the task once by hand in the browser window, slowly.
2. Click the copy icon in the Inspector.
3. Stop everything: just close the browser window, or Ctrl+C in the
   terminal. Nothing is saved anywhere - the code only exists in the
   Inspector until you copy it.
4. `cp tasks/_template.py tasks/my_task.py`, then paste the recorded
   lines between the markers in that file - unchanged. Only keep the
   middle of what codegen gave you: the lines between
   `page = context.new_page()` and `context.close()`. Everything above
   and below is browser-launching boilerplate that run.py already does
   (with your saved profile - the recorded script would use a blank one).

**Two rules for sites with login:**

- codegen launches a *fresh, blank* browser by default - it does NOT use or
  update this project's `profile/`. Logging in during a plain codegen
  session does nothing for your bot. To actually store a login, use
  `python login.py <url>`.
- **Never keep recorded login lines.** If you type your password while
  recording, the generated code contains it in plain text
  (`page.fill("#password", "yourpassword")`). Delete those lines; logins
  belong in `profile/` via login.py, not in code.

The clean way to record on a logged-in site - do the login.py step first,
then record *using the saved profile* so you start already logged in and
the recording contains only the real task actions:

```bash
# default engine (firefox):
playwright codegen --browser firefox --user-data-dir=profile/firefox https://the-site.com/portal
# chromium-pinned sites:
playwright codegen --user-data-dir=profile/chromium https://the-site.com/portal
```

(Run it from the project folder. Don't run it while a task is using the
same profile at the same time - one browser per profile.)

### Sites that need login

```bash
python login.py https://the-site.com/login
```

Log in by hand in the window, press Enter in the terminal. The login lives
in `profile/` and every future run of every task reuses it.

**Caveat - short-lived sessions:** shops and most sites keep you logged in
for weeks, but ERPs, banks, and university portals expire sessions within
hours, so profile/ alone won't hold. The pattern for those: the task checks
whether the login form is present, and only then logs in itself, reading
credentials from `.env` via `os.getenv()` (gitignored, machine-local -
never hardcode credentials in a task file). Copy this into the task and
swap the selectors for the site's real ones (`import os` at the top):

```python
    def run(self):
        page = self.page
        page.goto(LOGIN_URL)
        self.login_if_needed()
        # ... recorded actions continue here ...

    def login_if_needed(self):
        # when the saved session is alive, the site skips the login form
        # entirely, so the username box won't be on the page
        if self.page.get_by_role("textbox", name="Username").count() == 0:
            self.log.info("already logged in via saved session")
            return
        user, password = os.getenv("ERP_USER"), os.getenv("ERP_PASS")
        if not (user and password):
            raise RuntimeError("session expired and ERP_USER/ERP_PASS not in .env")
        self.log.info("session expired, logging in fresh")
        self.page.get_by_role("textbox", name="Username").fill(user)
        self.page.get_by_role("textbox", name="Password").fill(password)
        self.page.get_by_role("button", name="Sign In").click()
```

### Converting codegen output into a task (don't skip)

Codegen's output is a complete standalone program. If you paste all of it
into `tasks/`, the `with sync_playwright(): ...` block at the bottom runs
the moment run.py imports the file - launching its own blank, logged-out
browser and ignoring the profile entirely. Delete all of this:

```python
def run(playwright: Playwright) -> None:              # DELETE the wrapper
    browser = playwright.chromium.launch(...)         # DELETE
    context = browser.new_context()                   # DELETE
    page = context.new_page()                         # DELETE
    ...                                               # KEEP - the actual actions
    context.close()                                   # DELETE
    browser.close()                                   # DELETE

with sync_playwright() as playwright:                 # DELETE
    run(playwright)                                   # DELETE
```

Keep only the action lines (`page.goto/click/fill/...`) and paste them
between the markers in a copy of `tasks/_template.py` - no renaming
needed, the template's `page = self.page` line makes the recorded lines
work as-is. run.py and browser.py already do everything you just deleted,
with the right profile.

Three more paste-time rules, learned the hard way:

- **Fix the indentation.** Codegen indents 4 spaces; inside `run()` you
  need 8. Select the pasted block, indent once, make every line start
  directly under `page = self.page`. A misaligned block is an
  IndentationError - the task won't even start.
- **Prune fidget clicks.** Codegen records every click, including the
  ones you made just looking around. If a click doesn't cause something
  (navigate, open, submit), delete the line.
- **When using login_if_needed(), delete the whole recorded login** -
  clicks and Sign In included, not just the fill lines. And note it goes
  *inside* the class as a method, with `self.login_if_needed()` called in
  `run()` right after the first `goto`.

## Running on the server

Scheduling is cron's job, not this code's. `crontab -e`, then e.g.:

```cron
# every morning at 07:00
0 7 * * * cd /home/you/spider-base && .venv/bin/python run.py my_task >> logs/cron.log 2>&1

# long-running watch task: start at 3am the day registration opens
0 3 15 8 * cd /home/you/spider-base && .venv/bin/python run.py course_reg >> logs/cron.log 2>&1
```

The watch() loop keeps a single process alive until the condition hits, so
"check every 30s for 6 hours" is one cron entry, not thousands.

## Harvesting whole sites: crawl4ai

This base is built for *acting* on a few known pages. When a job is instead
"pull the content of many pages" - every article on a news site, every
product in a category, a whole documentation site - don't hand-roll a loop
of selectors. Use [crawl4ai](https://github.com/unclecode/crawl4ai) as a
library inside a task. It fetches pages (Playwright underneath, same as us)
and converts each one to clean Markdown: navigation, cookie banners, and
footer noise stripped, headings and tables preserved. That output is ideal
for reading, archiving, or feeding to an LLM.

It is deliberately NOT in requirements.txt - it pulls in a lot. Install it
the day you need it:

```bash
pip install crawl4ai
crawl4ai-setup     # its own post-install step (downloads/patches browser)
```

A complete harvesting task - copy into `tasks/`, adjust URLS, run with
`python run.py harvest`:

```python
"""Harvest a list of pages into markdown files under output/."""
import asyncio
from pathlib import Path

from base_task import Task


class Harvest(Task):
    name = "harvest"
    notify_on_success = False

    URLS = [
        "https://quotes.toscrape.com/page/1/",
        "https://quotes.toscrape.com/page/2/",
    ]

    def run(self):
        # crawl4ai is async-only; this bridges it into our sync world.
        asyncio.run(self.crawl())

    async def crawl(self):
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

        out = Path("output") / self.name
        out.mkdir(parents=True, exist_ok=True)

        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun_many(
                self.URLS,
                config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
            )
        for r in results:
            if not r.success:
                self.log.warning("failed: %s", r.url)
                continue
            fname = (r.url.rstrip("/").split("/")[-1] or "index") + ".md"
            (out / fname).write_text(r.markdown.raw_markdown)
            self.log.info("saved %s (%d chars)", fname, len(r.markdown.raw_markdown))
```

Notes that matter:

- **crawl4ai brings its own browser.** The task above never touches
  `self.page`; crawl4ai launches and manages its own Chromium internally.
  Your task is just orchestrating it and handling the results - which is
  exactly what the base is for: you still get logging, crash artifacts,
  Telegram pings, and cron scheduling for free.
- **It doesn't know your logins.** By default it crawls as a stranger. For
  pages behind your login, point it at this project's profile:
  `BrowserConfig(user_data_dir="profile", use_persistent_context=True)`
  passed to `AsyncWebCrawler(config=...)` - and don't run it simultaneously
  with another task (one browser per profile).
- **Caching:** `CacheMode.BYPASS` always fetches fresh. Drop that config to
  let crawl4ai cache pages - much faster when you re-run during development.
- **Don't reach for it for single pages.** For "grab three fields off one
  page", plain `self.page.locator(...)` is less machinery. crawl4ai earns
  its install weight from ~tens of pages upward, or when you need clean
  Markdown for an LLM.
- It can also crawl a site by following links itself (BFS deep crawling,
  `max_depth` etc.) instead of you listing URLs - see its docs at
  https://docs.crawl4ai.com when you need that.

## Ground rules (from experience, not lawyers)

- Keep `watch()` intervals humane. Every 10-30s is plenty; hammering a site
  every 200ms gets your IP blocked and helps nobody.
- Only automate accounts and purchases that are yours. Some sites' terms
  prohibit bots; know that before pointing this at anything that matters.
- Test with `--visible` and a dry-run version of `act()` (log instead of
  click "Pay") before trusting a task with real money.
- If a site throws a "verify you are human" wall, stop and say so - that is
  a different problem with different tools, not something to brute-force.
