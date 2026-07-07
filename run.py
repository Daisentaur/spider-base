"""Entry point. Runs one task by name:

    python run.py example              # headless (or per HEADLESS in .env)
    python run.py example --visible    # watch the browser do its thing

on failure it saves a full-page screenshot + the raw HTML into artifacts/
so you can see exactly what the bot saw, then notifies you and exits 1
(so cron/systemd can tell it failed).
"""

import argparse
import contextlib
import datetime as dt
import importlib
import logging
import sys
import traceback

import config
import notify
from base_task import Task
from browser import open_browser


def find_task_class(module_name: str):
    try:
        module = importlib.import_module(f"tasks.{module_name}")
    except ModuleNotFoundError as e:
        if e.name != f"tasks.{module_name}":
            raise  # the task file itself has a broken import - show it
        available = sorted(
            p.stem for p in (config.ROOT / "tasks").glob("*.py")
            if not p.stem.startswith("_")
        )
        sys.exit(f"no task named {module_name!r} - available: {', '.join(available)}")
    for obj in vars(module).values():
        if isinstance(obj, type) and issubclass(obj, Task) and obj is not Task:
            return obj
    sys.exit(f"no Task subclass found in tasks/{module_name}.py")


def save_crash_artifacts(page, name: str):
    # screenshot every open window, not just the main one - tasks that
    # die inside a popup are undebuggable otherwise
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    saved = []
    for i, p in enumerate(page.context.pages):
        base = config.ARTIFACTS_DIR / f"{name}-{stamp}-win{i}"
        try:
            p.screenshot(path=f"{base}.png", full_page=True)
            base.with_suffix(".html").write_text(p.content())
            saved.append(f"{base}.png")
        except Exception:
            continue  # a window may already be dead; artifacts are best-effort
    return saved[0] if saved else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="task in tasks/, e.g. 'example'")
    parser.add_argument(
        "--visible", action="store_true", help="show the browser window"
    )
    args = parser.parse_args()
    # accept "foo", "foo.py", and "tasks/foo.py" - people type all three
    task_name = args.task.removeprefix("tasks/").removesuffix(".py")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.LOGS_DIR / f"{task_name}.log"),
        ],
    )

    task_cls = find_task_class(task_name)

    # HTTP-only tasks (needs_browser = False) skip launching a browser
    browser_cm = (
        open_browser(visible=args.visible, engine=task_cls.browser)
        if task_cls.needs_browser
        else contextlib.nullcontext(None)
    )
    with browser_cm as page:
        task = task_cls(page)
        try:
            task.run()
        except Exception as e:
            shot = save_crash_artifacts(page, task.name) if page else None
            if task.notify_on_failure:
                msg = f"[{task.name}] FAILED: {e!r}"
                if shot:
                    notify.send_photo(shot, caption=msg)
                else:
                    notify.send(msg)
            traceback.print_exc()
            sys.exit(1)
        if task.notify_on_success:
            notify.send(f"[{task.name}] done")


if __name__ == "__main__":
    main()
