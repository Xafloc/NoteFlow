"""Planning-layer CLI subcommands.

Mirrors the Go rewrite's `append` and `tasks` subcommands, intended as a
write/query API for AI agents and shell scripts. Both commands operate
on the same notes.md / tasks.db that the web UI uses, so anything
written here shows up in the browser immediately (and vice versa).

Inline task metadata (recognized when filtering):
  !p1 !p2 !p3      — priority (1 = high)
  @YYYY-MM-DD      — due date
  #tag             — tag
These are not yet persisted as columns; they're parsed from the task
text at query time, matching the Go version's behavior.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import platformdirs


###############################################################################
# Inline metadata parsing
###############################################################################
_PRIORITY_RE = re.compile(r'(?<!\S)!p([1-3])(?!\S)', re.IGNORECASE)
_DUE_RE = re.compile(r'(?<!\S)@(\d{4}-\d{2}-\d{2})(?!\S)')
_TAG_RE = re.compile(r'(?<!\S)#([A-Za-z][A-Za-z0-9_\-]*)')


def parse_task_meta(text: str) -> Dict:
    """Pull out priority/due/tag markers from a task text."""
    priority = None
    pm = _PRIORITY_RE.search(text)
    if pm:
        priority = int(pm.group(1))
    due = None
    dm = _DUE_RE.search(text)
    if dm:
        try:
            due = datetime.strptime(dm.group(1), "%Y-%m-%d").date()
        except ValueError:
            due = None
    tags = [m.group(1).lower() for m in _TAG_RE.finditer(text)]
    return {"priority": priority, "due": due, "tags": tags}


def _due_matches(due, spec: str) -> bool:
    """`--due today|week|overdue|YYYY-MM-DD` filter."""
    if due is None:
        return False
    today = datetime.now().date()
    s = (spec or "").lower()
    if s == "today":
        return due == today
    if s == "week":
        return today <= due <= today + timedelta(days=7)
    if s == "overdue":
        return due < today
    try:
        target = datetime.strptime(spec, "%Y-%m-%d").date()
        return due == target
    except ValueError:
        return False


###############################################################################
# Saved views
###############################################################################
def _views_path() -> Path:
    # Same Python-specific dir as the rest of the app — keeps us out of
    # noteflow-go's config if both are installed.
    p = Path(platformdirs.user_config_dir("noteflow-py")) / "task_views.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_views() -> Dict:
    fp = _views_path()
    if not fp.exists():
        return {}
    try:
        return json.loads(fp.read_text())
    except Exception:
        return {}


def _save_views(views: Dict) -> None:
    _views_path().write_text(json.dumps(views, indent=2))


###############################################################################
# append
###############################################################################
def _build_append_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="noteflow append",
        description=(
            "Append a note to the current folder's notes.md. Body can come "
            "from --body, positional args, or stdin. +http URLs are archived "
            "the same way as the web UI."
        ),
    )
    p.add_argument("--title", default="", help="Note title (optional).")
    p.add_argument("--folder", default=None,
                   help="Target folder (defaults to the current working directory).")
    p.add_argument("--body", default=None, help="Body text. Overrides positional args / stdin.")
    p.add_argument("body_words", nargs="*", help="Body text as positional words.")
    return p


def run_append(argv: List[str]) -> int:
    args = _build_append_parser().parse_args(argv)
    if args.body is not None:
        body = args.body
    elif args.body_words:
        body = " ".join(args.body_words)
    elif not sys.stdin.isatty():
        body = sys.stdin.read()
    else:
        body = ""
    body = body.strip()
    if not body:
        print("error: empty body — pass --body, positional args, or pipe via stdin", file=sys.stderr)
        return 2

    # Defer heavy imports so `noteflow tasks --help` stays snappy.
    from .noteflow import NoteManager, create_directories, validate_folder_path, APP_PORT
    from . import archiver, folders as folders_module

    target = validate_folder_path(args.folder)
    create_directories(target)
    nm = NoteManager(target)

    if "+http" in body:
        processed = asyncio.run(archiver.process_plus_links(body, target, app_port=APP_PORT))
        body = processed["markdown"]

    nm.add_note(args.title, body)
    nm.save()

    # Best-effort: refresh the global registry so the new task is visible to
    # `noteflow tasks` and the global page immediately.
    try:
        registry = folders_module.FolderRegistry()
        folder = registry.add_folder(target)
        registry.sync_folder(folder["id"])
    except Exception as e:
        print(f"warning: registry sync failed: {e}", file=sys.stderr)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    suffix = f" - {args.title}" if args.title else ""
    print(f"appended: {ts}{suffix}")
    return 0


###############################################################################
# tasks
###############################################################################
def _build_tasks_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="noteflow tasks",
        description=(
            "Query, filter, and toggle tasks across every registered folder. "
            "By default lists open tasks from all active folders as a "
            "human-readable table."
        ),
    )
    # Filters
    p.add_argument("--done", action="store_true",
                   help="Include completed tasks. Default lists only open tasks.")
    p.add_argument("--only-done", action="store_true",
                   help="Show only completed tasks.")
    p.add_argument("--due", default=None,
                   help="Filter by due date: today | week | overdue | YYYY-MM-DD.")
    p.add_argument("--priority", type=int, default=None, choices=[1, 2, 3],
                   help="Filter by priority (!p1 !p2 !p3 markers in task text).")
    p.add_argument("--tag", default=None, help="Filter by #tag (case-insensitive).")
    p.add_argument("--project", default=None,
                   help="Filter by substring match on folder path.")
    # Actions
    p.add_argument("--toggle", default=None, metavar="HASH",
                   help="Toggle a task by its task_hash (prefix is fine, must be unique).")
    p.add_argument("--save-view", default=None, metavar="NAME",
                   help="Save the current filter combination under NAME.")
    p.add_argument("--view", default=None, metavar="NAME",
                   help="Apply a saved view's filters (extra flags override view values).")
    p.add_argument("--list-views", action="store_true", help="List saved views and exit.")
    p.add_argument("--delete-view", default=None, metavar="NAME", help="Delete a saved view and exit.")
    # Output
    p.add_argument("--json", action="store_true", help="Output JSON instead of a table.")
    p.add_argument("--status", action="store_true",
                   help="Print a one-line summary (counts) instead of the task list.")
    return p


def _apply_filters(tasks: List[Dict], *, done: bool, only_done: bool,
                   due: Optional[str], priority: Optional[int],
                   tag: Optional[str], project: Optional[str]) -> List[Dict]:
    out = []
    for t in tasks:
        if only_done and not t["completed"]:
            continue
        if not done and not only_done and t["completed"]:
            continue
        meta = parse_task_meta(t["text"])
        if priority is not None and meta["priority"] != priority:
            continue
        if tag is not None and tag.lower() not in meta["tags"]:
            continue
        if due is not None and not _due_matches(meta["due"], due):
            continue
        if project is not None and project.lower() not in t["folder_path"].lower():
            continue
        # Inline meta on the result for downstream printing
        t = dict(t)
        t["priority"] = meta["priority"]
        t["due"] = meta["due"].isoformat() if meta["due"] else None
        t["tags"] = meta["tags"]
        out.append(t)
    return out


def _print_table(tasks: List[Dict]) -> None:
    if not tasks:
        print("(no matching tasks)")
        return
    # Compact table; truncate long fields rather than wrapping.
    def trunc(s, n):
        s = str(s) if s is not None else ""
        return s if len(s) <= n else s[: n - 1] + "…"
    headers = ("HASH", "P", "DUE", "FOLDER", "TASK")
    widths = (8, 1, 10, 30, 60)
    print(" ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print(" ".join("-" * w for w in widths))
    for t in tasks:
        row = (
            trunc(t["task_hash"], widths[0]),
            trunc(t["priority"] or "-", widths[1]),
            trunc(t["due"] or "-", widths[2]),
            trunc(Path(t["folder_path"]).name, widths[3]),
            trunc(t["text"], widths[4]),
        )
        marker = "x" if t["completed"] else " "
        print(f"[{marker}] " + " ".join(c.ljust(w) for c, w in zip(row, widths)))


def run_tasks(argv: List[str]) -> int:
    args = _build_tasks_parser().parse_args(argv)
    views = _load_views()

    # View management actions exit early.
    if args.list_views:
        if not views:
            print("(no saved views)")
        else:
            for name, filters in sorted(views.items()):
                print(f"{name}: {json.dumps(filters)}")
        return 0
    if args.delete_view:
        if args.delete_view in views:
            del views[args.delete_view]
            _save_views(views)
            print(f"deleted view: {args.delete_view}")
            return 0
        print(f"no such view: {args.delete_view}", file=sys.stderr)
        return 1

    # If --view is given, fold its filters in (CLI args still override).
    if args.view:
        if args.view not in views:
            print(f"no such view: {args.view}", file=sys.stderr)
            return 1
        v = views[args.view]
        for key in ("done", "only_done", "due", "priority", "tag", "project"):
            cli_val = getattr(args, key)
            if cli_val in (None, False) and key in v:
                setattr(args, key, v[key])

    from . import folders as folders_module
    registry = folders_module.FolderRegistry()

    # --toggle action takes precedence over listing.
    if args.toggle:
        all_tasks = registry.get_all_tasks(include_done=True)
        matches = [t for t in all_tasks if t["task_hash"].startswith(args.toggle.lower())]
        if not matches:
            print(f"no task matched hash prefix: {args.toggle}", file=sys.stderr)
            return 1
        if len(matches) > 1:
            print(f"hash prefix is ambiguous ({len(matches)} matches); be more specific:", file=sys.stderr)
            for t in matches:
                print(f"  {t['task_hash']}  {t['text']}", file=sys.stderr)
            return 1
        target = matches[0]
        result = registry.toggle_task(target["id"])
        if not result:
            print(f"toggle failed for {target['task_hash']}", file=sys.stderr)
            return 1
        state = "[x]" if result["completed"] else "[ ]"
        print(f"{state} {result['text']}  ({result['task_hash']})")
        return 0

    # --save-view applies the current filters as a named view, then continues.
    if args.save_view:
        filters = {
            "done": args.done,
            "only_done": args.only_done,
            "due": args.due,
            "priority": args.priority,
            "tag": args.tag,
            "project": args.project,
        }
        # Strip empty values to keep the file readable.
        filters = {k: v for k, v in filters.items() if v not in (None, False)}
        views[args.save_view] = filters
        _save_views(views)
        print(f"saved view: {args.save_view} = {json.dumps(filters)}", file=sys.stderr)

    # Sync first so we get fresh task data without waiting for the background ticker.
    registry.sync_all()

    raw = registry.get_all_tasks(include_done=args.done or args.only_done)
    filtered = _apply_filters(
        raw,
        done=args.done,
        only_done=args.only_done,
        due=args.due,
        priority=args.priority,
        tag=args.tag,
        project=args.project,
    )

    if args.status:
        open_count = sum(1 for t in filtered if not t["completed"])
        done_count = sum(1 for t in filtered if t["completed"])
        folders = len({t["folder_id"] for t in filtered})
        print(f"{len(filtered)} task(s) — {open_count} open, {done_count} done, across {folders} folder(s)")
        return 0

    if args.json:
        out = []
        for t in filtered:
            out.append({
                "task_hash": t["task_hash"],
                "id": t["id"],
                "folder_path": t["folder_path"],
                "completed": t["completed"],
                "text": t["text"],
                "priority": t["priority"],
                "due": t["due"],
                "tags": t["tags"],
            })
        print(json.dumps(out, indent=2))
        return 0

    _print_table(filtered)
    return 0


###############################################################################
# Dispatcher
###############################################################################
SUBCOMMANDS = {"append", "tasks"}


def dispatch(cmd: str, argv: List[str]) -> int:
    if cmd == "append":
        return run_append(argv)
    if cmd == "tasks":
        return run_tasks(argv)
    print(f"unknown subcommand: {cmd}", file=sys.stderr)
    return 2
