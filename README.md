# NoteFlow

> **FORMAT CHANGE NOTICE**: As of version 0.3.0, the note separator changed from `---` to `<!-- note -->`. If you're upgrading from an older version, please update your `notes.md` accordingly.

NoteFlow is a lightweight, Markdown-based note-taking application with task management capabilities. It runs locally, stores everything in a single `notes.md` file per folder, and stays out of your way. One Python package, no cloud, no account.

## What's new

### 0.7.6 — Performance, safety & capability

- **Faster checkbox toggles** — flipping a task no longer re-renders every note or re-runs MathJax; the active-tasks panel updates from the response.
- **Shared MarkdownIt + per-note HTML cache** — note rendering reuses a single parser and caches HTML until content changes.
- **Atomic `notes.md` saves** — write via a temp file + replace so a crash mid-save cannot truncate your notes.
- **Localhost by default** — server binds to `127.0.0.1`; use `--host 0.0.0.0` only if you intentionally want LAN access (there is no authentication).
- **Hardened uploads** — basename-only filenames, automatic collision renames (`photo-1.png`), 50 MiB size cap.
- **External edit awareness** — edits to `notes.md` from other tools (or `noteflow append`) are picked up via mtime polling while the editor is idle.
- **Richer AI context** — recent N notes, note being edited, editor selection, no-notes mode, plus a char budget so huge journals don't blow the context window.
- **Abortable search** — in-flight search requests cancel when you keep typing.
- **First unit tests** — `python -m unittest tests.test_core -v`.

### 0.7.0 — Autosave

- **Autosave** — notes are automatically saved at a configurable interval (1, 3, or 5 minutes). Works for both new and existing notes — the timer starts as soon as you type in the editor. On by default; toggle and configure in the admin panel. A brief "autosaved" indicator flashes next to the Save button after each save.

### 0.6.0 — Smart editing & cheat sheet

- **Smart Enter** — pressing Enter in the editor continues list markers (`-`, `*`, `+`, `1.`, `- [ ]`), preserves indentation, and auto-increments numbered lists. A second Enter on an empty marker clears it.
- **Cheat sheet modal** — press `?` (or `Ctrl+?` while editing) to see all keyboard shortcuts, Markdown syntax, task tokens, and sigils in one overlay.
- **Full-width search bar** — `/` opens a fixed top bar with up/down arrow navigation, Enter to cycle matches, and an "All folders" toggle for cross-folder search.
- **Keyboard hints bar** — subtle always-visible hints below the editor for `/`, `?`, and `Ctrl+Enter`.

### 0.5.0 — Image management

- **Image lightbox** — images in notes render at 50 % width; click to expand full-size.
- **Image delete** — hover an image to reveal a delete button that removes the file from disk and strips the Markdown reference from `notes.md`.
- **Uploaded files panel** — a new "files" side tab lists all uploaded assets with thumbnails, size, and in-use / orphan status for easy cleanup.

### 0.4.0 — Feature parity with noteflow-go

