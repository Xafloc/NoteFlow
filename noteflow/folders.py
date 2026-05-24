"""Cross-folder task and search layer.

Backport of the Go rewrite's v1.4+ feature surface:
  - SQLite-backed folder registry (~/.config/noteflow/tasks.db)
  - Periodic background sync of registered folders' notes.md
  - Global task aggregation across folders
  - Cross-folder substring search

Storage uses Python's stdlib sqlite3 module so there's no extra
dependency. The DB is treated as a cache — notes.md is always the
source of truth; the DB is rebuilt by scanning notes.md.

Task identity is preserved across toggles by hashing the task line with
the checkbox marker stripped. That way [ ]↔[x] flips don't break the
link between rows and source-of-truth notes.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import platformdirs


###############################################################################
# Constants
###############################################################################
SCHEMA = """
CREATE TABLE IF NOT EXISTS folders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT NOT NULL UNIQUE,
    last_scan   TIMESTAMP,
    active      INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_folders_active ON folders(active);

CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id       INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
    file_path       TEXT NOT NULL,
    line_number     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    completed       INTEGER NOT NULL DEFAULT 0,
    last_updated    TIMESTAMP,
    task_hash       TEXT NOT NULL,
    UNIQUE(folder_id, task_hash)
);
CREATE INDEX IF NOT EXISTS idx_tasks_folder ON tasks(folder_id);
CREATE INDEX IF NOT EXISTS idx_tasks_hash ON tasks(task_hash);
"""

SYNC_INTERVAL_SECONDS = 30

NOTE_SEPARATOR = "\n<!-- note -->\n"
CHECKBOX_RE = re.compile(r'^(\s*[-*+]?\s*)\[([xX ])\](\s+)(.*)$')
NOTE_HEADER_RE = re.compile(r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\s+-\s+(.*))?$')


def get_db_path() -> Path:
    """Return the SQLite DB path, creating its parent if needed.

    Uses the Python-specific config dir so we don't share tasks.db with
    the Go rewrite (noteflow-go) when both are installed.
    """
    config_dir = Path(platformdirs.user_config_dir("noteflow-py"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "tasks.db"


def hash_task(line: str) -> str:
    """Stable identity for a task line — strip the checkbox so toggles don't change id."""
    normalized = re.sub(r'\[[xX ]\]', '[ ]', line, count=1).strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]


def _code_regions(text: str):
    """Same logic as Note._code_regions in noteflow.py — used here to skip
    fenced/inline code when scanning. Duplicated to keep folders.py
    standalone."""
    regions = []
    fence_re = re.compile(r'(^|\n)(```|~~~)[^\n]*\n.*?\n\2(?=\n|$)', re.DOTALL)
    for m in fence_re.finditer(text):
        regions.append((m.start(), m.end()))
    inline_re = re.compile(r'(`+)[^`\n]+?\1')
    for m in inline_re.finditer(text):
        pos = m.start()
        if any(s <= pos < e for s, e in regions):
            continue
        regions.append((m.start(), m.end()))
    return regions


def _read_notes(folder_path: Path) -> str:
    notes_md = folder_path / "notes.md"
    if not notes_md.exists():
        return ""
    try:
        content = notes_md.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = notes_md.read_text(encoding='cp1252')
        except UnicodeDecodeError:
            content = notes_md.read_text(encoding='utf-8', errors='replace')
    return content.replace('\r\n', '\n').replace('\r', '\n')


