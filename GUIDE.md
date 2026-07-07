# The spider-base guide

This is the long-form companion to the README. 
This is the thing you read *while* setting up and building your first
few tasks. Read it start to finish once and you'll understand not just the
commands but why each one exists and where it messes you up. It's written in 
order of how you'll actually do things.

---

## 1. What this thing is, and the one decision behind it

You want a computer to use a website for you: log in, click, fill a form,
grab a number, buy a thing, register for a thing. There are two ways a
program can do that, and understanding the split explains every design
choice here.

**Option A: raw HTTP.** Your script pretends to be a browser and downloads
the raw page, then digs data out of the HTML. Its Fast, its light, dosen't 
need a browser. But modern sites build themselves with JavaScript after the page
loads, so you often get an empty shell, and you can't "click" anything —
you'd have to reverse-engineer the exact network request each button fires.
Great for pulling data off simple pages. Miserable and I mean miserable for
*doing things*.

**Option B: drive a real browser.** Your script launches an actual Firefox
or Chrome and puppeteers it — go here, type this, click that. Heavier and
slower, but it works on any site a human can use, because it *is* a browser.
Logins, carts, multi-step forms, JavaScript evrything just works.

Since the whole point is *acting* on sites, spider-base is built on Option B,
using **Playwright** (Microsoft's browser-automation library). Option A is
still available when a task only needs data and the site hands it over
cleanly — more on that near the end (`needs_browser = False`).

Why Playwright and not the older Selenium: it *auto-waits* for elements to
be ready before clicking, which kills the single biggest source of flaky
scraper bugs. It can save a logged-in browser profile so you log in once and
stay logged in. And it ships `codegen`, a recorder that writes your task code
for you. That last one is the reason a person with zero scraping background
can build real tasks that's the main sauce or point of this tool.

---

## 2. Setup from zero

You need Python 3.10+ and a terminal. From the project folder:

```bash
python3 -m venv .venv          # make an isolated Python environment
source .venv/bin/activate      # switch into it (do this each new terminal)
pip install -r requirements.txt
playwright install firefox chromium   # downloads the browsers, ~250 MB, once
```

That `venv` is just a private box of Python packages so this project doesn't
collide with anything else on your machine, but i'm pretty sure you know that
. The `playwright install` step downloads actual browser builds into a cache 
in your home folder (shared across projects, so you only pay for it once).

Copy the env file and open it:

```bash
cp .env.example .env
```

`.env` is where secrets and settings live. It's gitignored but you should copy
`.env.example` to `.env` and edit it to your needs as described above.

Two things worth setting up now:

**Telegram alerts (5 minutes, do it).** The entire value of an unattended
bot is that it tells you what happened. Without this you'll hear from it
when you check on it yoruself and who knows when that will be.

1. On Telegram, message `@BotFather`, send `/newbot`, follow the prompts.
   You get a bot **token** — paste it as `TELEGRAM_BOT_TOKEN` in `.env`.
2. Send any message to your new bot (so it's allowed to message you back).
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser,
   find `"chat":{"id": ...}`, and paste that number as `TELEGRAM_CHAT_ID`.

If you skip this, nothing breaks — alerts just print to the log instead. But
do it.

**Browser engine.** `BROWSER=firefox` is the default. Leave it unless you
know a site misbehaves on Firefox (some do — see section 8).

Smoke test that everything works:

```bash
python run.py example          # scrapes quotes.toscrape.com, prints quotes
```

If quotes scroll past, you're done. Add `--visible` to watch the browser do
it (needs a screen; on a headless server just read the output).

---

## 3. The mental model: what a "task" is

Everything you build is a **task**: one Python file in `tasks/`, one job.
A task is a class that inherits from `Task` and fills in a `run()` method.
That's the whole contract.

```python
from base_task import Task

class MyThing(Task):
    name = "my-thing"        # the name that shows up in logs, alerts, screenshot names

    def run(self):
        self.page.goto("https://example.com")
        # ... do the job ...
```

You run it with `python run.py my_thing` (the filename without `.py`). 
(you can also run `python run.py my_thing.py it will work if you do it that way too ;p)

Here's what happens when you do that, because knowing the flow makes
everything else easier:

1. `run.py` reads your task, sees which browser engine it wants, and opens
   that browser with your saved profile.
2. It hands your task `self.page` — a live browser tab you command in Python.
3. It calls your `run()`.
4. If `run()` finishes cleanly, you optionally get a "done" ping.
5. If `run()` **crashes**, `run.py` screenshots every open window into
   `artifacts/`, saves the page HTML next to it, sends you the screenshot on
   Telegram with the error, prints the traceback, and exits with code 1
   (which is how a scheduler knows it failed).

You never write the browser-opening, screenshotting, or alerting code. That's
the base's whole job. You write `run()`. That's the deal that keeps tasks
short.

The API you'll use for 95% of everything, so better be at least a little familiar with
it :

```python
self.page.goto("https://...")
self.page.click("text=Register")           # click the thing that says Register
self.page.fill("#email", "you@x.com")      # type into a field
self.page.locator(".price").inner_text()   # read text off the page
self.page.reload()
self.watch(self.available, every=30)       # poll until available() is truthy
self.notify("it happened")                 # ping your phone
```

---

## 4. Building your first real task: the codegen workflow

You will not write selectors by hand. You'll *record* yourself doing the task
once and let Playwright write the code. This is the single most important
workflow in the whole tool, so here it is in full.

```bash
source .venv/bin/activate
playwright codegen https://the-site.com
```

**Two windows open, and everyone misses the second one:**

1. A normal browser window — you do the task in here, by hand.
2. A smaller **Playwright Inspector** window — the recorder. It often opens
   *behind* the browser or off to the side. Find it. As you click and
   type, Python code appears in it, live, line by line.

In the Inspector toolbar: a record button (red dot, pauses/resumes), a
target-language dropdown (leave it on **Python**), and a copy icon.

The loop:

1. Do the task by hand in the browser window, slowly and deliberately.
2. Click the copy icon in the **Inspector**.
3. Stop everything — just close the browser window, or Ctrl+C the terminal.
   Nothing is saved anywhere; the code only ever existed in that Inspector
   pane until you copied it.
4. `cp tasks/_template.py tasks/my_task.py`, and paste what you copied
   between the markers in that file.

**What to keep from the paste.** Codegen gives you a complete standalone
program. You want only the middle — the action lines. It looks like this:

```python
def run(playwright: Playwright) -> None:      # DELETE this wrapper
    browser = playwright.chromium.launch(...)  # DELETE
    context = browser.new_context()            # DELETE
    page = context.new_page()                  # DELETE
    page.goto("https://...")                   # KEEP everything from here
    page.click("text=Login")                   # KEEP
    context.close()                            # DELETE this and below
with sync_playwright() as playwright:          # DELETE
    run(playwright)                            # DELETE
```

Keep the `page.goto` / `page.click` / `page.fill` lines. Throw away the
launcher scaffolding at the top and bottom — `run.py` already does all of
that, with your real profile. The template has a line `page = self.page` at
the top precisely so the recorded lines (which say `page.something`) paste in
and work unchanged.

**Three paste-time fcuk-ups that will get you at least once:**

- **Indentation.** Codegen indents 4 spaces; inside `run()` you need 8.
  Select the pasted block and indent it one level. A misaligned block is an
  `IndentationError` and the task won't even start.
- **Prune the fidget clicks.** Codegen records *every* click, including ones
  you made just looking around. If a line didn't cause something to happen
  (navigate, open, submit), delete it.
- **Never keep recorded password lines.** If you typed a password while
  recording, it's sitting in the code as plain text
  (`page.fill("#password", "Hunt3rxHunt3rfanboy")`). Delete those. Logins are handled a
  better way.......in the next to next section.

---

## 5. Selectors: the one real skill

A selector is the address of a thing on the page. `text=Register` means "the
element that says Register". `#email` means "the element with id email".
`.price` means "elements with class price". Codegen writes these for you, but
you'll sometimes tweak them, and there's one rule that matters more than all
the others:

**If a selector contains a long blob of hex or random numbers, it's session
garbage, not an address.** Some sites generate a fresh random id every time
you log in — something like
`iframe[name="8DEF612E3BDC1AC69CD3875DA76511DB"]`. Codegen faithfully records
the one from your session, and it works exactly once, then breaks forever
because next login has a different id. This is *the* reason a recorded task
mysteriously stops working. When you see one of these, replace it with
something stable: match by role and label (`get_by_role("button",
name="Download")`), or search structurally ("the iframe inside this popup")
rather than by the random name.

Rule of thumb for durability: prefer `text=` and roles and ids you can *read
and understand*. Distrust anything that looks like a cat walked out of the
keyboard(with caps on).

---

## 6. Logins: two mechanisms, know which you're using

Sites keep you logged in with a session, stored as cookies. spider-base has
two ways to handle that, for two kinds of site.

**Mechanism 1 — the saved profile (much preferred).** Run:

```bash
python login.py https://the-site.com/login
```

A visible browser opens. Log in by hand, then press Enter in the terminal.
Your session is now saved in `profile/`, and every future run of every task —
headless, scheduled, whatever starts already logged in. Your password never
touches any code. For most sites (shops, Google, anything with "remember me")
this is all you ever need.

Important: the `profile/` is the *bot's* browser, completely separate from
your daily browser. Nothing needs importing or exporting. It's its own little
world living in the project folder.

**Mechanism 2 — credentials in `.env` (for sites that expire fast).** Banks,
university ERPs, and similar log you out within hours or even every session
, so the saved profile goes stale between runs. For those, the task logs 
*itself* in when it notices the login form is present, reading credentials from `.env`:

```python
# in .env (gitignored):
SITE_USER=you
SITE_PASS=secret
```

```python
def run(self):
    page = self.page
    page.goto(LOGIN_URL)
    self.login_if_needed()
    # ... rest of the task ...

def login_if_needed(self):
    import os
    # if the saved session is alive, the login box won't be on the page
    if self.page.get_by_role("textbox", name="Username").count() == 0:
        self.log.info("already logged in")
        return
    self.page.get_by_role("textbox", name="Username").fill(os.getenv("SITE_USER"))
    self.page.get_by_role("textbox", name="Password").fill(os.getenv("SITE_PASS"))
    self.page.get_by_role("button", name="Sign In").click()
```

Two subtleties too  look out for (i beg you this bugged me for so long):

- **Detect login state by something that's present, not absent.** The example
  above checks for the username box. But some sites show a *different*
  interstitial when your session is stale (a "cookies required" dead-end, an
  SSO redirect). Those pages *also* lack a username box, so "no username box =
  logged in" walks you straight into a wall. Check for the specific thing you
  expect, and handle the interstitials you actually hit. You'll discover them
  by running and reading the crash screenshot.(use claude to understand if you're 
  being lazy)
- **SSO / MFA.** If login redirects through Microsoft/Google and asks for a
  phone approval, the task can't tap your phone for you. The pattern is: log
  in, then poll for up to a couple of minutes for the login to complete,
  letting you approve on your phone once. After that one approval the session
  is saved and future runs are hands-free — until it expires again, at which
  point you get a failure ping and re-run it once by hand.

---

## 7. The watch pattern: acting the moment something is available

This is the heart of auto-register, auto-buy, restock-alert, seat-sniping —
anything that means "wait until X, then act". The base gives you one helper:

```python
def run(self):
    self.page.goto(URL)
    self.watch(self.available, every=30, max_wait=3600)  # poll up to an hour
    self.act()

def available(self):
    self.page.reload()
    return self.page.locator("text=Enroll").count() > 0   # truthy = stop

def act(self):
    self.page.click("text=Enroll")
    self.notify("enrolled")
```

`watch(check, every, max_wait)` calls your `check` function every `every`
seconds until it returns something truthy, then returns that value. If
`max_wait` passes first, it raises a clean timeout (which becomes a failure
ping, dosen't just sit silently). `check` returning a truthy *value* (not just True)
is useful — you can return the element you found and use it in `act()`.

Keep `every` humane: 10–30 seconds is plenty. Polling a site every 200ms gets
your IP blocked and helps no one lol.

---

## 8. Browser engines

The default engine is `BROWSER` in `.env` (Firefox). Some sites only behave
correctly on Chrome — you'll know because things silently don't render or
popups stay blank. Pin such a task to Chromium with one line:

```python
class MyTask(Task):
    browser = "chromium"
```

Each engine keeps its **own** profile (`profile/firefox`, `profile/chromium`)
because cookies aren't portable between them. So you log in once *per engine*
per site. If you pin a task to chromium, do its `login.py` with
`--browser chromium`, and record its codegen against `profile/chromium`:

```bash
python login.py https://site.com --browser chromium
playwright codegen --user-data-dir=profile/chromium https://site.com
```

A real miss from this project: when running **headless**, plain Chromium
uses a stripped-down "headless shell" build that mishandles some popup and
JavaScript flows — pages that work when you watch them stay blank when
unattended. The base already forces the full Chromium build to avoid this, so
you don't have to think about it, but that's *why* the "works when I watch it,
fails on schedule" class of bug mostly can't happen here.

---

## 9. When things break: reading a failure

You will hit failures constantly, especially while building. This is normal,
expected and the base is built around it. When a task crashes:

- **Your phone** gets the crash screenshot with the error as the caption.
  Look at the picture first — it shows exactly what the bot saw at the moment
  it died. Nine times out of ten the answer is right there: a login wall you
  didn't expect, a cookie banner covering the button, an error page.
- **`artifacts/`** has that screenshot plus the full page HTML, timestamped.
  Every open window is captured, so a task that dies inside a popup is still
  debuggable.
- **`logs/<task>.log`** has the traceback and every `self.log.info(...)` line
  you left, so you can see how far it got.
- **Exit code 1**, so cron/systemd know it failed.

The workflow for a stuck task is always the same: run it, read the
screenshot, adjust one thing, run again. Do not try to reason out what the
page looks like — *look* at what the bot saw. Sprinkle `self.log.info(...)`
lines liberally while building.

There's a `crash_demo` task in `tasks/` that fails on purpose — run it once
to see the whole alert pipeline light up, so the real thing is familiar.

Two page-behavior worth knowing up front, because they look like
bugs but aren't:

- **A page that redirects when you go straight to its URL.** Some apps only
  let you reach a page by clicking through their own menu; a direct `goto` of
  the deep URL bounces you elsewhere. Fix: navigate the way a human does,
  clicking the menu links, rather than jumping to the URL.
- **A popup that never "finishes loading".** Some sites open a popup as a
  blank shell and push content into it later, so the normal "page loaded"
  signal never fires and your wait times out. Fix: don't wait for "loaded" —
  poll for the actual element you need to appear (that's what `watch` is for).

---

## 10. HTTP-only tasks (skipping the browser)

Not everything needs a browser. If a site hands you clean data over a plain
web request — many have a JSON endpoint feeding their page — driving a whole
browser is wasteful. Mark the task `needs_browser = False` and it runs with
no browser at all, just `requests`:

```python
import requests
from base_task import Task

class Prices(Task):
    name = "prices"
    needs_browser = False        # no self.page, no browser launched

    def run(self):
        data = requests.get("https://api.site.com/items.json", timeout=20).json()
        ...
```

Rule of thumb: **scraping is the tool of last resort.** If a site offers RSS,
an API, or a JSON endpoint, use that — it's faster, lighter, and less likely
to break. Reach for the browser only when the site gives you no other door.
The `bounty_watch` task is a worked example of the HTTP-only pattern.

---

## 11. Scheduling: making it run without you

The code doesn't schedule itself — that's `cron`'s job, and keeping it out of
the code keeps things simple. Edit your crontab with `crontab -e` and add a
line like:

```cron
# every day at 07:57
57 7 * * * cd ~/dev/spider-base && .venv/bin/python run.py attendance >> logs/cron.log 2>&1
```

The five fields are: minute, hour, day-of-month, month, day-of-week. The
`>> logs/cron.log 2>&1` tacks all output onto a log file so you can see what
happened.

Two cron gotchas that catch everyone:

- **Cron doesn't wake a sleeping machine.** A laptop that's closed at 7:57
  won't run the job. This is exactly why unattended tasks belong on an
  always-on machine (a home server, a Pi, a cheap VPS) — see the next section.
- **Cron runs with a bare environment.** Always `cd` into the project and use
  the venv's Python by path (`.venv/bin/python`), as above. The task itself
  loads `.env` by absolute path, so credentials and tokens work fine, but the
  `cd` and the explicit Python path are what make it run at all.

A watch task (section 7) that polls for six hours is *one* cron entry that
starts once and stays alive — not one that fires thousands of times. Start it
a few minutes before the thing you're waiting for.

---

## 12. Deploying to an always-on machine

For anything scheduled or long-watching, you want it on a machine that never
sleeps. The move is: copy the project over, rebuild the environment there
(you can't copy the `.venv` — it has machine-specific paths), and run.

Assuming you can SSH to the box (set up key-based SSH once so you're not
typing passwords — `ssh-copy-id yourserver`), copy everything except the venv
and regenerated folders:

```bash
rsync -az --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
      --exclude 'artifacts' --exclude 'logs' \
      ~/dev/spider-base/  yourserver:dev/spider-base/
```

That `rsync` carries the code *and* your `.env` and your logged-in `profile/`,
so the server starts already authenticated. Then on the server, once:

```bash
cd ~/dev/spider-base
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install firefox chromium
.venv/bin/python run.py example       # smoke test, headless
```

Then add your cron entries there instead of on the laptop. To push code
updates later, re-run the same `rsync` (it only sends what changed) — but
know that it'll carry your latest `.env` and profile too, which is usually
what you want.

---

## 13. Harvesting whole sites (crawl4ai)

spider-base is built for *acting* on a few known pages. When the job is
instead "pull the content of many pages" — every article, every product, a
whole docs site — don't hand-roll a loop of selectors. Install
[crawl4ai](https://github.com/unclecode/crawl4ai) and call it inside a task;
it fetches pages and converts each to clean Markdown (nav and footer noise
stripped), which is ideal for reading, archiving, or feeding to an LLM.

It's a heavy dependency, so it's deliberately *not* in `requirements.txt` —
install it the day you actually need it (`pip install crawl4ai` then
`crawl4ai-setup`). The README has a complete worked `Harvest` task to copy.
Reach for it from roughly tens of pages upward; for three fields off one
page, plain `self.page.locator(...)` is less machinery.

---

## 14. The short version (pin this)

- One task = one file in `tasks/`, a `Task` subclass with a `run()`.
- Don't write selectors — record with `playwright codegen`, keep the middle,
  fix the indentation, delete password lines.
- Long hex/number in a selector = session garbage, replace with role/text.
- Log in once with `login.py` for normal sites; use `.env` credentials +
  `login_if_needed()` for sites that expire sessions fast.
- `watch(check, every=30)` is how you act-the-moment-something-happens.
- When it breaks, **look at the screenshot** in `artifacts/` or on your
  phone. Don't guess.
- No API/RSS available and the site needs a real browser? That's when you
  scrape. Otherwise `needs_browser = False` + `requests`.
- Schedule with cron on an always-on machine; `cd` in and use
  `.venv/bin/python`.
- Keep poll intervals humane and only automate accounts and purchases that
  are yours.

Build a task, break it a few times, read the screenshots. After two or three
you'll stop needing this guide which is very yippie if you ask me.