A major release that backports the feature surface from [noteflow-go](https://github.com/Xafloc/NoteFlow-Go):

- **AI assist slideout** — chat your notes via any OpenAI-compatible endpoint (OpenAI, Anthropic-direct, Ollama, LM Studio, LiteLLM, OpenRouter, Groq, Together, etc.). Streaming + automatic non-streaming fallback. Per-folder `ai_history.md` log.
- **Cross-folder global tasks** — register multiple folders; their tasks aggregate to a global page at `/global-tasks`. SQLite-backed with stable task IDs and a 30s background sync.
- **Planning CLI** — `noteflow tasks` (filter by priority/due/tag/project, save views, toggle by hash), `noteflow append` (write a note from stdin or args).
- **Inline task metadata** — `!p1` `!p2` `!p3` priorities, `@YYYY-MM-DD` due dates, `#tag` tags, rendered as colored chips and filterable from the CLI.
- **`+file:` snippet sigil** — `+file:path#10-25` in a note expands at save time into a fenced code block with the file's content at those lines.
- **External archiver autodetect** — if `monolith` or `obelisk` is on your PATH, NoteFlow uses it for higher-fidelity `+http://` archives; otherwise falls back to the built-in BeautifulSoup pipeline.
- **Right-edge tab UI** — four slideout panels (fonts / admin / ai / commits) replace the old hover-to-expand admin menu.
- **Per-section font scaling** — sliders for notes/tasks/links sections with live previews.
- **Local + global search** — press `/` anywhere to focus search; results jump to matching notes.
- **Git context** — branch + short SHA badge in the directory bar, plus a commits panel showing recent `git log`.
- **Code-region-aware task parsing** — checkboxes inside fenced or inline code blocks are no longer mis-parsed as real tasks.
- **CLI flags** — `--help`, `--version`, `--port`, `--host`, `--no-browser`.

## Screenshots

#### Main view — demo notes, tasks with metadata chips, right-edge tabs
![Main view](/screenshots/noteflow-py-main.png)

#### Fonts panel — live previews of per-section scaling
![Fonts panel](/screenshots/noteflow-py-fonts.png)

#### AI assist — chat your notes via any OpenAI-compatible endpoint
![AI assist](/screenshots/noteflow-py-ai.png)

#### Commits panel — recent git history for the active folder
![Commits panel](/screenshots/noteflow-py-commits.png)

#### Themes
![Themes](/screenshots/noteflow-py-theme.png)

## Features

- **📝 One big Markdown file** — all notes stream into a single `notes.md`, version-controllable with your code
- **✅ Active task tracking** — checkboxes in any note surface to a dedicated panel
- **🔖 Inline task metadata** — `!p1` priorities, `@YYYY-MM-DD` due dates, `#tag` tags, rendered as colored chips
- **🌐 Cross-folder global tasks** — register multiple project folders, see every open task in one place
- **🤖 AI assist** — chat your notes via any OpenAI-compatible endpoint; context modes include all / recent N / editing / selection / none
- **💾 Autosave** — automatic periodic save while editing (configurable interval, toggleable in admin)
- **⌨️ Smart Enter** — list markers, indentation, and numbered-list continuation while you type
- **📖 Cheat sheet** — press `?` for a quick-reference overlay of shortcuts, syntax, and sigils
- **🔍 Search** — full-width search bar with match navigation and cross-folder toggle
- **🖼️ Image management** — lightbox preview, hover-to-delete, and an uploaded-files panel with orphan detection
- **🔗 Web archiving** — prefix any URL with `+` to save a self-contained local copy
- **📎 File embed sigil** — `+file:path#10-25` embeds source code at save time
- **🚀 CLI** — `noteflow append`, `noteflow tasks` with filters / saved views / JSON output
- **💾 Zero database for notes** — your note history lives in one portable Markdown file (cross-folder task index uses SQLite for speed); atomic saves protect against mid-write crashes
- **🔒 Privacy first** — runs entirely local (binds to localhost by default); AI key never sent to the browser; no cloud or account
- **🎨 Multiple themes** — dark-orange, dark-blue, light-blue
- **🔢 Math** — MathJax inline (`$...$`) and block (`$$...$$`)
- **🖥️ Multiple instances** — run NoteFlow in any number of folders concurrently

## Installation

### pip (all platforms)

```bash
pip install noteflow
```

### Homebrew (macOS / Linux)

```bash
brew tap Xafloc/noteflow
brew install noteflow-py
```

The formula is named `noteflow-py` so it can live alongside [noteflow-go](https://github.com/Xafloc/NoteFlow-Go) (`brew install xafloc/noteflow-go/noteflow`, which installs as `noteflow-go`). Both binaries can be installed on the same machine without conflict.

### Optional: better-fidelity archiving

`monolith` produces higher-quality `+http://` archives on JS-heavy pages. If installed, NoteFlow uses it automatically; otherwise it falls back to the built-in archiver.

```bash
brew install monolith         # macOS / Linux
# or: cargo install monolith
# or: download binary from https://github.com/Y2Z/monolith/releases
```

## Quick start

```bash
# Run in the current folder
noteflow

# Or point at a specific folder
noteflow /path/to/notes

# Pin port / skip browser / expose on LAN (no auth — use carefully)
noteflow --port 8765 --no-browser
noteflow --host 0.0.0.0 --port 8765

noteflow --help
```

Your browser opens automatically at `http://127.0.0.1:8000` (or the next free port). The server binds to **localhost only** by default. Use `--no-browser` to suppress the tab, `--port 8765` to pin a port, and `--host 0.0.0.0` only if you intentionally want LAN access (there is no authentication).

## Daily use

### Taking notes

Type in the content area, optionally add a title, hit `Ctrl+Enter` (or `Cmd+Enter` on Mac) or click **Save Note**. Notes save to `notes.md` in the current folder.

### Tasks

Any Markdown checkbox becomes a tracked task:

```markdown
- [ ] Open task
- [x] Completed task
- [ ] !p1 @2026-06-15 #urgent Priority 1, due date, and tag tokens
```

The inline metadata tokens (`!p1` / `!p2` / `!p3`, `@YYYY-MM-DD`, `#tag`) render as colored chips and are filterable from the CLI. Checkboxes inside fenced code blocks (```` ``` ````) or inline backticks aren't parsed as real tasks — write task syntax in documentation without polluting your active-tasks list.

### Cross-folder global tasks

Click **global tasks →** below the active-tasks box (or visit `/global-tasks`) to see every open task across every registered folder. Add a new folder from that page; NoteFlow rescans them every 30 seconds.

### Web archiving — the `+http://` sigil

Prefix any URL with `+` and NoteFlow archives the page locally on save:

```
Saw this technique today: +https://example.com/some-article
```

The line is replaced with a markdown link to a self-contained HTML archive in `assets/sites/`. Useful for citation snapshots, reference material that might rot, and reading offline.

### Code embedding — the `+file:` sigil

```
The save flow lives at +file:noteflow/noteflow.py#883-900
```

On save, the sigil expands into a fenced code block with the file's lines 883–900 and a language hint detected from the extension. Variants:

- `+file:path` — entire file
- `+file:path#10` — just line 10
- `+file:path#10-25` — inclusive range

Path resolution is sandboxed to the project folder; `../escape` attempts and absolute paths are refused.

### AI assist

Click the **ai** tab on the right edge → **Settings**. Fill in:

- **Endpoint** — any OpenAI-compatible `/v1/chat/completions` URL, e.g.:
  - OpenAI: `https://api.openai.com/v1/chat/completions`
  - Anthropic native: `https://api.anthropic.com/v1/messages` (auto-detected)
  - Ollama local: `http://localhost:11434/v1/chat/completions`
  - LM Studio local: `http://localhost:1234/v1/chat/completions`
- **API key** — stored in `~/.config/noteflow-py/noteflow.json` (or the macOS equivalent). Never sent to the browser.
- **Model** — e.g. `gpt-4o-mini`, `claude-sonnet-4-5`, `llama3.2`.
- **Default context** — how much of `notes.md` to include by default (all notes, recent N notes, top N lines, or none).

Per-question **context** in the chat pane can further narrow to:

| Mode | What the model sees |
|------|---------------------|
| all notes | Entire `notes.md` (soft-capped by a char budget) |
| recent N notes | Newest N note blocks |
| note being edited | The note currently open in the editor |
| editor selection | Highlighted text in the note editor (or the whole buffer if nothing is selected) |
| top N lines | First N lines of the file (newest content is prepended) |
| no notes context | General knowledge only |

The AI sees *this folder's* notes as a system prompt, plus your conversation. Click **Save to history** on any answer to keep it in `ai_history.md`.

### Keyboard shortcuts

- `Ctrl+Enter` / `Cmd+Enter` — save the current note
- `Enter` — smart continuation: repeats list markers (`-`, `*`, `+`, `1.`, `- [ ]`), preserves indentation, auto-increments numbered lists
- `/` — open the full-width search bar (up/down to navigate, Enter to cycle)
- `?` — open the cheat sheet (Markdown syntax, shortcuts, sigils)
- `Esc` — close the active side panel, search bar, or cheat sheet

### CLI

```bash
noteflow append --title "from cli" "Some body text"
echo "- [ ] !p1 #release ship 0.4.0" | noteflow append

noteflow tasks                    # human-readable table of open tasks
noteflow tasks --status           # one-liner for shell prompts
noteflow tasks --priority 1       # urgent only
noteflow tasks --due today
noteflow tasks --tag release --json
noteflow tasks --toggle <hash>    # flip a task by task_hash prefix

noteflow tasks --priority 1 --save-view urgent
noteflow tasks --view urgent      # apply a saved filter
```

See `noteflow --help`, `noteflow tasks --help`, and `noteflow append --help` for the full surface.

## File structure

Per folder you point NoteFlow at:

```
your-folder/
├── notes.md            # your notes (the source of truth)
├── ai_history.md       # saved AI conversations (per-folder)
└── assets/
    ├── images/         # drag-and-dropped images
    ├── files/          # drag-and-dropped files
    └── sites/          # +http archives + sidecar .tags metadata
```

Per user (shared across all folders):

```
~/.config/noteflow-py/        # Linux; on macOS: ~/Library/Application Support/noteflow-py/
├── noteflow.json             # theme, font scales, autosave, AI config (key, endpoint, model)
├── tasks.db                  # SQLite cache for cross-folder global tasks
└── task_views.json           # saved CLI filter combinations
```

The `noteflow-py` dir name avoids collision with [noteflow-go](https://github.com/Xafloc/NoteFlow-Go) if both are installed.

## Requirements

- Python 3.9+
- Dependencies installed automatically by pip: `fastapi`, `uvicorn`, `markdown-it-py`, `mdit-py-plugins`, `python-multipart`, `pydantic`, `requests`, `beautifulsoup4`, `platformdirs`, `psutil`
- Optional: `monolith` or `obelisk` on PATH for higher-fidelity web archiving

## License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE) file for details. In short:

- You can freely use, modify, and distribute this software
- Modifications and derivative works must also be licensed under GPL-3.0
- Source code must be made available when distributing the software
- Changes must be documented

For more, see the [full license text](https://www.gnu.org/licenses/gpl-3.0.en.html).

<div align="center">
Made with ❤️ for note-taking enthusiasts
</div>