###############################################################################
# FolderRegistry
###############################################################################
class FolderRegistry:
    """SQLite-backed registry of folders, plus their task cache.

    Thread-safe via a single connection lock; we use stdlib sqlite3 in
    check_same_thread=False mode and serialize writes with a Python lock,
    which is plenty for our load.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # autocommit
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # -- folder lifecycle ------------------------------------------------
    def add_folder(self, path) -> Dict:
        """Register a folder. Reactivates a previously-forgotten one."""
        resolved = str(Path(path).expanduser().resolve())
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO folders (path, active) VALUES (?, 1) "
                "ON CONFLICT(path) DO UPDATE SET active = 1",
                (resolved,),
            )
            folder_id = cur.lastrowid or self._conn.execute(
                "SELECT id FROM folders WHERE path = ?", (resolved,)
            ).fetchone()["id"]
        self.sync_folder(folder_id)
        return self.get_folder(folder_id)

    def forget_folder(self, folder_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE folders SET active = 0 WHERE id = ?", (folder_id,)
            )
            return cur.rowcount > 0

    def get_folder(self, folder_id: int) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT id, path, last_scan, active FROM folders WHERE id = ?",
            (folder_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_active(self) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT id, path, last_scan, active FROM folders WHERE active = 1 ORDER BY path"
        ).fetchall()
        return [dict(r) for r in rows]

    # -- sync ------------------------------------------------------------
    def sync_folder(self, folder_id: int) -> int:
        """Re-scan notes.md for `folder_id`, update task cache, return task count.

        Uses UPSERT keyed on (folder_id, task_hash) so row IDs stay stable
        across syncs — frontends and CLIs can hold onto task IDs and
        still target the right task after a re-scan.
        """
        folder = self.get_folder(folder_id)
        if not folder:
            return 0
        folder_path = Path(folder["path"])
        content = _read_notes(folder_path)

        tasks = self._extract_tasks(content)
        now = datetime.utcnow().isoformat()
        notes_path = str(folder_path / "notes.md")
        current_hashes = {t['task_hash'] for t in tasks}

        with self._lock:
            # Prune tasks whose hash no longer appears in notes.md.
            existing = self._conn.execute(
                "SELECT task_hash FROM tasks WHERE folder_id = ?", (folder_id,)
            ).fetchall()
            for r in existing:
                if r["task_hash"] not in current_hashes:
                    self._conn.execute(
                        "DELETE FROM tasks WHERE folder_id = ? AND task_hash = ?",
                        (folder_id, r["task_hash"]),
                    )
            # Upsert each task. Skip duplicate hashes within one folder by
            # taking the first occurrence (later sibling tasks lose).
            seen = set()
            for t in tasks:
                if t['task_hash'] in seen:
                    continue
                seen.add(t['task_hash'])
                self._conn.execute(
                    "INSERT INTO tasks "
                    "(folder_id, file_path, line_number, content, completed, last_updated, task_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(folder_id, task_hash) DO UPDATE SET "
                    "  file_path=excluded.file_path, "
                    "  line_number=excluded.line_number, "
                    "  content=excluded.content, "
                    "  completed=excluded.completed, "
                    "  last_updated=excluded.last_updated",
                    (folder_id, notes_path, t['line_number'], t['content'],
                     1 if t['completed'] else 0, now, t['task_hash']),
                )
            self._conn.execute(
                "UPDATE folders SET last_scan = ? WHERE id = ?",
                (now, folder_id),
            )
        return len(seen)

    def sync_all(self) -> int:
        total = 0
        for folder in self.list_active():
            try:
                total += self.sync_folder(folder["id"])
            except Exception as e:
                print(f"sync_folder({folder['id']}) failed: {e}")
        return total

    @staticmethod
    def _extract_tasks(content: str) -> List[Dict]:
        """Pull every checkbox task out of the notes.md content.

        Returns a list of {line_number, content, completed, task_hash,
        note_title, note_timestamp}. Line numbers are 1-based against the
        raw file content. Note headers are tracked so each task knows
        which note it belongs to.
        """
        out: List[Dict] = []
        regions = _code_regions(content)
        note_title = ""
        note_timestamp = ""
        for line_no, line in enumerate(content.splitlines(), start=1):
            offset_start = sum(len(s) + 1 for s in content.splitlines()[:line_no - 1])
            offset_end = offset_start + len(line)
            if any(s <= offset_start < e or s < offset_end <= e for s, e in regions):
                continue
            header = NOTE_HEADER_RE.match(line)
            if header:
                note_timestamp = header.group(1)
                note_title = header.group(2) or ""
                continue
            m = CHECKBOX_RE.match(line)
            if not m:
                continue
            checked = m.group(2).lower() == 'x'
            out.append({
                'line_number': line_no,
                'content': line,
                'completed': checked,
                'task_hash': hash_task(line),
                'note_title': note_title,
                'note_timestamp': note_timestamp,
            })
        return out

    # -- queries ---------------------------------------------------------
    def get_all_tasks(self, include_done: bool = False) -> List[Dict]:
        sql = (
            "SELECT t.id, t.folder_id, t.file_path, t.line_number, t.content, "
            "       t.completed, t.task_hash, f.path AS folder_path "
            "FROM tasks t JOIN folders f ON f.id = t.folder_id "
            "WHERE f.active = 1 "
        )
        if not include_done:
            sql += "AND t.completed = 0 "
        sql += "ORDER BY f.path, t.line_number"
        rows = self._conn.execute(sql).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get_task(self, task_id: int) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT t.id, t.folder_id, t.file_path, t.line_number, t.content, "
            "       t.completed, t.task_hash, f.path AS folder_path "
            "FROM tasks t JOIN folders f ON f.id = t.folder_id "
            "WHERE t.id = ?",
            (task_id,),
        ).fetchone()
        return self._row_to_task(row) if row else None

    @staticmethod
    def _row_to_task(row) -> Dict:
        stripped = re.sub(r'^[\s\-\*\+]*\[[xX ]\]\s*', '', row["content"])
        return {
            'id': row["id"],
            'folder_id': row["folder_id"],
            'folder_path': row["folder_path"],
            'file_path': row["file_path"],
            'line_number': row["line_number"],
            'content': row["content"],
            'text': stripped,
            'completed': bool(row["completed"]),
            'task_hash': row["task_hash"],
        }

    def toggle_task(self, task_id: int) -> Optional[Dict]:
        """Flip the checkbox in the source notes.md and re-sync the folder."""
        task = self.get_task(task_id)
        if not task:
            return None
        notes_md = Path(task['file_path'])
        if not notes_md.exists():
            return None
        content = _read_notes(notes_md.parent)
        lines = content.split('\n')

        # Prefer match by line number, fall back to scanning for the same content
        # in case the file shifted between sync and toggle.
        target_idx = None
        if 0 < task['line_number'] <= len(lines) and CHECKBOX_RE.match(lines[task['line_number'] - 1]):
            target_idx = task['line_number'] - 1
        else:
            for idx, line in enumerate(lines):
                if hash_task(line) == task['task_hash'] and CHECKBOX_RE.match(line):
                    target_idx = idx
                    break
        if target_idx is None:
            return None

        line = lines[target_idx]
        new_line = re.sub(
            r'\[[xX ]\]',
            '[x]' if not task['completed'] else '[ ]',
            line,
            count=1,
        )
        lines[target_idx] = new_line
        notes_md.write_text('\n'.join(lines), encoding='utf-8')

        self.sync_folder(task['folder_id'])
        return self.get_task(task_id) or {**task, 'completed': not task['completed']}

    # -- search ----------------------------------------------------------
    def search_all(self, query: str) -> List[Dict]:
        """Substring search across every active folder's notes.md.

        Returns a list of folder-grouped results:
          [{folder_id, folder_path, matches: [{note_title, snippet, count}]}]
        """
        q = (query or "").strip().lower()
        if not q:
            return []
        results = []
        for folder in self.list_active():
            content = _read_notes(Path(folder["path"]))
            if q not in content.lower():
                continue
            matches = []
            for raw in [n.strip() for n in content.split(NOTE_SEPARATOR) if n.strip()]:
                if q not in raw.lower():
                    continue
                lines = raw.split('\n', 1)
                header = lines[0].replace('## ', '')
                note_title = header
                hm = NOTE_HEADER_RE.match(lines[0])
                if hm:
                    note_title = hm.group(2) or hm.group(1)
                body = raw.lower()
                pos = body.find(q)
                snip_start = max(0, pos - 40)
                snip_end = min(len(raw), pos + len(q) + 40)
                snippet = raw[snip_start:snip_end].replace('\n', ' ')
                matches.append({
                    'note_title': note_title or '(untitled)',
                    'snippet': snippet,
                    'count': body.count(q),
                })
            if matches:
                results.append({
                    'folder_id': folder['id'],
                    'folder_path': folder['path'],
                    'matches': matches,
                })
        return results

    # -- background sync -------------------------------------------------
    def start_background_sync(self, interval: int = SYNC_INTERVAL_SECONDS):
        if self._sync_thread and self._sync_thread.is_alive():
            return
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                try:
                    self.sync_all()
                except Exception as e:
                    print(f"background sync error: {e}")
                self._stop_event.wait(interval)

        self._sync_thread = threading.Thread(target=_loop, name="noteflow-folder-sync", daemon=True)
        self._sync_thread.start()

    def stop_background_sync(self):
        self._stop_event.set()


###############################################################################
# Global Tasks HTML page
###############################################################################
GLOBAL_TASKS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NoteFlow — Global Tasks</title>
<style>
  body { font-family: monospace; background: #313437; color: #c0c0c0; padding: 20px; }
  h1 { color: #df8a3e; font-size: 1.2rem; margin-top: 0; }
  a { color: #66d9ff; }
  .folder-header {
    color: #df8a3e; margin-top: 18px; padding: 4px 8px;
    background: #26292c; cursor: pointer; border-radius: 4px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .folder-header .count { color: #888; font-size: 0.75rem; }
  .folder-header:hover { filter: brightness(1.1); }
  .task-row {
    padding: 4px 8px 4px 24px; display: flex; gap: 8px; align-items: flex-start;
    border-bottom: 1px solid #26292c;
  }
  .task-row input { margin-top: 2px; }
  .task-row.completed label { text-decoration: line-through; opacity: 0.55; }
  .empty { opacity: 0.5; font-style: italic; padding: 8px; }
  .toolbar { display: flex; gap: 8px; margin: 8px 0 16px; align-items: center; }
  .toolbar button {
    background: #26292c; color: #df8a3e; border: 1px solid #555;
    padding: 4px 10px; font-family: monospace; cursor: pointer; border-radius: 3px;
  }
  .toolbar button:hover { background: #3a3f47; }
  .toolbar input[type="text"] {
    background: #26292c; color: #c0c0c0; border: 1px solid #555;
    padding: 4px 8px; font-family: monospace; flex: 1; max-width: 400px;
  }
  .toolbar label { font-size: 0.8rem; }
  .add-folder { display: flex; gap: 8px; margin-top: 8px; }
  .add-folder input { background: #26292c; color: #c0c0c0; border: 1px solid #555;
    padding: 4px 8px; font-family: monospace; flex: 1; }
  .folder-actions { display: inline-flex; gap: 8px; font-size: 0.7rem; }
  .folder-actions a { cursor: pointer; }
  mark { background: #df8a3e; color: #000; padding: 0 1px; }
</style>
</head>
<body>
  <h1>Global Tasks <span style="opacity:0.5;font-size:0.75rem;">— across all registered folders</span></h1>
  <p><a href="/">&larr; back to current folder</a></p>

  <div class="toolbar">
    <input type="text" id="searchInput" placeholder="Search across all folders…">
    <button onclick="document.getElementById('searchInput').value=''; refresh();">Clear</button>
    <label><input type="checkbox" id="showDone"> show completed</label>
    <button onclick="syncAll()">Sync All</button>
  </div>

  <div class="add-folder">
    <input type="text" id="newFolderPath" placeholder="/path/to/folder to register">
    <button onclick="addFolder()">Add Folder</button>
  </div>

  <div id="content" style="margin-top: 16px;"></div>

<script>
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]);
}
function highlight(text, q) {
  if (!q) return escapeHtml(text);
  const escQ = q.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
  return escapeHtml(text).replace(new RegExp(escQ, 'gi'), m => '<mark>'+m+'</mark>');
}

async function loadGlobalTasks() {
  const showDone = document.getElementById('showDone').checked;
  const tasksResp = await fetch('/api/global-tasks' + (showDone ? '?include_done=1' : ''));
  const tasks = await tasksResp.json();
  const foldersResp = await fetch('/api/global-folders');
  const folders = await foldersResp.json();

  const byFolder = {};
  folders.forEach(f => { byFolder[f.id] = { folder: f, tasks: [] }; });
  tasks.forEach(t => {
    if (!byFolder[t.folder_id]) byFolder[t.folder_id] = { folder: {id:t.folder_id, path:t.folder_path}, tasks: [] };
    byFolder[t.folder_id].tasks.push(t);
  });

  const html = Object.values(byFolder).map(({folder, tasks}) => {
    const header = (
      '<div class="folder-header">' +
        '<span onclick="copyPath(' + JSON.stringify(folder.path) + ', this)" title="Click to copy folder path">' +
          escapeHtml(folder.path) + ' <span class="count">(' + tasks.length + ')</span>' +
        '</span>' +
        '<span class="folder-actions">' +
          '<a onclick="syncFolder(' + folder.id + ')">sync</a>' +
          '<a onclick="forgetFolder(' + folder.id + ')" style="color:#c76;">forget</a>' +
        '</span>' +
      '</div>'
    );
    const rows = tasks.length ? tasks.map(t => (
      '<div class="task-row ' + (t.completed ? 'completed' : '') + '">' +
        '<input type="checkbox" ' + (t.completed ? 'checked' : '') +
          ' onchange="toggleTask(' + t.id + ')">' +
        '<label>' + escapeHtml(t.text) + '</label>' +
      '</div>'
    )).join('') : '<div class="empty">No tasks.</div>';
    return header + rows;
  }).join('');

  document.getElementById('content').innerHTML = html || '<div class="empty">No folders registered yet. Add one above.</div>';
}

async function runSearch(q) {
  const resp = await fetch('/api/search/global?q=' + encodeURIComponent(q));
  const data = await resp.json();
  const html = data.results.map(g => (
    '<div class="folder-header">' +
      '<span onclick="copyPath(' + JSON.stringify(g.folder_path) + ', this)">' +
        escapeHtml(g.folder_path) + ' <span class="count">(' + g.matches.length + ' notes)</span>' +
      '</span>' +
    '</div>' +
    g.matches.map(m => (
      '<div class="task-row">' +
        '<div>' +
          '<div style="font-weight:bold;">' + highlight(m.note_title, q) +
          ' <span style="opacity:0.5;">×' + m.count + '</span></div>' +
          '<div style="opacity:0.7;font-size:0.85em;">' + highlight(m.snippet, q) + '</div>' +
        '</div>' +
      '</div>'
    )).join('')
  )).join('');
  document.getElementById('content').innerHTML = html || '<div class="empty">No matches.</div>';
}

function refresh() {
  const q = document.getElementById('searchInput').value.trim();
  if (q) runSearch(q); else loadGlobalTasks();
}

async function toggleTask(id) {
  await fetch('/api/global-tasks/' + id + '/toggle', { method: 'POST' });
  refresh();
}
async function syncFolder(id) {
  await fetch('/api/global-folders/' + id + '/sync', { method: 'POST' });
  refresh();
}
async function forgetFolder(id) {
  if (!confirm('Remove this folder from global tracking?')) return;
  await fetch('/api/global-folders/' + id + '/forget', { method: 'POST' });
  refresh();
}
async function syncAll() {
  await fetch('/api/global-sync', { method: 'POST' });
  refresh();
}
async function addFolder() {
  const input = document.getElementById('newFolderPath');
  const path = input.value.trim();
  if (!path) return;
  const resp = await fetch('/api/global-folders/add', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ path })
  });
  if (resp.ok) {
    input.value = '';
    refresh();
  } else {
    alert('Failed to add folder: ' + await resp.text());
  }
}
async function copyPath(path, el) {
  try {
    await navigator.clipboard.writeText(path);
    const orig = el.style.color;
    el.style.color = '#fff';
    setTimeout(() => { el.style.color = orig; }, 600);
  } catch (e) { console.error('copy failed', e); }
}

let _searchTimer;
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('searchInput').addEventListener('input', (e) => {
    clearTimeout(_searchTimer);
    _searchTimer = setTimeout(refresh, 200);
  });
  document.getElementById('showDone').addEventListener('change', refresh);
  refresh();
});
</script>
</body>
</html>
"""
