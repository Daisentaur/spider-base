"""Template for a new task. Start every task like this:

    cp tasks/_template.py tasks/my_task.py

Record your actions with codegen (see README), then paste the recorded
lines between the markers below - UNCHANGED. The `page = self.page` line
is what makes that work: codegen writes `page.goto(...)`, `page.click(...)`
etc., and here `page` already means the right thing.

From codegen's output, take only the lines between `page = context.new_page()`
and `context.close()` - NOT including those two lines themselves. Everything
above and below is browser-launching boilerplate that run.py already handles
(with your saved profile).

After pasting, fix the indentation: codegen indents 4 spaces, this file
needs 8. Select the pasted block and indent it one level (Tab in most
editors) so every line starts directly under `page = self.page`.
"""

from base_task import Task


class MyTask(Task):
    name = "my-task"  # used in logs, notifications, and artifact filenames
    # browser = "chromium"  # uncomment to pin an engine (default: BROWSER in .env)

    def run(self):
        page = self.page  # lets recorded lines paste in without edits

        # --- paste recorded codegen lines below ---
        page.goto("https://quotes.toscrape.com")
        # --- end recorded lines ---

        self.notify("did the thing")  # optional phone ping; delete if noisy
